"use client";

import { useMutation } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { renderAllSnippets } from "@/lib/api/snippets";

export function RenderAllButton({
  sessionId,
  count,
  disabled,
}: {
  sessionId: number;
  count: number;
  disabled?: boolean;
}) {
  const mutation = useMutation({
    mutationFn: () => renderAllSnippets(sessionId),
    onSuccess: ({ tasks }) => toast.success(`Queued ${tasks.length} renders`),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Button
      size="sm"
      variant="outline"
      onClick={() => mutation.mutate()}
      disabled={disabled || mutation.isPending || count === 0}
    >
      <Sparkles className="size-4" />
      {mutation.isPending ? "Queueing…" : `Render all (${count})`}
    </Button>
  );
}
