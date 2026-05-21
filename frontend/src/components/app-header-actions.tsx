"use client";

import { useRouter } from "next/navigation";
import {
  ProjectSwitcher,
  type ProjectOption,
} from "@/components/project-switcher";

type Props = {
  active: ProjectOption | null;
  projects: ProjectOption[];
};

export function AppHeaderActions({ active, projects }: Props) {
  const router = useRouter();
  if (!active) return null;

  return (
    <ProjectSwitcher
      active={active}
      projects={projects}
      onSelect={(id) => router.push(`/projects/${id}`)}
      onCreate={() => router.push("/projects?new=1")}
      onManage={() => router.push("/projects")}
    />
  );
}
