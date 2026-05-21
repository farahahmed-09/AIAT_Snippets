import Link from "next/link";
import { notFound } from "next/navigation";
import { AppHeader } from "@/components/app-header";
import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { RoleBadge } from "@/components/role-badge";
import { createClient } from "@/lib/supabase/server";
import type { ProjectRole } from "@/lib/api/me";
import type { IntroAsset } from "@/lib/api/intro-assets";
import type { Session } from "@/lib/api/sessions";
import { IntrosTab } from "./_intros-tab";
import { MembersTab } from "./_members-tab";
import { ProjectActions } from "./_project-actions";
import { SessionsTab } from "./_sessions-tab";

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

export default async function ProjectDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { id } = await params;
  const { tab } = await searchParams;
  const projectId = Number(id);
  if (!Number.isFinite(projectId)) notFound();
  const initialTab =
    tab === "members" || tab === "intros" || tab === "sessions" ? tab : "sessions";

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

  const { data: sessionRows } = (await supabase
    .from("session")
    .select("*")
    .eq("project_id", projectId)
    .order("created_at", { ascending: false })) as { data: Session[] | null };
  const sessions = sessionRows ?? [];

  const { data: introRows } = (await supabase
    .from("intro_asset")
    .select("*")
    .eq("project_id", projectId)
    .order("created_at", { ascending: false })) as {
    data: Array<{
      id: number;
      project_id: number;
      name: string;
      video_path: string;
      thumbnail_path: string | null;
      created_by: string | null;
      created_at: string;
    }> | null;
  };
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  const bucket = "snippets";
  const intros: IntroAsset[] = (introRows ?? []).map((r) => ({
    id: r.id,
    project_id: r.project_id,
    name: r.name,
    video_url: `${supabaseUrl}/storage/v1/object/public/${bucket}/${r.video_path}`,
    thumbnail_url: r.thumbnail_path
      ? `${supabaseUrl}/storage/v1/object/public/${bucket}/${r.thumbnail_path}`
      : null,
    created_by: r.created_by,
    created_at: r.created_at,
  }));

  return (
    <>
      <AppHeader activeProjectId={projectId} />
      <main className="container mx-auto flex flex-1 flex-col gap-6 px-6 py-8">
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2 w-fit"
        render={<Link href="/projects" />}
      >
        ‹ back to projects
      </Button>

      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
            Project
          </p>
          <div className="mt-1 flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">
              {project.name}
            </h1>
            <RoleBadge role={myRole} withDot />
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

      <Tabs defaultValue={initialTab}>
        <TabsList>
          <TabsTrigger value="sessions">
            Sessions{" "}
            <span className="ml-1 text-xs opacity-60">{sessions.length}</span>
          </TabsTrigger>
          <TabsTrigger value="intros">
            Intros{" "}
            <span className="ml-1 text-xs opacity-60">{intros.length}</span>
          </TabsTrigger>
          <TabsTrigger value="members">
            Members <span className="ml-1 text-xs opacity-60">{members.length}</span>
          </TabsTrigger>
        </TabsList>
        <TabsContent value="sessions" className="pt-4">
          <SessionsTab
            projectId={projectId}
            myUserId={user.id}
            myRole={myRole}
            initialSessions={sessions}
          />
        </TabsContent>
        <TabsContent value="intros" className="pt-4">
          <IntrosTab
            projectId={projectId}
            myUserId={user.id}
            myRole={myRole}
            initialAssets={intros}
          />
        </TabsContent>
        <TabsContent value="members" className="pt-4">
          <MembersTab
            projectId={projectId}
            projectName={project.name}
            myUserId={user.id}
            myRole={myRole}
            initialMembers={members}
          />
        </TabsContent>
      </Tabs>
      </main>
    </>
  );
}
