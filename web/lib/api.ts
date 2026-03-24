import axios from "axios";

// Browser calls Vercel /api/* proxy which relays to VPS — no CORS, no Traefik needed
const API_BASE = "";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Attach token on every request
api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("tc_token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("tc_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { org_name: string; full_name: string; email: string; password: string }) =>
    api.post("/api/auth/register", data),
  login: (email: string, password: string) =>
    api.post("/api/auth/login", new URLSearchParams({ username: email, password }), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  me: () => api.get("/api/auth/me"),
};

// ─── Assessments ─────────────────────────────────────────────────────────────
export const assessmentsApi = {
  listTests: () => api.get("/api/assessments/tests"),
  create: (data: object) => api.post("/api/assessments/", data),
  list: () => api.get("/api/assessments/"),
  get: (id: string) => api.get(`/api/assessments/${id}`),
  updateStatus: (id: string, status: string) => api.patch(`/api/assessments/${id}/status?status=${status}`),
};

// ─── Candidates ──────────────────────────────────────────────────────────────
export const candidatesApi = {
  invite: (data: object) => api.post("/api/candidates/invite", data),
  listByAssessment: (assessmentId: string) => api.get(`/api/candidates/by-assessment/${assessmentId}`),
};

// ─── Sessions (candidate-facing, no auth) ───────────────────────────────────
export const sessionApi = {
  start: (token: string) => api.get(`/api/sessions/start/${token}`),
  logEvent: (sessionId: string, type: string, detail = "") =>
    api.post(`/api/sessions/session/${sessionId}/proctor-event`, { type, detail }),
  submit: (sessionId: string, responses: object[]) =>
    api.post("/api/sessions/submit", { session_id: sessionId, responses }),
};

// ─── Results ─────────────────────────────────────────────────────────────────
export const resultsApi = {
  score: (assessmentId: string) => api.post(`/api/results/score/${assessmentId}`),
  getByAssessment: (assessmentId: string) => api.get(`/api/results/assessment/${assessmentId}`),
  exportExcel: (assessmentId: string) =>
    api.get(`/api/results/export/${assessmentId}`, { responseType: "blob" }),
  downloadPdf: (candidateId: string) =>
    api.get(`/api/results/pdf/${candidateId}`, { responseType: "blob" }),
};
