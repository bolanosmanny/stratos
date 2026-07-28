"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";

type Profile = { 
    display_name: string | null;
    created_at: string;
};

export default function ProfilePage() { 
    const router = useRouter();

    const [email, setEmail] = useState("");
    const [displayName, setDisplayName] = useState("");
    const [createdAt, setCreatedAt] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [status, setStatus] = useState("");

    useEffect(() => {
        let isActive = true;

        supabase.auth.getUser().then(({ data: userData }) => {
            const user = userData.user;

            if (!user) { 
                router.replace("/login");
                return;
            }

            if (!isActive) {
                return;
            }

            setEmail(user.email ?? "");

            supabase
                .from("profiles")
                .select("display_name, created_at")
                .eq("id", user.id)
                .maybeSingle()
                .then(({data, error}) => { 
                    if (!isActive) { 
                        return;
                    }

                    if (error) { 
                        setStatus(`Error: ${error.message}`);
                    } else { 
                        const profile = data as Profile | null;

                        setDisplayName(
                            profile?.display_name ?? 
                                (user.email?.split("@")[0] ?? "")
                        );
                        setCreatedAt(profile?.created_at ?? "");
                    }

                    setLoading(false);
                });
        });

        return () => { 
            isActive = false;
        };     
    }, [router]);

    const saveProfile = async () => { 
        const trimmedName = displayName.trim();

        if (!trimmedName) { 
            setStatus("Enter a display name.");
            return;
        }

        setSaving(true);
        setStatus("");

        const { data: userData } = await supabase.auth.getUser();

        if (!userData.user) { 
            router.replace("/login");
            return;
        }

        const { error } = await supabase.from("profiles").upsert(
            { 
                id: userData.user.id,
                display_name: trimmedName,
                updated_at: new Date().toISOString(),
            },
            {
                onConflict: "id",
            }
        );

        if (error) { 
            setStatus(`Error: ${error.message}`);           
        } else { 
            setStatus("Profile saved.");
        }

        setSaving(false);
    };

    const signOut = async () => { 
        await supabase.auth.signOut();
        router.push("/login");
    };

    const joinedDate = createdAt
        ? new Date(createdAt).toLocaleDateString("en-US", { 
            month: "long",
            year: "numeric",
          })
        : "-";

    if (loading) { 
        return ( 
            <main
                className = "min-h-screen flex items-center justify-center"
                style = {{ 
                    backgroundColor: "#0B1120",
                    color: "#8A93A6",
                    fontFamily: "Inter, sans-serif",
                }}
            >
                Loading profile...
            </main>
        );
    }

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
                    style = {{ color: "#8A93A6" }}
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
                    href="/research"
                    className = "text-sm"
                    style = {{ color: "#8A93A6" }}
                >
                    Sparky AI
                </Link>

                <Link
                    href="/portfolio"
                    className = "text-sm"
                    style = {{ color: "#8A93A6" }}
                >
                    Portfolio
                </Link>

                <Link
                    href="/profile"
                    className = "text-sm"
                    style = {{ color: "#8A93A6" }}
                >
                    Profile
                </Link>
            </nav>

            <section className = "max-w-3xl mx-auto px-6 py-14">
                <p
                    className = "text-xs uppercase mb-2"
                    style = {{ 
                        letterSpacing: "0.15em",
                        color: "#8A93A6",
                        fontFamily: "'IBM Plex Mono', monospace",
                    }}
                >
                    Account Settings
                </p>

                <h1 className = "text-4xl font-semibold"> Your Profile</h1>

                <p
                    className = "mt-3 text-base"
                    style = {{ color: "#B8BFCC" }}
                >
                    Manage the account connected to your research workspace
                </p>

                <section
                    className = "mt-10 p-6"
                    style = {{
                        border: "1px solid #1E2A3D",
                        backgroundColor: "#0E1726",
                    }}
                >
                    <div className = "grid gap-6 md:grid-cols-2">
                        <div>
                            <p
                                className = "text-xs uppercase"
                                style = {{ 
                                    color: "#8A93A6",
                                    letterSpacing: "0.08em",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            >
                                Email
                            </p>

                            <p
                                className = "mt-2 text-sm"
                                style = {{
                                    color: "#EDEBE3",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            >
                                {email}
                            </p>
                        </div>

                        <div>
                            <p
                                className = "text-xs uppercase"
                                style = {{ 
                                    color: "#8A93A6",
                                    letterSpacing: "0.08em",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            >
                                Member Since
                            </p>

                            <p
                                className = "mt-2 text-sm"
                                style = {{ 
                                    color: "#EDEBE3",
                                    fontFamily: "'IBM Plex Mono', monospace",
                                }}
                            >
                                {joinedDate}
                            </p>
                        </div>
                    </div>

                    <div className = "mt-8">
                        <label
                            htmlFor = "displayName"
                            className = "block text-xs uppercase"
                            style = {{
                                color: "#8A93A6",
                                letterSpacing: "0.08em",
                                fontFamily: "'IBM Plex Mono', monospace",
                            }}
                        >
                            Display Name
                        </label>

                        <input
                            id = "displayName"
                            type = "text"
                            maxLength = {50}
                            value = {displayName}
                            onChange={(event) => 
                                setDisplayName(event.target.value)       
                            }
                            className = "w-full mt-3 px-4 py-3 text-sm rounded-sm focus:outline-none"
                            style = {{ 
                                backgroundColor: "#0B1120",
                                border: "1px solid #1E2A3D",
                                color: "#EDEBE3",
                                fontFamily: "'IBM Plex Mono', monospace",
                            }}
                        />
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

                    <div className = "flex flex-wrap items-center justify-between gap-4 mt-8">
                        <button
                            type = "button"
                            disabled = {saving}
                            onClick = {() => void saveProfile()}
                            className = "px-5 py-3 text-sm rounded-sm font-medium disabled:opacity-50"
                            style = {{
                                backgroundColor: "#C9963C",
                                color: "#0B1120",
                            }}
                        >
                            {saving ? "Saving..." : "Save Profile"}
                        </button>

                        <button
                            type = "button"
                            onClick ={() => void signOut()}
                            className = "text-sm"
                            style = {{ color: "#B5675A" }}
                        >
                            Sign Out
                        </button>
                    </div>
                </section>
            </section>
        </main>
    );
}
