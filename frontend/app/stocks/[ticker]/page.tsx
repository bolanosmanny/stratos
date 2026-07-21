"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

export default function StockPage() {
    const params = useParams<{ ticker: string }>();
    const ticker = params.ticker.toUpperCase();

    return (
        <main
            className = "min-h-screen"
            style = {{
                backgroundColor: "#0B1220",
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

                <Link href="/dashboard" className = "text-sm" style = {{ color: "#8A93A6" }}>
                    Research Dashboard
                </Link>
            </nav>

            <section className = "max-w-5xl mx-auto px-6 py-14">
                <p
                    className = "text-3xl uppercase mb-2"
                    style = {{
                        letterSpacing: "0.15em",
                        color: "#8A93A6",
                        fontFamily: "'IBM Plex Mono', monospace",
                    }}
                >
                    Company Research
                </p>

                <h1 className="text-4xl font-semibold">{ticker}</h1>

                <p className = "mt-3 text-sm" style = {{ color: "#8A93A6" }}>
                    Historical performance, company fundamentals, filings, and AI-assisted research will appear here.
                </p>
            </section>
        </main>
    );
}