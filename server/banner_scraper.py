"""Import public Dayton Banner sections using the Course-Scheduler term/search flow.

Adapted from github.com/singhp24-png/Course-Scheduler (main.py, 1dc2a91).
"""

import json
import re
from collections.abc import Iterable, Iterator
from html import unescape
from itertools import count
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import APIRequestContext, APIResponse, Page, Response, sync_playwright

from catalog import SectionRecord

BASE_URL = "https://banner.udayton.edu/StudentRegistrationSsb/ssb"
TERM_PICKER = f"{BASE_URL}/term/termSelection?mode=search"


class BannerError(RuntimeError):
    """A public Banner request failed or its results could not be verified."""


def list_banner_terms() -> list[dict[str, str]]:
    """Read the same public choices displayed in Banner's term picker."""
    try:
        with urlopen(f"{BASE_URL}/classSearch/getTerms?offset=1&max=100", timeout=15) as response:
            choices = json.load(response)
    except (OSError, ValueError) as exc:
        raise BannerError("Could not load terms from Banner.") from exc
    if not isinstance(choices, list) or not choices:
        raise BannerError("Banner returned no selectable terms.")
    terms = []
    for choice in choices:
        if (not isinstance(choice, dict) or not isinstance(choice.get("code"), str)
                or not re.fullmatch(r"[0-9]{6}", choice["code"])
                or not isinstance(choice.get("description"), str) or not choice["description"].strip()):
            raise BannerError("Banner returned an invalid term.")
        terms.append({"code": choice["code"], "description": choice["description"]})
    return terms


def _json_response(response: Response | APIResponse) -> object:
    if not response.ok:
        raise BannerError(f"Banner returned HTTP {response.status}.")
    try:
        return response.json()
    except ValueError as exc:
        raise BannerError("Banner returned an unreadable response.") from exc


def _result_pages(page: Page, term_code: str) -> Iterator[object]:
    page.goto(TERM_PICKER, wait_until="domcontentloaded")
    page.locator("#term-search-combobox .select2-chosen").click()

    def is_term_lookup(response: Response) -> bool:
        url = urlsplit(response.url)
        return (url.path.endswith("/classSearch/getTerms")
                and parse_qs(url.query).get("searchTerm") == [term_code])

    with page.expect_response(is_term_lookup) as lookup:
        page.locator(".select2-input:visible").fill(term_code)
    choices = _json_response(lookup.value)
    if not isinstance(choices, list):
        raise BannerError("Banner returned an invalid term lookup.")
    choice = next(
        (item for item in choices if isinstance(item, dict) and item.get("code") == term_code), None
    )
    if not choice or not choice.get("description"):
        raise BannerError("The selected term is no longer offered by Banner.")
    page.locator(".select2-results").get_by_text(choice["description"], exact=True).click()
    if page.locator("#txt_term").input_value() != term_code:
        raise BannerError("Banner did not select the requested term.")
    page.locator("#term-go").click()

    def is_search_result(response: Response) -> bool:
        return urlsplit(response.url).path.endswith("/searchResults/searchResults")

    with page.expect_response(is_search_result) as result:
        page.locator("#search-go").click()
    # The first search establishes the Banner session. CRN is unique within a
    # term, so restart at offset zero with that ordering for every collected page.
    _json_response(result.value)
    yield from _pages_by_crn(page.request, result.value.url)


def _pages_by_crn(request: APIRequestContext, search_url: str) -> Iterator[object]:
    url = urlsplit(search_url)
    query = parse_qs(url.query, keep_blank_values=True)
    page_size = 50  # Largest page size offered by Banner's results table.
    query["pageMaxSize"] = [str(page_size)]
    query["sortColumn"] = ["courseReferenceNumber"]
    query["sortDirection"] = ["asc"]
    for offset in count(0, page_size):
        query["pageOffset"] = [str(offset)]
        response = request.get(url._replace(query=urlencode(query, doseq=True)).geturl())
        try:
            payload = _json_response(response)
        finally:
            response.dispose()
        yield payload


def _collect_sections(term_code: str, pages: Iterable[object]) -> list[SectionRecord]:
    records = []
    first_offset_by_crn = {}
    expected_total = None
    for page in pages:
        if not isinstance(page, dict) or page.get("success") is not True:
            raise BannerError("Banner did not complete the class search.")
        total = page.get("totalCount")
        rows = page.get("data")
        if type(total) is not int or total < 1 or not isinstance(rows, list) or not rows:
            raise BannerError("Banner returned an empty or invalid result page.")
        if page.get("sectionsFetchedCount", total) != total:
            raise BannerError("Banner reported an incomplete result set.")
        if expected_total is None:
            expected_total = total
        if total != expected_total or page.get("pageOffset") != len(records) or len(records) + len(rows) > total:
            raise BannerError("Banner results changed or a page was skipped during the import.")

        offset = page["pageOffset"]
        for row in rows:
            keys = ("term", "courseReferenceNumber", "subject", "courseNumber", "courseTitle")
            if not isinstance(row, dict) or any(
                not isinstance(row.get(key), str) or not row[key].strip() for key in keys
            ):
                raise BannerError("Banner returned a section with missing course information.")
            crn = row["courseReferenceNumber"].strip()
            if row["term"] != term_code:
                raise BannerError(
                    f"Banner returned term {row['term']} for CRN {crn} at offset {offset}, expected {term_code}."
                )
            if crn in first_offset_by_crn:
                raise BannerError(
                    f"Banner term {term_code} repeated CRN {crn} at offset {offset} "
                    f"(first seen at offset {first_offset_by_crn[crn]})."
                )
            first_offset_by_crn[crn] = offset
            records.append(
                SectionRecord(term_code, crn, row["subject"], row["courseNumber"], unescape(row["courseTitle"]))
            )
        if len(records) == total:
            return records
    raise BannerError("Banner stopped returning pages before the import was complete.")


def scrape_banner(term_code: str) -> list[SectionRecord]:
    """Return a complete snapshot or raise; never publish partial results."""
    if not re.fullmatch(r"[0-9]{6}", term_code):
        raise BannerError("A Banner term code must contain six digits.")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.set_default_timeout(30_000)
                return _collect_sections(term_code, _result_pages(page, term_code))
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise BannerError("Could not finish loading Banner. Try the import again.") from exc
