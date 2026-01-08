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
          {/* Summary Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="glass rounded-xl p-4 text-center">
              <Film className="w-6 h-6 mx-auto mb-2 text-primary" />
              <div className="text-2xl font-bold">{segments.length}</div>
              <div className="text-xs text-muted-foreground">Clips</div>
            </div>
            <div className="glass rounded-xl p-4 text-center">
              <Clock className="w-6 h-6 mx-auto mb-2 text-primary" />
              <div className="text-2xl font-bold">
                {formatTime(totalDuration)}
              </div>
              <div className="text-xs text-muted-foreground">
                Total Duration
              </div>
            </div>
          </div>

          {/* Branding Summary */}
          <div className="glass rounded-xl p-4 space-y-2">
            <h4 className="text-sm font-medium">Branding</h4>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Intro</span>
              <span
                className={
                  introTemplate ? "text-primary" : "text-muted-foreground"
                }
              >
                {introTemplate?.name || "None"}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Outro</span>
              <span
                className={
                  outroTemplate ? "text-primary" : "text-muted-foreground"
                }
              >
                {outroTemplate?.name || "None"}
              </span>
            </div>
          </div>

          {/* Clips List */}
          <div className="glass rounded-xl p-4">
            <h4 className="text-sm font-medium mb-3">Clips to Render</h4>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {segments.map((segment, index) => (
                <div
                  key={segment.id}
                  className="flex items-center justify-between text-sm py-1"
                >
                  <span className="text-muted-foreground">
                    {index + 1}. {segment.topic}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatTime(segment.endTime - segment.startTime)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Progress or Complete State */}
          {isExporting && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Rendering clips...</span>
                <span className="text-muted-foreground">
                  {Math.round(progress)}%
                </span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}

          {isComplete && (
            <div className="glass rounded-xl p-4 text-center">
              <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
              <h4 className="font-semibold mb-1">Export Complete!</h4>
              <p className="text-sm text-muted-foreground">
                Your {segments.length} clips are ready for download
              </p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={handleClose}
            className="flex-1 rounded-xl"
          >
            {isComplete ? "Close" : "Cancel"}
          </Button>
          {!isComplete && (
            <Button
              onClick={handleExport}
              disabled={isExporting || segments.length === 0}
              className="flex-1 rounded-xl ai-gradient"
            >
              {isExporting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Rendering...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4 mr-2" />
                  Export All
                </>
              )}
            </Button>
          )}
          {isComplete && (
            <Button className="flex-1 rounded-xl ai-gradient">
              <Download className="w-4 h-4 mr-2" />
              Download All
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
