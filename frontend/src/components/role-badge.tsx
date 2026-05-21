import { cn } from "@/lib/utils";
import type { ProjectRole } from "@/lib/api/me";

const styles: Record<ProjectRole, string> = {
  manager: "bg-role-manager text-role-manager-foreground",
  editor: "bg-role-editor text-role-editor-foreground",
  viewer: "bg-role-viewer text-role-viewer-foreground",
};

export function RoleBadge({
  role,
  withDot = false,
  className,
}: {
  role: ProjectRole;
  withDot?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded border border-transparent px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide",
        styles[role],
        className,
      )}
    >
      {withDot ? (
        <span
          className="size-1.5 rounded-full"
          style={{ background: "currentColor" }}
        />
      ) : null}
      {role}
    </span>
  );
}
