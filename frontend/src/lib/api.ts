// SmartCut AI API Client

export const BACKEND_URL = "http://localhost:8000";
const API_BASE_URL = `${BACKEND_URL}/api/v1`;

// Fetch with timeout helper
const fetchWithTimeout = async (
  url: string,
  options?: RequestInit,
  timeout = 5000
): Promise<Response> => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
};

export interface Session {
  id: number;
  name: string;
  module?: string;
  drive_link: string;
  video_url?: string;
  job_status: string;
  created_at: string;
}

export interface Snippet {
  id: number;
  session_id: number;
  name: string;
  summary: string;
  start_second: number;
  end_second: number;
  storage_link?: string | null;
  created_at: string;
}

export interface SessionWithSnippets extends Session {
  snippets: Snippet[];
}

export interface UploadSessionRequest {
  name: string;
  module?: string;
  drive_link: string;
}

export interface UpdatePlanRequest {
  snippets: {
    name: string;
    start: number;
    end: number;
    summary: string;
  }[];
}

// Sessions API
export const sessionsApi = {
  uploadSession: async (data: UploadSessionRequest): Promise<Session> => {
    const response = await fetchWithTimeout(`${API_BASE_URL}/upload-session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error("Failed to upload session");
    return response.json();
  },

  listSessions: async (params?: {
    skip?: number;
    limit?: number;
    sort_by?: string;
    order?: "asc" | "desc";
  }): Promise<Session[]> => {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set("skip", params.skip.toString());
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.sort_by) searchParams.set("sort_by", params.sort_by);
    if (params?.order) searchParams.set("order", params.order);

    const response = await fetchWithTimeout(
      `${API_BASE_URL}/sessions?${searchParams}`
    );
    if (!response.ok) throw new Error("Failed to fetch sessions");
    return response.json();
  },

  getJobStatus: async (sessionId: number): Promise<{ job_status: string }> => {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/jobs/${sessionId}/status`
    );
    if (!response.ok) throw new Error("Failed to get job status");
    return response.json();
  },

  getSessionResults: async (
    sessionId: number
  ): Promise<SessionWithSnippets> => {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/sessions/${sessionId}/results`
    );
    if (!response.ok) throw new Error("Failed to get session results");
    return response.json();
  },

  updatePlan: async (
    sessionId: number,
    data: UpdatePlanRequest
  ): Promise<SessionWithSnippets> => {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/sessions/${sessionId}/plan`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }
    );
    if (!response.ok) throw new Error("Failed to update plan");
    return response.json();
  },
};

// Snippets API
export const snippetsApi = {
  processSnippet: async (
    snippetId: number
  ): Promise<{ message: string; task_id: string }> => {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/snippets/${snippetId}/process`,
      {
        method: "POST",
      }
    );
    if (!response.ok) throw new Error("Failed to process snippet");
    return response.json();
  },
};

export const getSnippetDownloadUrl = (snippetId: number): string =>
  `${API_BASE_URL}/snippets/${snippetId}/download`;

// Status helpers
export const getStatusColor = (status: string): string => {
  if (status === "Finished")
    return "bg-green-500/20 text-green-400 border-green-500/30";
  if (status === "Failed")
    return "bg-red-500/20 text-red-400 border-red-500/30";
  if (status === "Pending")
    return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
  if (status.startsWith("Processing"))
    return "bg-blue-500/20 text-blue-400 border-blue-500/30";
  return "bg-muted text-muted-foreground";
};

export const getStatusLabel = (status: string): string => {
  if (status.startsWith("Processing:")) {
    return status.replace("Processing:", "").trim();
  }
  return status;
};
