"use client"

import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react"
import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4 text-emerald-400" />,
        info: <InfoIcon className="size-4 text-cyan-400" />,
        warning: <TriangleAlertIcon className="size-4 text-amber-400" />,
        error: <OctagonXIcon className="size-4 text-red-400" />,
        loading: <Loader2Icon className="size-4 animate-spin text-cyan-400" />,
      }}
      toastOptions={{
        classNames: {
          toast:
            "!bg-zinc-950/90 !backdrop-blur-2xl !border !border-white/10 !rounded-xl !shadow-[0_8px_32px_rgba(0,0,0,0.5),0_0_20px_rgba(34,211,238,0.05)] !text-zinc-200",
          title: "!text-white !font-semibold !tracking-tight",
          description: "!text-zinc-400",
          actionButton:
            "!bg-gradient-to-r !from-emerald-600 !to-cyan-600 !text-white !rounded-lg !font-semibold !border-0 !shadow-[0_0_15px_rgba(16,185,129,0.2)]",
          cancelButton:
            "!bg-white/5 !text-zinc-400 !border !border-white/10 !rounded-lg hover:!text-white",
          closeButton:
            "!bg-white/5 !border !border-white/10 !text-zinc-400 hover:!text-white hover:!bg-white/10 !rounded-lg",
        },
      }}
      style={
        {
          "--normal-bg": "oklch(0.145 0 0 / 90%)",
          "--normal-text": "#e4e4e7",
          "--normal-border": "rgba(255,255,255,0.1)",
          "--border-radius": "0.75rem",
        } as React.CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }
