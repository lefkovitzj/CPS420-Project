from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest

from banner_scraper import BannerError, _collect_sections, _pages_by_crn
from catalog import SectionRecord


def page(offset, total, crns, **changes):
    # Field names and paging values follow Dayton Banner's searchResults response.
    rows = [
        {
            "term": "202680",
            "courseReferenceNumber": crn,
            "subject": "CPS",
            "courseNumber": "420",
            "courseTitle": "Systems &amp; Design",
            **changes,
        }
        for crn in crns
    ]
    return {"success": True, "totalCount": total, "pageOffset": offset, "data": rows}


def test_collects_partial_last_page_and_keeps_distinct_section_crns():
    pages = [page(0, 3, ["20001", "20002"]), page(2, 3, ["20003"])]
    assert _collect_sections("202680", pages) == [
        SectionRecord("202680", crn, "CPS", "420", "Systems & Design")
        for crn in ["20001", "20002", "20003"]
    ]


def test_pages_use_the_same_search_and_crn_order_from_offset_zero():
    search_url = ("https://banner.example/ssb/searchResults/searchResults?txt_term=202680"
                  "&uniqueSessionId=test-session&pageOffset=0&pageMaxSize=10"
                  "&sortColumn=subject,courseNumber,sequenceNumber&sortDirection=asc")
    crns = [str(number) for number in range(20000, 20052)]
    request = Mock()
    request.get.side_effect = [
        Mock(ok=True, json=Mock(return_value=page(0, 52, crns[:50]))),
        Mock(ok=True, json=Mock(return_value=page(50, 52, crns[50:]))),
    ]
    records = _collect_sections("202680", _pages_by_crn(request, search_url))
    assert [record.crn for record in records] == crns
    for call, offset in zip(request.get.call_args_list, ["0", "50"], strict=True):
        assert parse_qs(urlsplit(call.args[0]).query) == {
            "txt_term": ["202680"], "uniqueSessionId": ["test-session"],
            "pageOffset": [offset], "pageMaxSize": ["50"],
            "sortColumn": ["courseReferenceNumber"], "sortDirection": ["asc"],
        }


def test_spring_import_reports_where_a_crn_was_repeated():
    # Captured at offset 0 under Banner's default sort and 350 under CRN sort.
    # Two one-row pages reproduce that overlap when the orders are mixed.
    fields = dict(term="202710", subject="AEE", courseNumber="509", courseTitle="Experimental Aerodynamics")
    pages = [page(0, 2, ["36083"], **fields), page(1, 2, ["36083"], **fields)]
    with pytest.raises(BannerError, match=r"term 202710 repeated CRN 36083 at offset 1 .*offset 0"):
        _collect_sections("202710", pages)


def test_spring_import_reports_the_expected_and_returned_terms():
    # Change only the returned term on this captured WGS 310 section.
    wrong_term = page(0, 1, ["37019"], term="202706", subject="WGS",
                      courseNumber="310", courseTitle="Feminist Theory and Methodology")
    with pytest.raises(BannerError, match=r"term 202706 for CRN 37019 at offset 0.*expected 202710"):
        _collect_sections("202710", [wrong_term])


@pytest.mark.parametrize("pages", [
    [page(0, 2, ["20001"])],                                   # truncated scrape
    [page(0, 51, ["20001"]), page(50, 51, ["20051"])],           # short non-final page
    [page(0, 2, ["20001"]), page(0, 2, ["20002"])],             # stale page
    [page(0, 2, ["20001"]), page(1, 3, ["20002", "20003"])],    # term changed mid-run
    [page(0, 1, ["20001"], subject="")],                        # schema drift
    [dict(page(0, 1, ["20001"]), sectionsFetchedCount=2)],       # capped result set
    [page(0, 0, [])],                                           # empty result
])
def test_incomplete_or_inconsistent_results_fail_as_a_whole(pages):
    with pytest.raises(BannerError):
        _collect_sections("202680", pages)
