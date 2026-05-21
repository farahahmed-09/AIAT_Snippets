import { redirect } from "next/navigation";
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

  // Per-page <AppHeader/> is rendered so each page picks its own active
  // project + breadcrumb + trailing actions. Keeps the layout dumb.
  return <div className="flex min-h-screen flex-col">{children}</div>;
}
