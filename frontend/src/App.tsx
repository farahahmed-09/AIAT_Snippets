import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sessions from "./pages/Sessions";
import SessionDetails from "./pages/SessionDetails";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import { ThemeProvider } from "./components/theme-provider";

const queryClient = new QueryClient();

const App = () => (
  <ThemeProvider defaultTheme="dark" storageKey="aiat-theme">
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/sessions" replace />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/sessions/:id" element={<SessionDetails />} />
            <Route path="/demo" element={<Index />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
