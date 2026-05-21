import { Link } from "@tanstack/react-router"
import { Compass } from "lucide-react"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content =
    variant === "responsive" ? (
      <div className={cn("flex items-center gap-2", className)}>
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md">
          <Compass className="size-4" />
        </div>
        <span className="text-lg font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-500 to-purple-600 group-data-[collapsible=icon]:hidden">
          AEGIS
        </span>
      </div>
    ) : (
      <div className={cn("flex items-center gap-2", className)}>
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md">
          <Compass className="size-4" />
        </div>
        {variant === "full" && (
          <span className="text-lg font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-500 to-purple-600">
            AEGIS
          </span>
        )}
      </div>
    )

  if (!asLink) {
    return content
  }

  return <Link to="/">{content}</Link>
}
