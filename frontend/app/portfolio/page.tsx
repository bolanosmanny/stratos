"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";

type Holding = {
    id: number;
    ticker: string;
    shares: number;
    purchase_price: number;
    purchase_date: string;
};

type Quote = { 
    symbol: string;
    price: number;
}

function formatCurrency(value: number): string {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
    }).format(value);
}

export default function PortfolioPage() { 

    const [ticker, setTicker] = useState("");
    const [shares, setShares] = useState("");
    const [purchasePrice, setPurchasePrice] = useState("");
    const [purchaseDate, setPurchaseDate] = useState("");
    const [status, setStatus] = useState("");
    const [adding, setAdding] = useState(false);
    const [holdings, setHoldings] = useState<Holding[]>([]);
    const [prices, setPrices] = useState<Record<string, number>>({});

    const loadPrices = async (holdingRows: Holding[]) => { 
        const symbols = [
            ...new Set(holdingRows.map((holding) => holding.ticker)),
        ];

        if (symbols.length === 0) {
            setPrices({});
            return;
        }

        try { 
            const response = await fetch(
                `http://localhost:8000/stocks/quotes?symbols=${symbols.join(",")}`
            );
            const data: Quote[] = await response.json();

            if(!response.ok) { 
                throw new Error("Unable to load current prices.")
            }

            const priceMap = Object.fromEntries(
                data.map((quote) => [quote.symbol, quote.price])
            );

            setPrices(priceMap);
        } catch { 
            setPrices({});
        }
    };

    const loadHoldings = async () =>  {
        const { data, error } = await supabase
            .from("portfolio_holdings")
            .select("id, ticker, shares, purchase_price, purchase_date")
            .order("purchase_date", { ascending: false });

        if (!error && data) {
            setHoldings(data);
            await loadPrices(data);
        }
    };

    useEffect(() => {
        supabase
            .from("portfolio_holdings")
            .select("id, ticker, shares, purchase_price, purchase_date")
            .order("purchase_date", { ascending: false })
            .then(({ data, error }) => {
                if (!error && data) {
                    setHoldings(data);
                    void loadPrices(data);
                }
            });
    }, []);

    const addHolding = async () => {
        const normalizedTicker = ticker.trim().toUpperCase();
        const parsedShares = Number(shares);
        const parsedPurchasePrice = Number(purchasePrice);

        if ( 
            !normalizedTicker || 
            parsedShares <= 0 || 
            parsedPurchasePrice < 0 ||
            !purchaseDate
        ) { 
            setStatus("Enter a ticker, positive share count, purchase price and date.");
            return;
        }

        setAdding(true);
        setStatus("");

        const { data: userData } = await supabase.auth.getUser();

        if (!userData.user) {
            setStatus("Log in to add portfolio holdings.");
            setAdding(false);
            return;
        }

        const { error } = await supabase
            .from("portfolio_holdings")
            .insert({
                user_id: userData.user.id,
                ticker: normalizedTicker,
                shares: parsedShares,
                purchase_price: parsedPurchasePrice,
                purchase_date: purchaseDate,
            });

        if (error) {
            setStatus(`Error: ${error.message}`);   
        } else {
            setTicker("");
            setShares("");
            setPurchasePrice("");
            setPurchaseDate("");
            setStatus(`${normalizedTicker} added to your portfolio.`);;
            await loadHoldings();
        }

        setAdding(false);
    };

    const removeHolding = async (id: number) => { 
        const { error } = await supabase
            .from("portfolio_holdings")
            .delete()
            .eq("id", id);

        if (error) { 
            setStatus(`Error: ${error.message}`);
        } else { 
            setStatus("Holding removed from your portfolio.");
            await loadHoldings();
        }
    }

    const totalCost = holdings.reduce(
        (total, holding) => 
            total + 
        Number(holding.shares) * Number(holding.purchase_price),
        0
    );

    const totalValue = holdings.reduce(
        (total, holding) =>
            total + 
        Number(holding.shares) * (prices[holding.ticker] ?? 0),
        0
    );

    const totalProfitLoss = totalValue - totalCost;
    const hasCurrentPrices = Object.keys(prices).length > 0;
    const allocationByTicker = holdings.reduce<Record<string, number>> (
        (totals, holding) => {
            const currentPrice = prices[holding.ticker];

            if (currentPrice === undefined) {
                return totals;
            }

            const marketValue = Number(holding.shares) * currentPrice;

            totals[holding.ticker] = 
                (totals[holding.ticker] ?? 0) + marketValue;

            return totals;
        },
        {}
    );

    const allocationData = Object.entries(allocationByTicker)
        .map(([ticker, value]) => ({
            ticker, 
            value,
            percentage: totalValue > 0 ? (value / totalValue) * 100 : 0,
        }))
        .sort((first, second) => second.value - first.value);

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
                    href = "/dashboard"
                    className = "text-sm font-semibold"
                    style = {{
                        color: "#EDEBE3",
                        fontFamily: "'IBM Plex Mono', monospace",
                    }}
                >
                    STRATOS
                </Link>

                <Link href = "/dashboard" className = "text-sm" style = {{ color: "#8A93A6" }}>
                    Research Dashboard
                </Link>

                <Link href = "/research" className = "text-sm" style = {{ color: "#8A93A6" }}>
                    Sparky Research
                </Link>

                <Link href = "/portfolio" className = "text-sm" style = {{ color: "#EDEBE3" }}>
                    Portfolio
                </Link>
            </nav>

            <section className = "max-w-5xl mx-auto px-6 py-14">
                <p
                    className = "text-xs uppercase mb-2"
                    style = {{
                        letterSpacing: "0.15em",
                        color: "#8A93A6",
                        fontFamily: "'IBM Plex Mono', monospace",
                    }}
                >
                    Position Ledger
                </p>

                <h1 className = "text-4xl font-semibold"> Portfolio Tracker</h1>

                <p className = "mt-3 text-base" style = {{ color: "#B8BFCC" }}>
                    Track purchase lots, current value, and portfolio allocation.
                </p>

                <form
                    onSubmit={(event) => {
                        event.preventDefault();
                        addHolding();
                    }}
                    className = "mt-10 grid gap-4 md:grid-cols-4"
                >

                    <input
                        type = "text"
                        placeholder = "Ticker, e.g. AAPL"
                        value = {ticker}
                        onChange={(event) => setTicker(event.target.value)}
                        className = "px-4 py-3 text-sm rounded-sm focus:outline-none"
                        style = {{
                            backgroundColor: "#0E1726",
                            border: "1px solid #1E2A3D",
                            color: "#EDEBE3",
                            fontFamily: "'IBM Plex Mono', monospace",
                        }}
                    />

                    <input
                        type = "number"
                        min = "0.0000001"
                        step = "any"
                        placeholder = "Shares"
                        value = {shares}
                        onChange={(event) => setShares(event.target.value)}
                        className = "px-4 py-3 text-sm rounded-sm focus:outline-none"
                        style = {{
                            backgroundColor: "#0E1726",
                            border: "1px solid #1E2A3D",
                            color: "#EDEBE3",
                            fontFamily: "'IBM Plex Mono', monospace",
                        }}
                    />

                    <input
                        type = "number"
                        min = "0"
                        step = "0.01"
                        placeholder = "Purchase Price"
                        value = {purchasePrice}
                        onChange={(event) => setPurchasePrice(event.target.value)}
                        className = "px-4 py-3 text-sm rounded-sm focus:outline-none"
                        style = {{ 
                            backgroundColor: "#0E1726",
                            border: "1px solid #1E2A3D",
                            color: "#EDEBE3",
                            fontFamily: "'IBM Plex Mono', monospace",
                        }}
                    />

                    <input
                        type = "date"
                        value = {purchaseDate}
                        onChange = {(event) => setPurchaseDate(event.target.value)}
                        className = "px-4 py-3 text-sm rounded-sm focus:outline-none"
                        style = {{
                            backgroundColor: "#0E1726",
                            border: "1px solid #1E2A3D",
                            color: "#EDEBE3",
                            fontFamily: "'IBM Plex Mono', monospace",
                        }}
                    />

                    <button
                        type = "submit"
                        disabled = {adding}
                        className = "md:col-span-4 px-5 py-3 text-sm rounded-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
                        style = {{ backgroundColor: "#C9963C", color: "#0B1120" }}
                    >
                        {adding ? "Adding holding..." : "Add holding"}
                    </button>
                </form>

                {status && (
                    <p
                        className = "mt-4 text-sm"
                        style = {{
                            color: status.startsWith("Error") ? "#B5675A" : "#8A93A6",
                            fontFamily: "'IBM Plex Mono', monospace",
                        }}
                    >
                        {status}
                    </p>
                )}

                <div className = "grid gap-px md:grid-cols-3" style = {{ backgroundColor: "#1E2A3D" }}>
                    {[
                        ["Total Cost", formatCurrency(totalCost)],
                        [
                            "Current Value",
                            hasCurrentPrices
                                ? formatCurrency(totalValue)
                                : "Loading...",     
                        ],
                        [
                            "Profit / Loss",
                            hasCurrentPrices
                                ? formatCurrency(totalProfitLoss)
                                : "Loading..."
                        ],
                    ].map(([label, value]) => (
                        <div
                            key = {label}
                            className = "p-5"
                            style = {{ backgroundColor: "#0E1726" }}
                        >
                            <p
                                className = "text-xs uppercase"
                                style = {{
                                    color: "#8A94A6",
                                    letterSpacing: "0.08em",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            >
                                {label}
                            </p>
                            <p
                                className = "mt-2 text-xl"
                                style = {{ 
                                    color:
                                        label === "Profit / Loss" && totalProfitLoss < 0
                                            ? "#7FA37A"
                                            : "#EDEBE3",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            >
                                {value}
                            </p>
                        </div>
                    ))}
                </div>

                {hasCurrentPrices && allocationData.length > 0 && (
                    <section 
                        className = "mit-12 p-6"
                        style = {{ 
                            border: "1px solid #1E2A3D",
                            backgroundColor: "#0E1726",
                        }}
                    >
                        <p
                            className = "text-xs uppercase"
                            style = {{ 
                                color: "#8A93A6",
                                letterSpacing: "0.08em",
                                fontFamily: "'IBM Plex Mono', monospace",
                            }}
                        >
                            Allocation
                        </p>

                        <div className = "mt-5 space-y-4">
                            {allocationData.map((position) => (
                                <div key = {position.ticker}>
                                    <div className = "flex justify-between text-sm">
                                        <span 
                                            style = {{
                                                color: "#EDEBE3",
                                                fontFamily: "'IBM Plex Mono', monospace",
                                            }}
                                        >
                                            {position.ticker}
                                        </span>

                                        <span
                                            style = {{ 
                                                color: "#B8BFCC",
                                                fontFamily: "'IBM Plex Mono', monospace",
                                            }}
                                        >
                                            {position.percentage.toFixed(1)}% ·{" "}
                                            {formatCurrency(position.value)}
                                        </span>
                                    </div>

                                    <div
                                        className = "mt-2 h-2 overflow-hidden"
                                        style = {{ backgroundColor: "#1E2A3D" }}
                                    >
                                        <div
                                            className = "h-full"
                                            style = {{
                                                width: `${position.percentage}%`,
                                                backgroundColor: "#C9963C",
                                            }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                <div className = "mt-12">
                    <div
                        className = "grid grid-cols-6 gap-4 px-4 py-3 text-xs uppercase"
                        style = {{
                            borderTop: "1px solid #1E2A3D",
                            borderBottom: "1px solid #1E2A3D",
                            color: "#8A93A6",
                            letterSpacing: "0.08em",
                            fontFamily: "'IBM Plex Mono', monospace",
                        }}
                    >
                        <span>Position</span>
                        <span>Shares</span>
                        <span>Cost / Share</span>
                        <span>Current Price</span>
                        <span>Position P/L</span>
                        <span>Action</span>
                    </div>

                    {holdings.length === 0 ? (
                        <p className = "py-6 text-sm" style = {{ color: "#8A93A6" }}>
                            No holdings yet. Add your first purchase lot above.
                        </p>
                    ) : (
                        holdings.map((holding) => {
                            const currentPrice = prices[holding.ticker];
                            const costBasis = 
                                Number(holding.shares) * 
                                Number(holding.purchase_price);
                            const marketValue = 
                                Number(holding.shares) * (currentPrice ?? 0);
                            const profitLoss = marketValue - costBasis;

                            return ( 
                                <div
                                    key = {holding.id}
                                    className = "grid grid-cols-6 gap-4 px-4 py-4 text-sm"
                                    style = {{
                                        borderBottom: "1px solid #1E2A3D",
                                        fontFamily: "'IBM Plex Mono', monospace",
                                    }}
                                >
                                    <span style = {{ color: "#EDEBE3" }}>
                                        {holding.ticker}
                                        <span
                                            className = "block mt-1 text-xs"
                                            style = {{ color: "#8A93A6" }}
                                        >
                                            {holding.purchase_date}
                                        </span>
                                    </span>

                                    <span style = {{ color: "#B8BFCC" }}>
                                        {Number(holding.shares).toLocaleString()}
                                    </span>

                                    <span style = {{ color: "#B8BFCC" }}>
                                        {formatCurrency(
                                            Number(holding.purchase_price)
                                        )}
                                    </span>

                                    <span style = {{ color: "#B8BFCC" }}>
                                        {currentPrice !== undefined
                                            ? formatCurrency(currentPrice)
                                            : "-"}
                                    </span>

                                    <span
                                        style = {{ 
                                            color:
                                                currentPrice === undefined
                                                ? "#8A93A6"
                                                : profitLoss >= 0
                                                ? "#7FA37A"
                                                : "#B5675A",
                                        }}
                                    >
                                        {currentPrice !== undefined
                                            ? `${profitLoss >= 0 ? "+" : ""}${formatCurrency(profitLoss)}`
                                            : "-"}
                                        {currentPrice !== undefined && (
                                            <span
                                                className = "block mt-1 text-xs"
                                                style = {{ color: "#8A93A6" }}
                                            >
                                                Value {formatCurrency(marketValue)}
                                            </span>
                                        )}
                                    </span>

                                    <button
                                        onClick = {() => removeHolding(holding.id)}
                                        className = "text-left text-xs"
                                        style = {{ color: "#B5675A" }}
                                    >
                                        Remove
                                    </button>
                                </div>
                            );
                        })
                    )}
                  </div>       
            </section>
        </main>
    )
}
