import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SignInPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>
            Auth flow is wired through Supabase. Replace this stub with the
            real form when porting from old/frontend/.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          TODO: email/password + OAuth via supabase.auth.signInWithPassword /
          signInWithOAuth.
        </CardContent>
      </Card>
    </main>
  );
}
