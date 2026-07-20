"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";

type StockData = {
    symbol: string;
    name: string;
    price: number;
    change: number;
    changePercentage: number;
    marketCap: number;
    dayLow: number;
    dayHigh: number;
    yearLow: number;
    yearHigh: number;
    volume: number;
    exchange: string;
};

const TICKER_TAPE = [
  "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "JPM",
  "V", "WMT", "UNH", "XOM", "DIS", "NFLX", "INTC", "AMD","COST"
];

function formatMarketCap(value: number): string { 
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toLocaleString()}`;
}

function formatPrice(value: number): string { 
    return `$${value.toFixed(2)}`;
}

export default function Dashboard() { 
    const [ticker, setTicker] = useState("");
    const [stock, setStock] = useState<StockData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [addStatus, setAddStatus] = useState("");

    const addtoWatchList = async () => { 
        if (!stock) return;

        const { data: userData } = await supabase.auth.getUser();

        if (!userData.user) {
            setAddStatus("Log in to add stocks to your watchlist.");
            return;
        }

        const { error } = await supabase.from("watchlists").insert({
            ticker: stock.symbol,
            user_id: userData.user.id,
        });

        if (error) {
            setAddStatus("Erorr: " + error.message);
        } else {
            setAddStatus(`${stock.symbol} added to your watchlist.`);
        }
    };

    const searchStock = async () => {
        if (!ticker.trim()) return;
        setLoading(true);
        setError("");
        setStock(null);

        try { 
            const res = await fetch(`http://localhost:8000/stock/${ticker.trim().toUpperCase()}`);
            const data = await res.json();

            if (data.Error || !Array.isArray(data) || data.length == 0) {
                setError(`No record found for "${ticker.toUpperCase()}"`);
            } else {
                setStock(data[0]);
            }
        } catch {
            setError("Could not reach the data service. Please try again later.");
        } finally { 
            setLoading(false);
        }
    };

    const isPositive = stock ? stock.change >= 0 : true;

    const rows = stock
        ? [
            ["Last Price", formatPrice(stock.price)],
            ["Change", `${isPositive ? "+" : ""}${stock.change.toFixed(2)} (${isPositive ? "+" : ""}${stock.changePercentage.toFixed(2)}%)`],
            ["Day Range", `${formatPrice(stock.dayLow)} - ${formatPrice(stock.dayHigh)}`],
            ["52 Week Range", `${formatPrice(stock.yearLow)} - ${formatPrice(stock.yearHigh)}`],
            ["Market Cap", formatMarketCap(stock.marketCap)],
            ["Volume", stock.volume.toLocaleString()],
            ["Exchange", stock.exchange],
        ]
        : [];
    
    return (
        <main
            className = "min-h-screen"
            style = {{ backgroundColor: "#0B1120", color: "#EDEBE3", fontFamily: "Inter, sans-serif" }}
        >
            {/* Ticker Tape string */}
            <div
                className = "overflow-hidden border-b whitespace-nowrap"
                style = {{ borderColor: "#1E2A3D", backgroundColor: "#0E1726"}}
            >
                <div
                    className = "inline-flex py-2 animate-ticker"
                    style = {{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "12px", letterSpacing: "0.05em"}}
                >

                    {[...TICKER_TAPE, ...TICKER_TAPE, ...TICKER_TAPE].map((sym, i) => (
                        <span key = {i} className = "px-6" style={{ color: "#8A93A6" }} >
                            {sym} <span style={{ color: "#C9963C" }}>◆</span>
                        </span>
                    ))}
                </div>
            </div>

            <div className = "max-w-2xl mx-auto px-6 py-14">
                <div className ="mb-10">
                    <p
                        className = "text-xs uppercase mb-2"
                        style = {{ letterSpacing: "0.15em", color: "#8A93A6", fontFamily: "'IBM Plex Mono', monospace"}}
                    >
                        Stratos - Research Ledger
                    </p>
                    <h1 className = "text-3xl font-semibold" style={{ color: "#EDEBE3" }}>
                        Find a Stock
                    </h1>
                </div>

                <div className = "flex gap-2 mb-12">
                    <input
                        type = "text"
                        placeholder = "Ticker Symbol, e.g. AAPL"
                        value = {ticker}
                        onChange={(e) => setTicker(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && searchStock()}
                        className = "flex-1 px-4 py-2.5 text-sm rounded-sm focus:outline-none"
                        style = {{
                            backgroundColor: "#0E1726",
                            border: "1px solid #1E2A3D",
                            color: "#EDEBE3",
                            fontFamily: "'IBM Plex Mono', monospace",
                        }}
                    />

                    <button
                        onClick = {searchStock}
                        className = "px-6 py-2.5 text-sm rounded-sm font-medium transition-opacity hover:opacity-90"
                        style = {{ backgroundColor: "#C9963C", color: "#0B1220" }}
                    >
                        {loading ? "Searching..." : "Search"}
                    </button>
                </div>

                {error && (
                    <p className = "text-sm mb-8" style = {{ color: "#B5675A", fontFamily: "'IBM Plex Mono', monospace" }}>
                        {error}
                    </p>
                )}

                {stock && (
                    <div>
                        <div className = "flex items-baseline justify-between mb-1 pb-4" style = {{ borderBottom: "1px solid #1E2A3D" }}>
                            <div>
                                <h2 className = "text-2xl font-semibold" style = {{ color: "#EDEBE3" }}>
                                    {stock.symbol}
                                </h2>
                                <p className = "text-sm mt-1" style = {{ color: "#8A93A6"}}>
                                    {stock.name}
                                </p>
                            </div>
                            <p 
                                className = "text-2xl"
                                style = {{ color: isPositive ? "#7FA37A" : "#B5675A", fontFamily: "'IBM Plex Mono', monospace" }}
                            >
                                {formatPrice(stock.price)}
                            </p>
                        </div>

                        <button
                            onClick = {addtoWatchList}
                            className = "mb-6 px-4 py-2 text-sm rounded-sm transition-opacity hover:opacity-90"
                            style = {{ backgroundColor: "#1E2A3D", color: "#EDEBE3" }}
                        >
                            + Add to Watchlist
                        </button>
                        {addStatus && ( 
                            <p className = "text-xs mb-4" style={{ color: "#8A93A6" }}>
                                {addStatus}
                            </p>
                        )}

                        {rows.map(([label, value], i) => (
                            <div
                                key = {label}
                                className = "flex items-center justify-between py-3"
                                style = {{ borderBottom: i < rows.length - 1 ? "1px solid #17202F" : "none"}}
                            >
                                <span className = "text-sm" style={{ color: "#8A93A6" }}>
                                    {label}
                                </span>
                                <span
                                    className = "text-sm"
                                    style = {{ 
                                        fontFamily: "'IBM Plex Mono', monospace",
                                        color: label === "Change" ? (isPositive ? "#7FA37A" : "#B5675A") : "#EDEBE3",
                                    }}
                                >
                                    {value}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <style jsx global>{`
                @keyframes ticker-scroll { 
                    0% { transform: translateX(0); }
                    100% { transform: translateX(-33.333%); } 
                    }
                    .animate-ticker { 
                        animation: ticker-scroll 30s linear infinite;
                    }
                    @media (prefers-reduced-motion: reduce) { 
                        .animate-ticker {
                            animation: none;
                        }
                    }
                `}</style>            
        </main>
    );
}
