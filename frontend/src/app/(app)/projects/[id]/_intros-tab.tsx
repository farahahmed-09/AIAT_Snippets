"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  deleteIntroAsset,
  listIntroAssets,
  type IntroAsset,
} from "@/lib/api/intro-assets";
import type { ProjectRole } from "@/lib/api/me";
import { UploadIntroDialog } from "./_upload-intro-dialog";

type Props = {
  projectId: number;
  myUserId: string;
  myRole: ProjectRole;
  initialAssets: IntroAsset[];
};

export function IntrosTab({
  projectId,
  myUserId,
  myRole,
  initialAssets,
}: Props) {
  const queryClient = useQueryClient();
  const queryKey = ["intro-assets", projectId] as const;

  const { data: assets = initialAssets } = useQuery({
    queryKey,
    queryFn: () => listIntroAssets(projectId),
    initialData: initialAssets,
  });

  const canWrite = myRole === "manager" || myRole === "editor";

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteIntroAsset(id),
    onSuccess: () => {
      toast.success("Intro deleted");
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const canDelete = (a: IntroAsset) =>
    myRole === "manager" || (myRole === "editor" && a.created_by === myUserId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {assets.length} intro{assets.length === 1 ? "" : "s"}
        </p>
        {canWrite ? <UploadIntroDialog projectId={projectId} /> : null}
      </div>

      {assets.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No intros yet</CardTitle>
            <CardDescription>
              {canWrite
                ? "Upload a short branded intro that the pipeline will prepend to every snippet."
                : "An editor or manager has to upload the first intro."}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {assets.map((a) => (
            <li key={a.id}>
              <Card className="overflow-hidden">
                <div className="aspect-video bg-muted">
                  {a.thumbnail_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={a.thumbnail_url}
                      alt={a.name}
                      className="size-full object-cover"
                    />
                  ) : (
                    <video
                      src={a.video_url}
                      className="size-full object-cover"
                      preload="metadata"
                      muted
                    />
                  )}
                </div>
                <CardContent className="flex items-center justify-between gap-2 p-4">
                  <p className="truncate text-sm font-medium" title={a.name}>
                    {a.name}
                  </p>
                  {canDelete(a) ? (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => {
                        if (confirm(`Delete intro “${a.name}”?`))
                          deleteMutation.mutate(a.id);
                      }}
                      aria-label="Delete intro"
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  ) : null}
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
