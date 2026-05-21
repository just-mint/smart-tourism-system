const DEVTOOLS_SHORTCUTS = new Set(["F12"])

const isBlockedShortcut = (event: KeyboardEvent) => {
  const key = event.key.toLowerCase()
  return (
    DEVTOOLS_SHORTCUTS.has(event.key) ||
    (event.ctrlKey && event.shiftKey && ["i", "j", "c"].includes(key)) ||
    (event.metaKey && event.altKey && ["i", "j", "c"].includes(key))
  )
}

export const setupProductionDevtoolsGuard = () => {
  if (!import.meta.env.PROD || typeof window === "undefined") return

  const blockKeyboardShortcut = (event: KeyboardEvent) => {
    if (!isBlockedShortcut(event)) return
    event.preventDefault()
    event.stopPropagation()
  }

  const blockContextMenu = (event: MouseEvent) => {
    event.preventDefault()
  }

  window.addEventListener("keydown", blockKeyboardShortcut, { capture: true })
  window.addEventListener("contextmenu", blockContextMenu, { capture: true })
}
