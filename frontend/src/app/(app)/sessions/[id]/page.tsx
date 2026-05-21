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
import { createClient } from "@/lib/supabase/server";

export default async function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sessionId = Number(id);
  if (!Number.isFinite(sessionId)) notFound();

  const supabase = await createClient();
  const { data: session } = await supabase
    .from("session")
    .select("*")
    .eq("id", sessionId)
    .maybeSingle();
  if (!session) notFound();

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
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">
              {session.name}
            </h1>
            <Badge variant={statusVariant(session.job_status)}>
              {session.job_status}
            </Badge>
          </div>
          {session.module ? (
            <p className="mt-1 text-sm text-muted-foreground">{session.module}</p>
          ) : null}
        </div>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Editor</CardTitle>
          <CardDescription>
            Player, waveform timeline, and snippet list will land here in
            Phase 6 once the pipeline produces snippets.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div>
            <span className="text-muted-foreground">Source: </span>
            <a
              href={session.drive_link}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              {session.drive_link}
            </a>
          </div>
          {session.speaker_name ? (
            <div>
              <span className="text-muted-foreground">Speaker: </span>
              {session.speaker_name}
              {session.speaker_title ? `, ${session.speaker_title}` : null}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
