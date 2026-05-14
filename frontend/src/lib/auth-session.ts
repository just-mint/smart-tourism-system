const AUTH_MARKER_COOKIE = "aegis_logged_in"

const isBrowser = () => typeof document !== "undefined"

export const hasAuthSession = () => {
  if (!isBrowser()) return false
  return document.cookie
    .split(";")
    .some((cookie) => cookie.trim().startsWith(`${AUTH_MARKER_COOKIE}=true`))
}

export const markAuthSession = () => {
  if (!isBrowser()) return
  document.cookie = `${AUTH_MARKER_COOKIE}=true; path=/; max-age=604800; SameSite=Lax`
}

export const clearAuthSession = () => {
  if (!isBrowser()) return
  document.cookie = `${AUTH_MARKER_COOKIE}=; path=/; max-age=0; SameSite=Lax`
}

export const redirectToLogin = () => {
  if (typeof window === "undefined") return
  if (window.location.pathname !== "/login") {
    window.location.assign("/login")
  }
}

export const handleUnauthorizedSession = () => {
  clearAuthSession()
  redirectToLogin()
}
