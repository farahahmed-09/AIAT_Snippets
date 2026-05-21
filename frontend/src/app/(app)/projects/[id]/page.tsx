import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { createClient } from "@/lib/supabase/server";
import type { ProjectRole } from "@/lib/api/me";
import { MembersTab } from "./_members-tab";
import { ProjectActions } from "./_project-actions";

type ProjectRow = {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

type MemberRow = {
  user_id: string;
  role: ProjectRole;
  joined_at: string;
  profiles: {
    email: string | null;
    full_name: string | null;
    avatar_url: string | null;
  } | null;
};

const roleBadgeVariant: Record<
  ProjectRole,
  "default" | "secondary" | "outline"
> = {
  manager: "default",
  editor: "secondary",
  viewer: "outline",
};

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const projectId = Number(id);
  if (!Number.isFinite(projectId)) notFound();

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) notFound();

  const { data: project } = (await supabase
    .from("projects")
    .select("*")
    .eq("id", projectId)
    .maybeSingle()) as { data: ProjectRow | null };

  const { data: myMembership } = await supabase
    .from("project_members")
    .select("role")
    .eq("project_id", projectId)
    .eq("user_id", user.id)
    .maybeSingle();

  if (!project || !myMembership) notFound();
  const myRole = myMembership.role as ProjectRole;

  const { data: memberRows } = (await supabase
    .from("project_members")
    .select(
      "user_id, role, joined_at, profiles(email, full_name, avatar_url)",
    )
    .eq("project_id", projectId)
    .order("joined_at", { ascending: true })) as { data: MemberRow[] | null };

  const members =
    (memberRows ?? []).map((r) => ({
      user_id: r.user_id,
      role: r.role,
      joined_at: r.joined_at,
      email: r.profiles?.email ?? null,
      full_name: r.profiles?.full_name ?? null,
      avatar_url: r.profiles?.avatar_url ?? null,
    })) ?? [];

  return (
    <div className="container mx-auto flex flex-1 flex-col gap-6 px-6 py-8">
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2 w-fit"
        render={<Link href="/projects" />}
      >
        ← All projects
      </Button>

      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">
              {project.name}
            </h1>
            <Badge variant={roleBadgeVariant[myRole]}>{myRole}</Badge>
          </div>
          {project.description ? (
            <p className="mt-1 text-sm text-muted-foreground">
              {project.description}
            </p>
          ) : null}
        </div>
        {myRole === "manager" ? (
          <ProjectActions
            projectId={projectId}
            initialName={project.name}
            initialDescription={project.description ?? ""}
          />
        ) : null}
      </header>

      <Tabs defaultValue="sessions">
        <TabsList>
          <TabsTrigger value="sessions">Sessions</TabsTrigger>
          <TabsTrigger value="members">
            Members <span className="ml-1 text-xs opacity-60">{members.length}</span>
          </TabsTrigger>
        </TabsList>
        <TabsContent value="sessions" className="pt-4">
          <p className="text-sm text-muted-foreground">
            Sessions will land here once the upload flow is wired (Phase 3).
          </p>
        </TabsContent>
        <TabsContent value="members" className="pt-4">
          <MembersTab
            projectId={projectId}
            myUserId={user.id}
            myRole={myRole}
            initialMembers={members}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
