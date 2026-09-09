import { ref } from "vue"

const STORAGE_KEY = "paymethodfinder.token"

function readStoredToken() {
  try {
    return localStorage.getItem(STORAGE_KEY) || ""
  } catch {
    return ""
  }
}

const tokenRef = ref(readStoredToken())

export function getToken() {
  return tokenRef.value
}

export function setToken(token) {
  tokenRef.value = token
  try {
    localStorage.setItem(STORAGE_KEY, token)
  } catch {
    // A blocked storage only means the login is asked for again next visit.
  }
}

export function clearToken() {
  tokenRef.value = ""
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing to clean up.
  }
}

export const isUnlocked = () => Boolean(tokenRef.value)
