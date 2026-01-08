import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Plus, Video, Clock, RefreshCw, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { sessionsApi, getStatusColor, getStatusLabel } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { UploadSessionDialog } from "@/components/UploadSessionDialog";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function Sessions() {
  const [uploadOpen, setUploadOpen] = useState(false);

  const { data: sessions, isLoading, refetch, isRefetching, isError } = useQuery({
    queryKey: ["sessions"],
    queryFn: () => sessionsApi.listSessions({ limit: 50, order: "desc" }),
    refetchInterval: 10000, // Poll every 10 seconds for status updates
    retry: 1,
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl ai-gradient flex items-center justify-center">
              <Video className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-2xl font-bold">SmartCut AI</h1>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => refetch()}
              disabled={isRefetching}
            >
              <RefreshCw className={`w-4 h-4 ${isRefetching ? "animate-spin" : ""}`} />
            </Button>
            <Button onClick={() => setUploadOpen(true)} className="ai-gradient">
              <Plus className="w-4 h-4 mr-2" />
              New Session
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-6 py-8">
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-1">Live Sessions</h2>
          <p className="text-muted-foreground">
            Upload lecture recordings and let AI identify key snippets
          </p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : isError ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-yellow-500/20 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">⚠️</span>
            </div>
            <h3 className="font-semibold mb-2">Cannot connect to API</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Make sure your backend server is running at the configured URL. Update the API_BASE_URL in src/lib/api.ts if needed.
            </p>
            <Button onClick={() => refetch()} variant="outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
          </div>
        ) : sessions && sessions.length > 0 ? (
          <div className="grid gap-4">
            {sessions.map((session) => (
              <Link
                key={session.id}
                to={`/sessions/${session.id}`}
                className="block"
              >
                <div className="glass rounded-xl p-5 hover:bg-muted/30 transition-colors group border border-border/50">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-semibold text-lg truncate group-hover:text-primary transition-colors">
                          {session.name}
                        </h3>
                        {session.module && (
                          <Badge variant="secondary" className="shrink-0">
                            {session.module}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5" />
                          {formatDistanceToNow(new Date(session.created_at), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={`shrink-0 ${getStatusColor(session.job_status)}`}
                    >
                      {session.job_status.startsWith("Processing") && (
                        <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                      )}
                      {getStatusLabel(session.job_status)}
                    </Badge>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mx-auto mb-4">
              <Video className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="font-semibold mb-2">No sessions yet</h3>
            <p className="text-muted-foreground mb-6">
              Upload your first lecture recording to get started
            </p>
            <Button onClick={() => setUploadOpen(true)} className="ai-gradient">
              <Plus className="w-4 h-4 mr-2" />
              Upload Session
            </Button>
          </div>
        )}
      </main>

      <UploadSessionDialog open={uploadOpen} onOpenChange={setUploadOpen} />
    </div>
  );
}
