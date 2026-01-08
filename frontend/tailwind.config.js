/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
    './app/**/*.{js,jsx}',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        neu: {
          base: '#e8ecef',
          'base-dark': '#2a2d3a',
          dark: '#c8ccd0',
          light: '#ffffff',
          text: '#6b7280',
          'text-dark': '#9ca3af',
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      boxShadow: {
        // Soft neumorphic shadows (stronger)
        'neu-flat': '10px 10px 20px #c4c8cc, -10px -10px 20px #ffffff',
        'neu-pressed': 'inset 6px 6px 12px #c4c8cc, inset -6px -6px 12px #ffffff',
        'neu-convex': '10px 10px 20px #c4c8cc, -10px -10px 20px #ffffff, inset 2px 2px 4px #ffffff, inset -2px -2px 4px #c4c8cc',
        'neu-icon': '6px 6px 12px #c4c8cc, -6px -6px 12px #ffffff',
        'neu-btn': '8px 8px 16px #c4c8cc, -8px -8px 16px #ffffff',
        'neu-btn-sm': '5px 5px 10px #c4c8cc, -5px -5px 10px #ffffff',
        
        // Dark Mode Shadows (stronger)
        'neu-flat-dark': '10px 10px 20px #1a1c24, -10px -10px 20px #3a3e50',
        'neu-pressed-dark': 'inset 6px 6px 12px #1a1c24, inset -6px -6px 12px #3a3e50',
        'neu-convex-dark': '10px 10px 20px #1a1c24, -10px -10px 20px #3a3e50, inset 2px 2px 4px #3a3e50, inset -2px -2px 4px #1a1c24',
        'neu-btn-dark': '8px 8px 16px #1a1c24, -8px -8px 16px #3a3e50',
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}