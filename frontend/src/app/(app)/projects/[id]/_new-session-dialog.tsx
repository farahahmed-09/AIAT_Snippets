"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { createSession } from "@/lib/api/sessions";

export function NewSessionDialog({ projectId }: { projectId: number }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const mutation = useMutation({
    mutationFn: (vars: {
      name: string;
      module: string;
      drive_link: string;
      speaker_name: string;
      speaker_title: string;
      speaker_image_url: string;
      intro_video_url: string;
      background_image_url: string;
    }) =>
      createSession(projectId, {
        name: vars.name,
        module: vars.module || null,
        drive_link: vars.drive_link,
        speaker_name: vars.speaker_name || null,
        speaker_title: vars.speaker_title || null,
        speaker_image_url: vars.speaker_image_url || null,
        intro_video_url: vars.intro_video_url || null,
        background_image_url: vars.background_image_url || null,
      }),
    onSuccess: (session) => {
      toast.success(`Session “${session.name}” queued`);
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["sessions", projectId] });
      router.refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>New session</DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            mutation.mutate({
              name: String(fd.get("name") ?? "").trim(),
              module: String(fd.get("module") ?? "").trim(),
              drive_link: String(fd.get("drive_link") ?? "").trim(),
              speaker_name: String(fd.get("speaker_name") ?? "").trim(),
              speaker_title: String(fd.get("speaker_title") ?? "").trim(),
              speaker_image_url: String(fd.get("speaker_image_url") ?? "").trim(),
              intro_video_url: String(fd.get("intro_video_url") ?? "").trim(),
              background_image_url: String(
                fd.get("background_image_url") ?? "",
              ).trim(),
            });
          }}
        >
          <DialogHeader>
            <DialogTitle>New session</DialogTitle>
            <DialogDescription>
              Paste a Google Drive link to the long recording. The processing
              pipeline picks it up next.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Session name</Label>
              <Input id="name" name="name" required maxLength={200} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="module">Module (optional)</Label>
              <Input id="module" name="module" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="drive_link">Google Drive link</Label>
              <Input
                id="drive_link"
                name="drive_link"
                type="url"
                required
                placeholder="https://drive.google.com/..."
              />
            </div>

            <Separator />

            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Branding (optional)
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="speaker_name">Speaker name</Label>
                <Input id="speaker_name" name="speaker_name" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="speaker_title">Speaker title</Label>
                <Input id="speaker_title" name="speaker_title" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="speaker_image_url">Speaker image URL</Label>
              <Input
                id="speaker_image_url"
                name="speaker_image_url"
                type="url"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="intro_video_url">Intro video URL</Label>
              <Input id="intro_video_url" name="intro_video_url" type="url" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="background_image_url">Background image URL</Label>
              <Input
                id="background_image_url"
                name="background_image_url"
                type="url"
              />
            </div>
          </div>

          <DialogFooter>
            <DialogClose render={<Button type="button" variant="outline" />}>
              Cancel
            </DialogClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating…" : "Create session"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
