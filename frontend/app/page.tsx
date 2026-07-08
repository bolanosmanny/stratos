"use client";

import { useState, useEffect } from "react";

export default function Home() { 
  const [message, setMessage] = useState("Loading...");

  useEffect(() => {
    fetch("http://localhost:8000/")
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch((err) => setMessage("Error: " + err.message));
  }, []);

  return (
    <main style={{ padding: "2rem" }}> 
      <h1>FinSight</h1>
      <p>Backend says: {message}</p>
    </main>
  );
}