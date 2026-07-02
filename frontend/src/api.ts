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
  tool_names: string[];
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
}

export function listFindings(params: URLSearchParams): Promise<Page<Finding>> {
  return apiFetch<Page<Finding>>(`/findings?${params.toString()}`);
}

export function getFinding(id: string): Promise<FindingDetail> {
  return apiFetch<FindingDetail>(`/findings/${id}`);
}

export function uploadScan(file: File, repository: string): Promise<Scan> {
  const form = new FormData();
  form.append("file", file);
  form.append("repository", repository);
  return apiFetch<Scan>("/scans", { method: "POST", body: form });
}
