import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { ApiError, OpenAPI } from "./client"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import "./index.css"

import { API_BASE } from "./client/aegis-api"
import { clearAuthSession, handleUnauthorizedSession } from "./lib/auth-session"
import { setupProductionDevtoolsGuard } from "./lib/production-devtools-guard"
import { routeTree } from "./routeTree.gen"

OpenAPI.BASE = API_BASE
OpenAPI.WITH_CREDENTIALS = true
setupProductionDevtoolsGuard()

OpenAPI.interceptors.response.use((response) => {
  if ([401, 403].includes(response.status)) {
    handleUnauthorizedSession()
  }
  return response
})

const handleApiError = (error: Error) => {
  if (error instanceof ApiError && [401, 403].includes(error.status)) {
    clearAuthSession()
    window.location.assign("/login")
  }
}
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

const router = createRouter({ routeTree })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
