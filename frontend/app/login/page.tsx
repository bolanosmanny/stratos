"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {supabase } from "@/lib/supabaseClient";

export default function Login() { 
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState("");
    const router = useRouter();

    const handleLogin = async () => {
        const { error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (error) {
            setMessage("Error: " + error.message);
        } else {
            router.push("/");
        }
    };

    return ( 
        <main
            className="min-h-screen flex items-center justify-center"
            style={{ backgroundColor: "#0B1120", color: "#EDEBE3", fontFamily: "Inter, sans-serif" }}
        >
            <div className="w-full max-w-sm px-6">
                <p
                    className="text-xs uppercase mb-2 text-center"
                    style={{ letterSpacing: "0.15em", color: "#8A93A6", fontFamily: "'IBM Plex Mono', monospace" }}
                >
                    Stratos
                </p>
                <h1 className="text-2xl font-semibold mb-8 text-center" style={{ color: "#EDEBE3" }}>
                    Log In
                </h1>

                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-2.5 text-sm rounded-sm mb-3 focus:outline-none"
                    style={{
                        backgroundColor: "#0E1726",
                        border: "1px solid #1E2A3D",
                        color: "#EDEBE3",
                        fontFamily: "'IBM Plex Mono', monospace",
                    }}
                />
                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                    className="w-full px-4 py-2.5 text-sm rounded-sm mb-4 focus:outline-none"
                    style={{
                        backgroundColor: "#0E1726",
                        border: "1px solid #1E2A3D",
                        color: "#EDEBE3",
                        fontFamily: "'IBM Plex Mono', monospace",
                    }}
                />

                <button
                    onClick={handleLogin}
                    className="w-full px-4 py-2.5 text-sm rounded-sm font-medium mb-4 transition-opacity hover:opacity-90"
                    style={{ backgroundColor: "#C9963C", color: "#0B1220" }}
                >
                    Log In
                </button>

                {message && (
                    <p className="text-xs mb-4" style={{ color: "#B5675A" }}>
                        {message}
                    </p>
                )}

                <p className="text-xs text-center" style={{ color: "#8A93A6" }}>
                    Don&apos;t have an account?{" "}
                    <Link href="/signup" style={{ color: "C9963C" }}>
                        Sign Up
                    </Link>
                </p>
            </div>
        </main>
    );
}