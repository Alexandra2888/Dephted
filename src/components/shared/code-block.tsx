import { cn } from "@/lib/utils"

interface CodeBlockProps {
  code: string
  language?: string
  className?: string
}

const KEYWORDS = new Set([
  "def", "async", "await", "return", "class", "import", "from",
  "if", "else", "elif", "for", "in", "with", "as", "raise", "try",
  "except", "finally", "None", "True", "False", "self", "lambda",
  "yield", "pass", "break", "continue", "global", "nonlocal", "not",
  "and", "or", "is",
])

function tokenize(line: string, lineKey: number): React.ReactNode {
  const commentMatch = line.match(/^(\s*)(#.*)$/)
  if (commentMatch) {
    return (
      <>
        <span>{commentMatch[1]}</span>
        <span className="text-subtle-foreground italic">{commentMatch[2]}</span>
      </>
    )
  }

  const tokens = line.split(/(\s+|[(),:\[\]{}=.@]|"[^"]*"|'[^']*')/)
  return tokens.map((t, i) => {
    if (!t) return null
    if (KEYWORDS.has(t)) {
      return (
        <span key={`${lineKey}-${i}`} className="text-primary-light">
          {t}
        </span>
      )
    }
    if (/^["']/.test(t)) {
      return (
        <span key={`${lineKey}-${i}`} className="text-success">
          {t}
        </span>
      )
    }
    if (/^\d+(\.\d+)?$/.test(t)) {
      return (
        <span key={`${lineKey}-${i}`} className="text-warning">
          {t}
        </span>
      )
    }
    if (/^[A-Z][A-Za-z0-9_]*$/.test(t)) {
      return (
        <span key={`${lineKey}-${i}`} className="text-cyan-300">
          {t}
        </span>
      )
    }
    return <span key={`${lineKey}-${i}`}>{t}</span>
  })
}

export function CodeBlock({ code, language = "python", className }: CodeBlockProps) {
  const lines = code.split("\n")
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card-elevated overflow-hidden",
        className,
      )}
    >
      <div className="flex items-center justify-between px-3.5 py-2 border-b border-border">
        <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-subtle-foreground">
          {language}
        </span>
        <div className="flex gap-1.5">
          <span className="w-2 h-2 rounded-full bg-destructive/60" />
          <span className="w-2 h-2 rounded-full bg-warning/60" />
          <span className="w-2 h-2 rounded-full bg-success/60" />
        </div>
      </div>
      <pre className="m-0 px-3.5 py-4 overflow-x-auto font-mono text-[13px] leading-[1.7] text-foreground">
        {lines.map((line, i) => (
          <div key={i}>{line ? tokenize(line, i) : " "}</div>
        ))}
      </pre>
    </div>
  )
}
