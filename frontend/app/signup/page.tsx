"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export default function SignUp() { 
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState("");

    const handleSignUp = async () => { 
        const { data, error } = await supabase.auth.signUp({
            email,
            password,
        });

        if (error) {
            setMessage("Error: " + error.message);
        } else {
            setMessage("Success! Check your email to confirm your account.");
        }
    };

    return ( 
        <main style={{ padding: "2rem" }}>
            <h1>Sign Up</h1>
            <input 
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ display: "block", marginBottom: "1rem", padding: "0.5rem"}}
            />
            <input 
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ display: "block", marginBottom: "1rem", padding: "0.5rem"}}
            />
            <button onClick={handleSignUp} style={{ padding: "0.5rem 1rem" }}>Sign Up
            </button>
            <p>{message}</p>
        </main>
    );
}
