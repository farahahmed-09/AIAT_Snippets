import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SignUpPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Create your account</CardTitle>
          <CardDescription>
            Signup triggers handle_new_user + create_default_project_for_user
            in the database, so the user lands with a starter project.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          TODO: email, password, full_name. Pass full_name via options.data so
          the DB trigger populates public.profiles.full_name.
        </CardContent>
      </Card>
    </main>
  );
}
