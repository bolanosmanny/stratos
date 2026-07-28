"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";

type WatchlistItem = {
  id: number;
  ticker: string;
  created_at: string;
};

type WatchlistCollection = { 
  id: number;
  name: string;
  created_at: string;
  watchlist_items: WatchlistItem[];
};

type Quote = { 
  symbol: string;
  price: number;
  change: number;
  changePercentage: number;
}

export default function Home() { 
  const [collections, setCollections] = useState<WatchlistCollection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [newWatchlistName, setNewWatchlistName] = useState("");
  const [ticker, setTicker] = useState("");
  const [status, setStatus] = useState("");
  const [creatingList, setCreatingList] = useState(false);
  const [addingTicker, setAddingTicker] = useState(false);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});

  const selectedCollection = 
    collections.find(
      (collection) => collection.id === selectedCollectionId
    ) ?? null;
    
  const loadCollections = async () => { 
    const { data, error }  = await supabase
      .from("watchlist_collections")
      .select(`
        id,
        name,
        created_at,
        watchlist_items ( 
          id,
          ticker,
          created_at
          )
      `)
      .order("created_at", { ascending: true });

    if (error) { 
      setStatus(`Error: ${error.message}`);
      return;
    }

    const loadedCollections = (data ?? []) as WatchlistCollection[];

    setCollections(loadedCollections);

    setSelectedCollectionId((currentId) => { 
      const currentStillExists = loadedCollections.some(
        (collection) => collection.id === currentId
      );

      if (currentStillExists) {
        return currentId;
      }

      return loadedCollections[0]?.id ?? null;

    });
  };

  useEffect(() => {
    supabase
        .from("watchlist_collections")
        .select(`
            id,
            name,
            created_at,
            watchlist_items (
                id,
                ticker,
                created_at
            )
        `)
        .order("created_at", { ascending: true })
        .then(({ data, error }) => {
            if (error) {
                setStatus(`Error: ${error.message}`);
                return;
            }

            const loadedCollections =
                (data ?? []) as WatchlistCollection[];

            setCollections(loadedCollections);

            setSelectedCollectionId((currentId) => {
                const currentStillExists = loadedCollections.some(
                    (collection) => collection.id === currentId
                );

                return currentStillExists
                    ? currentId
                    : loadedCollections[0]?.id ?? null;
              });
        });
  }, []);

  useEffect(() => { 
    const symbols = 
    selectedCollection?.watchlist_items.map((item) => item.ticker) ?? [];

    if (symbols.length ===0 ) { 
      return;
    }

    fetch(
      `http://localhost:8000/stocks/quotes?symbols=${symbols?.join(",")}`
    )
      .then(async (response) => { 
        const data: Quote[] = await response.json();

        if (!response.ok) { 
          throw new Error("Unable to load watchlist quotes.");
        }

        return data;
      })
      .then((data) => { 
        setQuotes(
          Object.fromEntries(
            data.map((quote) => [quote.symbol, quote])
        )
      );
      })
      .catch(() => { 
        setQuotes({});
      });
  }, [selectedCollection]);


  const createWatchlist = async () => { 
    const trimmedName = newWatchlistName.trim();
    
    if (!trimmedName) {
      setStatus("Enter a name for your new watchlist.");
      return;
  }

    setCreatingList(true);
    setStatus("");

    const { data: userData } = await supabase.auth.getUser();

    if (!userData.user) { 
      setStatus("Log in to create a watchlist.");
      setCreatingList(false);
      return;
    }

    const { data, error } = await supabase
      .from("watchlist_collections")
      .insert({
        user_id: userData.user.id,
        name: trimmedName,
      })
      .select("id")
      .single();

    if (error) { 
      setStatus(
        error.code === "23505"
          ? "You already have a watchlist with that name."
          : `Error: ${error.message}`
      );
    } else { 
      setNewWatchlistName("");
      setSelectedCollectionId(data.id);
      setStatus(`${trimmedName} watchlist created.`);
      await loadCollections();
    }

    setCreatingList(false);
  };

  const addTicker = async () => { 
    const normalizedTicker = ticker.trim().toUpperCase();

    if (!normalizedTicker || !selectedCollectionId) { 
      setStatus("Choose a watchlist and enter a ticker.");
      return;
    }

    setAddingTicker(true);
    setStatus("");

    const { error } = await supabase.from("watchlist_items").insert({
      watchlist_id: selectedCollectionId,
      ticker: normalizedTicker,
    });

    if (error) { 
      setStatus(
        error.code === "23505"
          ? `${normalizedTicker} is already in this watchlist.`
          : `Error: ${error.message}`
      );
    } else { 
      setTicker("");
      setStatus(`${normalizedTicker} added to ${selectedCollection?.name}.`)
      await loadCollections();
    }

    setAddingTicker(false);
  };

  const removeTicker = async (id: number) => { 
    const { error } = await supabase
      .from("watchlist_items")
      .delete()
      .eq("id", id);

      if (error) { 
        setStatus(`Error: ${error.message}`)
        return;
      }

      setStatus("Ticker removed from watchlist.");
      await loadCollections();
  };

  const deleteWatchlist = async () => { 
    if (!selectedCollection) {
      return;
  }

  const { error } = await supabase
    .from("watchlist_collections")
    .delete()
    .eq("id", selectedCollection.id);

  if (error) { 
    setStatus(`Error: ${error.message}`);
    return;
  }

  setStatus(`${selectedCollection.name} deleted.`)
  await loadCollections();
  };

  const loadedQuotes = selectedCollection
    ? selectedCollection.watchlist_items
      .map((item) => quotes[item.ticker])
      .filter((quote): quote is Quote => quote !== undefined)
    : [];

    const averageDailyChange = 
      loadedQuotes.length > 0
        ? loadedQuotes.reduce(
            (total, quote) => total + quote.changePercentage,
            0
          ) / loadedQuotes.length
        : 0;

    const positiveTickers = loadedQuotes.filter(
        (quote) => quote.changePercentage >= 0
    ).length;
        
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
          href = "/"
          className = "text-sm font-semibold"
          style = {{ 
            color: "#EDEBE3",
            fontFamily: "'IBM Plex Mono', monospace",
          }}
          >
            STRATOS
          </Link>

          <Link
            href="/"
            className = "text-sm"
            style = {{ color: "#EDEBE3" }}
          >
            Watchlists
          </Link>

          <Link
            href="/dashboard"
            className = "text-sm"
            style = {{ color: "#8A93A6" }}
          >
            Research Dashboard
          </Link>

          <Link
            href = "/research"
            className = "text-sm"
            style = {{ color: "#8A93A6" }}
          >
            Sparky AI
          </Link>

          <Link
            href = "/portfolio"
            className = "text-sm"
            style = {{ color: "#8A93A6" }}
          >
            Portfolio 
          </Link>
      </nav>

      <section className = "max-w-7xl mx-auto px-6 py-14">
        <p
          className = "text-xs uppercase mb-2"
          style = {{
            letterSpacing: "0.15em",
            color: "#8A93A6",
            fontFamily: "'IBM Plex Mono', monospace",
          }}
        >
          Market Workspace
        </p>

        <h1 className = "text-4xl font-semibold"> Watchlists</h1>

        <p
          className = "mt-3 text-base"
          style = {{ color: "#B8BFCC" }}
        >
          Organize the companies you want to track and research.
        </p>

        <div className = "grid gap-6 mt-10 lg:grid-cols-3">
          <aside 
            className = "p-5"
            style = {{
              border: "1px solid #1E2A3D",
              backgroundColor: "#0E1726",
            }}
          >
            <p
              className = "text-xs uppercase"
              style = {{
                letterSpacing: "0.1em",
                color: "#8A93A6",
                fontFamily: "'IBM Plex Mono', monospace",
              }}
            >
              Your Watchlists
            </p>

            <div className= "mt-5 flex gap-2">
              <input
                type = "text"
                placeholder = "e.g. Long-Term"
                value = {newWatchlistName}
                onChange = {(event) => 
                  setNewWatchlistName(event.target.value)
                }
                onKeyDown = {(event) => {
                  if (event.key === "Enter") {
                    void createWatchlist();
                  }
                }}
                className = "min-w-0 flex-1 px-3 py-2 text-sm rounded-sm focus:outline-none"
                style = {{ 
                  backgroundColor: "#0B1120",
                  border: "1px solid #1E2A3D",
                  color: "#EDEBE3",
                  fontFamily: "'IBM Plex Mono', monospace",
                }}
              />

              <button 
                type = "button"
                disabled = {creatingList}
                onClick = {() => void createWatchlist()}
                className = "px-3 py-2 text-xs rounded-sm disabled:opacity-50"
                style = {{
                  backgroundColor: "#C9963C",
                  color: "#0B1120",
                }}
              >
                {creatingList ? "..." : "New"}
              </button>
            </div>

            <div className = "mt-5 space-y-2">
              {collections.map((collection) => (
                <button
                  key = {collection.id}
                  type = "button"
                  onClick = {() =>
                    setSelectedCollectionId(collection.id)
                  }
                  className = "w-full flex items-center justify-between px-3 py-3 text-left text-sm rounded-sm"
                  style = {{
                    backgroundColor:
                      selectedCollectionId === collection.id
                        ? "#1E2A3D"
                        : "transparent",
                    color: "#EDEBE3",
                  }}
                >
                  <span>{collection.name}</span>

                  <span
                    className = "text-xs"
                    style = {{ 
                      color: "#8A93A6",
                      fontFamily: "'IBM Plex Mono', monospace",
                    }}
                  >
                    {collection.watchlist_items.length}
                  </span>
                </button>
              ))}

              {collections.length === 0 && (
                <p
                  className = "py-4 text-sm"
                  style = {{ color: "#8A93A6" }}
                >
                  Create your first watchlist to begin.
                </p>
              )}
            </div>
          </aside>

          <section
            className = "lg:col-span-2 p-6"
            style = {{
              border: "1px solid #1E2A3D",
              backgroundColor: "#0E1726",
            }}
          >
            {selectedCollection ? (
              <>
                <div className = "flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p
                      className = "text-xs uppercase"
                      style = {{ 
                        letterSpacing: "0.1em",
                        color: "#8A93A6",
                        fontFamily: "'IBM Plex Mono', monospace",
                      }}
                    >
                      Active Watchlist
                    </p>

                    <h2 className = "mt-2 text-2xl font-semibold">
                      {selectedCollection.name}
                    </h2>
                  </div>

                  <button
                    type = "button"
                    onClick = {() => void deleteWatchlist()}
                    className = "text-xs"
                    style = {{ color: "#B5675A" }}
                  >
                    Delete Watchlist
                  </button>
                </div>

                <div className = "grid gap-px mt-8 md:grid-cols-3"
                  style = {{ backgroundColor: "#1E2A3D" }}>
                    {[
                      [
                        "Tracked",
                        `${selectedCollection.watchlist_items.length} ${
                          selectedCollection.watchlist_items.length === 1 ? "stock" : "stocks" 
                        }`,
                      ],
                      [
                        "Advancers Today",
                        `${positiveTickers} / ${loadedQuotes.length || "-"}`,
                        "#7FA37A",
                      ],
                      [
                        "Equal-Weight Daily Move",
                        loadedQuotes.length > 0
                          ? `${averageDailyChange >= 0 ? "+" : ""}${averageDailyChange.toFixed(2)}%`
                          : "Loading...",
                        averageDailyChange >= 0 ? "#7FA37A" : "#B5675A"
                      ],
                    ].map(([label, value, color]) => (
                      <div
                        key = {label}
                        className = "p-4"
                        style = {{ backgroundColor: "#0B1120" }}
                      >
                        <p
                          className = "text-xs uppercase"
                          style = {{
                            color: "#8A93A6",
                            letterSpacing: "0.08em",
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >
                          {label}
                        </p>

                        <p
                          className = "mt-2 text-lg"
                          style = {{ 
                            color, 
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>

                <div className = "flex gap-2 mt-8">
                  <input
                    type = "text"
                    placeholder = "Ticker Symbol, e.g. AAPL"
                    value = {ticker}
                    onChange = {(event) =>
                      setTicker(event.target.value)
                    }
                    onKeyDown = {(event) => { 
                      if (event.key === "Enter") { 
                        void addTicker();
                      }
                    }}
                    className = "flex-1 px-4 py-3 text-sm rounded-sm focus:outline-none"
                    style = {{ 
                      backgroundColor: "#0B1120",
                      border: "1px solid #1E2A3D",
                      color: "#EDEBE3",
                      fontFamily:
                        "'IBM Plex Mono', monospace",
                    }}
                  />

                  <button
                    type = "button"
                    disabled = {addingTicker}
                    onClick = {() => void addTicker()}
                    className = "px-5 py-3 text-sm rounded-sm font-medium disabled:opacity-50"
                    style = {{
                      backgroundColor: "#C9963C",
                      color: "#0B1120"
                    }}
                  >
                    {addingTicker ? "Adding..." : "Add"}
                  </button>
                </div>

                {status && ( 
                  <p
                    className = "mt-4 text-sm"
                    style = {{
                      color: status.startsWith("Error")
                        ? "#B5675A"
                        : "#8A93A6",
                    }}
                  >
                    {status}
                  </p>
                )}

                <div className = "mt-8">
                  <div
                    className = "grid grid-cols-5 gap-4 px-4 py-3 text-xs uppercase"
                    style = {{ 
                      borderTop: "1px solid #1E2A3D",
                      borderBottom: "1px solid #1E2A3D",
                      color: "#8A93A6",
                      letterSpacing: "0.08em",
                      fontFamily: "'IBM Plex Mono', monospace",
                    }}
                  >
                    <span>Ticker</span>
                    <span>Current Price</span>
                    <span>Daily Change</span>
                    <span>Date Added</span>
                    <span>Action</span>
                  </div>

                  {selectedCollection.watchlist_items.length === 0 ? (
                    <p
                      className = "py-6 text-sm"
                      style = {{ color: "#8A93A6" }}
                    >
                      No stocks in this watchlist yet.
                    </p>
                  ) : (
                    selectedCollection.watchlist_items.map((item) => { 
                      const quote = quotes[item.ticker];
                      const isPositive = (quote?.changePercentage ?? 0) >= 0;

                      return (
                        <div
                          key = {item.id}
                          className = "grid grid-cols-5 gap-4 px-4 py-3 text-sm"
                          style = {{ 
                            borderBottom: "1px solid #1E2A3D",
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >
                          <Link
                            href = {`/stocks/${item.ticker}`}
                            style = {{ color: "#EDEBE3" }}
                          >
                            {item.ticker}
                          </Link>

                          <span style = {{ color: "#B8BFCC" }}>
                            {quote ? `$${quote.price.toFixed(2)}` : "Loading..."}
                          </span>

                          <span
                            style = {{ 
                              color: quote
                                ? isPositive
                                  ? "#7FA37A"
                                  : "#B5675A"
                                : "#8A93A6",
                            }}
                          >
                            {quote
                              ? `${isPositive ? "+" : ""}${quote.changePercentage.toFixed(2)}%`
                              : "-"}
                          </span>

                          <span style = {{ color: "#B8BFCC" }}>
                            {item.created_at.slice(0, 10)}
                          </span>

                          <button
                            type = "button"
                            onClick = {() => void removeTicker(item.id)}
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
              </>
            ) : (
                <p
                  className = "text-sm"
                  style = {{ color: "#8A93A6" }}
                >
                  Create a watchlist from the panel on the left.
                </p>
            )}
          </section>
        </div>
      </section>
    </main>
  )
}