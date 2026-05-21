import Link from "next/link";
import { redirect } from "next/navigation";
import { UserMenu } from "@/components/user-menu";
import { createClient } from "@/lib/supabase/server";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/sign-in");

  const { data: profile } = await supabase
    .from("profiles")
    .select("full_name, avatar_url, email")
    .eq("id", user.id)
    .maybeSingle();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b bg-background/70 backdrop-blur">
        <div className="container mx-auto flex h-14 items-center justify-between px-6">
          <Link
            href="/projects"
            className="text-sm font-semibold tracking-tight"
          >
            SmartCut AI
          </Link>
          <UserMenu
            email={profile?.email ?? user.email}
            fullName={profile?.full_name}
            avatarUrl={profile?.avatar_url}
          />
        </div>
      </header>
      <main className="flex flex-1 flex-col">{children}</main>
    </div>
  );
}
