"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  deleteSnippet,
  formatSeconds,
  listSessionSnippets,
  renderSnippet,
  updateSnippet,
  type Snippet,
} from "@/lib/api/snippets";

type Props = {
  sessionId: number;
  canWrite: boolean;
  initialSnippets: Snippet[];
};

export function SnippetsList({ sessionId, canWrite, initialSnippets }: Props) {
  const queryClient = useQueryClient();
  const queryKey = ["snippets", sessionId] as const;
  const [editing, setEditing] = useState<number | null>(null);

  const { data: snippets = initialSnippets } = useQuery({
    queryKey,
    queryFn: () => listSessionSnippets(sessionId),
    initialData: initialSnippets,
    refetchInterval: 10_000,
  });

  const updateMutation = useMutation({
    mutationFn: (vars: {
      id: number;
      name: string;
      start: number;
      end: number;
      summary: string;
    }) =>
      updateSnippet(vars.id, {
        name: vars.name,
        start_second: vars.start,
        end_second: vars.end,
        summary: vars.summary || null,
      }),
    onSuccess: () => {
      toast.success("Snippet updated");
      setEditing(null);
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const renderMutation = useMutation({
    mutationFn: (id: number) => renderSnippet(id),
    onSuccess: () => toast.success("Render queued"),
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteSnippet(id),
    onSuccess: () => {
      toast.success("Snippet deleted");
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (snippets.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No snippets yet</CardTitle>
          <CardDescription>
            Once the pipeline runs, the LLM-proposed segments will show up here.
            You can trim, rename, and re-render each one.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <ul className="space-y-3">
      {snippets.map((s) => {
        const isEditing = editing === s.id;
        return (
          <li key={s.id}>
            <Card>
              {isEditing && canWrite ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const fd = new FormData(e.currentTarget);
                    updateMutation.mutate({
                      id: s.id,
                      name: String(fd.get("name") ?? "").trim(),
                      start: Number(fd.get("start") ?? 0),
                      end: Number(fd.get("end") ?? 0),
                      summary: String(fd.get("summary") ?? "").trim(),
                    });
                  }}
                >
                  <CardHeader className="space-y-3">
                    <div className="space-y-2">
                      <Label htmlFor={`name-${s.id}`}>Name</Label>
                      <Input
                        id={`name-${s.id}`}
                        name="name"
                        defaultValue={s.name}
                        required
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label htmlFor={`start-${s.id}`}>Start (s)</Label>
                        <Input
                          id={`start-${s.id}`}
                          name="start"
                          type="number"
                          min={0}
                          defaultValue={s.start_second}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor={`end-${s.id}`}>End (s)</Label>
                        <Input
                          id={`end-${s.id}`}
                          name="end"
                          type="number"
                          min={1}
                          defaultValue={s.end_second}
                          required
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`summary-${s.id}`}>Summary</Label>
                      <Input
                        id={`summary-${s.id}`}
                        name="summary"
                        defaultValue={s.summary ?? ""}
                      />
                    </div>
                  </CardHeader>
                  <CardContent className="flex justify-end gap-2 pt-0">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setEditing(null)}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" disabled={updateMutation.isPending}>
                      {updateMutation.isPending ? "Saving…" : "Save"}
                    </Button>
                  </CardContent>
                </form>
              ) : (
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{s.name}</p>
                        <Badge variant="outline">
                          {formatSeconds(s.start_second)}–
                          {formatSeconds(s.end_second)}
                        </Badge>
                        {s.storage_link ? (
                          <Badge>rendered</Badge>
                        ) : (
                          <Badge variant="secondary">draft</Badge>
                        )}
                      </div>
                      {s.summary ? (
                        <p className="mt-1 text-sm text-muted-foreground">
                          {s.summary}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      {s.storage_link ? (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          render={
                            <a
                              href={s.storage_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              aria-label="Download"
                            />
                          }
                        >
                          <Download className="size-4" />
                        </Button>
                      ) : null}
                      {canWrite ? (
                        <>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => renderMutation.mutate(s.id)}
                            disabled={renderMutation.isPending}
                            aria-label="Render"
                          >
                            <Play className="size-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditing(s.id)}
                          >
                            Edit
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => {
                              if (confirm(`Delete “${s.name}”?`))
                                deleteMutation.mutate(s.id);
                            }}
                            aria-label="Delete"
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </div>
                </CardHeader>
              )}
            </Card>
          </li>
        );
      })}
    </ul>
  );
}
