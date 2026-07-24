import re 

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException

def sec_get_json(url: str, headers: dict[str, str]) -> dict:
    response = requests.get(url, headers = headers, timeout = 30)
    response.raise_for_status()
    return response.json()

def get_company_from_ticker(
        ticker: str,
        headers: dict[str, str],
) -> dict:
    companies = sec_get_json(
        "https://www.sec.gov/files/company_tickers.json",
        headers,
    )

    for company in companies.values():
        if company["ticker"].upper() == ticker.upper():
            return {
                "ticker": company["ticker"].upper(),
                "name": company["title"],
                "cik": str(company["cik_str"]).zfill(10),

            }

    raise HTTPException(
        status_code=404,
        detail=f"No SEC company record found for {ticker.upper()}.",
)

def get_latest_10k(company: dict, headers: dict[str, str]) -> dict:
    submissions = sec_get_json(
        f"https://data.sec.gov/submissions/CIK{company['cik']}.json",
        headers,
    )
    recent_filings = submissions["filings"]["recent"]

    for index, form in enumerate(recent_filings["form"]):
        if form == "10-K":
            accession_number = recent_filings["accessionNumber"][index]
            primary_document = recent_filings["primaryDocument"][index]
            filing_date = recent_filings["filingDate"][index]
            cik_without_zeros = str(int(company["cik"]))  # Remove leading zeros from CIK
            accession_without_dashes = accession_number.replace("-", "")

            return { 
                "accession_number": accession_number,
                "filing_date": filing_date,
                "source_url": (
                    "https://www.sec.gov/Archives/edgar/data/"
                    f"{cik_without_zeros}/{accession_without_dashes}/"
                    f"{primary_document}"
                ),
            }
        
    raise HTTPException(
        status_code=404,
        detail=f"No 10-K filing found for {company['ticker']}.",
    )

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

    if not starts:
        return None

    start = starts[-1].start()
    end = re.search(end_pattern, text[start:], re.IGNORECASE)

    if not end:
        return None

    section = text[start : start + end.start()].strip()

    return section if len(section) > 500 else None

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
            "start_pattern": r"item\s+1a\.?\s+risk factors",
            "end_pattern": r"item\s+1b\.?"
        },
        {
            "section": "Management's Discussion and Analysis",
            "start_pattern": r"item\s+7(?:\.|\s)",
            "end_pattern": r"item\s+7a\.?|item\s+8\.?"
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

    if not sections:
        raise HTTPException(
            status_code=422,
            detail="Could not extract supported sections from this 10-K.",
        )

    return company, filing, sections