import re 

import requests
from fastapi import HTTPException

from .sec_filings import ( 
    chunk_text,
    filing_html_to_text,
    get_company_from_ticker,
    get_latest_filing,
    sec_get_json,
)

def get_latest_earnings_release_sections(
        ticker: str,
        headers: dict[str, str],
) -> tuple[dict, dict, list[dict]]:
    company = get_company_from_ticker(ticker, headers)

    filing = get_latest_filing(
        company,
        headers,
        "8-K",
        required_item="2.02",
    )

    cik_without_zeros = str(int(company["cik"]))
    accession_without_dashes = filing["accession_number"].replace("-", "")

    archive_url = ( 
        "https://www.sec.gov/Archives/edgar/data/"
        f"{cik_without_zeros}/{accession_without_dashes}"
    )

    index_data = sec_get_json(
        f"{archive_url}/index.json",
        headers,
    )

    files = index_data["directory"]["item"]

    exhibit_name = next(
        (
        file["name"]
        for file in files
        if re.search(r"ex[-_]?99", file["name"], re.IGNORECASE)
        and file["name"].endswith((".htm", ".html"))
    ),
    None,
)

    source_url = ( 
        f"{archive_url}/{exhibit_name}"
        if exhibit_name
        else filing["source_url"]
    )

    response = requests.get(
        source_url,
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()

    content = filing_html_to_text(response.text)

    if len(content) < 500:
        raise HTTPException(
            status_code=422,
            detail="Could not extract earnings release from this 8-K.",
        )

    filing["source_url"] = source_url

    return ( 
        company,
        filing,
        [
            {
                "section": "Earnings Release",
                "chunks": chunk_text(content),
            }
        ],
    )