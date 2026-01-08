import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Link as LinkIcon } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { sessionsApi } from "@/lib/api";
import { toast } from "sonner";

interface UploadSessionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function UploadSessionDialog({ open, onOpenChange }: UploadSessionDialogProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [module, setModule] = useState("");
  const [driveLink, setDriveLink] = useState("");

  const uploadMutation = useMutation({
    mutationFn: () =>
      sessionsApi.uploadSession({
        name,
        module: module || undefined,
        drive_link: driveLink,
      }),
    onSuccess: () => {
      toast.success("Session uploaded! Processing will begin shortly.");
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to upload session");
    },
  });

  const resetForm = () => {
    setName("");
    setModule("");
    setDriveLink("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !driveLink.trim()) {
      toast.error("Please fill in all required fields");
      return;
    }
    uploadMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload New Session</DialogTitle>
          <DialogDescription>
            Provide a Google Drive link to your lecture recording
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Session Name *</Label>
            <Input
              id="name"
              placeholder="e.g., Marketing Lecture 1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="module">Module (optional)</Label>
            <Input
              id="module"
              placeholder="e.g., Marketing 101"
              value={module}
              onChange={(e) => setModule(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="drive_link">Google Drive Link *</Label>
            <div className="relative">
              <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                id="drive_link"
                placeholder="https://drive.google.com/..."
                value={driveLink}
                onChange={(e) => setDriveLink(e.target.value)}
                className="pl-9"
                required
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="ai-gradient"
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              Upload Session
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
