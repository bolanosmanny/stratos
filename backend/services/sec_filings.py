import re

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException


SEC_COMPANY_OVERRIDES = {
    "XOM": {
        "ticker": "XOM",
        "name": "EXXON MOBIL CORP",
        "cik": "0000034088",
    },
}


def sec_get_json(url: str, headers: dict[str, str]) -> dict:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def get_company_from_ticker(
        ticker: str,
        headers: dict[str, str],
) -> dict:
    ticker_upper = ticker.upper()

    if ticker_upper in SEC_COMPANY_OVERRIDES:
        return SEC_COMPANY_OVERRIDES[ticker_upper]

    companies = sec_get_json(
        "https://www.sec.gov/files/company_tickers.json",
        headers,
    )

    for company in companies.values():
        if company["ticker"].upper() == ticker_upper:
            return {
                "ticker": company["ticker"].upper(),
                "name": company["title"],
                "cik": str(company["cik_str"]).zfill(10),
            }

    raise HTTPException(
        status_code=404,
        detail=f"No SEC company record found for {ticker_upper}.",
    )


def get_latest_10k(company: dict, headers: dict[str, str]) -> dict:
    submissions = sec_get_json(
        f"https://data.sec.gov/submissions/CIK{company['cik']}.json",
        headers,
    )

    filing_sets = [submissions["filings"]["recent"]]

    for filing_file in submissions["filings"].get("files", []):
        historical_filings = sec_get_json(
            f"https://data.sec.gov/submissions/{filing_file['name']}",
            headers,
        )
        filing_sets.append(historical_filings)

    original_10k_candidates = []
    amendment_candidates = []

    for filings in filing_sets:
        for index, form in enumerate(filings["form"]):
            if not form.startswith("10-K"):
                continue

            candidate = {
                "accession_number": filings["accessionNumber"][index],
                "filing_date": filings["filingDate"][index],
                "primary_document": filings["primaryDocument"][index],
            }

            if form == "10-K":
                original_10k_candidates.append(candidate)
            else:
                amendment_candidates.append(candidate)

    candidates = original_10k_candidates or amendment_candidates

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No 10-K filing found for {company['ticker']}.",
        )

    latest = max(candidates, key=lambda filing: filing["filing_date"])

    cik_without_zeros = str(int(company["cik"]))
    accession_without_dashes = latest["accession_number"].replace("-", "")

    return {
        "accession_number": latest["accession_number"],
        "filing_date": latest["filing_date"],
        "source_url": (
            "https://www.sec.gov/Archives/edgar/data/"
            f"{cik_without_zeros}/{accession_without_dashes}/"
            f"{latest['primary_document']}"
        ),
    }


def filing_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def extract_section(
        text: str,
        start_pattern: str,
        end_pattern: str,
) -> str | None:
    starts = list(re.finditer(start_pattern, text, re.IGNORECASE))
    candidates = []

    for start_match in starts:
        start = start_match.start()
        end = re.search(end_pattern, text[start:], re.IGNORECASE)

        if not end:
            continue

        section = text[start : start + end.start()].strip()

        if len(section) > 500:
            candidates.append(section)

    return max(candidates, key=len) if candidates else None


def chunk_text(
        text: str,
        chunk_size: int = 1400,
        overlap: int = 200,
) -> list[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def get_latest_10k_sections(
        ticker: str,
        headers: dict[str, str],
) -> tuple[dict, dict, list[dict]]:
    company = get_company_from_ticker(ticker, headers)
    filing = get_latest_10k(company, headers)

    response = requests.get(
        filing["source_url"],
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()

    text = filing_html_to_text(response.text)

    section_definitions = [
        {
            "section": "Risk Factors",
            "start_pattern": r"item\s*1a\b[^\w]{0,20}risk\s+factors",
            "end_pattern": r"item\s*1b\b",
        },
        {
            "section": "Management's Discussion and Analysis",
            "start_pattern": (
                r"item\s*7\b[^\w]{0,20}"
                r"management[’']?s\s+discussion\s+(?:and|&)\s+analysis"
            ),
            "end_pattern": (
                r"item\s*7a\b|"
                r"item\s*8\b[^\w]{0,20}financial\s+statements"
            ),
        },
    ]

    sections = []

    for definition in section_definitions:
        content = extract_section(
            text,
            definition["start_pattern"],
            definition["end_pattern"],
        )

        if content:
            sections.append(
                {
                    "section": definition["section"],
                    "chunks": chunk_text(content),
                }
            )

    if not sections and ticker.upper() == "INTC":
        intel_section_definitions = [
            {
                "section": "Risk Factors",
                "start_pattern": (
                    r"risk\s+factors\s+"
                    r"the\s+following\s+summarizes"
                ),
                "end_pattern": r"\bcybersecurity\b",
            },
            {
                "section": "Management's Discussion and Analysis",
                "start_pattern": (
                    r"management[’']?s\s+discussion\s+"
                    r"(?:and|&)\s+analysis\s+overview"
                ),
                "end_pattern": (
                    r"quantitative\s+and\s+qualitative\s+"
                    r"disclosures\s+about\s+market\s+risk"
                ),
            },
        ]

        for definition in intel_section_definitions:
            content = extract_section(
                text,
                definition["start_pattern"],
                definition["end_pattern"],
            )

            if content:
                sections.append(
                    {
                        "section": definition["section"],
                        "chunks": chunk_text(content),
                    }
                )

    fallback_section_definitions = [
        {
            "section": "Risk Factors",
            "start_pattern": r"\brisk\s+factors\b",
            "end_pattern": (
                r"\bunresolved\s+staff\s+comments\b|"
                r"\bcybersecurity\b|"
                r"\bitem\s*1b\b|"
                r"\bitem\s*1c\b"
            ),
        },
        {
            "section": "Management's Discussion and Analysis",
            "start_pattern": (
                r"\bmanagement[’']?s\s+discussion\s+"
                r"(?:and|&)\s+analysis\b"
            ),
            "end_pattern": (
                r"\bquantitative\s+and\s+qualitative\s+"
                r"disclosures\s+about\s+market\s+risk\b|"
                r"\bmarket\s+risk\b|"
                r"\bitem\s*7a\b|"
                r"\bitem\s*8\b"
            ),
        },
    ]

    indexed_section_names = {
        section_data["section"]
        for section_data in sections
    }

    for definition in fallback_section_definitions:
        if definition["section"] in indexed_section_names:
            continue

        content = extract_section(
            text,
            definition["start_pattern"],
            definition["end_pattern"],
        )

        if content:
            sections.append(
                {
                    "section": definition["section"],
                    "chunks": chunk_text(content),
                }
            )
            indexed_section_names.add(definition["section"])

    if not sections:
        raise HTTPException(
            status_code=422,
            detail="Could not extract supported sections from this 10-K.",
        )

    return company, filing, sections