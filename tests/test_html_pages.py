"""Structural, accessibility and asset checks for the static project pages."""

from __future__ import annotations

import collections
from pathlib import Path
from urllib.parse import urlparse

import html5lib
import pytest
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES = sorted(REPO_ROOT.glob("*.html"))
PAGE_IDS = [page.name for page in PAGES]

# Assets that are referenced by a page but are not committed to the repository.
# Each entry is a (page name, asset path) pair. Remove an entry once the file is
# added; test_known_missing_assets_are_still_referenced guards against stale
# entries.
KNOWN_MISSING_ASSETS = {
    ("Fraud_Detection.html", "confusion_matrices.png"),
    ("Fraud_Detection.html", "model_performance.png"),
    ("Fraud_Detection.html", "operational_impact.png"),
    ("Fraud_Detection.html", "threshold_tuning.png"),
}


def _soup(page: Path) -> BeautifulSoup:
    return BeautifulSoup(page.read_text(encoding="utf-8"), "html5lib")


def _referenced_paths(soup: BeautifulSoup) -> list[str]:
    refs = [element["src"] for element in soup.select("[src]")]
    refs += [
        element["href"]
        for element in soup.select("link[href], a[href]")
        if element["href"]
    ]
    return refs


def _is_local(reference: str) -> bool:
    parsed = urlparse(reference)
    return not parsed.scheme and not parsed.netloc and not reference.startswith("#")


def test_pages_exist():
    assert PAGES, "no HTML pages found in the repository root"


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS)
def test_page_is_valid_html5(page: Path):
    parser = html5lib.HTMLParser(strict=True)
    parser.parse(page.read_bytes())
    assert parser.errors == [], f"{page.name}: {parser.errors}"


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS)
def test_page_has_required_head_metadata(page: Path):
    soup = _soup(page)
    assert soup.html is not None and soup.html.get("lang"), "missing <html lang>"
    assert soup.title is not None and soup.title.get_text(strip=True), "missing <title>"
    assert soup.find("meta", charset=True) is not None, "missing <meta charset>"
    assert soup.find("meta", attrs={"name": "viewport"}) is not None, "missing viewport"


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS)
def test_page_starts_with_doctype(page: Path):
    head = page.read_text(encoding="utf-8").lstrip()
    assert head[:15].lower().startswith("<!doctype html"), "missing HTML5 doctype"


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS)
def test_page_has_exactly_one_h1(page: Path):
    headings = [h.get_text(strip=True) for h in _soup(page).find_all("h1")]
    assert len(headings) == 1, f"expected 1 <h1>, found {headings}"


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS)
def test_images_have_non_empty_alt_text(page: Path):
    missing = [
        image.get("src", "<no src>")
        for image in _soup(page).find_all("img")
        if not (image.get("alt") or "").strip()
    ]
    assert missing == [], f"images without alt text: {missing}"


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS)
def test_element_ids_are_unique(page: Path):
    counts = collections.Counter(
        element["id"] for element in _soup(page).select("[id]")
    )
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    assert duplicates == [], f"duplicate ids: {duplicates}"


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS)
def test_internal_anchors_resolve(page: Path):
    soup = _soup(page)
    targets = {element["id"] for element in soup.select("[id]")}
    targets |= {element["name"] for element in soup.select("a[name]")}
    broken = [
        href
        for href in (a["href"] for a in soup.select('a[href^="#"]'))
        if href != "#" and href[1:] not in targets
    ]
    assert broken == [], f"anchors pointing at missing targets: {broken}"


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS)
def test_local_assets_exist(page: Path):
    broken = [
        reference
        for reference in _referenced_paths(_soup(page))
        if _is_local(reference)
        and not (page.parent / urlparse(reference).path).exists()
        and (page.name, reference) not in KNOWN_MISSING_ASSETS
    ]
    assert broken == [], f"references to files that do not exist: {broken}"


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS)
def test_external_references_use_https(page: Path):
    insecure = [
        reference
        for reference in _referenced_paths(_soup(page))
        if urlparse(reference).scheme == "http"
    ]
    assert insecure == [], f"insecure http references: {insecure}"


def test_known_missing_assets_are_still_referenced():
    """Keep KNOWN_MISSING_ASSETS from going stale."""
    stale = []
    for page_name, reference in sorted(KNOWN_MISSING_ASSETS):
        page = REPO_ROOT / page_name
        if not page.exists():
            stale.append((page_name, reference, "page removed"))
            continue
        if reference not in _referenced_paths(_soup(page)):
            stale.append((page_name, reference, "no longer referenced"))
        elif (page.parent / reference).exists():
            stale.append((page_name, reference, "file now committed"))
    assert stale == [], f"remove these KNOWN_MISSING_ASSETS entries: {stale}"
