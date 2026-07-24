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
                f"Spary could not find indexed SEC filing material for "
                f"{ticker.upper()} yet."
            ),
            "citations": [],
        }

    source_context = "\n\n".join(
        (
            f"[{index}] {match['filing_type']}"
            f"filed {match['filing_date']}\n"
            f"{match['content']}"
        )
        for index, match in enumerate(matches, start=1)
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are Sparky, a financial research assistant." 
                "With over 10 years of experience." 
                "Answer only from the provided SEC filing excerpts." "Do not use outside knowledge." 
                "If the excerpts are insufficient, say so."
                "Keep the answer concise and cite very factual claim using"
                "the matching source labels, such as [1] or [2]."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Compan ticker: {ticker.upper()}\n"
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
            "filing_date": match["filing_date"],
            "source_url": match["source_url"],
        }
        for index, match in enumerate(matches, start=1)
    ]

    return { 
        "answer": answer,
        "citations": citations,
    }
