import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center justify-center rounded-full border px-3 py-0.5 text-[11px] font-semibold w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1.5 [&>svg]:pointer-events-none tracking-wide uppercase font-mono transition-all duration-300 overflow-hidden",
  {
    variants: {
      variant: {
        default:
          "border-cyan-500/30 bg-cyan-500/10 text-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.1)]",
        secondary:
          "border-white/10 bg-white/5 text-zinc-300 backdrop-blur-md",
        destructive:
          "border-red-500/30 bg-red-500/10 text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.1)]",
        outline:
          "border-white/15 bg-transparent text-zinc-300 hover:bg-white/5 hover:text-white",
        success:
          "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.1)]",
        warning:
          "border-amber-500/30 bg-amber-500/10 text-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.1)]",
        purple:
          "border-purple-500/30 bg-purple-500/10 text-purple-400 shadow-[0_0_10px_rgba(168,85,247,0.1)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "span"

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
