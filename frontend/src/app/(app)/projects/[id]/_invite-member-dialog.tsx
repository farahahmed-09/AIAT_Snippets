"use client";

import { useState, type KeyboardEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Kbd } from "@/components/kbd";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RoleBadge } from "@/components/role-badge";
import { cn } from "@/lib/utils";
import { inviteMember } from "@/lib/api/projects";
import type { ProjectRole } from "@/lib/api/me";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Chip = { value: string; valid: boolean };

export function InviteMemberDialog({
  projectId,
  projectName,
}: {
  projectId: number;
  projectName: string;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<ProjectRole>("editor");
  const [chips, setChips] = useState<Chip[]>([]);
  const [draft, setDraft] = useState("");

  function commitDraft(next = draft) {
    const trimmed = next.trim().replace(/,$/, "");
    if (!trimmed) return;
    setChips((prev) => [
      ...prev.filter((c) => c.value !== trimmed),
      { value: trimmed, valid: EMAIL_RE.test(trimmed) },
    ]);
    setDraft("");
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === "," || e.key === "Tab") {
      e.preventDefault();
      commitDraft();
    } else if (e.key === "Backspace" && !draft && chips.length) {
      setChips((prev) => prev.slice(0, -1));
    }
  }

  const mutation = useMutation({
    mutationFn: async () => {
      const valid = chips.filter((c) => c.valid).map((c) => c.value);
      if (valid.length === 0) throw new Error("Add at least one valid email.");
      const results = await Promise.allSettled(
        valid.map((email) => inviteMember(projectId, email, role)),
      );
      const failed = results.filter((r) => r.status === "rejected");
      const added = results.length - failed.length;
      return { added, failed: failed.length };
    },
    onSuccess: ({ added, failed }) => {
      toast.success(
        failed === 0
          ? `Sent ${added} invite${added === 1 ? "" : "s"}`
          : `Sent ${added}; ${failed} failed`,
      );
      setChips([]);
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["members", projectId] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" />}>
        Invite <Kbd className="ml-1">I</Kbd>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            Invite · {projectName}
          </p>
          <DialogTitle>Add members by email</DialogTitle>
          <DialogDescription>
            The recipient joins with the role you pick below.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label className="text-[11px] uppercase tracking-widest text-muted-foreground">
              Emails
            </Label>
            <div
              className="flex min-h-10 flex-wrap items-center gap-1 rounded-md border border-input bg-background px-2 py-1.5"
              onClick={(e) => {
                const input = (e.currentTarget as HTMLElement).querySelector(
                  "input",
                );
                input?.focus();
              }}
            >
              {chips.map((c) => (
                <span
                  key={c.value}
                  className={cn(
                    "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs",
                    c.valid
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-destructive/40 bg-destructive/10 text-destructive",
                  )}
                >
                  {c.value}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setChips((prev) => prev.filter((p) => p.value !== c.value));
                    }}
                    aria-label="Remove"
                  >
                    <X className="size-3" />
                  </button>
                </span>
              ))}
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={onKey}
                onBlur={() => commitDraft()}
                placeholder={chips.length ? "" : "Add another…"}
                className="min-w-32 flex-1 bg-transparent px-1 py-1 text-sm outline-none"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Press <Kbd>↵</Kbd> or comma. Invalid entries are skipped.
            </p>
          </div>

          <fieldset className="space-y-2">
            <Label className="text-[11px] uppercase tracking-widest text-muted-foreground">
              Role
            </Label>
            <RoleRadio role="manager" current={role} onChange={setRole}>
              Full control · invite, edit any session, delete project.
            </RoleRadio>
            <RoleRadio role="editor" current={role} onChange={setRole}>
              Create &amp; edit their own sessions. Can&apos;t manage members.
            </RoleRadio>
            <RoleRadio role="viewer" current={role} onChange={setRole}>
              Read-only · watch sessions and download snippets.
            </RoleRadio>
          </fieldset>
        </div>

        <DialogFooter>
          <DialogClose render={<Button type="button" variant="ghost" />}>
            Cancel
          </DialogClose>
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || chips.length === 0}
          >
            <Send className="size-4" />
            {mutation.isPending ? "Sending…" : "Send invites"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RoleRadio({
  role,
  current,
  onChange,
  children,
}: {
  role: ProjectRole;
  current: ProjectRole;
  onChange: (r: ProjectRole) => void;
  children: React.ReactNode;
}) {
  const selected = current === role;
  return (
    <label
      className={cn(
        "flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2.5 text-sm",
        selected
          ? "border-primary/60 bg-primary/5"
          : "border-border hover:bg-accent/40",
      )}
    >
      <input
        type="radio"
        name="role"
        value={role}
        checked={selected}
        onChange={() => onChange(role)}
        className="mt-1 accent-primary"
      />
      <div className="min-w-0 space-y-0.5">
        <div className="flex items-center gap-2 capitalize">
          {role}
          <RoleBadge role={role} />
        </div>
        <p className="text-xs text-muted-foreground">{children}</p>
      </div>
    </label>
  );
}
