import * as React from "react"
import { Eye, EyeOff } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "./button"

interface PasswordInputProps extends React.ComponentProps<"input"> {
  error?: string
}

const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, error, ...props }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false)

    return (
      <div className="relative">
        <input
          type={showPassword ? "text" : "password"}
          data-slot="input"
          className={cn(
            "h-10 w-full min-w-0 rounded-xl border border-white/10 bg-white/[0.04] backdrop-blur-md px-4 py-2 pr-11 text-sm text-white placeholder:text-zinc-500 shadow-[inset_0_1px_2px_rgba(0,0,0,0.3)] transition-all duration-300 outline-none",
            "focus-visible:border-cyan-500/50 focus-visible:bg-white/[0.06] focus-visible:shadow-[0_0_15px_rgba(34,211,238,0.1),inset_0_1px_2px_rgba(0,0,0,0.3)] focus-visible:ring-1 focus-visible:ring-cyan-500/30",
            "selection:bg-cyan-500/30 selection:text-white",
            "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-40",
            "aria-invalid:border-red-500/50 aria-invalid:shadow-[0_0_15px_rgba(239,68,68,0.1)]",
            className
          )}
          ref={ref}
          aria-invalid={!!error}
          {...props}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="absolute right-1 top-1/2 -translate-y-1/2 size-8 rounded-lg text-zinc-500 hover:text-cyan-400 hover:bg-white/[0.06]"
          onClick={() => setShowPassword(!showPassword)}
          aria-label={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </Button>
      </div>
    )
  }
)

PasswordInput.displayName = "PasswordInput"

export { PasswordInput }
