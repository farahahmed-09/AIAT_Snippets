import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (user) redirect("/projects");

  return (
    <div className="flex min-h-screen flex-col">
      <header className="px-6 py-4">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          SmartCut AI
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center px-6 pb-12">
        {children}
      </main>
    </div>
  );
}
