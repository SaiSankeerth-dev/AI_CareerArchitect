"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { API_BASE, api, getToken } from "@/lib/api";

const PHASE_LABELS: Record<string, string> = {
  collect: "Collecting profiles",
  extract: "Extracting content",
  research: "Researching role & market",
  analyze: "Analyzing platforms",
  gaps: "Finding gaps",
  improve: "Drafting improvements",
  validate: "Fact-validating every suggestion",
  approve: "Preparing approval queue",
  report: "Generating career report",
};

export default function RunProgress() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [events, setEvents] = useState<string[]>([]);
  const [status, setStatus] = useState("running");
  const polled = useRef(false);

  useEffect(() => {
    let stop = false;

    async function poll() {
      // SSE via EventSource can't send Authorization headers, so poll
      // status + replayable events endpoint with fetch streaming.
      try {
        const response = await fetch(`${API_BASE}/runs/${id}/events`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        });
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (reader && !stop) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";
          for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith("data:")) continue;
            const { event } = JSON.parse(line.slice(5));
            setEvents((prev) => [...prev, event]);
            if (event === "run:done") {
              setStatus("done");
              stop = true;
            } else if (event.startsWith("run:failed")) {
              setStatus("failed");
              stop = true;
            }
          }
        }
      } catch {
        // Stream unavailable (e.g. run already finished) — check status.
        if (!polled.current) {
          polled.current = true;
          const run = await api<{ status: string }>(`/runs/${id}`);
          setStatus(
            run.status === "reviewing" || run.status === "done"
              ? "done"
              : run.status
          );
        }
      }
    }
    poll();
    return () => {
      stop = true;
    };
  }, [id]);

  const phases = Object.keys(PHASE_LABELS);
  const currentPhase = [...events]
    .reverse()
    .find((e) => e.startsWith("phase:"))
    ?.split(":")[1];
  const doneCount = phases.filter((p) =>
    events.includes(`phase:${p}:end`)
  ).length;

  return (
    <main className="max-w-2xl">
      <h1 className="text-2xl font-bold">Analysis in progress</h1>
      <div className="mt-2 h-2 w-full rounded bg-slate-800">
        <div
          className="h-2 rounded bg-accent transition-all"
          style={{ width: `${(doneCount / phases.length) * 100}%` }}
        />
      </div>

      <ol className="mt-6 space-y-2">
        {phases.map((phase) => {
          const isDone = events.includes(`phase:${phase}:end`);
          const active = currentPhase === phase && !isDone;
          return (
            <li
              key={phase}
              className={`flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm ${
                isDone
                  ? "border-emerald-800 bg-emerald-950/40 text-emerald-300"
                  : active
                    ? "border-accent bg-accent/10 text-white"
                    : "border-slate-800 bg-slate-900 text-slate-500"
              }`}
            >
              <span>{isDone ? "✓" : active ? "●" : "○"}</span>
              {PHASE_LABELS[phase]}
            </li>
          );
        })}
      </ol>

      <details className="mt-4 text-xs text-slate-500">
        <summary className="cursor-pointer">Agent log ({events.length})</summary>
        <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-900 p-3">
          {events.join("\n")}
        </pre>
      </details>

      {status === "done" && (
        <button
          onClick={() => router.push(`/run/${id}/review`)}
          className="mt-6 rounded-lg bg-accent px-6 py-2.5 font-medium text-white hover:bg-indigo-500"
        >
          Review suggestions →
        </button>
      )}
      {status === "failed" && (
        <p className="mt-6 text-red-400">
          Run failed. Check the API logs and try again.
        </p>
      )}
    </main>
  );
}
