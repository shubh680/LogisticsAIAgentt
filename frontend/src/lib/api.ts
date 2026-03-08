// In production (Vercel) VITE_API_BASE_URL points to the DigitalOcean backend.
// In development the Vite proxy forwards /api/* to localhost:8000, so base stays empty.
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';
