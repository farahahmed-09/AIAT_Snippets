import { API_BASE_URL, apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export type IntroAsset = {
  id: number;
  project_id: number;
  name: string;
  video_url: string;
  thumbnail_url: string | null;
  created_by: string | null;
  created_at: string;
};

export function listIntroAssets(projectId: number): Promise<IntroAsset[]> {
  return apiFetch<IntroAsset[]>(`/projects/${projectId}/intro-assets`);
}

export async function uploadIntroAsset(
  projectId: number,
  payload: { name: string; video: File; thumbnail: File | null },
): Promise<IntroAsset> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const form = new FormData();
  form.append("name", payload.name);
  form.append("video", payload.video);
  if (payload.thumbnail) form.append("thumbnail", payload.thumbnail);

  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/intro-assets`,
    {
      method: "POST",
      headers: session
        ? { Authorization: `Bearer ${session.access_token}` }
        : undefined,
      body: form,
    },
  );

  if (!response.ok) {
    const detail = await response
      .json()
      .then((b) => b?.detail ?? response.statusText)
      .catch(() => response.statusText);
    throw new Error(detail);
  }
  return response.json();
}

export function deleteIntroAsset(assetId: number): Promise<void> {
  return apiFetch<void>(`/intro-assets/${assetId}`, { method: "DELETE" });
}
