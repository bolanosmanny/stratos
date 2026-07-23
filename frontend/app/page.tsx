"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";

type WatchlistItem = { 
  id: string;
  ticker: string;
  created_at: string;
};

export default function Home() { 
  const [ticker, setTicker] = useState("");
  const [status, setStatus] = useState("");
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);

  const fetchWatchlist = async () => {
    const { data, error } = await supabase 
      .from("watchlists")
      .select("id, ticker, created_at")
      .order("created_at", { ascending: false });

    if (!error && data) { 
      setWatchlist(data);
    }
  };

  useEffect(() => {
    supabase
      .from("watchlists")
      .select("id, ticker, created_at")
      .order("created_at", { ascending: false })
      .then(({data, error }) => {
        if (!error && data) {
          setWatchlist(data);
        }
      })
  }, []);

  const addToWatchList = async () => { 
    if (!ticker.trim()) return;
    const { data: userData } = await supabase.auth.getUser();

    if(!userData.user) {
      setStatus("You must be logged in to add to your watchlist.");
      return;
    }

    const { error } = await supabase.from("watchlists").insert({
      ticker: ticker.toUpperCase(),
      user_id: userData.user.id,
    });

    if (error) { 
      setStatus("Error: " + error.message);
    } else {
      setStatus(`Added ${ticker.trim().toUpperCase()} to your watchlists.`);
      setTicker("");
      fetchWatchlist();
    }
  };

  const removeFromWatchlist = async (id: string) => {
    const { error } = await supabase.from("watchlists").delete().eq("id", id);

    if (error) fetchWatchlist();
  };

  return (
    <main
      className = "min-h-screen"
      style={{ backgroundColor: "#0B1120", color: "#EDEBE3", fontFamily: "Inter, sans-serif" }}
    >
      {/* Nav */}
      <div
        className="flex items-center gap-6 px-6 py-4"
        style={{ borderBottom: "1px solid #1E2A3D", backgroundColor: "#0E1726" }}
      >
        <span
          className = "text-sm font-semibold"
          style={{ color: "#EDEBE3", fontFamily: "'IBMPlexMono', monospace" }}
        >
          STRATOS
        </span>
        <Link href="/" className="text-sm" style={{ color: "#EDEBE3" }}>
          Watchlist
        </Link>
        <Link href="/dashboard" className="text-sm" style={{ color: "#8A93A6" }}>
          Research Dashboard
        </Link>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-14">
        <div className="mb-10">
          <p
            className="text-xs uppercase mb-2"
            style={{ letterSpacing: "0.15em", color: "#8A93A6", fontFamily:"'IBMPlexMono', monospace" }}
          >
            Stratos - Your Positions
          </p>
          <h1 className="text-3xl font-semibold" style={{ color: "#EDEBE3" }}>
            Watchlist
          </h1>
        </div>

        <div className="flex gap-2 mb-12">
          <input
            type="text"
            placeholder="Ticker symbol, e.g. AAPL"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addToWatchList()}
            className="flex-1 px-4 py-2.5 text-sm rounded-sm focus:outline-none"
            style={{ 
              backgroundColor: "#0E1726",
              border: "1px solid #1E2A3D",
              color: "#EDEBE3",
              fontFamily: "'IBMPlexMono', monospace",
            }}
        />
          <button
            onClick={addToWatchList}
            className="px-6 py-2.5 text-sm rounded-sm font-medium transition-opacity hover:opacity-90"
            style={{ backgroundColor: "#C9963C", color: "#0B1220" }}
          >
            Add
          </button>
        </div>

        {status && (
          <p className="text-sm" style={{ color: "#8A93A6" }}>
            {status}
          </p>
        )}

        {watchlist.length === 0 ? (
          <p className="text-sm" style={{ color: "#8A93A6" }}>
            No positions yet. Add a stock above or search one on the research dashboard.
          </p>
        ) : (
          <div>
            {watchlist.map((item, i) => (
              <div
                key={item.id}
                className="flex items-center justify-betweeen py-3"
                style={{ borderBottom: i < watchlist.length - 1 ? "ipx solid #17202F" : "none" }}
              >
                <span 
                  className="text-sm"
                  style={{ fontFamily: "'IBMPlexMono', monospace", color: "#EDEBE3" }}
                >
                  {item.ticker}
                </span>
                <button
                  onClick={() => removeFromWatchlist(item.id)}
                  className="text-xs"
                  style={{ color: "#B5675A" }}
                >
                   - Remove
                </button>
              </div>
            ))}
      </div>
        )}
      </div>
    </main>
  );
}
