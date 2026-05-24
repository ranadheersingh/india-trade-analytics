"use client";

import axios, { AxiosInstance } from "axios";

// Relative URL — requests go through the Next.js proxy rewrite to the backend.
// Works from any IP/hostname; browser never needs direct access to :8001.
const API_BASE = "/api/v1";

let cachedClient: AxiosInstance | null = null;

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("trade_token");
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem("trade_token", token);
  else localStorage.removeItem("trade_token");
}

export function api(): AxiosInstance {
  if (cachedClient) return cachedClient;
  const client = axios.create({ baseURL: API_BASE });
  client.interceptors.request.use(cfg => {
    const t = getToken();
    if (t) cfg.headers.Authorization = `Bearer ${t}`;
    return cfg;
  });
  client.interceptors.response.use(
    r => r,
    err => {
      if (err.response?.status === 401 && typeof window !== "undefined") {
        setToken(null);
        if (window.location.pathname !== "/login") {
          window.location.href = "/login";
        }
      }
      return Promise.reject(err);
    }
  );
  cachedClient = client;
  return client;
}

// ---- Helpers ----
export async function login(email: string, password: string) {
  const r = await api().post("/auth/login", { email, password });
  setToken(r.data.access_token);
  return r.data;
}

export async function getMe() {
  const r = await api().get("/auth/me");
  return r.data;
}

export function logout() {
  setToken(null);
  if (typeof window !== "undefined") window.location.href = "/login";
}
