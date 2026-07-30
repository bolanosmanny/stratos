"use client";

import { useEffect, useState } from "react";

type FilingEvent = {
    date: string;
    title: string;
    detail: string;
    source_url: string;
};

type FilingTimelineProps = {
    ticker: string;
};

function formatEventDate(date: string) { 
    return new Intl.DateTimeFormat("en-US", { 
        month: "short",
        day: "numeric",
        year: "numeric",
    }).format(new Date(`${date}T12:00:00`));
}

function eventColor(title: string) { 
    if (title.includes("Earnings")) return "#C9963C";
    if (title.includes("Annual")) return "#7FA37A";
    return "#8A93A6"
}

export default function FilingTimeline({
    ticker,
}: FilingTimelineProps) {
    const [events, setEvents] = useState<FilingEvent[]>([]);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => { 
        let isActive = true;

        const loadEvents = async () => { 
            setLoading(true);

            try { 
                const response = await fetch(
                    `http://localhost:8000/stock/${ticker}/events`
                );

                const data = await response.json();

                if (response.ok && isActive) { 
                    setEvents(
                        Array.isArray(data.events) ? data.events : []
                    );
                }
            } finally { 
                if (isActive) { 
                    setLoading(false);
                }
            }
        };

        loadEvents();

        return () => { 
            isActive = false;
        };
    }, [ticker]);

    return ( 
        <section>
            <p
                className = "text-xs uppercase"
                style = {{ 
                    letterSpacing: "0.15em",
                    color: "#8A93A6",
                    fontFamily: "'IBM Plex Mono', monospace"
                }}
            >
                Major Events Timeline
            </p>

            <p className = "mt-2 text-sm" style = {{ color: "#B8BFCC" }}>
                Recent SEC filings and earnings releases
            </p>

            {loading && (
                <p className = "mt-5 text-sm" style = {{ color: "#8A93A6" }}>
                    Loading filing events...
                </p>
            )}

            {!loading && events.length === 0 && ( 
                <p className = "mt-5 text-sm" style = {{ color: "#8A93A6" }}>
                    No recent filing events found.
                </p>
            )}

            <div className = "mt-6 space-y-1">
                {events.slice(0, 6).map((event, index) => ( 
                    <div key = {`${event.date}-${event.title}`} className = "flex gap-4">
                        <div className = "flex w-3 flex-col items-center">
                            <span
                                className = "mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
                                style = {{ backgroundColor: eventColor(event.title) }}
                            />
                            {index < events.length - 1 && (
                                <span
                                    className = "mt-1 w-px flex-1"
                                    style = {{ backgroundColor: "#1E2A3D" }}
                                />
                            )}
                        </div>

                        <a 
                            href = {event.source_url}
                            target = "_blank"
                            rel = "noreferrer"
                            className = "block pb-5 transition-opacity hover:opacity-80"
                        >

                            <p
                                className = "text-xs"
                                style = {{
                                    color: "#8A93A6",
                                    fontFamily: "'IBM Plex Mono', monospace"
                                }}
                            >
                                {formatEventDate(event.date)}
                            </p>

                            <p className = "mt-1 text-sm font-medium">
                                {event.title}
                            </p>

                            <p className = "mt-1 text-xs" style = {{ color: "#C9963C" }}>
                                {event.detail} · Open SEC filing ↗
                            </p>
                        </a>
                    </div>
                ))}
            </div>
        </section>
    )
}