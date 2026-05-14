import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold tracking-wide transition-all duration-300 ease-out disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/40 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 cursor-pointer",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-emerald-600 to-cyan-600 text-white shadow-[0_0_20px_rgba(16,185,129,0.25)] hover:shadow-[0_0_30px_rgba(16,185,129,0.4)] hover:from-emerald-500 hover:to-cyan-500 hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_0_15px_rgba(16,185,129,0.2)]",
        destructive:
          "bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-[0_0_15px_rgba(239,68,68,0.2)] hover:shadow-[0_0_25px_rgba(239,68,68,0.35)] hover:from-red-500 hover:to-rose-500 hover:-translate-y-0.5",
        outline:
          "border border-white/10 bg-white/[0.03] backdrop-blur-xl text-zinc-200 shadow-xs hover:bg-white/[0.08] hover:border-cyan-500/40 hover:text-white hover:shadow-[0_0_20px_rgba(34,211,238,0.1)]",
        secondary:
          "bg-zinc-800/60 backdrop-blur-md text-zinc-200 border border-white/5 hover:bg-zinc-700/60 hover:border-white/10 hover:text-white",
        ghost:
          "text-zinc-400 hover:text-white hover:bg-white/[0.06] hover:backdrop-blur-md",
        link: "text-cyan-400 underline-offset-4 hover:underline hover:text-cyan-300",
        gold: "bg-gradient-to-r from-amber-600 to-yellow-500 text-zinc-950 font-bold shadow-[0_0_20px_rgba(245,158,11,0.25)] hover:shadow-[0_0_30px_rgba(245,158,11,0.4)] hover:from-amber-500 hover:to-yellow-400 hover:-translate-y-0.5",
      },
      size: {
        default: "h-10 px-5 py-2.5 has-[>svg]:px-4",
        sm: "h-8 rounded-lg gap-1.5 px-3.5 text-xs has-[>svg]:px-2.5",
        lg: "h-12 rounded-xl px-8 text-base has-[>svg]:px-5",
        icon: "size-10 rounded-xl",
        "icon-sm": "size-8 rounded-lg",
        "icon-lg": "size-12 rounded-xl",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
