import { useRef, useState, useCallback, useMemo } from "react";
import { ZoomIn, ZoomOut, GripVertical, GripHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Segment, formatTime, getSegmentColor } from "@/data/mockData";

interface TimelineProps {
  segments: Segment[];
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
  activeSegmentId: number | null;
  onSegmentClick: (segment: Segment) => void;
  onSegmentUpdate: (segment: Segment) => void;
}

// Generate fake waveform data
const generateWaveform = (count: number): number[] => {
  const waveform: number[] = [];
  for (let i = 0; i < count; i++) {
    const base = 0.2 + Math.random() * 0.3;
    const peak = Math.sin(i * 0.1) * 0.3 + Math.random() * 0.4;
    waveform.push(Math.min(1, base + peak));
  }
  return waveform;
};

export const Timeline = ({
  segments,
  currentTime,
  duration,
  onSeek,
  activeSegmentId,
  onSegmentClick,
  onSegmentUpdate,
}: TimelineProps) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<{
    segmentId: number;
    handle: "start" | "end" | "move";
    initialOffset?: number;
  } | null>(null);
  const [zoom, setZoom] = useState(1); // 1 = 100%, 2 = 200%, etc.

  // Generate waveform once
  const waveformData = useMemo(() => generateWaveform(300), []);

  // Calculate timeline width based on zoom
  const timelineWidth = zoom * 100; // percentage

  const getTimeFromPosition = useCallback(
    (clientX: number): number => {
      const container = scrollContainerRef.current;
      const timeline = timelineRef.current;
      if (!container || !timeline) return 0;

      const rect = timeline.getBoundingClientRect();
      const x = clientX - rect.left;
      const percentage = Math.max(0, Math.min(1, x / rect.width));
      return percentage * duration;
    },
    [duration]
  );

  const handleTimelineClick = (e: React.MouseEvent) => {
    if (dragging) return;
    // Don't seek if clicking on a segment
    if ((e.target as HTMLElement).closest(".segment-block")) return;
    const time = getTimeFromPosition(e.clientX);
    onSeek(time);
  };

  const handleMouseDown = (
    e: React.MouseEvent,
    segmentId: number,
    handle: "start" | "end" | "move",
    segmentStartTime?: number
  ) => {
    e.stopPropagation();
    let initialOffset = 0;
    if (handle === "move" && segmentStartTime !== undefined) {
      const clickTime = getTimeFromPosition(e.clientX);
      initialOffset = clickTime - segmentStartTime;
    }
    setDragging({ segmentId, handle, initialOffset });
  };

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging) return;

      const segment = segments.find((s) => s.id === dragging.segmentId);
      if (!segment) return;

      const time = getTimeFromPosition(e.clientX);
      const segmentIndex = segments.findIndex(
        (s) => s.id === dragging.segmentId
      );
      const prevSegment = segments[segmentIndex - 1];
      const nextSegment = segments[segmentIndex + 1];

      if (dragging.handle === "start") {
        const minStart = prevSegment ? prevSegment.endTime + 0.1 : 0;
        const maxStart = segment.endTime - 1;
        const newStart = Math.max(minStart, Math.min(maxStart, time));
        onSegmentUpdate({ ...segment, startTime: newStart });
      } else if (dragging.handle === "end") {
        const minEnd = segment.startTime + 1;
        const maxEnd = nextSegment ? nextSegment.startTime - 0.1 : duration;
        const newEnd = Math.max(minEnd, Math.min(maxEnd, time));
        onSegmentUpdate({ ...segment, endTime: newEnd });
      } else if (dragging.handle === "move") {
        const segmentDuration = segment.endTime - segment.startTime;
        const offset = dragging.initialOffset || 0;
        let newStart = time - offset;

        // Constraints
        const minBound = prevSegment ? prevSegment.endTime + 0.1 : 0;
        const maxBound = nextSegment
          ? nextSegment.startTime - segmentDuration - 0.1
          : duration - segmentDuration;

        newStart = Math.max(minBound, Math.min(maxBound, newStart));
        const newEnd = newStart + segmentDuration;

        onSegmentUpdate({ ...segment, startTime: newStart, endTime: newEnd });
      }
    },
    [dragging, segments, getTimeFromPosition, duration, onSegmentUpdate]
  );

  const handleMouseUp = useCallback(() => {
    setDragging(null);
  }, []);

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + 0.5, 4));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev - 0.5, 1));
  };

  // Generate time markers based on zoom level
  const markerInterval = zoom >= 3 ? 15 : zoom >= 2 ? 30 : 60;
  const markers = [];
  for (let i = 0; i <= duration; i += markerInterval) {
    markers.push(i);
  }

  const playheadPosition = (currentTime / duration) * 100;

  if (segments.length === 0) {
    return (
      <div className="glass rounded-2xl p-4">
        <p className="text-center text-muted-foreground">
          No segments available
        </p>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-4">
      {/* Header with zoom controls */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Timeline</span>
          <span className="text-xs text-muted-foreground">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleZoomOut}
            disabled={zoom <= 1}
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-xs w-12 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleZoomIn}
            disabled={zoom >= 4}
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Scrollable Timeline Container */}
      <div
        ref={scrollContainerRef}
        className="overflow-x-auto scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent"
      >
        <div
          ref={timelineRef}
          onClick={handleTimelineClick}
          onMouseMove={dragging ? handleMouseMove : undefined}
          onMouseUp={dragging ? handleMouseUp : undefined}
          onMouseLeave={dragging ? handleMouseUp : undefined}
          className={`relative ${
            dragging ? "cursor-ew-resize" : "cursor-pointer"
          }`}
          style={{ width: `${timelineWidth}%`, minWidth: "100%" }}
        >
          {/* Time Markers */}
          <div className="relative h-5 mb-1">
            {markers.map((time) => (
              <div
                key={time}
                className="absolute text-[10px] text-muted-foreground -translate-x-1/2"
                style={{ left: `${(time / duration) * 100}%` }}
              >
                {formatTime(time)}
              </div>
            ))}
          </div>

          {/* Timeline Track with Waveform */}
          <div className="relative h-24 rounded-xl bg-muted/30 overflow-hidden">
            {/* Waveform Visualization */}
            <div className="absolute inset-0 flex items-center justify-around px-1">
              {waveformData.map((height, i) => (
                <div
                  key={i}
                  className="w-[2px] bg-muted-foreground/20 rounded-full"
                  style={{ height: `${height * 70}%` }}
                />
              ))}
            </div>

            {/* Segment Blocks */}
            {segments.map((segment) => {
              const left = (segment.startTime / duration) * 100;
              const width =
                ((segment.endTime - segment.startTime) / duration) * 100;
              const isActive = segment.id === activeSegmentId;

              return (
                <div
                  key={segment.id}
                  onMouseDown={(e) =>
                    handleMouseDown(e, segment.id, "move", segment.startTime)
                  }
                  onClick={(e) => {
                    e.stopPropagation();
                    onSegmentClick(segment);
                  }}
                  className={`segment-block absolute top-1 bottom-1 rounded-lg transition-all ${getSegmentColor(
                    segment.color
                  )} ${
                    isActive
                      ? "ring-2 ring-white ring-offset-2 ring-offset-background z-10"
                      : "opacity-80 hover:opacity-100"
                  } ${
                    dragging?.segmentId === segment.id &&
                    dragging?.handle === "move"
                      ? "cursor-grabbing"
                      : "cursor-move"
                  }`}
                  style={{
                    left: `${left}%`,
                    width: `${width}%`,
                    minWidth: "20px",
                  }}
                >
                  {/* Segment Content */}
                  <div className="h-full flex items-center justify-center px-2 overflow-hidden pointer-events-none">
                    <GripVertical className="w-3 h-3 text-white/50 mr-1 shrink-0" />
                    <span className="text-[10px] text-white font-medium truncate drop-shadow">
                      {segment.topic}
                    </span>
                  </div>

                  {/* Left Trim Handle */}
                  <div
                    onMouseDown={(e) => handleMouseDown(e, segment.id, "start")}
                    className={`absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize flex items-center justify-center bg-black/20 hover:bg-black/40 rounded-l-lg transition-colors ${
                      dragging?.segmentId === segment.id &&
                      dragging?.handle === "start"
                        ? "bg-black/50"
                        : ""
                    }`}
                  >
                    <div className="w-0.5 h-6 bg-white/80 rounded-full" />
                  </div>

                  {/* Right Trim Handle */}
                  <div
                    onMouseDown={(e) => handleMouseDown(e, segment.id, "end")}
                    className={`absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize flex items-center justify-center bg-black/20 hover:bg-black/40 rounded-r-lg transition-colors ${
                      dragging?.segmentId === segment.id &&
                      dragging?.handle === "end"
                        ? "bg-black/50"
                        : ""
                    }`}
                  >
                    <div className="w-0.5 h-6 bg-white/80 rounded-full" />
                  </div>
                </div>
              );
            })}

            {/* Playhead */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg z-20 pointer-events-none"
              style={{ left: `${playheadPosition}%` }}
            >
              <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-white rounded-full shadow" />
            </div>
          </div>
        </div>
      </div>

      {/* Zoom Slider */}
      <div className="flex items-center gap-3 mt-3">
        <ZoomOut className="h-3 w-3 text-muted-foreground" />
        <Slider
          value={[zoom]}
          onValueChange={(v) => setZoom(v[0])}
          min={1}
          max={4}
          step={0.25}
          className="flex-1"
        />
        <ZoomIn className="h-3 w-3 text-muted-foreground" />
      </div>

      {/* Instructions */}
      <p className="text-[10px] text-muted-foreground mt-2 text-center">
        Click segment to select • Drag edges to trim • Click track to seek •
        Scroll to pan when zoomed
      </p>
    </div>
  );
};
