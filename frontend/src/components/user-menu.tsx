"use client";

import Link from "next/link";
import { useTheme } from "next-themes";
import { Folder, LogOut, Moon, Sun, UserRound } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { RoleBadge } from "@/components/role-badge";
import { signOut } from "@/app/sign-out/actions";
import { initials } from "@/lib/initials";
import type { ProjectRole } from "@/lib/api/me";

type Props = {
  email: string | null | undefined;
  fullName: string | null | undefined;
  avatarUrl: string | null | undefined;
  activeProjectName?: string;
  activeRole?: ProjectRole;
};

export function UserMenu({
  email,
  fullName,
  avatarUrl,
  activeProjectName,
  activeRole,
}: Props) {
  const { resolvedTheme, setTheme } = useTheme();
  const dark = resolvedTheme === "dark";
  const display = fullName?.trim() || email || "Account";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={<Button variant="ghost" size="icon-sm" className="rounded-md" />}
        aria-label="Open profile menu"
      >
        <Avatar className="size-7">
          {avatarUrl ? <AvatarImage src={avatarUrl} alt={display} /> : null}
          <AvatarFallback>{initials(fullName, email)}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-64">
        <div className="flex items-center gap-3 px-3 py-3">
          <Avatar className="size-9">
            {avatarUrl ? <AvatarImage src={avatarUrl} alt={display} /> : null}
            <AvatarFallback>{initials(fullName, email)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">
              {fullName || "Unnamed"}
            </p>
            <p className="truncate text-xs text-muted-foreground">{email}</p>
          </div>
        </div>
        {activeRole && activeProjectName ? (
          <div className="flex items-center gap-2 px-3 pb-2 text-xs text-muted-foreground">
            <RoleBadge role={activeRole} />
            <span>in {activeProjectName}</span>
          </div>
        ) : null}
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled>
          <UserRound className="size-4" /> Profile
        </DropdownMenuItem>
        <DropdownMenuItem render={<Link href="/projects" />}>
          <Folder className="size-4" /> Projects
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme(dark ? "light" : "dark")}>
          {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
          Theme
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <form action={signOut}>
          <DropdownMenuItem
            variant="destructive"
            render={<button type="submit" className="w-full text-left" />}
          >
            <LogOut className="size-4" /> Sign out
          </DropdownMenuItem>
        </form>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
