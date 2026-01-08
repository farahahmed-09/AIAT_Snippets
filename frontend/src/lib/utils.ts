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
