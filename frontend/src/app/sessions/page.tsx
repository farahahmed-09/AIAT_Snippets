import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { createClient } from "@/lib/supabase/server";

export default async function SessionsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <main className="container mx-auto flex flex-1 flex-col gap-6 px-6 py-8">
      <header className="flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Sessions</h1>
          <p className="text-sm text-muted-foreground">
            Signed in as {user?.email ?? "unknown"}
          </p>
        </div>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Empty</CardTitle>
          <CardDescription>
            Port the session list, polling, and upload dialog from
            old/frontend/src/pages/Sessions.tsx.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          The backend lives at NEXT_PUBLIC_API_URL. Use the apiFetch helper in
          src/lib/api.ts — it injects the Supabase bearer token automatically.
        </CardContent>
      </Card>
    </main>
  );
}
