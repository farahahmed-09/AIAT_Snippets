import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Play,
  Save,
  Loader2,
  Scissors,
  Download,
  RefreshCw,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  sessionsApi,
  snippetsApi,
  getStatusColor,
  getStatusLabel,
  Snippet,
  getSnippetDownloadUrl,
} from "@/lib/api";
import { toast } from "sonner";
import { VideoPlayer } from "@/components/VideoPlayer";
import { Timeline } from "@/components/Timeline";
import { SegmentList } from "@/components/SegmentList";
import { Segment } from "@/data/mockData";
import { toPlayableVideoUrl } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function SessionDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sessionId = parseInt(id || "0");

  const [currentTime, setCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [activeSegmentId, setActiveSegmentId] = useState<number | null>(null);
  const [localSegments, setLocalSegments] = useState<Segment[]>([]);
  const [hasChanges, setHasChanges] = useState(false);

  const {
    data: session,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => sessionsApi.getSessionResults(sessionId),
    enabled: sessionId > 0,
    refetchInterval: (query) => {
      // Poll while processing
      const data = query.state.data;
      if (
        data?.job_status?.startsWith("Processing") ||
        data?.job_status === "Pending"
      ) {
        return 5000;
      }
      return false;
    },
  });

  // Convert API snippets to local segment format
  useEffect(() => {
    if (session?.snippets) {
      const segments: Segment[] = session.snippets.map((snippet, index) => ({
        id: snippet.id,
        topic: snippet.name,
        startTime: snippet.start_second,
        endTime: snippet.end_second,
        color: (["blue", "green", "purple", "orange", "pink"] as const)[
          index % 5
        ],
      }));
      setLocalSegments(segments);
      if (segments.length > 0 && !activeSegmentId) {
        setActiveSegmentId(segments[0].id);
      }
    }
  }, [session?.snippets]);

  const saveMutation = useMutation({
    mutationFn: () =>
      sessionsApi.updatePlan(sessionId, {
        snippets: localSegments.map((seg) => ({
          name: seg.topic,
          start: seg.startTime,
          end: seg.endTime,
          summary:
            session?.snippets?.find((s) => s.id === seg.id)?.summary || "",
        })),
      }),
    onSuccess: () => {
      toast.success("Changes saved successfully");
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
    },
    onError: () => toast.error("Failed to save changes"),
  });

  const processMutation = useMutation({
    mutationFn: (snippetId: number) => snippetsApi.processSnippet(snippetId),
    onSuccess: () => toast.success("Snippet processing started"),
    onError: () => toast.error("Failed to start processing"),
  });

  const handleSegmentUpdate = (updatedSegment: Segment) => {
    setLocalSegments((prev) =>
      prev.map((seg) => (seg.id === updatedSegment.id ? updatedSegment : seg))
    );
    setHasChanges(true);
  };

  const handleSegmentDelete = (id: number) => {
    setLocalSegments((prev) => prev.filter((seg) => seg.id !== id));
    setHasChanges(true);
  };

  const handleAddSnippet = () => {
    const name = prompt(
      "Enter snippet name:",
      `New Snippet ${localSegments.length + 1}`
    );
    if (name === null) return; // Cancelled

    // Generate a unique random positive int4 (signed 32-bit integer)
    let newId: number;
    do {
      newId = Math.floor(Math.random() * 2147483647);
    } while (localSegments.some((s) => s.id === newId));
    const duration = 60; // Default 60 seconds
    let start = 0;
    let end = duration;

    // Find first gap
    const sorted = [...localSegments].sort((a, b) => a.startTime - b.startTime);
    let found = false;

    // Check gap at the very beginning
    if (sorted.length === 0 || sorted[0].startTime >= duration + 1) {
      start = 0;
      end = duration;
      found = true;
    }

    // Check gaps between segments
    if (!found) {
      for (let i = 0; i < sorted.length - 1; i++) {
        const gap = sorted[i + 1].startTime - sorted[i].endTime;
        if (gap >= duration + 1) {
          start = sorted[i].endTime + 1;
          end = start + duration;
          found = true;
          break;
        }
      }
    }

    // Check gap at the end
    if (!found) {
      const lastEnd = sorted.length > 0 ? sorted[sorted.length - 1].endTime : 0;
      if (!videoDuration || lastEnd + duration + 1 <= videoDuration) {
        start = lastEnd + 1;
        end = start + duration;
        found = true;
      } else {
        // No space? Just put it at the very end or where you can
        start = lastEnd;
        end = videoDuration || start + duration;
      }
    }

    const newSegment: Segment = {
      id: newId,
      topic: name || "New Snippet",
      startTime: Math.round(start * 10) / 10,
      endTime: Math.round(end * 10) / 10,
      color: (["blue", "green", "purple", "orange", "pink"] as const)[
        localSegments.length % 5
      ],
    };

    setLocalSegments((prev) => [...prev, newSegment]);
    setActiveSegmentId(newId);
    setHasChanges(true);
    setCurrentTime(start);
  };

  const handleSegmentClick = (segment: Segment) => {
    setActiveSegmentId(segment.id);
    setCurrentTime(segment.startTime);
  };

  const totalDuration =
    videoDuration ||
    (localSegments.length > 0
      ? Math.max(...localSegments.map((s) => s.endTime))
      : 600);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Session not found</p>
      </div>
    );
  }

  const isProcessing =
    session.job_status.startsWith("Processing") ||
    session.job_status === "Pending";
  const isFinished = session.job_status === "Finished";
  const activeSnippet: Snippet | undefined = session.snippets?.find(
    (s) => s.id === activeSegmentId
  );
  const rawVideoUrl = session.video_url || session.drive_link || "";
  const sessionVideoUrl = toPlayableVideoUrl(rawVideoUrl);

  const handleDownloadSnippet = () => {
    if (!activeSnippet) {
      toast.error("Select a snippet to download");
      return;
    }
    if (!activeSnippet.storage_link) {
      toast.error("Snippet is not ready yet. Generate the clip first.");
      return;
    }
    const downloadUrl = getSnippetDownloadUrl(activeSnippet.id);
    window.open(downloadUrl, "_blank", "noopener");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate("/sessions")}
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold">{session.name}</h1>
                <Badge
                  variant="outline"
                  className={getStatusColor(session.job_status)}
                >
                  {isProcessing && (
                    <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                  )}
                  {getStatusLabel(session.job_status)}
                </Badge>
              </div>
              {session.module && (
                <p className="text-sm text-muted-foreground">
                  {session.module}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            {isProcessing && (
              <Button variant="ghost" size="icon" onClick={() => refetch()}>
                <RefreshCw className="w-4 h-4" />
              </Button>
            )}
            {isFinished && hasChanges && (
              <Button
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
                className="ai-gradient"
              >
                {saveMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                Save Changes
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-6 py-6">
        {isProcessing ? (
          <div className="text-center py-20">
            <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">
              Processing your session
            </h3>
            <p className="text-muted-foreground max-w-md mx-auto">
              {session.job_status.includes("Downloading") &&
                "Downloading video from Google Drive..."}
              {session.job_status.includes("Transcribing") &&
                "Extracting audio and generating transcript..."}
              {session.job_status.includes("Analyzing") &&
                "AI is identifying key segments..."}
              {session.job_status === "Pending" &&
                "Waiting to start processing..."}
            </p>
          </div>
        ) : session.job_status === "Failed" ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">⚠️</span>
            </div>
            <h3 className="font-semibold text-lg mb-2">Processing Failed</h3>
            <p className="text-muted-foreground">
              Something went wrong while processing this session.
            </p>
          </div>
        ) : (
          <div className="grid lg:grid-cols-[1fr,380px] gap-6">
            {/* Main Editor */}
            <div className="space-y-4">
              <VideoPlayer
                videoUrl={sessionVideoUrl}
                currentTime={currentTime}
                onTimeUpdate={setCurrentTime}
                onDurationChange={setVideoDuration}
                isProcessing={false}
              />
              <Timeline
                segments={localSegments}
                currentTime={currentTime}
                duration={totalDuration}
                onSeek={setCurrentTime}
                activeSegmentId={activeSegmentId}
                onSegmentClick={handleSegmentClick}
                onSegmentUpdate={handleSegmentUpdate}
              />
            </div>

            {/* Sidebar */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">
                  Snippets ({localSegments.length})
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleAddSnippet}
                  className="text-primary hover:text-primary hover:bg-primary/10"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add New
                </Button>
              </div>
              <SegmentList
                segments={localSegments}
                activeSegmentId={activeSegmentId}
                onSegmentClick={handleSegmentClick}
                onSegmentUpdate={handleSegmentUpdate}
                onSegmentDelete={handleSegmentDelete}
                totalDuration={totalDuration}
              />

              {activeSegmentId && (
                <div className="glass rounded-xl p-4 space-y-3">
                  <h4 className="font-medium text-sm">Actions</h4>
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={() => processMutation.mutate(activeSegmentId)}
                    disabled={processMutation.isPending}
                  >
                    {processMutation.isPending ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Scissors className="w-4 h-4 mr-2" />
                    )}
                    Generate Video
                  </Button>
                  <Button
                    className="w-full"
                    onClick={handleDownloadSnippet}
                    variant="secondary"
                    disabled={!activeSnippet}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Download Snippet
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
