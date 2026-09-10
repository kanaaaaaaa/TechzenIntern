import axios from "axios"

import { clearToken, getToken } from "./auth"


export const api = axios.create({
  // In a build, Django serves the app from the same origin, so /api is enough.
  baseURL: import.meta.env.VITE_API_URL || (import.meta.env.DEV
    ? `http://${window.location.hostname}:8000/api`
    : "/api"),
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Token ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // An expired or invalid token means the password has to be entered again.
    if (error.response?.status === 401 || error.response?.status === 403) {
      clearToken()
      if (window.location.pathname !== "/login") window.location.assign("/login")
    }
    return Promise.reject(error)
  },
)

export const register = (username) =>
  api.post("/auth/register/", { username }).then((response) => response.data)

export const login = (username) =>
  api.post("/auth/login/", { username }).then((response) => response.data)

export const logout = () =>
  api.post("/auth/logout/")

export const getAccount = () =>
  api.get("/auth/me/").then((response) => response.data)

export const listStores = (params = {}) =>
  api.get("/stores/", { params }).then((response) => response.data)

export const getStore = (id) =>
  api.get(`/stores/${id}/`).then((response) => response.data)

export const createStore = (payload) =>
  api.post("/stores/", payload).then((response) => response.data)

export const updateStore = (id, payload) =>
  api.patch(`/stores/${id}/`, payload).then((response) => response.data)

export const deleteStore = (id) =>
  api.delete(`/stores/${id}/`)

export const submitStoreFeedback = (id, vote) =>
  api.post(`/stores/${id}/feedback/`, { vote }).then((response) => response.data)

export const listStoreComments = (id) =>
  api.get(`/stores/${id}/comments/`).then((response) => response.data)

export const createStoreComment = (id, text) =>
  api.post(`/stores/${id}/comments/`, { text }).then((response) => response.data)

export const updateStoreComment = (id, text) =>
  api.patch(`/stores/${id}/comments/`, { text }).then((response) => response.data)

export const listPaymentMethods = () =>
  api.get("/payment-methods/").then((response) => response.data)

export const getUserPoints = () =>
  api.get("/user/points/").then((response) => response.data)

export function apiErrorMessage(error) {
  if (!error.response) return "Cannot reach the API. Check that the Django server is running."
  const data = error.response.data
  if (typeof data === "string") return data
  if (data?.detail) return data.detail
  const first = Object.values(data || {}).flat()[0]
  return first || "The request failed."
}
