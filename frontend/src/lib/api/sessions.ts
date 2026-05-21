import { apiFetch } from "@/lib/api";

export type JobStatus = "Pending" | "Processing" | "Finished" | "Failed" | string;

export type Session = {
  id: number;
  project_id: number;
  user_id: string;
  name: string;
  module: string | null;
  drive_link: string;
  speaker_name: string | null;
  speaker_title: string | null;
  speaker_image_url: string | null;
  intro_video_url: string | null;
  background_image_url: string | null;
  job_status: JobStatus;
  source_video_stored: boolean;
  created_at: string;
  started_at: string | null;
  updated_at: string;
  completed_at: string | null;
  last_accessed_at: string | null;
};

export type SessionCreateInput = {
  name: string;
  module?: string | null;
  drive_link: string;
  speaker_name?: string | null;
  speaker_title?: string | null;
  speaker_image_url?: string | null;
  intro_video_url?: string | null;
  background_image_url?: string | null;
};

export type SessionUpdateInput = Partial<SessionCreateInput>;

export function listProjectSessions(projectId: number): Promise<Session[]> {
  return apiFetch<Session[]>(`/projects/${projectId}/sessions`);
}

export function createSession(
  projectId: number,
  input: SessionCreateInput,
): Promise<Session> {
  return apiFetch<Session>(`/projects/${projectId}/sessions`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getSession(sessionId: number): Promise<Session> {
  return apiFetch<Session>(`/sessions/${sessionId}`);
}

export function updateSession(
  sessionId: number,
  input: SessionUpdateInput,
): Promise<Session> {
  return apiFetch<Session>(`/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteSession(sessionId: number): Promise<void> {
  return apiFetch<void>(`/sessions/${sessionId}`, { method: "DELETE" });
}

export function statusVariant(
  status: JobStatus,
): "default" | "secondary" | "outline" | "destructive" {
  if (status === "Finished") return "default";
  if (status === "Failed" || status.startsWith?.("Failed")) return "destructive";
  if (status === "Pending") return "outline";
  return "secondary";
}
