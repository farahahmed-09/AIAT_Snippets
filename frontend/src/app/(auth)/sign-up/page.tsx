"use client";

import Link from "next/link";
import { useActionState, useState } from "react";
import { ArrowUpRight, Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { signUp } from "./actions";

function strength(pw: string): { score: 0 | 1 | 2 | 3 | 4; hint: string } {
  let score = 0;
  if (pw.length >= 10) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return {
    score: Math.min(score, 4) as 0 | 1 | 2 | 3 | 4,
    hint: "≥10 characters · mix letters and numbers",
  };
}

export default function SignUpPage() {
  const [state, formAction, pending] = useActionState(signUp, undefined);
  const [pw, setPw] = useState("");
  const [show, setShow] = useState(false);
  const { score, hint } = strength(pw);
  const bars = [0, 1, 2, 3];

  return (
    <div className="w-full max-w-sm space-y-6">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
          Get started
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Create account</h1>
      </div>

      <form action={formAction} className="space-y-4">
        <Field id="full_name" label="Full name" icon={<User className="size-4" />}>
          <Input
            id="full_name"
            name="full_name"
            type="text"
            autoComplete="name"
            required
            disabled={pending}
            className="pl-9"
          />
        </Field>

        <Field id="email" label="Email" icon={<Mail className="size-4" />}>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            disabled={pending}
            placeholder="sami@acme.com"
            className="pl-9"
          />
        </Field>

        <div className="space-y-2">
          <Label
            htmlFor="password"
            className="text-[11px] uppercase tracking-widest text-muted-foreground"
          >
            Password
          </Label>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="password"
              name="password"
              type={show ? "text" : "password"}
              autoComplete="new-password"
              minLength={8}
              required
              disabled={pending}
              value={pw}
              onChange={(e) => setPw(e.target.value)}
              className="px-9"
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label={show ? "Hide password" : "Show password"}
            >
              {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </div>
          <div className="flex gap-1">
            {bars.map((i) => (
              <span
                key={i}
                className={
                  i < score
                    ? "h-1 flex-1 rounded bg-primary"
                    : "h-1 flex-1 rounded bg-muted"
                }
              />
            ))}
          </div>
          <p className="text-xs text-muted-foreground">{hint}</p>
        </div>

        {state && "error" in state ? (
          <p className="text-sm text-destructive" role="alert">
            {state.error}
          </p>
        ) : null}
        {state && "info" in state ? (
          <p className="text-sm text-muted-foreground" role="status">
            {state.info}
          </p>
        ) : null}

        <Button type="submit" className="w-full" disabled={pending}>
          {pending ? "Creating…" : "Create account"}
          <ArrowUpRight className="size-4" />
        </Button>
      </form>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-border" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          or
        </span>
        <div className="h-px flex-1 bg-border" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Button variant="outline" disabled>
          Google
        </Button>
        <Button variant="outline" disabled>
          GitHub
        </Button>
      </div>

      <p className="text-center text-sm text-muted-foreground">
        Already have one?{" "}
        <Link href="/sign-in" className="font-medium text-primary hover:underline">
          Sign in →
        </Link>
      </p>
    </div>
  );
}

function Field({
  id,
  label,
  icon,
  children,
}: {
  id: string;
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label
        htmlFor={id}
        className="text-[11px] uppercase tracking-widest text-muted-foreground"
      >
        {label}
      </Label>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
          {icon}
        </span>
        {children}
      </div>
    </div>
  );
}
