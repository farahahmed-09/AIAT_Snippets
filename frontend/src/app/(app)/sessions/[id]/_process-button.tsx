"use client";

import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { processSession, retrySession } from "@/lib/api/snippets";
import type { JobStatus } from "@/lib/api/sessions";

type Props = {
  sessionId: number;
  status: JobStatus;
};

export function ProcessButton({ sessionId, status }: Props) {
  const router = useRouter();
  const isFailed = typeof status === "string" && status.startsWith("Failed");
  const inFlight =
    status === "Pending" ||
    (typeof status === "string" && status.startsWith("Processing"));

  const mutation = useMutation({
    mutationFn: () =>
      isFailed ? retrySession(sessionId) : processSession(sessionId),
    onSuccess: () => {
      toast.success(isFailed ? "Retry queued" : "Pipeline queued");
      router.refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const label = isFailed
    ? "Retry"
    : inFlight
      ? "Re-run pipeline"
      : "Run pipeline";

  return (
    <Button
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending || inFlight}
      variant={isFailed ? "default" : inFlight ? "outline" : "default"}
    >
      {mutation.isPending ? "Queueing…" : label}
    </Button>
  );
}
