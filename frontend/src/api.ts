const BASE = "/api/v1";
const TOKEN_KEY = "vc_access_token";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Finding {
  id: string;
  fingerprint: string;
  finding_class: string;
  rule_key: string;
  title: string;
  severity: string;
  status: string;
  repository: string;
  file_path: string | null;
  line: number | null;
  package: string | null;
  cve_id: string | null;
  fixed_version: string | null;
  tool_names: string[];
  owner: string | null;
  assigned_at: string | null;
  status_reason: string | null;
  status_changed_at: string | null;
  status_changed_by: string | null;
  risk_accepted_until: string | null;
  sla_due_at: string | null;
  sla_status: "on_track" | "due_soon" | "overdue" | "none";
  first_seen: string;
  last_seen: string;
}

export interface Scan {
  id: string;
  repository: string;
  status: string;
  tool_name: string | null;
  created_at: string;
}

export interface Page<T> {
  data: T[];
  pagination: { next_cursor: string | null; has_more: boolean; limit: number };
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function problemDetail(res: Response): Promise<string> {
  try {
    const problem = (await res.json()) as { detail?: string; title?: string };
    return problem.detail ?? problem.title ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function login(username: string, password: string): Promise<TokenPair> {
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${BASE}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error(await problemDetail(res));
  const pair = (await res.json()) as TokenPair;
  localStorage.setItem(TOKEN_KEY, pair.access_token);
  return pair;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...(init?.headers ?? {}), Authorization: `Bearer ${getToken() ?? ""}` },
  });
  if (res.status === 401) {
    logout();
    window.location.reload();
  }
  if (!res.ok) throw new Error(await problemDetail(res));
  return (await res.json()) as T;
}

export interface FindingSource {
  scan_id: string;
  raw_finding_id: string;
  created_at: string;
}

export interface FindingDetail extends Finding {
  sources: FindingSource[];
  allowed_transitions: string[];
}

export interface TransitionInput {
  status: string;
  reason: string;
  risk_accepted_until?: string | null;
}

export function transitionFinding(id: string, input: TransitionInput): Promise<Finding> {
  return apiFetch<Finding>(`/findings/${id}/transition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function listFindings(params: URLSearchParams): Promise<Page<Finding>> {
  return apiFetch<Page<Finding>>(`/findings?${params.toString()}`);
}

export function getFinding(id: string): Promise<FindingDetail> {
  return apiFetch<FindingDetail>(`/findings/${id}`);
}

export function assignFinding(id: string, owner: string | null): Promise<Finding> {
  return apiFetch<Finding>(`/findings/${id}/assignment`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ owner }),
  });
}

// Fetch the branded audit report (authenticated) and open it in a new tab, where
// the user can read it or print to PDF. `since`/`until` are ISO date strings.
export async function openAuditReport(since: string, until: string): Promise<void> {
  const params = new URLSearchParams({
    since: `${since}T00:00:00Z`,
    until: `${until}T23:59:59Z`,
  });
  const res = await fetch(`${BASE}/reports/audit?${params.toString()}`, {
    headers: { Authorization: `Bearer ${getToken() ?? ""}` },
  });
  if (!res.ok) throw new Error(await problemDetail(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener");
  // Revoke shortly after so the new tab has time to load the document.
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function uploadScan(file: File, repository: string): Promise<Scan> {
  const form = new FormData();
  form.append("file", file);
  form.append("repository", repository);
  return apiFetch<Scan>("/scans", { method: "POST", body: form });
}
