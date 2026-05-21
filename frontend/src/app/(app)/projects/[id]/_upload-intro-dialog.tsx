"use client";

import { useState } from "react";
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
import { uploadIntroAsset } from "@/lib/api/intro-assets";

export function UploadIntroDialog({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const mutation = useMutation({
    mutationFn: (vars: { name: string; video: File; thumbnail: File | null }) =>
      uploadIntroAsset(projectId, vars),
    onSuccess: (asset) => {
      toast.success(`Intro “${asset.name}” uploaded`);
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["intro-assets", projectId] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" />}>Upload intro</DialogTrigger>
      <DialogContent>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            const name = String(fd.get("name") ?? "").trim();
            const video = fd.get("video") as File | null;
            const thumbnail = fd.get("thumbnail") as File | null;
            if (!name || !video || video.size === 0) {
              toast.error("Name and video are required");
              return;
            }
            mutation.mutate({
              name,
              video,
              thumbnail: thumbnail && thumbnail.size > 0 ? thumbnail : null,
            });
          }}
        >
          <DialogHeader>
            <DialogTitle>Upload intro</DialogTitle>
            <DialogDescription>
              Reusable across sessions in this project. Keep it short — these
              get prepended to every snippet.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" name="name" required maxLength={120} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="video">Video</Label>
              <Input
                id="video"
                name="video"
                type="file"
                accept="video/*"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="thumbnail">Thumbnail (optional)</Label>
              <Input
                id="thumbnail"
                name="thumbnail"
                type="file"
                accept="image/*"
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button type="button" variant="outline" />}>
              Cancel
            </DialogClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Uploading…" : "Upload"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
