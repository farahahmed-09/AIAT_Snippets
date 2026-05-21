import { apiFetch } from "@/lib/api";

export type Snippet = {
  id: number;
  session_id: number;
  name: string;
  summary: string | null;
  start_second: number;
  end_second: number;
  intro_id: number | null;
  style_name: string | null;
  storage_link: string | null;
  is_persisted: boolean;
  created_at: string;
};

export type SnippetUpdateInput = {
  name?: string;
  summary?: string | null;
  start_second?: number;
  end_second?: number;
};

export function listSessionSnippets(sessionId: number): Promise<Snippet[]> {
  return apiFetch<Snippet[]>(`/sessions/${sessionId}/snippets`);
}

export function updateSnippet(
  snippetId: number,
  input: SnippetUpdateInput,
): Promise<Snippet> {
  return apiFetch<Snippet>(`/snippets/${snippetId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteSnippet(snippetId: number): Promise<void> {
  return apiFetch<void>(`/snippets/${snippetId}`, { method: "DELETE" });
}

export function renderSnippet(
  snippetId: number,
): Promise<{ task_id: string; status: string }> {
  return apiFetch(`/snippets/${snippetId}/render`, { method: "POST" });
}

export function processSession(
  sessionId: number,
): Promise<{ task_id: string; status: string }> {
  return apiFetch(`/sessions/${sessionId}/process`, { method: "POST" });
}

export function retrySession(
  sessionId: number,
): Promise<{ task_id: string; status: string }> {
  return apiFetch(`/sessions/${sessionId}/retry`, { method: "POST" });
}

export function renderAllSnippets(
  sessionId: number,
): Promise<{
  session_id: number;
  tasks: { snippet_id: number; task_id: string }[];
}> {
  return apiFetch(`/sessions/${sessionId}/snippets/render-all`, {
    method: "POST",
  });
}

export type TaskStatusResponse = {
  task_id: string;
  status: string;
  ready: boolean;
  info?: { message?: string; progress?: number };
  result?: unknown;
  error?: string;
};

export function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  return apiFetch<TaskStatusResponse>(`/snippet-tasks/${taskId}`);
}

export function formatSeconds(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
