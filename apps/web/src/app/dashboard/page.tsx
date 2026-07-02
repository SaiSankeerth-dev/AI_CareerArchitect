"use client";

import { useEffect, useState } from "react";
import { api, Report } from "@/lib/api";

interface DashboardData {
  latest: (Report & { run_id: number }) | null;
  trend: { run_id: number; date: string; overall: number }[];
  runs?: { id: number; role: string; status: string }[];
}

function ScoreRing({ label, value }: { label: string; value: number }) {
  const hue = value >= 70 ? "text-emerald-400" : value >= 40 ? "text-amber-400" : "text-red-400";
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-center">
      <p className={`text-3xl font-bold ${hue}`}>{value}</p>
      <p className="mt-1 text-xs text-slate-400">{label}</p>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<DashboardData>("/dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error)
    return <p className="text-red-400">Failed to load dashboard: {error}. Sign in first.</p>;
  if (!data) return <p className="text-slate-500">Loading…</p>;
  if (!data.latest)
    return (
      <p className="text-slate-400">
        No completed analysis yet.{" "}
        <a href="/setup" className="text-accent hover:underline">Run your first →</a>
      </p>
    );

  const { scores, gaps, roadmap, learning_plan } = data.latest;

  return (
    <main className="space-y-8">
      <section>
        <h1 className="mb-4 text-2xl font-bold">Career Dashboard</h1>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <ScoreRing label="Overall Professional Score" value={scores.overall} />
          <ScoreRing label="ATS Score" value={scores.ats} />
          <ScoreRing label="Recruiter Readiness" value={scores.recruiter_readiness} />
          <ScoreRing label="Interview Readiness" value={scores.interview_readiness} />
          <ScoreRing label="Brand Consistency" value={scores.brand_consistency} />
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Platform scores</h2>
        <div className="space-y-2">
          {Object.entries(scores.platforms).map(([platform, score]) => (
            <div key={platform} className="flex items-center gap-3">
              <span className="w-24 text-sm capitalize text-slate-400">{platform}</span>
              <div className="h-2.5 flex-1 rounded bg-slate-800">
                <div
                  className={`h-2.5 rounded ${score >= 70 ? "bg-emerald-500" : score >= 40 ? "bg-amber-500" : "bg-red-500"}`}
                  style={{ width: `${score}%` }}
                />
              </div>
              <span className="w-8 text-right text-sm">{score}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["Missing skills", gaps.missing_skills],
          ["Missing projects", gaps.missing_projects],
          ["Missing certifications", gaps.missing_certifications],
        ].map(([title, items]) => (
          <div key={title as string} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h3 className="mb-2 text-sm font-semibold">{title as string}</h3>
            {(items as string[]).length === 0 ? (
              <p className="text-sm text-emerald-400">None — well covered ✓</p>
            ) : (
              <ul className="space-y-1 text-sm text-slate-300">
                {(items as string[]).map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Improvement roadmap</h2>
        <ol className="space-y-2">
          {roadmap.map((step, i) => (
            <li key={i} className="flex gap-3 rounded-lg border border-slate-800 bg-slate-900 p-3 text-sm">
              <span className={`mt-0.5 rounded px-1.5 text-xs ${step.priority === "high" ? "bg-red-900 text-red-200" : "bg-slate-800 text-slate-400"}`}>
                {step.priority}
              </span>
              <div>
                <p className="font-medium">{step.step}</p>
                <p className="text-slate-400">{step.detail}</p>
              </div>
            </li>
          ))}
          {roadmap.length === 0 && <p className="text-sm text-slate-500">Nothing urgent 🎉</p>}
        </ol>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Learning plan (free resources)</h2>
        <ul className="grid gap-2 md:grid-cols-2">
          {learning_plan.map((item, i) => (
            <li key={i} className="rounded-lg border border-slate-800 bg-slate-900 p-3 text-sm">
              <p className="font-medium capitalize">{item.skill}</p>
              <a href={item.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
                {item.resource}
              </a>
            </li>
          ))}
        </ul>
      </section>

      {data.trend.length > 1 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Weekly progress</h2>
          <div className="flex items-end gap-2">
            {data.trend.map((point) => (
              <div key={point.run_id} className="flex flex-col items-center gap-1">
                <div className="w-10 rounded-t bg-accent" style={{ height: `${point.overall}px` }} />
                <span className="text-xs text-slate-500">{point.overall}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
