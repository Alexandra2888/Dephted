import { cn } from "@/lib/utils"

type Variant = "wordmark" | "wordmark-tagline" | "favicon"
type Theme = "light" | "dark" | "auto"

interface DepthedLogoProps {
  variant?: Variant
  theme?: Theme
  className?: string
}

const CURSOR_STYLE = `
  @keyframes depthed-blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
  }
  .depthed-cursor { animation: depthed-blink 1.1s step-end infinite; }
`

export function DepthedLogo({
  variant = "wordmark",
  theme = "auto",
  className,
}: DepthedLogoProps) {
  const isDark = theme === "dark"
  const textColor = isDark ? "#ffffff" : "currentColor"
  const mutedColor = isDark ? "rgba(255,255,255,0.35)" : "currentColor"
  const mutedOpacity = isDark ? 1 : 0.4
  const faviconBg = isDark ? "#1e1e1e" : "#f0f0ee"

  if (variant === "favicon") {
    return (
      <svg
        width="52"
        height="52"
        viewBox="0 0 52 52"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={cn(className)}
        role="img"
        aria-label="depthed"
      >
        <style>{CURSOR_STYLE}</style>
        <rect width="52" height="52" rx="10" fill={faviconBg} />
        <text x="8" y="36" fontFamily="monospace" fontSize="26" fontWeight="700" fill={textColor}>d</text>
        <rect className="depthed-cursor" x="30" y="13" width="8" height="18" rx="1.5" fill={textColor} />
      </svg>
    )
  }

  if (variant === "wordmark-tagline") {
    return (
      <svg
        width="190"
        height="62"
        viewBox="0 0 190 62"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={cn(className)}
        role="img"
        aria-label="depthed — learn by going deeper"
      >
        <style>{CURSOR_STYLE}</style>
        <text x="0" y="34" fontFamily="monospace" fontSize="30" fontWeight="700" fill={textColor} letterSpacing="-1">depthed</text>
        <rect className="depthed-cursor" x="158" y="10" width="14" height="26" rx="2" fill={textColor} />
        <text x="1" y="52" fontFamily="monospace" fontSize="11" fill={mutedColor} opacity={mutedOpacity} letterSpacing="0.1em">learn by going deeper_</text>
      </svg>
    )
  }

  return (
    <svg
      width="180"
      height="52"
      viewBox="0 0 180 52"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn(className)}
      role="img"
      aria-label="depthed"
    >
      <style>{CURSOR_STYLE}</style>
      <text x="0" y="36" fontFamily="monospace" fontSize="30" fontWeight="700" fill={textColor} letterSpacing="-1">depthed</text>
      <rect className="depthed-cursor" x="158" y="10" width="14" height="26" rx="2" fill={textColor} />
    </svg>
  )
}
