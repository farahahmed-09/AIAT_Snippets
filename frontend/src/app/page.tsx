import Link from "next/link";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/server";

export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user) redirect("/projects");

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-4xl font-semibold tracking-tight">SmartCut AI</h1>
      <p className="max-w-md text-muted-foreground">
        Turn long lectures and webinars into branded short clips, automatically.
      </p>
      <div className="flex gap-3">
        <Button render={<Link href="/sign-in" />}>Sign in</Button>
        <Button render={<Link href="/sign-up" />} variant="outline">
          Create an account
        </Button>
      </div>
    </main>
  );
}
