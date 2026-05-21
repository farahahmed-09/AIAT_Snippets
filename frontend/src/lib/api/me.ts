import { apiFetch } from "@/lib/api";

export type ProjectRole = "manager" | "editor" | "viewer";

export type Profile = {
  id: string;
  email: string | null;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
};

export type Project = {
  id: number;
  name: string;
  description: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectMembership = {
  project: Project;
  role: ProjectRole;
};

export type MeResponse = {
  profile: Profile;
  memberships: ProjectMembership[];
};

export function getMe(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/me");
}
