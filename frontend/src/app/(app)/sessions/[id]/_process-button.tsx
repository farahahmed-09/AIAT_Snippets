"use client";

import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { processSession } from "@/lib/api/snippets";
import type { JobStatus } from "@/lib/api/sessions";

type Props = {
  sessionId: number;
  status: JobStatus;
};

export function ProcessButton({ sessionId, status }: Props) {
  const router = useRouter();
  const mutation = useMutation({
    mutationFn: () => processSession(sessionId),
    onSuccess: () => {
      toast.success("Pipeline queued");
      router.refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const inFlight =
    status === "Pending" ||
    (typeof status === "string" && status.startsWith("Processing"));
  const label = inFlight ? "Re-run pipeline" : "Run pipeline";

  return (
    <Button
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
      variant={inFlight ? "outline" : "default"}
    >
      {mutation.isPending ? "Queueing…" : label}
    </Button>
  );
}
