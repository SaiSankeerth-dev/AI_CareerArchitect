import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Career Architect",
  description:
    "Truth-only AI career operating system: analyze, validate and improve your professional presence.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto max-w-5xl px-4 py-8">
          <header className="mb-8 flex items-center justify-between">
            <a href="/" className="text-xl font-bold tracking-tight">
              <span className="text-accent">AI</span> Career Architect
            </a>
            <nav className="flex gap-4 text-sm text-slate-300">
              <a href="/setup" className="hover:text-white">New Analysis</a>
              <a href="/dashboard" className="hover:text-white">Dashboard</a>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
