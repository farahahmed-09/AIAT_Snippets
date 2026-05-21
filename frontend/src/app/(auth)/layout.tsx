import { redirect } from "next/navigation";
import { AuthRail } from "@/components/auth-rail";
import { LogoMark } from "@/components/logo-mark";
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
    <div className="grid min-h-screen md:grid-cols-2">
      <AuthRail />
      <main className="flex flex-col bg-background">
        <header className="px-6 py-4 md:hidden">
          <LogoMark />
        </header>
        <div className="flex flex-1 items-center justify-center px-6 pb-12">
          {children}
        </div>
      </main>
    </div>
  );
}
