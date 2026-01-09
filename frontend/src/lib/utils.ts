import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { BACKEND_URL } from "./api";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Convert share links from Google Drive into a direct download URL so the
 * native video element can play them. Returns the original URL if it is
 * already playable or no drive id can be found.
 */
export function toPlayableVideoUrl(url?: string | null): string {
  if (!url) return "";

  // If it's a relative path from our backend, prefix it
  if (url.startsWith("/output/")) {
    return BACKEND_URL ? `${BACKEND_URL}${url}` : url;
  }

  if (!url.includes("drive.google.com")) return url;

  const fileIdMatch =
    url.match(/\/file\/d\/([^/]+)/) ||
    url.match(/id=([^&]+)/) ||
    url.match(/\/d\/([^/]+)/);

  if (!fileIdMatch) return url;

  const fileId = fileIdMatch[1];
  return `https://drive.google.com/uc?export=download&id=${fileId}`;
}

/**
 * Format seconds into a readable time string (MM:SS or HH:MM:SS)
 */
export function formatTime(seconds: number): string {
  if (!seconds || isNaN(seconds)) return "0:00";
  
  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Get Tailwind background color class for a segment color
 */
export function getSegmentColor(color?: string): string {
  const colorMap: Record<string, string> = {
    blue: "bg-blue-500",
    green: "bg-green-500",
    purple: "bg-purple-500",
    orange: "bg-orange-500",
    pink: "bg-pink-500",
  };
  return colorMap[color || "blue"] || "bg-blue-500";
}

/**
 * Get Tailwind border color class for a segment color
 */
export function getSegmentBorderColor(color?: string): string {
  const colorMap: Record<string, string> = {
    blue: "border-blue-500",
    green: "border-green-500",
    purple: "border-purple-500",
    orange: "border-orange-500",
    pink: "border-pink-500",
  };
  return colorMap[color || "blue"] || "border-blue-500";
}
