"use client";

import { useEffect, useState } from "react";

type NewsArticle = { 
    title: string;
    source: string;
    url: string;
    published_at: string;
    sentiment: string;
};

type StockNewsProps = {
    ticker: string;
    companyName: string;
};

function formatPublishedAt(value: string) { 
    const match = value.match(
        /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/
    );

    if (!match) return "Recent";

    const [, year, month, day, hour, minute] = match;

    return new Intl.DateTimeFormat("en-US", { 
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    }).format(
        new Date(
            Number(year),
            Number(month) - 1,
            Number(day),
            Number(hour),
            Number(minute)
        )
    );
}

export default function StockNews({ 
    ticker ,
    companyName,
}: StockNewsProps) { 
    const [articles, setArticles] = useState<NewsArticle[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => { 
        let isActive = true;

        const loadNews = async() => { 
            setLoading(true);
            setError("");
            setArticles([]);

            try { 
                const response = await fetch(
                    `http://localhost:8000/stock/${ticker}/news?company_name=${encodeURIComponent(companyName)}`
                );

                const data = await response.json();

                if (!response.ok) { 
                    throw new Error(data.detail || "News could not be loaded");
                }

                if (isActive) { 
                    setArticles(
                        Array.isArray(data.articles) ? data.articles : []
                    );
                }
            } catch (error) { 
                if (isActive) { 
                    setError(
                        error instanceof Error
                            ? error.message
                            : "News could not be loaded."
                    );
                }
            } finally { 
                if (isActive) {
                setLoading(false);
            }
        }
    };

    loadNews();

    return () => { 
        isActive = false;
    };
}, [ticker, companyName]);

return ( 
    <section>
        <p
            className = "text-xs uppercase"
            style = {{ 
                letterSpacing: "0.15em",
                color: "#8A93A6",
                fontFamily: "'IBM Plex Mono', monospace",
            }}
        >
            Latest News
        </p>

        <p
            className = "mt-2 text-sm" style = {{ color: "#B8BFCC" }}>
                Linked market context for {ticker}
        </p>

        {loading && ( 
            <p className = "mt-4 text-sm" style = {{ color: "#8A93A6" }}>
                Loading news...
            </p>
        )}

        {error && (
            <p className = "mt-4 text-sm" style = {{ color: "#B5675A" }}>
                {error}
            </p>
        )}

        {!loading && !error && articles.length === 0 && (
            <p className = "mt-4 text-sm" style = {{ color: "#8A93A6" }}>
                no recent news found.
            </p>
        )}

        <div className = "mt-4 space-y-4">
            {articles.map((article) => (
                <a
                    key = {article.url}
                    href = {article.url}
                    target = "_blank"
                    rel = "noreferrer"
                    className = "block transition-opacity hover:opacity-80"
                    style = {{ 
                        borderBottom: "1px solid #1E2A3D",
                        paddingBottom: "16px",
                    }}
                >
                    <p className = "text-sm leading-5" style = {{ color: "#EDEBE3" }}>
                        {article.title}
                    </p>

                    <p
                        className = "mt-2 text-xs"
                        style = {{ 
                            color: "#8A93A6",
                            fontFamily: "'IBM Plex Mono', monospace",
                        }}
                    >
                        {article.source} · {formatPublishedAt(article.published_at)} · {" "}
                        {article.sentiment}
                    </p>
                </a>
            ))}
        </div>
    </section>
    );
}

