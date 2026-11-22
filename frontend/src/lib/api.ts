/* Typed client for the FastAPI backend.
 *
 * - Base URL from NEXT_PUBLIC_API_URL (default http://localhost:8000/api/v1).
 * - JWT access token (15 min) in localStorage, refreshed once on a 401 using
 *   the stored refresh token (7 days). If refresh fails, tokens are cleared
 *   and the user is sent back to /login.
 * - The backend returns errors as {"detail": "..."}; ApiError carries that
 *   message so pages can show it directly.
 */

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// The localhost fallback is for local development only. If a deployed site
// (served from a real domain) is still pointing at localhost, the env var
// was never set in Vercel — say so plainly in the console instead of failing
// every request with an opaque network error.
if (
  typeof window !== "undefined" &&
  API_URL.includes("localhost") &&
  !window.location.hostname.includes("localhost") &&
  window.location.hostname !== "127.0.0.1"
) {
  console.error(
    "AI Study Assistant: NEXT_PUBLIC_API_URL is not set — the app is calling " +
      "localhost:8000, which does not exist for your visitors. Set it in " +
      "Vercel (Settings → Environment Variables) and redeploy."
  );
}

const ACCESS_KEY = "asa_access_token";
const REFRESH_KEY = "asa_refresh_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let message = `Request failed (${res.status})`;
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") message = data.detail;
    else if (Array.isArray(data?.detail) && data.detail[0]?.msg)
      message = data.detail[0].msg;
  } catch {
    /* keep the default message */
  }
  return new ApiError(res.status, message);
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  // Default to JSON unless the caller sends FormData (file upload).
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401 && retry && token) {
    // Access token expired: refresh once and retry.
    if (await refreshAccessToken()) return apiFetch<T>(path, options, false);
    clearTokens();
    if (typeof window !== "undefined") window.location.href = "/login";
  }
  if (res.status === 204) return undefined as T;
  if (!res.ok) throw await parseError(res);
  return res.json() as Promise<T>;
}

/** Login uses OAuth2 form data (username = email), not JSON. */
export async function login(
  email: string,
  password: string
): Promise<{ access_token: string; refresh_token: string }> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}
