import type { ReactNode } from "react";
import { Inter } from "next/font/google";

import "../app/globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
});

export const metadata = {
  title: "Tavily Polymarket Signals",
  description: "Dashboard for multi-agent Polymarket signals.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}


