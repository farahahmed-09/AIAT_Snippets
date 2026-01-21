import { useState, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Loader2,
  Upload,
  FileVideo,
  Image as ImageIcon,
  Check,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { sessionsApi } from "@/lib/api";
import { toast } from "sonner";

interface UploadIntroDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function UploadIntroDialog({
  open,
  onOpenChange,
}: UploadIntroDialogProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [videoBase64, setVideoBase64] = useState("");
  const [thumbnailBase64, setThumbnailBase64] = useState("");

  const videoInputRef = useRef<HTMLInputElement>(null);
  const thumbnailInputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useMutation({
    mutationFn: () =>
      sessionsApi.uploadIntroAsset({
        name,
        video_base64: videoBase64,
        thumbnail_base64: thumbnailBase64,
      }),
    onSuccess: () => {
      toast.success("Intro video uploaded successfully");
      queryClient.invalidateQueries({ queryKey: ["intro-assets"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to upload intro video");
    },
  });

  const resetForm = () => {
    setName("");
    setVideoBase64("");
    setThumbnailBase64("");
  };

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    setter: (val: string) => void,
    type: "video" | "image",
  ) => {
    const file = e.target.files?.[0];
    if (file) {
      const limit = type === "video" ? 50 : 5;
      if (file.size > limit * 1024 * 1024) {
        toast.error(`File too large. Max allowed: ${limit}MB`);
        return;
      }

      const reader = new FileReader();
      reader.onloadend = () => {
        setter(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !videoBase64 || !thumbnailBase64) {
      toast.error("All fields are required");
      return;
    }
    uploadMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Upload New Intro</DialogTitle>
          <DialogDescription>
            Add a new intro video and thumbnail to the system library.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="intro_name">Intro Name</Label>
            <Input
              id="intro_name"
              placeholder="e.g. Corporate Intro 2024"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label>Intro Video (.mp4, max 50MB)</Label>
            <div
              onClick={() => videoInputRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors ${
                videoBase64
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/20 hover:border-primary/50"
              }`}
            >
              {videoBase64 ? (
                <>
                  <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                    <Check className="w-5 h-5 text-primary" />
                  </div>
                  <span className="text-sm font-medium">Video Attached</span>
                </>
              ) : (
                <>
                  <FileVideo className="w-8 h-8 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground text-center">
                    Click to upload video
                  </span>
                </>
              )}
            </div>
            <input
              type="file"
              ref={videoInputRef}
              onChange={(e) => handleFileChange(e, setVideoBase64, "video")}
              accept="video/mp4"
              className="hidden"
            />
          </div>

          <div className="space-y-2">
            <Label>Thumbnail (.png/.jpg, max 5MB)</Label>
            <div
              onClick={() => thumbnailInputRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors ${
                thumbnailBase64
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/20 hover:border-primary/50"
              }`}
            >
              {thumbnailBase64 ? (
                <div className="relative w-full aspect-video rounded-md overflow-hidden">
                  <img
                    src={thumbnailBase64}
                    className="w-full h-full object-cover"
                    alt="Thumbnail preview"
                  />
                  <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                    <Check className="w-6 h-6 text-white" />
                  </div>
                </div>
              ) : (
                <>
                  <ImageIcon className="w-8 h-8 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground text-center">
                    Click to upload thumbnail
                  </span>
                </>
              )}
            </div>
            <input
              type="file"
              ref={thumbnailInputRef}
              onChange={(e) => handleFileChange(e, setThumbnailBase64, "image")}
              accept="image/*"
              className="hidden"
            />
          </div>

          <DialogFooter className="pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={uploadMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={uploadMutation.isPending}
              className="ai-gradient"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                "Upload Intro"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
