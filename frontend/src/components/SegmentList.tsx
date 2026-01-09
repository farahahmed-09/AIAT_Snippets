import { useState } from "react";
import { Play, Trash2, GripVertical, Check, X, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { formatTime, getSegmentColor, getSegmentBorderColor } from "@/lib/utils";

interface SegmentListProps {
  segments: Segment[];
  activeSegmentId: number | null;
  onSegmentClick: (segment: Segment) => void;
  onSegmentUpdate: (segment: Segment) => void;
  onSegmentDelete: (id: number) => void;
  totalDuration: number;
}

export const SegmentList = ({
  segments,
  activeSegmentId,
  onSegmentClick,
  onSegmentUpdate,
  onSegmentDelete,
  totalDuration,
}: SegmentListProps) => {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const startEditing = (segment: Segment) => {
    setEditingId(segment.id);
    setEditValue(segment.topic);
  };

  const saveEdit = (segment: Segment) => {
    if (editValue.trim()) {
      onSegmentUpdate({ ...segment, topic: editValue.trim() });
    }
    setEditingId(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValue("");
  };

  const handleTimeChange = (
    segment: Segment,
    type: "start" | "end",
    value: number
  ) => {
    if (type === "start") {
      onSegmentUpdate({
        ...segment,
        startTime: Math.min(value, segment.endTime - 1),
      });
    } else {
      onSegmentUpdate({
        ...segment,
        endTime: Math.max(value, segment.startTime + 1),
      });
    }
  };

  return (
    <div className="space-y-3">
      {segments.map((segment) => {
        const isActive = segment.id === activeSegmentId;
        const isEditing = editingId === segment.id;
        const isExpanded = expandedId === segment.id;
        const duration = segment.endTime - segment.startTime;

        return (
          <div
            key={segment.id}
            className={`glass rounded-xl overflow-hidden transition-all duration-200 ${
              isActive
                ? `border-2 ${getSegmentBorderColor(segment.color)}`
                : "border border-transparent hover:border-muted"
            }`}
          >
            {/* Main Row */}
            <div
              className="p-3 flex items-center gap-3 cursor-pointer"
              onClick={() => {
                onSegmentClick(segment);
                setExpandedId(isExpanded ? null : segment.id);
              }}
            >
              <GripVertical className="w-4 h-4 text-muted-foreground shrink-0" />

              <div
                className={`w-3 h-3 rounded ${getSegmentColor(
                  segment.color
                )} shrink-0`}
              />

              <div className="flex-1 min-w-0">
                {isEditing ? (
                  <div
                    className="flex items-center gap-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Input
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="h-7 text-sm"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter") saveEdit(segment);
                        if (e.key === "Escape") cancelEdit();
                      }}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => saveEdit(segment)}
                    >
                      <Check className="w-4 h-4 text-green-500" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={cancelEdit}
                    >
                      <X className="w-4 h-4 text-red-500" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 group/name">
                    <div
                      className="text-sm font-medium truncate hover:text-primary cursor-pointer flex-1"
                      onDoubleClick={(e) => {
                        e.stopPropagation();
                        startEditing(segment);
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSegmentClick(segment);
                      }}
                    >
                      {segment.topic}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 opacity-0 group-hover/name:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation();
                        startEditing(segment);
                      }}
                    >
                      <Pencil className="w-3 h-3 text-muted-foreground" />
                    </Button>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-muted-foreground px-2 py-1 bg-muted/50 rounded-lg">
                  {formatTime(duration)}
                </span>

                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 rounded-lg hover:bg-primary/10 hover:text-primary"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSegmentClick(segment);
                  }}
                >
                  <Play className="w-4 h-4" />
                </Button>

                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 rounded-lg hover:bg-destructive/10 hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSegmentDelete(segment.id);
                  }}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Expanded Trim Controls */}
            {isExpanded && (
              <div className="px-4 pb-4 space-y-4 border-t border-border/50">
                <div className="pt-4">
                  <div className="flex justify-between text-xs text-muted-foreground mb-2">
                    <span>Start: {formatTime(segment.startTime)}</span>
                    <span>End: {formatTime(segment.endTime)}</span>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">
                        Start Time
                      </label>
                      <Slider
                        value={[segment.startTime]}
                        min={0}
                        max={totalDuration}
                        step={0.1}
                        onValueChange={(v) =>
                          handleTimeChange(segment, "start", v[0])
                        }
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">
                        End Time
                      </label>
                      <Slider
                        value={[segment.endTime]}
                        min={0}
                        max={totalDuration}
                        step={0.1}
                        onValueChange={(v) =>
                          handleTimeChange(segment, "end", v[0])
                        }
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">
                        Move Position
                      </label>
                      <Slider
                        value={[segment.startTime]}
                        min={0}
                        max={
                          totalDuration - (segment.endTime - segment.startTime)
                        }
                        step={0.1}
                        onValueChange={(v) => {
                          const duration = segment.endTime - segment.startTime;
                          onSegmentUpdate({
                            ...segment,
                            startTime: v[0],
                            endTime: v[0] + duration,
                          });
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}

      {segments.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          <p>No segments detected yet.</p>
        </div>
      )}
    </div>
  );
};
