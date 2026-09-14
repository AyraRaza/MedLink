import { apiClient } from "./api";

const ACCESS_TOKEN_KEY = "medlink_access_token";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "hospital_staff";
  is_active: boolean;
  created_at: string;
};

type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type Registration = {
  email: string;
  password: string;
  full_name: string;
};

export function getAccessToken() {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY) || window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string, rememberMe = true) {
  const storage = rememberMe ? window.localStorage : window.sessionStorage;
  const otherStorage = rememberMe ? window.sessionStorage : window.localStorage;
  otherStorage.removeItem(ACCESS_TOKEN_KEY);
  storage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken() {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}

export async function login(email: string, password: string, rememberMe = true) {
  const { data } = await apiClient.post<AuthResponse>("/auth/login", { email, password });
  setAccessToken(data.access_token, rememberMe);
  return data.user;
}

export async function registerUser(payload: Registration) {
  const { data } = await apiClient.post<User>("/auth/register", payload);
  return data;
}

export async function getCurrentUser() {
  const { data } = await apiClient.get<User>("/auth/me");
  return data;
}
