"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNowStrict } from "date-fns";
import { ArrowUpRight, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import {
  deleteSession,
  listProjectSessions,
  type Session,
} from "@/lib/api/sessions";
import type { ProjectRole } from "@/lib/api/me";
import { NewSessionDialog } from "./_new-session-dialog";

type Props = {
  projectId: number;
  myUserId: string;
  myRole: ProjectRole;
  initialSessions: Session[];
};

export function SessionsTab({
  projectId,
  myUserId,
  myRole,
  initialSessions,
}: Props) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const queryKey = ["sessions", projectId] as const;

  const { data: sessions = initialSessions } = useQuery({
    queryKey,
    queryFn: () => listProjectSessions(projectId),
    initialData: initialSessions,
    refetchInterval: (q) => {
      const data = q.state.data as Session[] | undefined;
      const active = data?.some(
        (s) => s.job_status === "Pending" || s.job_status === "Processing",
      );
      return active ? 5000 : false;
    },
  });

  const canWrite = myRole === "manager" || myRole === "editor";

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteSession(id),
    onSuccess: () => {
      toast.success("Session deleted");
      queryClient.invalidateQueries({ queryKey });
      router.refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const canDelete = (s: Session) =>
    myRole === "manager" || (myRole === "editor" && s.user_id === myUserId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {sessions.length} session{sessions.length === 1 ? "" : "s"}
        </p>
        {canWrite ? <NewSessionDialog projectId={projectId} /> : null}
      </div>

      {sessions.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No sessions yet</CardTitle>
            <CardDescription>
              {canWrite
                ? "Click New session above to drop in a Google Drive link and start the pipeline."
                : "An editor or manager has to add the first session."}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <ul className="space-y-2">
          {sessions.map((s, i) => (
            <li key={s.id}>
              <Card className="transition-colors hover:bg-accent/20">
                <CardHeader className="flex flex-row items-center gap-4 p-4">
                  <span className="font-mono text-xs text-muted-foreground">
                    #{String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/sessions/${s.id}`}
                        className="truncate font-medium hover:underline"
                      >
                        {s.name}
                      </Link>
                      {s.module ? (
                        <Badge variant="secondary">{s.module}</Badge>
                      ) : null}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {formatDistanceToNowStrict(new Date(s.created_at), {
                        addSuffix: true,
                      })}
                    </p>
                  </div>
                  <StatusBadge status={s.job_status} />
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    render={<Link href={`/sessions/${s.id}`} />}
                    aria-label="Open session"
                  >
                    <ArrowUpRight className="size-4" />
                  </Button>
                  {canDelete(s) ? (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={(e) => {
                        e.preventDefault();
                        if (confirm(`Delete “${s.name}”?`))
                          deleteMutation.mutate(s.id);
                      }}
                      aria-label="Delete session"
                    >
                      <Trash2 className="size-4 text-destructive" />
                    </Button>
                  ) : null}
                </CardHeader>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
