import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { statusVariant } from "@/lib/api/sessions";
import type { Snippet } from "@/lib/api/snippets";
import type { ProjectRole } from "@/lib/api/me";
import { createClient } from "@/lib/supabase/server";
import { ProcessButton } from "./_process-button";
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

  const { data: snippetRows } = (await supabase
    .from("snippet")
    .select("*")
    .eq("session_id", sessionId)
    .order("start_second", { ascending: true })) as {
    data: Snippet[] | null;
  };
  const snippets = snippetRows ?? [];

  return (
    <div className="container mx-auto flex flex-1 flex-col gap-6 px-6 py-8">
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2 w-fit"
        render={<Link href={`/projects/${session.project_id}`} />}
      >
        ← Back to project
      </Button>

      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">
              {session.name}
            </h1>
            <Badge variant={statusVariant(session.job_status)}>
              {session.job_status}
            </Badge>
            {session.module ? (
              <Badge variant="secondary">{session.module}</Badge>
            ) : null}
          </div>
          {session.speaker_name ? (
            <p className="mt-1 text-sm text-muted-foreground">
              {session.speaker_name}
              {session.speaker_title ? `, ${session.speaker_title}` : null}
            </p>
          ) : null}
        </div>
        {canWrite ? (
          <ProcessButton sessionId={sessionId} status={session.job_status} />
        ) : null}
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Source</CardTitle>
          <CardDescription>
            <a
              href={session.drive_link}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              {session.drive_link}
            </a>
          </CardDescription>
        </CardHeader>
        {session.background_image_url || session.speaker_image_url ? (
          <CardContent className="flex flex-wrap gap-3">
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
        ) : null}
      </Card>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">Snippets</h2>
          <p className="text-sm text-muted-foreground">
            {snippets.length} snippet{snippets.length === 1 ? "" : "s"}
          </p>
        </div>
        <SnippetsList
          sessionId={sessionId}
          canWrite={canWrite}
          initialSnippets={snippets}
        />
      </section>
    </div>
  );
}
