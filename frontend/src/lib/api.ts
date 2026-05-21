import { createClient } from "@/lib/supabase/client";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function authHeader(): Promise<Record<string, string>> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session ? { Authorization: `Bearer ${session.access_token}` } : {};
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const auth = await authHeader();
  for (const [k, v] of Object.entries(auth)) headers.set(k, v);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const detail = await response
      .json()
      .then((b) => b?.detail ?? response.statusText)
      .catch(() => response.statusText);
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export { ApiError, API_BASE_URL };
