import { Hash, Users } from "lucide-react";
import Link from "next/link";
import { formatDistanceToNowStrict } from "date-fns";
import { AppHeader } from "@/components/app-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RoleBadge } from "@/components/role-badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { initials } from "@/lib/initials";
import { createClient } from "@/lib/supabase/server";
import type { ProjectRole } from "@/lib/api/me";
import { NewProjectDialog } from "./_new-project-dialog";

type Row = {
  role: ProjectRole;
  joined_at: string;
  projects: {
    id: number;
    name: string;
    description: string | null;
    created_at: string;
  } | null;
};

type MemberPreview = {
  user_id: string;
  full_name: string | null;
  email: string | null;
};

export default async function ProjectsPage() {
  const supabase = await createClient();
  const { data: rows } = (await supabase
    .from("project_members")
    .select("role, joined_at, projects(id, name, description, created_at)")
    .order("joined_at", { ascending: false })) as { data: Row[] | null };

  const memberships = (rows ?? []).filter((r) => r.projects !== null);
  const projectIds = memberships.map((m) => m.projects!.id);

  const counts = await Promise.all(
    projectIds.map((id) =>
      supabase
        .from("session")
        .select("id", { count: "exact", head: true })
        .eq("project_id", id)
        .then((r) => r.count ?? 0),
    ),
  );
  const sessionCount = new Map<number, number>(
    projectIds.map((id, i) => [id, counts[i]]),
  );

  const memberPreviewsByProject = new Map<number, MemberPreview[]>();
  const memberCountByProject = new Map<number, number>();
  for (const id of projectIds) {
    const { data, count } = await supabase
      .from("project_members")
      .select("user_id, profiles(full_name, email)", { count: "exact" })
      .eq("project_id", id)
      .limit(4);
    const previews =
      ((data ?? []) as unknown as Array<{
        user_id: string;
        profiles: { full_name: string | null; email: string | null } | null;
      }>).map((m) => ({
        user_id: m.user_id,
        full_name: m.profiles?.full_name ?? null,
        email: m.profiles?.email ?? null,
      }));
    memberPreviewsByProject.set(id, previews);
    memberCountByProject.set(id, count ?? previews.length);
  }

  return (
    <>
      <AppHeader />
      <main className="container mx-auto flex flex-1 flex-col gap-6 px-6 py-8">
        <header className="flex items-end justify-between">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
              Workspaces
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              Projects{" "}
              <span className="text-muted-foreground">/ {memberships.length}</span>
            </h1>
          </div>
          <NewProjectDialog />
        </header>

        {memberships.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              No projects yet. Click <em>New project</em> to start one.
            </CardContent>
          </Card>
        ) : (
          <ul className="space-y-4">
            {memberships.map((m) => {
              const p = m.projects!;
              const sCount = sessionCount.get(p.id) ?? 0;
              const mCount = memberCountByProject.get(p.id) ?? 0;
              const previews = memberPreviewsByProject.get(p.id) ?? [];
              return (
                <li key={p.id}>
                  <ProjectRow
                    id={p.id}
                    name={p.name}
                    description={p.description}
                    createdAt={p.created_at}
                    role={m.role}
                    sessionCount={sCount}
                    memberCount={mCount}
                    members={previews}
                  />
                </li>
              );
            })}
          </ul>
        )}
      </main>
    </>
  );
}

function ProjectRow({
  id,
  name,
  description,
  createdAt,
  role,
  sessionCount,
  memberCount,
  members,
}: {
  id: number;
  name: string;
  description: string | null;
  createdAt: string;
  role: ProjectRole;
  sessionCount: number;
  memberCount: number;
  members: MemberPreview[];
}) {
  const isManager = role === "manager";
  return (
    <Card className="border-l-4 border-l-transparent transition-colors hover:bg-accent/20">
      <CardContent className="flex flex-wrap items-start gap-4 p-5">
        <div className="grid size-10 shrink-0 place-items-center rounded-md border bg-muted text-muted-foreground">
          <Hash className="size-4" />
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <Link
              href={`/projects/${id}`}
              className="text-base font-semibold tracking-tight hover:underline"
            >
              {name}
            </Link>
            <RoleBadge role={role} withDot />
          </div>
          {description ? (
            <p className="text-sm text-muted-foreground">{description}</p>
          ) : null}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span className="font-mono">
              📼 {sessionCount.toString().padStart(2, "0")} sessions
            </span>
            <span className="font-mono">
              <Users className="mr-1 inline size-3 align-[-2px]" />
              {memberCount.toString().padStart(2, "0")} members
            </span>
            <span className="font-mono">
              ⏱ created{" "}
              {formatDistanceToNowStrict(new Date(createdAt), {
                addSuffix: true,
              })}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 pt-2">
            <Button size="sm" render={<Link href={`/projects/${id}`} />}>
              Open ↗
            </Button>
            <Button
              size="sm"
              variant="outline"
              render={<Link href={`/projects/${id}?tab=members`} />}
            >
              Members
            </Button>
            {isManager ? (
              <Button
                size="sm"
                variant="ghost"
                render={<Link href={`/projects/${id}`} />}
              >
                Manage
              </Button>
            ) : null}
          </div>
        </div>
        <div className="flex shrink-0 -space-x-1.5">
          {members.slice(0, 4).map((m) => (
            <Avatar
              key={m.user_id}
              className="size-7 border-2 border-background"
            >
              <AvatarFallback className="text-[10px]">
                {initials(m.full_name, m.email)}
              </AvatarFallback>
            </Avatar>
          ))}
          {memberCount > 4 ? (
            <span className="grid size-7 place-items-center rounded-full border-2 border-background bg-muted text-[10px] text-muted-foreground">
              +
            </span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
