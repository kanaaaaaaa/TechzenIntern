const STORAGE_KEY = "paymethodfinder.token"

export function getToken() {
  try {
    return localStorage.getItem(STORAGE_KEY) || ""
  } catch {
    return ""
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(STORAGE_KEY, token)
  } catch {
    // A blocked storage only means the password is asked for again next visit.
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing to clean up.
  }
}

export const isUnlocked = () => Boolean(getToken())
