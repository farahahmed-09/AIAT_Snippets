import { Check } from "lucide-react";
import { LogoMark } from "@/components/logo-mark";

export function AuthRail() {
  return (
    <aside className="relative hidden flex-col justify-between bg-rail p-10 text-rail-foreground md:flex">
      <LogoMark />

      <div className="space-y-6">
        <p className="font-mono text-[11px] uppercase tracking-widest text-rail-foreground/60">
          SmartCut AI
        </p>
        <h1 className="text-3xl font-semibold leading-tight tracking-tight md:text-4xl">
          Cut long recordings
          <br />
          into shareable
          <br />
          moments.
        </h1>
        <p className="max-w-sm text-sm text-rail-foreground/70">
          Drop in a Google Drive link. We&apos;ll transcribe, segment, brand,
          and ship the snippets — you just decide which moments matter.
        </p>
        <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-rail-foreground/80">
          <li className="inline-flex items-center gap-2">
            <Check className="size-3.5 text-primary" />
            Trim on a real timeline
          </li>
          <li className="inline-flex items-center gap-2">
            <Check className="size-3.5 text-primary" />
            Branded intros &amp; outros
          </li>
        </ul>
      </div>

      <p className="font-mono text-[11px] text-rail-foreground/40">
        /snippets · internal tool
      </p>
    </aside>
  );
}
