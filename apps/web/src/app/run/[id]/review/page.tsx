"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, Suggestion } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  validated: "bg-slate-700 text-slate-200",
  approved: "bg-emerald-800 text-emerald-100",
  declined: "bg-slate-800 text-slate-500",
  rejected: "bg-red-900 text-red-200",
  applied: "bg-indigo-800 text-indigo-100",
  verified: "bg-emerald-700 text-white",
};

export default function Review() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [busy, setBusy] = useState(false);
  const [showRejected, setShowRejected] = useState(false);

  async function load() {
    setSuggestions(await api<Suggestion[]>(`/runs/${id}/suggestions`));
  }
  useEffect(() => {
    load().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function decide(suggestionId: number, approve: boolean) {
    await api(`/suggestions/${suggestionId}/decision`, {
      method: "POST",
      body: JSON.stringify({ approve }),
    });
    await load();
  }

  async function applyApproved() {
    setBusy(true);
    try {
      await api(`/runs/${id}/apply`, { method: "POST" });
      await load();
    } finally {
      setBusy(false);
    }
  }

  const active = suggestions.filter((s) => s.status !== "rejected");
  const rejected = suggestions.filter((s) => s.status === "rejected");
  const approvedCount = active.filter((s) => s.status === "approved").length;
  const appliedCount = active.filter(
    (s) => s.status === "applied" || s.status === "verified"
  ).length;

  return (
    <main>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Review suggestions</h1>
          <p className="text-sm text-slate-400">
            Current → Suggested → Reason → Benefit. You approve each change;
            approved items become ready-to-apply artifacts. Nothing touches
            your accounts silently.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={applyApproved}
            disabled={busy || approvedCount === 0}
            className="rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
          >
            Apply {approvedCount} approved
          </button>
          <button
            onClick={() => router.push("/dashboard")}
            className="rounded-lg border border-slate-700 px-5 py-2 text-sm hover:border-slate-500"
          >
            Dashboard →
          </button>
        </div>
      </div>

      {appliedCount > 0 && (
        <p className="mt-3 rounded-lg border border-indigo-800 bg-indigo-950/50 px-4 py-2 text-sm text-indigo-200">
          {appliedCount} artifact(s) generated under{" "}
          <code>apps/api/data/output/run_{id}/</code> — apply them to your
          accounts, then re-run analysis to verify.
        </p>
      )}

      <div className="mt-6 space-y-4">
        {active.map((s) => (
          <article
            key={s.id}
            className="rounded-xl border border-slate-800 bg-slate-900 p-5"
          >
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded bg-accent/20 px-2 py-0.5 font-medium uppercase text-accent">
                {s.platform}
              </span>
              <span className="text-slate-400">{s.field}</span>
              <span
                className={`ml-auto rounded px-2 py-0.5 ${STATUS_STYLES[s.status] ?? ""}`}
              >
                {s.status}
              </span>
              <span className="text-slate-600">
                evidence: {s.evidence_ids.length} item(s)
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-lg bg-slate-950 p-3">
                <p className="mb-1 text-xs font-medium text-slate-500">CURRENT</p>
                <p className="whitespace-pre-wrap text-sm text-slate-300">
                  {s.current || "—"}
                </p>
              </div>
              <div className="rounded-lg bg-slate-950 p-3">
                <p className="mb-1 text-xs font-medium text-emerald-500">SUGGESTED</p>
                <p className="max-h-48 overflow-auto whitespace-pre-wrap text-sm">
                  {s.suggested}
                </p>
              </div>
            </div>
            <p className="mt-3 text-sm text-slate-400">
              <span className="font-medium text-slate-300">Reason:</span> {s.reason}
            </p>
            <p className="mt-1 text-sm text-slate-400">
              <span className="font-medium text-slate-300">Benefit:</span> {s.benefit}
            </p>
            {s.status === "validated" && (
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => decide(s.id, true)}
                  className="rounded-lg bg-emerald-700 px-4 py-1.5 text-sm font-medium hover:bg-emerald-600"
                >
                  Approve
                </button>
                <button
                  onClick={() => decide(s.id, false)}
                  className="rounded-lg border border-slate-700 px-4 py-1.5 text-sm hover:border-slate-500"
                >
                  Decline
                </button>
              </div>
            )}
            {s.artifact_path && (
              <p className="mt-2 text-xs text-indigo-300">
                Artifact: <code>{s.artifact_path}</code>
              </p>
            )}
          </article>
        ))}
        {active.length === 0 && (
          <p className="text-slate-500">No suggestions yet.</p>
        )}
      </div>

      {rejected.length > 0 && (
        <section className="mt-8">
          <button
            onClick={() => setShowRejected(!showRejected)}
            className="text-sm text-slate-500 hover:text-slate-300"
          >
            {showRejected ? "▾" : "▸"} {rejected.length} suggestion(s) rejected
            by fact validation (transparency log)
          </button>
          {showRejected &&
            rejected.map((s) => (
              <article
                key={s.id}
                className="mt-2 rounded-lg border border-red-900/50 bg-red-950/20 p-4 text-sm"
              >
                <p className="text-slate-400">{s.suggested}</p>
                <p className="mt-1 text-red-300">✕ {s.rejection_reason}</p>
              </article>
            ))}
        </section>
      )}
    </main>
  );
}
