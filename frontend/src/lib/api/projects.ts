import { apiFetch } from "@/lib/api";
import type { Project, ProjectMembership, ProjectRole } from "@/lib/api/me";

export type ProjectInput = {
  name: string;
  description?: string | null;
};

export function listMyProjects(): Promise<ProjectMembership[]> {
  return apiFetch<ProjectMembership[]>("/projects");
}

export function getProject(id: number): Promise<ProjectMembership> {
  return apiFetch<ProjectMembership>(`/projects/${id}`);
}

export function createProject(input: ProjectInput): Promise<Project> {
  return apiFetch<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateProject(
  id: number,
  input: Partial<ProjectInput>,
): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteProject(id: number): Promise<void> {
  return apiFetch<void>(`/projects/${id}`, { method: "DELETE" });
}

export type Member = {
  user_id: string;
  role: ProjectRole;
  joined_at: string;
  email: string | null;
  full_name: string | null;
  avatar_url: string | null;
};

export function listMembers(projectId: number): Promise<Member[]> {
  return apiFetch<Member[]>(`/projects/${projectId}/members`);
}

export function inviteMember(
  projectId: number,
  email: string,
  role: ProjectRole,
): Promise<Member> {
  return apiFetch<Member>(`/projects/${projectId}/members`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

export function updateMemberRole(
  projectId: number,
  userId: string,
  role: ProjectRole,
): Promise<Member> {
  return apiFetch<Member>(`/projects/${projectId}/members/${userId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export function removeMember(projectId: number, userId: string): Promise<void> {
  return apiFetch<void>(`/projects/${projectId}/members/${userId}`, {
    method: "DELETE",
  });
}
