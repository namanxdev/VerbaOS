import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority"

import { cn } from "../../lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-all duration-200 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90 rounded-md",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded-md",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground rounded-md",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80 rounded-md",
        ghost: "hover:bg-accent hover:text-accent-foreground rounded-md",
        link: "text-primary underline-offset-4 hover:underline",
        // Neumorphic variants
        neu: "bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark rounded-full hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark",
        "neu-pill": "bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark rounded-full hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark",
        "neu-square": "bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark rounded-2xl hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark",
        "neu-pressed": "bg-neu-base dark:bg-neu-base-dark text-slate-500 dark:text-slate-400 shadow-neu-pressed dark:shadow-neu-pressed-dark rounded-full",
        "neu-convex": "bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-convex dark:shadow-neu-convex-dark rounded-full",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3 text-xs",
        lg: "h-12 px-8 text-base",
        xl: "h-14 px-10 text-lg",
        icon: "h-10 w-10",
        "icon-lg": "h-14 w-14",
        "icon-xl": "h-20 w-20",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const Button = React.forwardRef(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      {...props}
    />
  )
})
Button.displayName = "Button"

export { Button, buttonVariants }