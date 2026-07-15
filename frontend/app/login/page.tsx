"use client";

import { useState } from "react";
import {supabase } from "@/lib/supabaseClient";

export default function Login() { 
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState("");

    const handleLogin = async () => {
        const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (error) {
            setMessage("Error: " + error.message);
        } else {
            setMessage("Login Successful. Welcome " + data.user.email);
        }
    };

    return ( 
        <main style={{ padding:"2rem" }}>
            <h1>Log In</h1>
            <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ display: "block", marginBottom: "1rem", padding: "0.5rem" }}
                />
            <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ display: "block", marginBottom: "1rem", padding: "0.5rem" }}
            />
            <button onClick={handleLogin} style={{ padding: "0.5rem 1rem" }}>Log In</button>
            <p>{message}</p>
        </main>
    );
}