/* LipiLens API client — single place for all backend calls. */

const BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

/** Backend returns image paths like /files/raw/1/original.png — absolutize. */
export function imgUrl(path) {
  return path ? BASE + path : null;
}

async function request(path, options = {}) {
  const res = await fetch(BASE + path, options);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) {
        detail = Array.isArray(body.detail)
          ? body.detail.map((d) => d.msg).join("; ")
          : body.detail;
      }
    } catch {
      /* keep generic message */
    }
    throw new Error(detail);
  }
  return res.json();
}

export function uploadManuscript(file, { title, identifier, configName }) {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  if (identifier) form.append("identifier", identifier);
  form.append("config_name", configName || "full_restoration");
  return request("/api/manuscripts", { method: "POST", body: form });
}

export function listManuscripts({ search, verifiedOnly, limit = 50, offset = 0 } = {}) {
  const q = new URLSearchParams();
  if (search) q.append("search", search);
  if (verifiedOnly) q.append("verified", "true");
  q.append("limit", String(limit));
  q.append("offset", String(offset));
  return request(`/api/manuscripts?${q.toString()}`);
}

export function getManuscript(id) {
  return request(`/api/manuscripts/${id}`);
}

export function verifyTranscription(id, verifiedTranscription) {
  return request(`/api/transcriptions/${id}/verify`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ verified_transcription: verifiedTranscription }),
  });
}

export function health() {
  return request("/api/health");
}

export const PRESET_CONFIGS = [
  "original",
  "grayscale",
  "denoised",
  "enhanced",
  "binarized",
  "deskewed",
  "full_restoration",
];
