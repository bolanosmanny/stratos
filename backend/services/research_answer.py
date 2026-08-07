from supabase import Client

from .ollama_client import chat_with_ollama
from .retrieval import retrieve_relevant_chunks

def answer_research_question(
        ticker: str,
        question: str,
        supabase: Client,
        ollama_base_url: str,
        ollama_model: str,
) -> dict:
    matches = retrieve_relevant_chunks(
        ticker,
        question,
        supabase,
    )

    if not matches:
        return { 
            "answer": (
                f"Sparky could not find indexed SEC filing material for "
                f"{ticker.upper()} yet."
            ),
            "citations": [],
        }

    source_context = "\n\n".join(
        (
            f"[{index}] {match['filing_type']} · {match['section']} "
            f"filed {match['filing_date']}\n"
            f"{match['content']}"
        )
        for index, match in enumerate(matches, start=1)
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are Sparky, a financial research assistant. "
                "Answer only from the provided SEC filing excerpts. "
                "Do not use outside knowledge, make predictions, or give investment advice. "
                "State dates, fiscal periods, and numbers only when they appear explicitly in an excerpt; never infer them. "
                "Do not volunteer a fiscal year-end date unless the user specifically asks for it. "
                "If the user asks about a year, repeat only that year and do not infer its ending date. "
                "Keep the answer concise. Every factual sentence and every bullet point must end with one or more matching source labels, such as [1] or [2]. "
                "Never provide an uncited factual claim."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Company ticker: {ticker.upper()}\n"
                f"Question: {question}\n\n"
                f"SEC filing excerpts:\n{source_context}"
            ),
        },
    ]

    answer = chat_with_ollama(
        messages,
        ollama_base_url,
        ollama_model,
    )

    citations = [
        {
            "label": index,
            "filing_type": match["filing_type"],
            "section": match["section"],
            "filing_date": match["filing_date"],
            "source_url": match["source_url"],
            "excerpt": (
                match["content"][:420].strip()
                + ("..." if len(match["content"]) > 420 else "")
            )
        }
        for index, match in enumerate(matches, start=1)
    ]

    return { 
        "answer": answer,
        "citations": citations,
    }
