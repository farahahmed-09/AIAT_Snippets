"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ChevronDown, FolderPlus, Hash, Plus, Search, Settings } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Kbd } from "@/components/kbd";
import { RoleBadge } from "@/components/role-badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { ProjectRole } from "@/lib/api/me";

export type ProjectOption = {
  id: number;
  name: string;
  role: ProjectRole;
  session_count?: number;
};

type Props = {
  active: ProjectOption;
  projects: ProjectOption[];
};

export function ProjectSwitcher({ active, projects }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q
      ? projects.filter((p) => p.name.toLowerCase().includes(q))
      : projects;
  }, [projects, query]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1.5 text-sm hover:bg-accent"
      >
        <Hash className="size-3.5 text-muted-foreground" />
        <span className="font-medium">{active.name}</span>
        <RoleBadge role={active.role} />
        <ChevronDown className="size-3.5 text-muted-foreground" />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 p-0">
        <div className="flex items-center justify-between px-3 py-2 text-[10px] uppercase tracking-widest text-muted-foreground">
          Switch project
          <Kbd>⌘K</Kbd>
        </div>
        <div className="relative border-t px-2 py-2">
          <Search className="pointer-events-none absolute left-4 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter projects"
            className="h-8 pl-8 text-sm"
          />
        </div>
        <ul className="max-h-72 overflow-y-auto border-t">
          {filtered.map((p) => {
            const isActive = p.id === active.id;
            return (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    router.push(`/projects/${p.id}`);
                  }}
                  className={cn(
                    "flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-accent",
                    isActive && "bg-accent/60",
                  )}
                >
                  <span
                    className={cn(
                      "size-1.5 rounded-full",
                      isActive ? "bg-primary" : "bg-transparent border border-border",
                    )}
                  />
                  <span className="flex-1 truncate">{p.name}</span>
                  {typeof p.session_count === "number" ? (
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {p.session_count.toString().padStart(2, "0")}
                    </span>
                  ) : null}
                  <RoleBadge role={p.role} />
                </button>
              </li>
            );
          })}
          {filtered.length === 0 ? (
            <li className="px-3 py-3 text-sm text-muted-foreground">
              No matches.
            </li>
          ) : null}
        </ul>
        <div className="border-t">
          <Link
            href="/projects?new=1"
            onClick={() => setOpen(false)}
            className="flex items-center gap-3 px-3 py-2 text-sm hover:bg-accent"
          >
            <Plus className="size-3.5 text-muted-foreground" />
            <span className="flex-1">Create project</span>
            <Kbd>⌘N</Kbd>
          </Link>
          <Link
            href="/projects"
            onClick={() => setOpen(false)}
            className="flex items-center gap-3 px-3 py-2 text-sm hover:bg-accent"
          >
            <Settings className="size-3.5 text-muted-foreground" />
            <span className="flex-1">Manage projects</span>
            <FolderPlus className="size-3.5 text-muted-foreground" />
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}
