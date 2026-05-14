import * as React from "react"
import * as CheckboxPrimitive from "@radix-ui/react-checkbox"
import { CheckIcon } from "lucide-react"

import { cn } from "@/lib/utils"

function Checkbox({
  className,
  ...props
}: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        "peer size-4.5 shrink-0 rounded-md border border-white/20 bg-white/[0.04] shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 outline-none",
        "focus-visible:ring-2 focus-visible:ring-cyan-500/30 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950",
        "data-[state=checked]:bg-gradient-to-br data-[state=checked]:from-emerald-500 data-[state=checked]:to-cyan-500 data-[state=checked]:border-transparent data-[state=checked]:text-white data-[state=checked]:shadow-[0_0_10px_rgba(16,185,129,0.3)]",
        "disabled:cursor-not-allowed disabled:opacity-40",
        "aria-invalid:border-red-500/50",
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator
        data-slot="checkbox-indicator"
        className="flex items-center justify-center text-current transition-none"
      >
        <CheckIcon className="size-3.5" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
}

export { Checkbox }
