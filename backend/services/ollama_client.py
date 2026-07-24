import requests
from fastapi import HTTPException

def chat_with_ollama(
        messages:list[dict[str,str]],
        base_url: str,
        model: str,
) -> str:
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                },
            },
            timeout=180,
        )
        response.raise_for_status()

        answer = response.json()["message"]["content"].strip()

        if not answer:
            raise HTTPException(
                status_code=502,
                detail="Ollama returned an empty response. Please try again.",
            )

        return answer

    except HTTPException:
        raise
    except (requests.RequestException, KeyError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is unavailable: {error}",
        )
    