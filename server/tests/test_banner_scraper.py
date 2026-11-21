import pytest

from banner_scraper import BannerError, _collect_sections
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


@pytest.mark.parametrize("pages", [
    [page(0, 2, ["20001"])],                                   # truncated scrape
    [page(0, 2, ["20001"]), page(1, 2, ["20001"])],             # repeated section
    [page(0, 2, ["20001"]), page(0, 2, ["20002"])],             # stale page
    [page(0, 2, ["20001"]), page(1, 3, ["20002", "20003"])],    # term changed mid-run
    [page(0, 1, ["20001"], term="202710")],                     # wrong term
    [page(0, 1, ["20001"], subject="")],                        # schema drift
    [dict(page(0, 1, ["20001"]), sectionsFetchedCount=2)],       # capped result set
    [page(0, 0, [])],                                           # empty result
])
def test_incomplete_or_inconsistent_results_fail_as_a_whole(pages):
    with pytest.raises(BannerError):
        _collect_sections("202680", pages)
