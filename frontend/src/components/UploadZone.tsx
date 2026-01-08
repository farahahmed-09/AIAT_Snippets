import { Upload, Sparkles, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface UploadZoneProps {
  onDemoMode: () => void;
  onFileUpload: (file: File) => void;
}

export const UploadZone = ({ onDemoMode, onFileUpload }: UploadZoneProps) => {
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('video/')) {
      onFileUpload(file);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileUpload(file);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-2xl w-full">
        {/* Logo and Title */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl ai-gradient flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-4xl font-bold ai-gradient-text">SmartCut AI</h1>
          </div>
          <p className="text-muted-foreground text-lg">
            Transform long videos into perfectly segmented clips with AI
          </p>
        </div>

        {/* Upload Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="glass rounded-2xl p-12 text-center border-2 border-dashed border-muted hover:border-primary/50 transition-all duration-300 cursor-pointer group"
        >
          <div className="w-20 h-20 rounded-2xl bg-muted/50 flex items-center justify-center mx-auto mb-6 group-hover:bg-primary/10 transition-colors">
            <Upload className="w-10 h-10 text-muted-foreground group-hover:text-primary transition-colors" />
          </div>
          
          <h2 className="text-xl font-semibold mb-2">
            Drop your webinar here to let AI slice it up
          </h2>
          <p className="text-muted-foreground mb-6">
            Supports MP4, WebM, MOV up to 2GB
          </p>

          <input
            type="file"
            accept="video/*"
            onChange={handleFileInput}
            className="hidden"
            id="video-upload"
          />
          <label htmlFor="video-upload">
            <Button variant="outline" className="rounded-xl" asChild>
              <span>Browse Files</span>
            </Button>
          </label>
        </div>

        {/* Demo Mode Button */}
        <div className="mt-8 text-center">
          <div className="inline-flex items-center gap-2 text-muted-foreground mb-4">
            <div className="h-px w-12 bg-border" />
            <span className="text-sm">or try it out</span>
            <div className="h-px w-12 bg-border" />
          </div>
          
          <div>
            <Button
              onClick={onDemoMode}
              className="rounded-xl ai-gradient hover:opacity-90 transition-opacity"
            >
              <Play className="w-4 h-4 mr-2" />
              Launch Demo Mode
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
