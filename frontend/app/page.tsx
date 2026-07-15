"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabaseClient";

type WatchlistItem = { 
  id: string;
  ticker: string;
  created_at: string;
};

export default function Home() { 
  const [message, setMessage] = useState("Loading...");
  const [ticker, setTicker] = useState("");
  const [status, setStatus] = useState("");
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);

  useEffect(() => {
    fetch("http://localhost:8000/")
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch((err) => setMessage("Error: " + err.message));

    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    const { data, error } = await supabase 
      .from("watchlists")
      .select("id, ticker, created_at")
      .order("created_at", { ascending: false });

    if (!error && data) { 
      setWatchlist(data);
    }
  };

  const addToWatchList = async () => { 
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
      setStatus(`Added ${ticker.toUpperCase()} to your watchlists.`);
      setTicker("");
      fetchWatchlist();
    }
  };

  return (
    <main style={{ padding: "2rem" }}> 
      <h1>Stratos</h1>
      <p>Backend says: {message}</p>

    <h2> Add to Watchlist</h2>
    <input
    type="text"
    placeholder="Ticker (e.g. AAPL)"
    value={ticker}
    onChange={(e) => setTicker(e.target.value)}
    style={{ padding: "0.5rem", marginRight: "0.5rem" }}
    />
    <button onClick={addToWatchList} style={{ padding: "0.5rem 1rem" }}>Add</button>
    <p>{status}</p>

    <h2> Your Watchlist</h2>
    <ul>
      {watchlist.map((item) => (
        <li key={item.id}>{item.ticker}</li>
      ))}
    </ul>
    </main>
  );
}
