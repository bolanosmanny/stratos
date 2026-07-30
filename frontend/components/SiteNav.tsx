"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [ 
    { href: "/", label: "Watchlists"},
    { href: "/dashboard", label: "Research Dashboard" },
    { href: "/research", label: "Sparky Research" },
    { href: "/portfolio", label: "Portfolio" },
    { href: "/profile", label: "Profile" }
];

export default function SiteNav() { 
    const pathname = usePathname();

    return ( 
        <nav
            className = "flex items-center gap-6 overflow-x-auto px-6 py-4"
            style = {{ 
                borderBottom: "1px solid #1E2A3D",
                backgroundColor: "#0E1726",
            }}
        >
            <Link
                href = "/"
                className = "shrink-0 text-sm font-semibold"
                style = {{ 
                    color: "#EDEBE3",
                    fontFamily: "'IBM Plex Mono', monospace",
                }}
            >
                STRATOS
            </Link>

            {navItems.map((item) => { 
                const isActive = 
                    pathname === item.href || 
                    (item.href === "/dashboard" && 
                        pathname.startsWith("/stocks/"));

                return ( 
                    <Link
                        key = {item.href}
                        href = {item.href}
                        className = "shrink-0 text-sm"
                        style = {{ 
                            color: isActive ? "#EDEBE3" : "#8A93A6",
                        }}
                    >
                        {item.label}
                    </Link>
                );  
            })}
        </nav>
    );
}
            