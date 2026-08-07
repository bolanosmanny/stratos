import requests

from fastapi import HTTPException


def check_fmp_response(response: requests.Response) -> None:
    if response.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="Market-data API limit reached. Please try again later.",
        )

    response.raise_for_status()