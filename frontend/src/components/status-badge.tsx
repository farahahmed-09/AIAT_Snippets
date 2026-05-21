import { cn } from "@/lib/utils";

type Tone = "finished" | "processing" | "pending" | "failed" | "neutral";

function toneFor(status: string): Tone {
  const s = status.toLowerCase();
  if (s.startsWith("finish")) return "finished";
  if (s.startsWith("fail")) return "failed";
  if (s.startsWith("pending")) return "pending";
  if (s.startsWith("processing") || s.startsWith("analyz")) return "processing";
  return "neutral";
}

const styles: Record<Tone, string> = {
  finished:
    "bg-status-finished text-status-finished-foreground [--dot:var(--status-finished-foreground)]",
  processing:
    "bg-status-processing text-status-processing-foreground [--dot:var(--status-processing-foreground)]",
  pending:
    "bg-status-pending text-status-pending-foreground [--dot:var(--status-pending-foreground)]",
  failed:
    "bg-status-failed text-status-failed-foreground [--dot:var(--status-failed-foreground)]",
  neutral: "bg-muted text-muted-foreground [--dot:var(--muted-foreground)]",
};

export function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const tone = toneFor(status);
  const label = status.startsWith("Processing:")
    ? status.replace("Processing:", "").trim() || "Processing"
    : status.startsWith("Failed:")
      ? "Failed"
      : status;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded border border-transparent px-2 py-0.5 text-xs font-medium",
        styles[tone],
        className,
      )}
    >
      <span
        className="size-1.5 rounded-full"
        style={{ background: "var(--dot)" }}
      />
      {label}
    </span>
  );
}
