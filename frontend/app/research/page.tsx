"use client"

import { FormEvent, useEffect, useState } from "react";
import Image from "next/image";
import { supabase } from "@/lib/supabaseClient";
import SiteNav from "@/components/SiteNav";

type Citation = { 
    label: number;
    filing_type: string;
    filing_date: string;
    source_url: string;
    section: string;
    excerpt: string;
};

type ResearchHistoryEntry = { 
    id: number;
    ticker: string;
    question: string;
    answer: string;
    citations: Citation[];
    created_at: string;
};

function formatAnswer(text: string) {
    return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
        const isBold = part.startsWith("**") && part.endsWith("**");

        if (isBold) {
            return (
                <strong key = {index}>
                    {part.slice(2, -2)}
                </strong>
            );
        }

        return part;
    });
}

const SUGGESTED_QUESTIONS = [
    {
        ticker: "AAPL",
        question: "Summarize Apple's latest earnings report.",
    },
    {
        ticker: "NVDA",
        question: "What risks does Nvidia mention in its latest filing",
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
    const [citations, setCitations] = useState<Citation[]>([]);
    const [researchLoading, setResearchLoading] = useState(false);
    const [researchError, setResearchError] = useState("");
    
    const [researchHistory, setResearchHistory] = useState<ResearchHistoryEntry[]>([]);
    const [historyLoading, setHistoryLoading] = useState(true);

    useEffect(() => { 
        let isActive = true;

        const loadResearchHistory = async () => { 
            const { data: userData } = await supabase.auth.getUser();

            if (!userData.user) { 
                if (isActive) setHistoryLoading(false);
                return;
            }

            const { data } = await supabase
                .from("research_history")
                .select(
                    "id, ticker, question, answer, citations, created_at"
                )
                .eq("user_id", userData.user.id)
                .order("created_at", { ascending: false })
                .limit(5);

            if (isActive) { 
                setResearchHistory(
                    (data ?? []) as unknown as ResearchHistoryEntry[]
                );
                setHistoryLoading(false);
            }
        };

        loadResearchHistory();

        return () => { 
            isActive = false;
        };
    }, []);

    const saveResearchHistory = async ( 
        researchTicker: string,
        researchQuestion: string,
        researchAnswer: string,
        researchCitations: Citation[],
    ) => { 
        const { data: userData } = await supabase.auth.getUser();

        if (!userData.user) return;

        const { data: savedEntry } = await supabase
            .from("research_history")
            .insert({
                user_id: userData.user.id,
                ticker: researchTicker,
                question: researchQuestion,
                answer: researchAnswer,
                citations: researchCitations,
            })
            .select(
                "id, ticker, question, answer, citations, created_at"
            ).single();

        if (savedEntry) { 
            setResearchHistory((curent) => [
                savedEntry as unknown as ResearchHistoryEntry,
                ...curent
            ].slice(0,5));
        }

    }

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (!ticker.trim() || !question.trim()) return;

        setResearchLoading(true);
        setResearchError("");
        setAnswer("");
        setCitations([]);
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
            setCitations(data.citations ?? []);
            await saveResearchHistory(
                data.ticker,
                data.question,
                data.answer,
                data.citations ?? [],
            )

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
            
            <SiteNav />

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
                            Sparky searches SEC annual reports, quarterly filings, and official earnings
                            releases, then answers with citations so you can verify the source.
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
                                ["Earnings", "Official 8-K earnings releases"],
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

                        <div
                            className = "mt-6 pt-5"
                            style = {{ borderTop: "1px solid #1E2A3D" }}
                        >
                            <p
                                className = "text-xs uppercase"
                                style = {{
                                    letterSpacing: "0.15em",
                                    color: "#8A93A6",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            >
                                Research History
                            </p>

                            {historyLoading && ( 
                                <p
                                    className = "mt-4 text-sm"
                                    style = {{ color: "#8A93A6" }}
                                >
                                    Loading history...
                                </p>
                            )}

                            {!historyLoading && researchHistory.length === 0 && (
                                <p
                                    className = "mt-4 text-sm"
                                    style = {{ color: "#8A93A6" }}
                                >
                                    Your saved Sparky research history will appear here.
                                </p>
                            )}

                            <div className = "mt-4 space-y-3">
                                {researchHistory.map((entry) => ( 
                                    <button
                                        key = {entry.id}
                                        type = "button"
                                        onClick = {() => { 
                                            setTicker(entry.ticker);
                                            setQuestion(entry.question);
                                            setSubmittedQuestion(entry.question);
                                            setAnswer(entry.answer);
                                            setCitations(entry.citations ?? []);
                                        }}
                                        className = "w-full text-left transition-opacity hover:opacity-80"
                                        style = {{
                                            color: "#C9963C",
                                            fontFamily: "'IBM Plex Mono', monospace",
                                        }}
                                    >
                                        <p
                                            className = "text-sm"
                                            style = {{ 
                                                color: "#C9963C",
                                                fontFamily: "'IBM Plex Mono', monospace",
                                            }}
                                        >
                                            {entry.ticker} ·{" "}
                                            {new Date(
                                                entry.created_at
                                            ).toLocaleDateString("en-US", { 
                                                month: "short",
                                                day: "numeric",
                                            })}
                                        </p>

                                        <p
                                            className = "mt-1 text-sm leading-5"
                                            style = {{ color: "#EDEBE3" }}
                                        >
                                            {entry.question}
                                        </p>
                                    </button>
                                ))}
                            </div>
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
                            {ticker} Research Question
                        </p>

                        <p className = "mt-3 text-lg">{submittedQuestion}</p>

                        <p 
                            className = "mt-5 whitespace-pre-line text-sm leading-6"
                            style = {{ color: "#B8BFCC"}}
                        >
                            {formatAnswer(answer)}
                        </p>

                        {citations.length > 0 && (
                            <div
                                className = "mt-6 pt-5"
                                style = {{ borderTop: "1px solid #1E2A3D" }}
                            >
                                <p
                                    className = "text-xs uppercase"
                                    style = {{ 
                                        letterSpacing: "0.15em",
                                        color: "#8A93A6",
                                        fontFamily: "'IBM Plex Mono', monospace",
                                    }}
                                >
                                    SEC Sources
                                </p>

                                <div className = "mt-3 space-y-2">
                                    {citations.map((citation) => (
                                        <details
                                            key = {citation.label}
                                            className = "py-3"
                                            style = {{ borderBottom: "1px solid #1E2A3D" }}
                                        >
                                            <summary
                                                className = "cursor-pointer text-sm"
                                                style = {{ color: "#C9963C" }}
                                            >
                                                [{citation.label}] {citation.filing_type} · {citation.section}
                                            </summary>

                                            <p
                                                className = "mt-3 text-xs leading-5"
                                                style = {{ color: "#B8BFCC" }}
                                            >
                                                {citation.excerpt}
                                            </p>

                                            <a
                                                href = {citation.source_url}
                                                target = "_blank"
                                                rel = "noreferrer"
                                                className = "mt-3 inline-block text-xs hover:opacity-80"
                                                style = {{ color: "#C9963C" }}
                                            >
                                                Open SEC filing · filed {citation.filing_date} ↗
                                            </a>
                                        </details>
                                    ))}
                                </div>
                            </div>
                        )}
                    </section>
                )}
            </section>
        </main>    
    );
}
