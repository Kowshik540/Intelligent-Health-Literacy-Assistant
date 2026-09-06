// Central API configuration.
//
// The backend base URL is read from the Vite env variable VITE_API_BASE_URL
// when provided (e.g. in a .env file), otherwise it defaults to the local
// backend on port 8000. This keeps every API call in the app pointing at one
// place, so the project runs on any machine without editing source files.

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

// Convenience builder for API v1 endpoints.
export const apiUrl = (path: string): string => {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}/api/v1${clean}`;
};
