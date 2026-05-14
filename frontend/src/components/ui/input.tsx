import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-10 w-full min-w-0 rounded-xl border border-white/10 bg-white/[0.04] backdrop-blur-md px-4 py-2 text-sm text-white placeholder:text-zinc-500 shadow-[inset_0_1px_2px_rgba(0,0,0,0.3)] transition-all duration-300 outline-none",
        "focus-visible:border-cyan-500/50 focus-visible:bg-white/[0.06] focus-visible:shadow-[0_0_15px_rgba(34,211,238,0.1),inset_0_1px_2px_rgba(0,0,0,0.3)] focus-visible:ring-1 focus-visible:ring-cyan-500/30",
        "file:text-white file:inline-flex file:h-7 file:border-0 file:bg-white/10 file:rounded-lg file:px-3 file:text-sm file:font-medium file:mr-3 file:cursor-pointer",
        "selection:bg-cyan-500/30 selection:text-white",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-40",
        "aria-invalid:border-red-500/50 aria-invalid:shadow-[0_0_15px_rgba(239,68,68,0.1)]",
        className
      )}
      {...props}
    />
  )
}

export { Input }
