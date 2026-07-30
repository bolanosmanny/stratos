from .sec_filings import get_company_from_ticker, sec_get_json

def get_company_filing_events(
        ticker: str,
        headers: dict[str, str],
        limit: int = 12,
) -> list[dict]:
    company = get_company_from_ticker(ticker, headers)

    submissions = sec_get_json(
        f"https://data.sec.gov/submissions/CIK{company['cik']}.json",
        headers,
    )

    filings = submissions["filings"]["recent"]
    cik_without_zeros = str(int(company["cik"]))
    events = []

    for index, form in enumerate(filings["form"]):
        items = filings.get("items",[""] * len(filings["form"]))[
            index
        ] or ""

        if form == "10-K":
            title = "Annual Report Filed"
            detail = "Form 10-K"

        elif form == "10-Q":
            title = "Quarterly Report Filed"
            detail = "Form 10-Q"

        elif form == "8-K" and "2.02" in items:
            title = "Earnings Release Filed"
            detail = "Form 8-K · Results of Operations"

        else:
            continue

        accession_number = filings["accessionNumber"][index]
        accession_without_dashes = accession_number.replace("-", "")
        primary_document = filings["primaryDocument"][index]

        events.append(
            {
                "date": filings["filingDate"][index],
                "title": title,
                "detail": detail,
                "source_url": ( 
                    "https://www.sec.gov/Archives/edgar/data/"
                    f"{cik_without_zeros}/"
                    f"{accession_without_dashes}/"
                    f"{primary_document}"
                ),
            }
        )

    return events[:limit]