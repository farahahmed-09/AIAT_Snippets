import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { createClient } from "@/lib/supabase/server";
import { NewProjectDialog } from "./_new-project-dialog";

type MembershipRow = {
  role: "manager" | "editor" | "viewer";
  joined_at: string;
  projects: {
    id: number;
    name: string;
    description: string | null;
    created_at: string;
    updated_at: string;
  } | null;
};

const roleBadgeVariant: Record<
  MembershipRow["role"],
  "default" | "secondary" | "outline"
> = {
  manager: "default",
  editor: "secondary",
  viewer: "outline",
};

export default async function ProjectsPage() {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("project_members")
    .select("role, joined_at, projects(*)")
    .order("joined_at", { ascending: false });

  const memberships = ((data ?? []) as unknown as MembershipRow[]).filter(
    (m) => m.projects !== null,
  );

  return (
    <div className="container mx-auto flex flex-1 flex-col gap-6 px-6 py-8">
      <header className="flex items-baseline justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Every project you&apos;re a member of.
          </p>
        </div>
        <NewProjectDialog />
      </header>

      {error ? (
        <Card>
          <CardHeader>
            <CardTitle>Couldn&apos;t load projects</CardTitle>
            <CardDescription>{error.message}</CardDescription>
          </CardHeader>
        </Card>
      ) : memberships.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No projects yet</CardTitle>
            <CardDescription>
              On signup the database creates a default project for you — if
              you&apos;re seeing this, the
              <code className="mx-1">on_auth_user_create_default_project</code>
              trigger didn&apos;t run. You can also start a fresh one with
              <em> New project</em>.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {memberships.map(({ projects: project, role }) => (
            <li key={project!.id}>
              <Link href={`/projects/${project!.id}`}>
                <Card className="h-full transition-colors hover:bg-accent/30">
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <CardTitle className="text-base">
                        {project!.name}
                      </CardTitle>
                      <Badge variant={roleBadgeVariant[role]}>{role}</Badge>
                    </div>
                    {project!.description ? (
                      <CardDescription>{project!.description}</CardDescription>
                    ) : null}
                  </CardHeader>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
