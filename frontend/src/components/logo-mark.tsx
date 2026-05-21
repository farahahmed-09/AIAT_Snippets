import { cn } from "@/lib/utils";

export function LogoMark({
  withWord = true,
  className,
}: {
  withWord?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span className="grid size-7 place-items-center rounded-md bg-primary font-mono text-sm font-bold text-primary-foreground">
        S/
      </span>
      {withWord ? (
        <span className="font-semibold tracking-tight">
          SmartCut <span className="text-muted-foreground">AI</span>
        </span>
      ) : null}
    </span>
  );
}
