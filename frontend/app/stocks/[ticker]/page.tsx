"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

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

type HistoryPoint = {
    date: string,
    close: number,
    high: number,
    low: number,
    volume: number,
};

type HistoryPeriod = "1M" | "6M" | "1Y" | "5Y";

const HISTORY_PERIODS: HistoryPeriod[] = ["1M", "6M", "1Y", "5Y"];

function formatPrice(value: number) {
    return `$${value.toFixed(2)}`;
}

function formatMarketCap(value: number) {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    return `$${value.toLocaleString()}`;
}


export default function StockPage() {
    const params = useParams<{ ticker: string }>();
    const ticker = params.ticker.toUpperCase();

    const [stock, setStock] = useState<StockData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [history, setHistory] = useState<HistoryPoint[]>([]);
    const [period, setPeriod] = useState<HistoryPeriod>("1Y");

    useEffect(() => { 
        const loadStock = async () => {
            setLoading(true);
            setError("");

            try { 
                const response = await fetch(
                    `http://localhost:8000/stock/${ticker}`
                );
                const data = await response.json();

                if (!response.ok || !Array.isArray(data) || data.length === 0) {
                    throw new Error("Stock data not found");
                }

                setStock(data[0]);

        const historyResponse = await fetch(
            `http://localhost:8000/stock/${ticker}/history?period=${period}`
        );

        const historyData = await historyResponse.json();

        if (!historyResponse.ok || !Array.isArray(historyData.history)) {
            throw new Error("Historical Data could not be loaded");
        }

        setHistory(historyData.history);

            } catch (error) {
                setError(
                    error instanceof Error
                    ? error.message
                    : "Unable to load stock data"
                );
            } finally { 
                setLoading(false);
            }
        };

        loadStock();
    }, [ticker, period]);

    const isPositive = stock ? stock.change >= 0 : true;

    const performance = 
        history.length > 0
        ? {
            high: Math.max(...history.map((point) => point.high)),
            low: Math.min(...history.map((point) => point.low)),
            returnPercent:
                ((history[history.length - 1].close - history[0].close) / 
                  history[0].close) * 100
        }
        : null;

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

                <Link href="/dashboard" className = "text-sm" style = {{ color: "#8A93A6" }}>
                    Research Dashboard
                </Link>
            </nav>

            <section className = "max-w-5xl mx-auto px-6 py-14">
                {loading && (
                    <p style = {{ color: "#8A93A6" }}>
                        Loading {ticker} data...
                    </p>
                )}

                {error && (
                    <p style = {{ color: "#B5675A" }}>
                        {error}
                    </p>
                )}

                {stock && (
                    <>
                    <p
                        className = "text-xs uppercase mb-2"
                        style = {{
                            letterSpacing: "0.15em",
                            color: "#8A93A6",
                            fontFamily: "'IBM Plex Mono', monospace",    
                        }}
                    >
                        Company Research
                    </p>

                    <div className = "flex flex-wrap items-end justify-between gap-5 pb-8">
                        <div>
                        <h1 className = "text-4xl font-semibold">
                            {stock.symbol}
                        </h1>
                        <p className = "mt-2 text-base" style = {{ color: "#8A93A6" }}>
                            {stock.name}
                        </p>
                    </div>

                    <div className = "text-right">
                        <p
                            className = "text-3xl"
                            style = {{ fontFamily: "'IBM Plex Mono', monospace" }}
                        >
                            {formatPrice(stock.price)}
                        </p>
                        <p
                            className = "mt-1 text-sm"
                            style = {{
                                color: isPositive ? "#7FA37A" : "#B5675A",
                                fontFamily: "'IBM Plex Mono', monospace",
                            }}
                        >
                            {isPositive ? "+" : ""}
                            {stock.change.toFixed(2)} ({isPositive ? "+" : ""}
                            {stock.changePercentage.toFixed(2)}%)
                        </p>
                    </div>
                </div>

                <div
                    className = "grid grid-cols-2 md:grid-cols-4"
                    style = {{ 
                        borderTop: "1px solid #1E2A3D",
                        borderBottom: "1px solid #1E2A3D",
                    }}
                >
                    {[
                        ["Market Cap", formatMarketCap(stock.marketCap)],
                        ["Volume", stock.volume.toLocaleString()],
                        ["Day Range", `${formatPrice(stock.dayLow)} - ${formatPrice(stock.dayHigh)}`],
                        ["52 Week Range", `${formatPrice(stock.yearLow)} - ${formatPrice(stock.yearHigh)}`],
                    ].map(([label, value]) => (
                        <div
                            key={label}
                            className = "p-5"
                            style = {{
                                borderRight: "1px solid #1E2A3D",
                                borderBottom: "1px solid #1E2A3D",
                            }}
                        >
                            <p className = "text-xs mb-2" style = {{ color: "#8A93A6" }}>
                                {label}
                            </p>
                            <p className = "text-sm" 
                                style = {{ fontFamily: "'IBM Plex Mono', monospace" }}
                            >
                                {value}
                            </p>
                        </div>
                    ))}
                    </div>

                    {performance && (
                        <section
                            className = "mt-10 pt-6"
                            style = {{ borderTop: "1px solid #1E2A3D" }}
                        >   

                            <div className = "flex items-center justify-between mb-5">

                                <h2 className = "text-lg font-semibold">
                                    {period} Performance
                                </h2>

                                <div className = "flex gap-1">
                                    {HISTORY_PERIODS.map((option) => (
                                        <button
                                            key={option}
                                            onClick={() => setPeriod(option)}
                                            className = "px-2.5 py-1 text-xs rounded-sm"
                                            style = {{
                                                backgroundColor: period === option ? "#C9963C" : "#1E2A3D",
                                                color: period === option ? "#0B1120" : "#EDEBE3",
                                            }}
                                        >
                                            {option}
                                        </button>
                                    ))}
                                            
                                </div>
                            </div>

                            <div className = "grid grid-cols-3 gap-4">
                                <div>
                                    <p className = "text-xs mb-1" style = {{ color: "#8A93A6" }}>
                                        Return
                                    </p>
                                    <p
                                        className = "text-base"
                                        style = {{
                                            color: performance.returnPercent >= 0 ? "#7FA37A" : "#B5675A",
                                            fontFamily: "'IBM Plex Mono', monospace",                                  
                                        }}
                                    >
                                        {performance.returnPercent >= 0 ? "+" : ""}
                                        {performance.returnPercent.toFixed(2)}%
                                    </p>
                                </div>

                                <div>
                                    <p className = "text-xs mb-1" style = {{ color: "#8A93A6" }}>
                                        Period High
                                    </p>
                                    <p
                                        className = "text-base"
                                        style = {{ fontFamily: "'IBM Plex Mono', monospace" }}
                                    >
                                        {formatPrice(performance.high)}
                                    </p>    
                                </div>

                                <div>
                                    <p className = "text-xs mb-1" style = {{ color: "#8A93A6" }}>
                                        Period Low
                                    </p>
                                    <p
                                        className = "text-base"
                                        style = {{ fontFamily: "'IBM Plex Mono', monospace" }}
                                    >
                                        {formatPrice(performance.low)}
                                    </p>
                                </div>
                            </div>
                        </section>
                    )}
                    </>
                 )}
                </section>     
        </main>
    );
}