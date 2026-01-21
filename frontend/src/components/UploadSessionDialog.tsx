import { useState, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Loader2,
  Link as LinkIcon,
  Upload,
  User,
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
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AspectRatio } from "@/components/ui/aspect-ratio";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { sessionsApi } from "@/lib/api";
import { toast } from "sonner";

interface UploadSessionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Helper Component for "URL or File" input
const InputWithUpload = ({
  id,
  label,
  value,
  onChange,
  icon: Icon,
  accept,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (val: string) => void;
  icon: any;
  accept: string;
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Check file size (5MB limit for images)
      const isImage = file.type.startsWith("image/");
      const limit = isImage ? 5 : 50; // 5MB for images, 50MB for others
      if (file.size > limit * 1024 * 1024) {
        toast.error(`File too large. Max allowed: ${limit}MB`);
        return;
      }

      // Convert to Base64
      const reader = new FileReader();
      reader.onloadend = () => {
        onChange(reader.result as string);
        toast.success("File attached successfully");
      };
      reader.readAsDataURL(file);
    }
  };

  const isBase64 = value.startsWith("data:");

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            id={id}
            placeholder={isBase64 ? "File attached (Base64)" : "Paste URL..."}
            value={isBase64 ? "File attached" : value}
            onChange={(e) => !isBase64 && onChange(e.target.value)}
            className="pl-9"
            readOnly={isBase64} // Prevent editing text if it's a file
          />
        </div>
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept={accept}
          onChange={handleFileChange}
        />
        <Button
          type="button"
          variant="outline"
          size="icon"
          title="Upload Local File"
          onClick={() =>
            isBase64 ? onChange("") : fileInputRef.current?.click()
          }
        >
          {isBase64 ? (
            <span className="text-red-500 font-bold">X</span>
          ) : (
            <Upload className="w-4 h-4" />
          )}
        </Button>
      </div>
      {isBase64 && (
        <p className="text-xs text-green-600">Local file ready for upload.</p>
      )}
    </div>
  );
};

export function UploadSessionDialog({
  open,
  onOpenChange,
}: UploadSessionDialogProps) {
  const queryClient = useQueryClient();
  const { data: introAssets, isLoading: isLoadingIntros } = useQuery({
    queryKey: ["intro-assets"],
    queryFn: () => sessionsApi.listIntroAssets(),
  });

  const [activeTab, setActiveTab] = useState("basic");

  // Basic Info
  const [name, setName] = useState("");
  const [module, setModule] = useState("");
  const [driveLink, setDriveLink] = useState("");

  // Branding Info
  const [speakerName, setSpeakerName] = useState("");
  const [speakerTitle, setSpeakerTitle] = useState("");
  const [speakerImage, setSpeakerImage] = useState("");
  const [introVideo, setIntroVideo] = useState("");
  const [backgroundImage, setBackgroundImage] = useState("");

  const uploadMutation = useMutation({
    mutationFn: () =>
      sessionsApi.uploadSession({
        name,
        module: module || undefined,
        drive_link: driveLink,
        speaker_name: speakerName || undefined,
        speaker_title: speakerTitle || undefined,

        // FIX: Map your state variables to the "_url" keys expected by the backend
        speaker_image_url: speakerImage || undefined,
        intro_video_url: introVideo || undefined,
        background_image_url: backgroundImage || undefined,
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
    setSpeakerName("");
    setSpeakerTitle("");
    setSpeakerImage("");
    setIntroVideo("");
    setBackgroundImage("");
    setActiveTab("basic");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !driveLink.trim()) {
      toast.error("Name and Drive Link are required");
      return;
    }
    if (!introVideo) {
      toast.error("Please select an intro video in the Branding tab");
      setActiveTab("branding");
      return;
    }
    uploadMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Upload New Session</DialogTitle>
          <DialogDescription>
            Configure session details and speaker branding.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="basic">Basic Info</TabsTrigger>
              <TabsTrigger value="branding">Speaker & Branding</TabsTrigger>
            </TabsList>

            {/* --- TAB 1: BASIC INFO --- */}
            <TabsContent value="basic" className="space-y-4">
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
            </TabsContent>

            {/* --- TAB 2: BRANDING --- */}
            <TabsContent value="branding" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="speaker_name">Speaker Name</Label>
                  <Input
                    id="speaker_name"
                    placeholder="John Doe"
                    value={speakerName}
                    onChange={(e) => setSpeakerName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="speaker_title">Speaker Title</Label>
                  <Input
                    id="speaker_title"
                    placeholder="Prof. of Economics"
                    value={speakerTitle}
                    onChange={(e) => setSpeakerTitle(e.target.value)}
                  />
                </div>
              </div>

              {/* Profile Pic Input */}
              <InputWithUpload
                id="speaker_image"
                label="Profile Picture (URL or Upload)"
                value={speakerImage}
                onChange={setSpeakerImage}
                icon={User}
                accept="image/*"
              />

              {/* Intro Video Selection Grid */}
              <div className="space-y-2">
                <Label>Select Intro Video *</Label>
                {isLoadingIntros ? (
                  <div className="flex items-center justify-center p-8">
                    <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-3">
                    {introAssets && introAssets.length > 0 ? (
                      introAssets.map((asset) => (
                        <div
                          key={asset.id}
                          onClick={() => setIntroVideo(asset.video_url)}
                          className={`relative rounded-lg overflow-hidden border-2 cursor-pointer transition-all hover:scale-[1.02] ${
                            introVideo === asset.video_url
                              ? "border-primary ring-2 ring-primary/20"
                              : "border-transparent bg-muted"
                          }`}
                        >
                          <AspectRatio ratio={16 / 9}>
                            <img
                              src={asset.thumbnail_url}
                              alt={asset.name}
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                (e.target as HTMLImageElement).src =
                                  "https://placehold.co/600x400?text=No+Thumbnail";
                              }}
                            />
                            {introVideo === asset.video_url && (
                              <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
                                <div className="bg-primary text-white rounded-full p-1">
                                  <Check className="w-4 h-4" />
                                </div>
                              </div>
                            )}
                            <div className="absolute bottom-0 inset-x-0 bg-black/60 p-1 text-[10px] text-white text-center truncate">
                              {asset.name}
                            </div>
                          </AspectRatio>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-3 p-8 text-center border-2 border-dashed rounded-lg text-muted-foreground">
                        No intro videos found in storage.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Background Image Input */}
              <InputWithUpload
                id="background_image"
                label="Background Image (URL or Upload)"
                value={backgroundImage}
                onChange={setBackgroundImage}
                icon={ImageIcon}
                accept="image/*"
              />
            </TabsContent>
          </Tabs>

          <div className="flex justify-end gap-3 pt-6">
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
