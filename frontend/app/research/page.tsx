"use client"

import { FormEvent, useState } from "react";
import Link from "next/link";
import Image from "next/image";

const SUGGESTED_QUESTIONS = [
    {
        ticker: "AAPL",
        question: "Summarize Apple's latest earnings report.",
    },
    {
        ticker: "NVDA",
        question: "What risks does Nvidia mention in it's latest filing",
    },
    {
        ticker: "MSFT",
        question: "What were Microsoft's main revenue drivers",
    },
    {
        ticker: "TSLA",
        question: "what major risks should an investor research",
    },
];

export default function ResearchPage() {
    const [ticker, setTicker] = useState("AAPL");
    const [question, setQuestion] = useState("");
    const [submittedQuestion, setSubmittedQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [researchLoading, setResearchLoading] = useState(false);
    const [researchError, setResearchError] = useState("");

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (!ticker.trim() || !question.trim()) return;

        setResearchLoading(true);
        setResearchError("");
        setAnswer("");
        setSubmittedQuestion("");

        try { 
            const response = await fetch("http://localhost:8000/research", {
                method: "POST",
                headers: {
                    "Content-Type" : "application/json",
                },
                body: JSON.stringify({
                    ticker: ticker.trim(),
                    question: question.trim(),
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Sparky could not process that request.");  
            }

            setSubmittedQuestion(data.question);
            setAnswer(data.answer);
        } catch (error) {
            setResearchError(
                error instanceof Error
                ? error.message
                : "Unable to reach Sparky right now."
            );
        } finally {
            setResearchLoading(false);
        }
    };

    return ( 
        <main
            className = "min-h-screen"
            style = {{
                backgroundColor: "#0B1120",
                color: "#EDEBE3",
                fontFamily: "Inter, sans-serif",
            }}
        >
            <nav
                className = "flex items-center gap-6 px-6 py-4"
                style = {{
                    borderBottom: "1px solid #1E2A3D",
                    backgroundColor: "#0E1726",
                }}
            >
                <Link
                    href="/dashboard"
                    className = "text-sm font-semibold"
                    style = {{
                        color: "#EDEBE3",
                        fontFamily: "'IBM Plex Mono', monospace",
                    }}
                >
                    STRATOS
                </Link> 

                <Link
                    href="/research"
                    className = "text-sm"
                    style = {{ color: "#C9963C"}}
                >
                    AI Research
                </Link>
            </nav>

            <section className = "max-w-5xl mx-auto px-6 py-12">
                
                <div className = "flex items-start gap-5">
                    <div
                        className = "flex h-20 w-20 shrink-0 items-center justify-center"
                        style = {{
                            backgroundColor: "#0E1726",
                            border: "1px solid #C9963C",
                        }}
                    >
                        <Image
                            src="/cat.webp"
                            alt="Sparky the research cat"
                            width={72}
                            height={72}
                            loading = "eager"
                            className = "object-contain"
                            style = {{ imageRendering: "pixelated" }}
                        />
                    </div>

                    <div>
                        <p
                            className = "text-xs uppercase mb-2"
                            style = {{
                                letterSpacing: "0.15em",
                                color: "#C9963C",
                                fontFamily: "'IBM Plex Mono', monospace",
                            }}
                        >
                            Sparky · AI Research Cat
                        </p>

                        <h1 className = "text-3xl font-semibold">
                            Ask better investment research questions using Sparky.
                        </h1>

                        <p
                            className = "mt-4 max-w-2xl text-base leading-7"
                            style = {{ color: "#B8BFCC" }}
                        >
                            Sparky searches company SEC filings, earnings material, and financial
                            context, then answers with citations so you can verify the source.
                        </p>
                    </div>     
                </div>

                <form
                    onSubmit = {handleSubmit}
                    className = "mt-10 p-6"
                    style = {{
                        backgroundColor: "#0E1726",
                        border: "1px solid #1E2A3D",
                    }}
                >
                    <div className = "grid gap-4 md:grid-cols-[140px_minmax(0,1fr)]">
                        <div>
                            <label
                                htmlFor = "ticker"
                                className = "block text-xs uppercase mb-2"
                                style = {{
                                    color: "#8A93A6",
                                    letterSpacing: "0.1em",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            >
                                Ticker
                            </label> 

                            <input
                                id = "ticker"
                                value = {ticker}
                                onChange = {(event) =>
                                    setTicker(event.target.value.toUpperCase())
                                }
                                placeholder = "AAPL"
                                maxLength = {10}
                                className = "w-full px-4 py-4 text-sm uppercase focus:outline-none"
                                style = {{
                                    backgroundColor: "#0B1120",
                                    border: "1px solid #1E2A3D",
                                    color: "#EDEBE3",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            />
                        </div>

                        <div>
                            <label
                                htmlFor = "question"
                                className = "block text-xs uppercase mb-2"
                                style = {{
                                    color: "#8A93A6",
                                    letterSpacing: "0.1em",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            >
                                Research Question
                            </label> 

                            <input
                                id="question"
                                value={question}
                                onChange = {(event) => setQuestion(event.target.value)}
                                placeholder = "What risks does this company mention?"
                                className = "w-full px-4 py-3 text-sm focus:outline-none"
                                style = {{
                                    backgroundColor: "#0B1120",
                                    border: "1px solid #1E2A3D",
                                    color: "#EDEBE3",
                                }}
                            />    
                        </div>
                    </div>

                    <button
                        type = "submit"
                        disabled = {researchLoading}
                        className = "mt-5 px-5 py-3 text-sm font:medium transition-opacity hover:opacity-90 disabled:opacity-60"
                        style = {{ 
                            backgroundColor: "#C9963C",
                            color: "#0B1120",
                        }}
                    >
                        {researchLoading
                            ? "Sparky is researching..."
                            : `Research ${ticker || "Company"}→`}
                    </button>    
                </form>

                {researchError && (
                    <p className = "mt-4 text-sm" style = {{ color: "#B5675A" }}>
                        {researchError}
                    </p>
                )}

                <div className = "mt-10 grid gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
                    <section>
                        <p
                            className = "text-xs uppercase mb-4"
                            style = {{
                                letterSpacing: "0.15em",
                                color: "#8A93A6",
                                fontFamily: "'IBM Plex Mono', monospace",
                            }}
                        >
                            Suggested Questions
                        </p>

                        <div className = "grid gap-3">
                            {SUGGESTED_QUESTIONS.map((suggestion) => (
                                <button
                                    key = {suggestion.question}
                                    onClick = {() => {
                                        setTicker(suggestion.ticker);
                                        setQuestion(suggestion.question);
                                    }}
                                    className = "w-full p-4 text-left transition-opacity hover:opacity-80"
                                    style = {{
                                        backgroundColor: "#0E1726",
                                        border: "1px solid #1E2A3D",
                                    }}
                                >
                                    <span
                                        className = "text-xs"
                                        style = {{
                                            color: "#C9963C",
                                            fontFamily: "'IBM Plex Mono', monospace",
                                        }}
                                    >
                                        {suggestion.ticker}
                                    </span>
                                    <p className = "mt-2 text-sm"> {suggestion.question}</p>
                                </button>
                            ))}
                        </div>    
                    </section>

                    <aside
                        className = "h-fit p-5"
                        style = {{
                            backgroundColor: "#0E1726",
                            border: "1px solid #1E2A3D",
                        }}
                    >
                        <p
                            className = "text-xs uppercase"
                            style = {{
                                letterSpacing: "0.15em",
                                color: "#8A93A6",
                                fontFamily: "'IBM Plex Mono', monospace",
                            }}
                        >
                            Source Coverage
                        </p>

                        <div className = "mt-5 space-y-4">
                            {[
                                ["SEC Filings", "10-K and 10-Q reports"],
                                ["Earnings", "Calls and company results"],
                                ["Citations", "Verifiable source excerpts"],
                            ].map(([label, detail]) => (
                                <div 
                                    key={label}
                                    className = "pb-4"
                                    style = {{ borderBottom: "1px solid #1E2A3D" }}
                                >
                                    <p className = "text-sm">{label}</p>
                                    <p className = "mt-1 text-xs" style = {{ color: "#8A93A6" }}>
                                        {detail}
                                    </p>    
                                </div>
                            ))}
                        </div>
                    </aside>
                </div>

                {submittedQuestion && (
                    <section
                        className = "mt-10 p-6"
                        style = {{
                            backgroundColor: "#0E1726",
                            border: "1px solid #1E2A3D",
                        }}
                    >
                        <p
                            className = "text-xs uppercase"
                            style = {{
                                letterSpacing: "0.15em",
                                color: "#8A93A6",
                                fontFamily: "'IBM Plex Mono', monospace",
                            }}
                        >
                            {ticker} Research Request
                        </p>

                        <p className = "mt-3 text-lg">{submittedQuestion}</p>

                        <p 
                            className = "mt-5 text-sm leading-6"
                            style = {{ color: "#B8BFCC"}}
                        >
                            {answer}
                        </p>
                    </section>
                )}
            </section>
        </main>    
    );
}