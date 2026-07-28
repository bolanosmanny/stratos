"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";

type AuthGuardProps = { 
    children: ReactNode;
};

export default function AuthGuard({ children }: AuthGuardProps) { 
    const router = useRouter();
    const [checkingSession, setCheckingSession] = useState(true);

    useEffect(() => { 
        let isActive = true;

        supabase.auth.getUser().then(({ data: userData }) => { 
            if (!isActive) { 
                return;
            }

            if (!userData.user) { 
                router.replace("/login");
                return;
            }

            setCheckingSession(false);
        });

        return () => { 
            isActive = false;
        };
    }, [router]);

    if (checkingSession) { 
        return ( 
            <main
                className = "flex min-h-screen flex items-center justify-center"
                style = {{ 
                    backgroundColor: "#0B1120",
                    color: "#8A93A6",
                    fontFamily: "Inter, sans-serif",
                }}
            >
                Checking account session...
            </main>
        );
    }

    return <>{children}</>;
}