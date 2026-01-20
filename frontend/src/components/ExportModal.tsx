import { useState } from "react";
import {
  Download,
  Loader2,
  CheckCircle,
  Film,
  Clock,
  Sparkles,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { formatTime } from "@/lib/utils";

interface ExportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  segments: Segment[];
  selectedIntro: string | null;
  selectedOutro: string | null;
}

export const ExportModal = ({
  open,
  onOpenChange,
  segments,
  selectedIntro,
  selectedOutro,
}: ExportModalProps) => {
  const [isExporting, setIsExporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  // Moved this hook up to keep state declarations together
  const [downloadChoice, setDownloadChoice] = useState<string | null>(null);

  // Ensure 'brandingTemplates' is imported or defined in your parent/context
  const introTemplate = brandingTemplates.find((t) => t.id === selectedIntro);
  const outroTemplate = brandingTemplates.find((t) => t.id === selectedOutro);

  const totalDuration = segments.reduce(
    (acc, seg) => acc + (seg.endTime - seg.startTime),
    0
  );

  const handleExport = () => {
    setIsExporting(true);
    setProgress(0);

    // Simulate export progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsExporting(false);
          setIsComplete(true);
          return 100;
        }
        return prev + Math.random() * 15;
      });
    }, 500);
  };

  const handleClose = () => {
    setIsExporting(false);
    setProgress(0);
    setIsComplete(false);
    onOpenChange(false);
  };

  // Function to handle the user's choice
  const handleDownloadChoice = (choice: string) => {
    setDownloadChoice(choice);
    // Proceed with the chosen option
    // You can now call the backend API based on this choice
    console.log(`User chose to download: ${choice}`);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="glass border-glass-border sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            Export Clips
          </DialogTitle>
          <DialogDescription>
            Review your export settings before rendering
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Add the choice dialog */}
          {!downloadChoice && (
            <div className="glass rounded-xl p-4">
              <h4 className="text-sm font-medium">Choose Download Option</h4>
              <div className="flex justify-between mt-4">
                <Button 
                  onClick={() => handleDownloadChoice("separate")}
                  variant="outline"
                >
                  Separate Snippets
                </Button>
                <Button 
                  onClick={() => handleDownloadChoice("merged")}
                  variant="outline"
                >
                  Merged Highlight Video
                </Button>
              </div>
            </div>
          )}

          {/* If user has made a choice, show the export button */}
          {downloadChoice && (
            <div>
              {/* Optional: Show progress bar if exporting */}
              {isExporting && (
                <div className="mb-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Exporting...</span>
                    <span>{Math.round(progress)}%</span>
                  </div>
                  <Progress value={progress} />
                </div>
              )}
              
              <Button
                onClick={handleExport}
                disabled={isExporting || segments.length === 0}
                className="w-full rounded-xl ai-gradient flex items-center justify-center gap-2"
              >
                {isExporting && <Loader2 className="w-4 h-4 animate-spin" />}
                Export {downloadChoice === "separate" ? "Snippets" : "Merged Video"}
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};