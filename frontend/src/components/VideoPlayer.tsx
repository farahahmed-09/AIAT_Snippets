import { useRef, useEffect, useState } from "react";
import { Play, Pause, Volume2, VolumeX, Maximize, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

interface VideoPlayerProps {
  videoUrl: string;
  currentTime: number;
  onTimeUpdate: (time: number) => void;
  onDurationChange?: (duration: number) => void;
  isProcessing: boolean;
}

export const VideoPlayer = ({
  videoUrl,
  currentTime,
  onTimeUpdate,
  onDurationChange,
  isProcessing,
}: VideoPlayerProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [playbackError, setPlaybackError] = useState<string | null>(null);
  const hasVideoSource = Boolean(videoUrl);
  const controlsDisabled = !hasVideoSource || Boolean(playbackError);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      onTimeUpdate(video.currentTime);
    };

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
      if (onDurationChange) onDurationChange(video.duration);
    };

    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("loadedmetadata", handleLoadedMetadata);
    const handleError = () => {
      setPlaybackError(
        "Video source not supported. Confirm your backend is returning a direct media URL."
      );
      setIsPlaying(false);
    };
    video.addEventListener("error", handleError);

    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("loadedmetadata", handleLoadedMetadata);
      video.removeEventListener("error", handleError);
    };
  }, [onTimeUpdate]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // Only seek if the difference is significant (avoid loop from timeupdate)
    if (Math.abs(video.currentTime - currentTime) > 0.5) {
      video.currentTime = currentTime;
    }
  }, [currentTime]);

  useEffect(() => {
    const video = videoRef.current;
    setPlaybackError(null);
    setIsPlaying(false);
    if (!video) return;
    if (!videoUrl) {
      video.removeAttribute("src");
    }
    video.load();
  }, [videoUrl]);

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video || controlsDisabled) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play();
    }
    setIsPlaying(!isPlaying);
  };

  const toggleMute = () => {
    const video = videoRef.current;
    if (!video || controlsDisabled) return;
    video.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleVolumeChange = (value: number[]) => {
    const video = videoRef.current;
    if (!video || controlsDisabled) return;
    const newVolume = value[0];
    video.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  };

  const handleSeek = (value: number[]) => {
    const video = videoRef.current;
    if (!video || controlsDisabled) return;
    video.currentTime = value[0];
    onTimeUpdate(value[0]);
  };

  const handleFullscreen = () => {
    const video = videoRef.current;
    if (!video || controlsDisabled) return;
    video.requestFullscreen();
  };

  return (
    <div className="glass rounded-2xl overflow-hidden">
      {/* Video Container */}
      <div className="relative aspect-video bg-black">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        />

        {/* Processing Overlay */}
        {isProcessing && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center">
            <div className="glass rounded-xl px-6 py-4 flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
              <span className="font-medium">AI Processing...</span>
            </div>
          </div>
        )}

        {/* Error / Missing Source Overlay */}
        {controlsDisabled && !isProcessing && (
          <div className="absolute inset-0 bg-black/70 text-center px-6 flex items-center justify-center">
            <div>
              <p className="text-sm text-white/80">
                {playbackError ||
                  "No video source available for this session yet."}
              </p>
              <p className="text-xs text-white/60 mt-2">
                Ensure the backend exposes a playable URL or download the
                original file instead.
              </p>
            </div>
          </div>
        )}

        {/* Play Button Overlay (when paused) */}
        {!isPlaying && !isProcessing && !controlsDisabled && (
          <button
            onClick={togglePlay}
            className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/30 transition-colors group"
          >
            <div className="w-20 h-20 rounded-full ai-gradient flex items-center justify-center opacity-80 group-hover:opacity-100 group-hover:scale-110 transition-all">
              <Play className="w-8 h-8 text-white ml-1" fill="white" />
            </div>
          </button>
        )}
      </div>

      {/* Controls */}
      <div className="p-4 space-y-3">
        {/* Progress Bar */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground w-12">
            {formatTime(currentTime)}
          </span>
          <Slider
            value={[currentTime]}
            max={duration || 100}
            step={0.1}
            onValueChange={handleSeek}
            disabled={controlsDisabled}
            className="flex-1"
          />
          <span className="text-sm text-muted-foreground w-12 text-right">
            {formatTime(duration)}
          </span>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={togglePlay}
              disabled={controlsDisabled}
              className="rounded-xl"
            >
              {isPlaying ? (
                <Pause className="w-5 h-5" />
              ) : (
                <Play className="w-5 h-5" />
              )}
            </Button>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleMute}
                disabled={controlsDisabled}
                className="rounded-xl"
              >
                {isMuted ? (
                  <VolumeX className="w-5 h-5" />
                ) : (
                  <Volume2 className="w-5 h-5" />
                )}
              </Button>
              <Slider
                value={[isMuted ? 0 : volume]}
                max={1}
                step={0.1}
                onValueChange={handleVolumeChange}
                disabled={controlsDisabled}
                className="w-24"
              />
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={handleFullscreen}
            disabled={controlsDisabled}
            className="rounded-xl"
          >
            <Maximize className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
};
