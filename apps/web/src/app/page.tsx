"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken, getToken } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { access_token } = await api<{ access_token: string }>(
        `/auth/${mode}`,
        { method: "POST", body: JSON.stringify({ email, password }) }
      );
      setToken(access_token);
      router.push("/setup");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="grid gap-12 md:grid-cols-2 md:items-center">
      <section>
        <h1 className="text-4xl font-bold leading-tight">
          Your career, engineered.{" "}
          <span className="text-accent">100% truthful.</span>
        </h1>
        <p className="mt-4 text-slate-300">
          AI Career Architect reads your real LinkedIn, GitHub, resume,
          portfolio and coding profiles, benchmarks them against your target
          role, and proposes evidence-backed improvements. Nothing is ever
          fabricated, and nothing is applied without your approval.
        </p>
        <ul className="mt-6 space-y-2 text-sm text-slate-400">
          <li>• 29 specialized agents analyze every platform in parallel</li>
          <li>• Every suggestion cites evidence from your own profiles</li>
          <li>• Runs 100% free on local AI models (Ollama)</li>
          <li>• Career dashboard: scores, gaps, roadmap, learning plan</li>
        </ul>
        {getToken() && (
          <a
            href="/setup"
            className="mt-6 inline-block rounded-lg bg-accent px-5 py-2.5 font-medium text-white hover:bg-indigo-500"
          >
            Start a new analysis →
          </a>
        )}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="mb-4 flex gap-2 text-sm">
          <button
            onClick={() => setMode("register")}
            className={`rounded-md px-3 py-1.5 ${mode === "register" ? "bg-accent text-white" : "bg-slate-800 text-slate-300"}`}
          >
            Sign up
          </button>
          <button
            onClick={() => setMode("login")}
            className={`rounded-md px-3 py-1.5 ${mode === "login" ? "bg-accent text-white" : "bg-slate-800 text-slate-300"}`}
          >
            Sign in
          </button>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <input
            type="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 outline-none focus:border-accent"
          />
          <input
            type="password"
            required
            minLength={8}
            placeholder="Password (min 8 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 outline-none focus:border-accent"
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            disabled={busy}
            className="w-full rounded-lg bg-accent py-2.5 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {busy ? "…" : mode === "register" ? "Create account" : "Sign in"}
          </button>
        </form>
        <p className="mt-3 text-xs text-slate-500">
          Local account, stored in your own database. No external auth
          service, no cost.
        </p>
      </section>
    </main>
  );
}
