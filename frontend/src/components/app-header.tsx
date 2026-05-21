import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { AppHeaderActions } from "@/components/app-header-actions";
import { LogoMark } from "@/components/logo-mark";
import { UserMenu } from "@/components/user-menu";
import type { ProjectOption } from "@/components/project-switcher";
import type { ProjectRole } from "@/lib/api/me";

type MembershipRow = {
  role: ProjectRole;
  projects: { id: number; name: string } | null;
};

export async function AppHeader({
  activeProjectId,
  breadcrumb,
  trailing,
}: {
  activeProjectId?: number;
  breadcrumb?: React.ReactNode;
  trailing?: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { data: profile } = await supabase
    .from("profiles")
    .select("full_name, avatar_url, email")
    .eq("id", user!.id)
    .maybeSingle();

  const { data: rows } = (await supabase
    .from("project_members")
    .select("role, projects(id, name)")
    .order("joined_at", { ascending: false })) as { data: MembershipRow[] | null };

  const projects: ProjectOption[] = (rows ?? [])
    .filter((r) => r.projects !== null)
    .map((r) => ({
      id: r.projects!.id,
      name: r.projects!.name,
      role: r.role,
    }));

  const active = projects.find((p) => p.id === activeProjectId) ?? projects[0] ?? null;

  return (
    <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
      <div className="flex h-14 items-center gap-3 px-4">
        <Link href="/projects" className="shrink-0">
          <LogoMark />
        </Link>
        {active ? <span className="text-muted-foreground">·</span> : null}
        <AppHeaderActions active={active} projects={projects} />
        {breadcrumb ? (
          <>
            <span className="text-muted-foreground">›</span>
            <div className="min-w-0 text-sm text-muted-foreground">{breadcrumb}</div>
          </>
        ) : null}
        <div className="ml-auto flex items-center gap-2">
          {trailing}
          <UserMenu
            email={profile?.email ?? user?.email}
            fullName={profile?.full_name}
            avatarUrl={profile?.avatar_url}
            activeProjectName={active?.name}
            activeRole={active?.role}
          />
        </div>
      </div>
    </header>
  );
}
