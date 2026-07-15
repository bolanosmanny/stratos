"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabaseClient";

export default function Home() { 
  const [message, setMessage] = useState("Loading...");
  const [ticker, setTicker] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/")
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch((err) => setMessage("Error: " + err.message));
  }, []);

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
    </main>
  );
}
