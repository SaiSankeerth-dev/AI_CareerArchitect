export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail ?? JSON.stringify(data);
    } catch {}
    throw new Error(detail);
  }
  return response.json();
}

export interface Suggestion {
  id: number;
  agent: string;
  platform: string;
  field: string;
  current: string;
  suggested: string;
  reason: string;
  benefit: string;
  evidence_ids: number[];
  status: string;
  rejection_reason: string;
  artifact_path: string;
}

export interface Report {
  run_id: number;
  scores: {
    overall: number;
    platforms: Record<string, number>;
    ats: number;
    recruiter_readiness: number;
    interview_readiness: number;
    brand_consistency: number;
  };
  gaps: {
    missing_skills: string[];
    missing_projects: string[];
    missing_certifications: string[];
    experience_notes: string[];
  };
  roadmap: { step: string; detail: string; priority: string }[];
  learning_plan: { skill: string; resource: string; url: string }[];
}

export const ROLES = [
  { key: "ai_engineer", label: "AI Engineer" },
  { key: "software_engineer", label: "Software Engineer" },
  { key: "full_stack", label: "Full Stack Developer" },
  { key: "backend", label: "Backend Engineer" },
  { key: "frontend", label: "Frontend Engineer" },
  { key: "devops", label: "DevOps Engineer" },
  { key: "data_scientist", label: "Data Scientist" },
  { key: "cybersecurity", label: "Cybersecurity Engineer" },
];
