import Link from "next/link";
import { notFound } from "next/navigation";
import { formatDistanceToNowStrict } from "date-fns";
import { AppHeader } from "@/components/app-header";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RoleBadge } from "@/components/role-badge";
import { StatusBadge } from "@/components/status-badge";
import type { Snippet } from "@/lib/api/snippets";
import type { ProjectRole } from "@/lib/api/me";
import { createClient } from "@/lib/supabase/server";
import { initials } from "@/lib/initials";
import { ProcessButton } from "./_process-button";
import { RenderAllButton } from "./_render-all-button";
import { SnippetsList } from "./_snippets-list";

export default async function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sessionId = Number(id);
  if (!Number.isFinite(sessionId)) notFound();

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) notFound();

  const { data: session } = await supabase
    .from("session")
    .select("*")
    .eq("id", sessionId)
    .maybeSingle();
  if (!session) notFound();

  const { data: membership } = await supabase
    .from("project_members")
    .select("role")
    .eq("project_id", session.project_id)
    .eq("user_id", user.id)
    .maybeSingle();
  if (!membership) notFound();

  const myRole = membership.role as ProjectRole;
  const canWrite =
    myRole === "manager" ||
    (myRole === "editor" && session.user_id === user.id);

  const { data: owner } = await supabase
    .from("profiles")
    .select("full_name, email")
    .eq("id", session.user_id)
    .maybeSingle();

  const { data: snippetRows } = (await supabase
    .from("snippet")
    .select("*")
    .eq("session_id", sessionId)
    .order("start_second", { ascending: true })) as {
    data: Snippet[] | null;
  };
  const snippets = snippetRows ?? [];
  const drivePath = stripDriveDomain(session.drive_link);

  return (
    <>
      <AppHeader
        activeProjectId={session.project_id}
        breadcrumb={
          <span className="inline-flex items-center gap-2">
            <span className="opacity-60">▶</span>
            <span className="truncate">{session.name}</span>
          </span>
        }
      />
      <main className="container mx-auto flex flex-1 flex-col gap-6 px-6 py-8">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-2 w-fit"
          render={<Link href={`/projects/${session.project_id}`} />}
        >
          ‹
        </Button>

        <header className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-muted-foreground">
                #{String(sessionId).padStart(2, "0")}
              </span>
              <h1 className="text-xl font-semibold tracking-tight">
                {session.name}
              </h1>
              <StatusBadge status={session.job_status} />
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              {session.module ? <span>{session.module}</span> : null}
              <span className="inline-flex items-center gap-1.5">
                <Avatar className="size-4">
                  <AvatarFallback className="text-[8px]">
                    {initials(owner?.full_name, owner?.email)}
                  </AvatarFallback>
                </Avatar>
                {owner?.full_name ?? owner?.email ?? "Unknown"}
              </span>
              <RoleBadge role={myRole} />
              <span>
                {formatDistanceToNowStrict(new Date(session.created_at), {
                  addSuffix: true,
                })}
              </span>
              {drivePath ? (
                <span className="font-mono">drive · {drivePath}</span>
              ) : null}
            </div>
          </div>
          {canWrite ? (
            <ProcessButton sessionId={sessionId} status={session.job_status} />
          ) : (
            <span className="inline-flex items-center gap-2 rounded-md border px-2 py-1 text-xs text-muted-foreground">
              👁 Read-only
            </span>
          )}
        </header>

        {typeof session.job_status === "string" &&
        session.job_status.startsWith("Failed") ? (
          <Card className="border-destructive/40 bg-destructive/5">
            <CardContent className="p-4 text-sm">
              <p className="font-medium text-destructive">Pipeline failed</p>
              <p className="mt-1 text-muted-foreground">
                {session.job_status.replace(/^Failed:\s*/, "")}
              </p>
              {canWrite ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  Click <strong>Retry</strong> above to re-run from scratch.
                </p>
              ) : null}
            </CardContent>
          </Card>
        ) : null}

        {session.background_image_url || session.speaker_image_url ? (
          <Card>
            <CardContent className="flex flex-wrap gap-3 p-4">
              {session.background_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={session.background_image_url}
                  alt="Background"
                  className="h-24 rounded-md border object-cover"
                />
              ) : null}
              {session.speaker_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={session.speaker_image_url}
                  alt={session.speaker_name ?? "Speaker"}
                  className="h-24 w-24 rounded-md border object-cover"
                />
              ) : null}
            </CardContent>
          </Card>
        ) : null}

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-baseline gap-3">
              <h2 className="text-sm font-mono uppercase tracking-widest text-muted-foreground">
                Snippets · {snippets.length}
              </h2>
              <p className="text-xs text-muted-foreground">
                Click a row to trim.
              </p>
            </div>
            {canWrite && snippets.length > 0 ? (
              <RenderAllButton sessionId={sessionId} count={snippets.length} />
            ) : null}
          </div>
          <SnippetsList
            sessionId={sessionId}
            canWrite={canWrite}
            initialSnippets={snippets}
          />
        </section>
      </main>
    </>
  );
}

function stripDriveDomain(url: string): string | null {
  try {
    const u = new URL(url);
    if (u.hostname.includes("drive")) return u.pathname;
    return u.pathname || null;
  } catch {
    return null;
  }
}
