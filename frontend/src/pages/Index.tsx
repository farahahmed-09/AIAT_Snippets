import { useState, useCallback } from 'react';
import { Sparkles, Download, LayoutList, Palette } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { UploadZone } from '@/components/UploadZone';
import { VideoPlayer } from '@/components/VideoPlayer';
import { Timeline } from '@/components/Timeline';
import { SegmentList } from '@/components/SegmentList';
import { BrandingTab } from '@/components/BrandingTab';
import { ExportModal } from '@/components/ExportModal';
import { Segment, mockSegments, demoVideoUrl } from '@/data/mockData';
import { ThemeToggle } from '@/components/ThemeToggle';

const Index = () => {
  // Video state
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  // Segments state
  const [segments, setSegments] = useState<Segment[]>([]);
  const [activeSegmentId, setActiveSegmentId] = useState<number | null>(null);

  // Branding state
  const [selectedIntro, setSelectedIntro] = useState<string | null>(null);
  const [selectedOutro, setSelectedOutro] = useState<string | null>(null);
  const [applyToAll, setApplyToAll] = useState(true);

  // Export modal state
  const [showExportModal, setShowExportModal] = useState(false);

  // Calculate total duration from segments
  const totalDuration = segments.length > 0 
    ? segments[segments.length - 1].endTime 
    : 720;

  const handleDemoMode = () => {
    setVideoUrl(demoVideoUrl);
    setIsProcessing(true);

    // Simulate AI processing
    setTimeout(() => {
      setSegments(mockSegments);
      setIsProcessing(false);
    }, 3000);
  };

  const handleFileUpload = (file: File) => {
    const url = URL.createObjectURL(file);
    setVideoUrl(url);
    setIsProcessing(true);

    // Simulate AI processing
    setTimeout(() => {
      setSegments(mockSegments);
      setIsProcessing(false);
    }, 3000);
  };

  const handleTimeUpdate = useCallback((time: number) => {
    setCurrentTime(time);
  }, []);

  const handleSeek = (time: number) => {
    setCurrentTime(time);
  };

  const handleSegmentClick = (segment: Segment) => {
    setActiveSegmentId(segment.id);
    setCurrentTime(segment.startTime);
  };

  const handleSegmentUpdate = (updatedSegment: Segment) => {
    setSegments((prev) =>
      prev.map((s) => (s.id === updatedSegment.id ? updatedSegment : s))
    );
  };

  const handleSegmentDelete = (id: number) => {
    setSegments((prev) => prev.filter((s) => s.id !== id));
    if (activeSegmentId === id) {
      setActiveSegmentId(null);
    }
  };

  // Show upload zone if no video
  if (!videoUrl) {
    return <UploadZone onDemoMode={handleDemoMode} onFileUpload={handleFileUpload} />;
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="glass border-b border-border/50 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg ai-gradient flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold ai-gradient-text">SmartCut AI</span>
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Button
            onClick={() => setShowExportModal(true)}
            className="rounded-xl ai-gradient hover:opacity-90"
            disabled={segments.length === 0}
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row gap-4 p-4 overflow-hidden">
        {/* Left Column - Video Player */}
        <div className="lg:w-[60%] flex flex-col gap-4">
          <VideoPlayer
            videoUrl={videoUrl}
            currentTime={currentTime}
            onTimeUpdate={handleTimeUpdate}
            isProcessing={isProcessing}
          />

          {/* Timeline */}
          <Timeline
            segments={segments}
            currentTime={currentTime}
            duration={totalDuration}
            onSeek={handleSeek}
            activeSegmentId={activeSegmentId}
            onSegmentClick={handleSegmentClick}
            onSegmentUpdate={handleSegmentUpdate}
          />
        </div>

        {/* Right Column - Control Center */}
        <div className="lg:w-[40%] glass rounded-2xl p-4 overflow-hidden flex flex-col">
          <Tabs defaultValue="segments" className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="w-full grid grid-cols-2 mb-4">
              <TabsTrigger value="segments" className="rounded-xl gap-2">
                <LayoutList className="w-4 h-4" />
                Segments
              </TabsTrigger>
              <TabsTrigger value="branding" className="rounded-xl gap-2">
                <Palette className="w-4 h-4" />
                Branding
              </TabsTrigger>
            </TabsList>

            <div className="flex-1 overflow-y-auto">
              <TabsContent value="segments" className="mt-0 h-full">
                <SegmentList
                  segments={segments}
                  activeSegmentId={activeSegmentId}
                  onSegmentClick={handleSegmentClick}
                  onSegmentUpdate={handleSegmentUpdate}
                  onSegmentDelete={handleSegmentDelete}
                  totalDuration={totalDuration}
                />
              </TabsContent>

              <TabsContent value="branding" className="mt-0 h-full">
                <BrandingTab
                  selectedIntro={selectedIntro}
                  selectedOutro={selectedOutro}
                  onSelectIntro={setSelectedIntro}
                  onSelectOutro={setSelectedOutro}
                  applyToAll={applyToAll}
                  onApplyToAllChange={setApplyToAll}
                />
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>

      {/* Export Modal */}
      <ExportModal
        open={showExportModal}
        onOpenChange={setShowExportModal}
        segments={segments}
        selectedIntro={selectedIntro}
        selectedOutro={selectedOutro}
      />
    </div>
  );
};

export default Index;
