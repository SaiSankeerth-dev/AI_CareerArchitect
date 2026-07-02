"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE, ROLES, getToken } from "@/lib/api";

export default function Setup() {
  const router = useRouter();
  const [role, setRole] = useState(ROLES[0].key);
  const [links, setLinks] = useState<string[]>([""]);
  const [resume, setResume] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const form = new FormData();
      form.set("target_role", role);
      form.set(
        "links",
        JSON.stringify(links.map((l) => l.trim()).filter(Boolean))
      );
      if (resume) form.set("resume", resume);
      const response = await fetch(`${API_BASE}/runs`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      });
      if (!response.ok) throw new Error((await response.json()).detail ?? "Failed");
      const run = await response.json();
      router.push(`/run/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
      setBusy(false);
    }
  }

  return (
    <main className="max-w-2xl">
      <h1 className="text-2xl font-bold">New career analysis</h1>
      <p className="mt-1 text-sm text-slate-400">
        Pick your target role and share the public links you want analyzed.
        Only public pages are read — nothing is modified without approval.
      </p>

      <form onSubmit={submit} className="mt-6 space-y-6">
        <div>
          <label className="mb-2 block text-sm font-medium">Target role</label>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {ROLES.map((r) => (
              <button
                type="button"
                key={r.key}
                onClick={() => setRole(r.key)}
                className={`rounded-lg border px-3 py-2 text-sm ${
                  role === r.key
                    ? "border-accent bg-accent/20 text-white"
                    : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium">
            Profile links (GitHub, LinkedIn, portfolio, LeetCode, Kaggle…)
          </label>
          {links.map((link, i) => (
            <input
              key={i}
              type="url"
              placeholder="https://github.com/yourname"
              value={link}
              onChange={(e) => {
                const next = [...links];
                next[i] = e.target.value;
                setLinks(next);
              }}
              className="mb-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 outline-none focus:border-accent"
            />
          ))}
          <button
            type="button"
            onClick={() => setLinks([...links, ""])}
            className="text-sm text-accent hover:underline"
          >
            + Add another link
          </button>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium">
            Resume (PDF / DOCX / TXT, parsed locally)
          </label>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => setResume(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-800 file:px-4 file:py-2 file:text-slate-200"
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          disabled={busy}
          className="rounded-lg bg-accent px-6 py-2.5 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {busy ? "Starting…" : "Run analysis"}
        </button>
      </form>
    </main>
  );
}
