import { Fragment } from "react"
import { CodeBlock } from "./code-block"

function renderInline(text: string, keyBase: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let last = 0
  let i = 0
  let m: RegExpExecArray | null
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index))
    const tok = m[0]
    if (tok.startsWith("**")) {
      nodes.push(
        <strong key={`${keyBase}-${i}`} className="text-foreground font-semibold">
          {tok.slice(2, -2)}
        </strong>,
      )
    } else {
      nodes.push(
        <code key={`${keyBase}-${i}`} className="font-mono text-[0.9em] text-primary-light">
          {tok.slice(1, -1)}
        </code>,
      )
    }
    last = m.index + tok.length
    i++
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}

/** Minimal markdown renderer: fenced code, bold, inline code, bullets, headings. */
export function Prose({ text }: { text: string }) {
  const segments = text.split(/```/)
  return (
    <div className="flex flex-col gap-3">
      {segments.map((seg, si) => {
        if (si % 2 === 1) {
          const nl = seg.indexOf("\n")
          const lang = nl > 0 ? seg.slice(0, nl).trim() : ""
          const code = (nl > 0 ? seg.slice(nl + 1) : seg).replace(/\n$/, "")
          return <CodeBlock key={si} code={code} language={lang || "text"} />
        }

        const blocks: React.ReactNode[] = []
        let bullets: string[] = []
        const flush = (k: string) => {
          if (bullets.length) {
            const items = bullets
            blocks.push(
              <ul key={k} className="flex flex-col gap-1.5 list-disc pl-5">
                {items.map((b, bi) => (
                  <li key={bi} className="font-sans text-[15px] leading-[1.7] text-muted-foreground">
                    {renderInline(b, `${k}-${bi}`)}
                  </li>
                ))}
              </ul>,
            )
            bullets = []
          }
        }

        seg.split("\n").forEach((line, li) => {
          const t = line.trim()
          const bullet = t.match(/^[-*]\s+(.*)$/)
          if (bullet) {
            bullets.push(bullet[1])
            return
          }
          flush(`${si}-ul-${li}`)
          if (!t || /^-{3,}$/.test(t)) return
          const heading = t.match(/^#{1,6}\s+(.*)$/)
          if (heading) {
            blocks.push(
              <p key={`${si}-h-${li}`} className="font-sans text-foreground font-semibold mt-1">
                {renderInline(heading[1], `${si}-h-${li}`)}
              </p>,
            )
            return
          }
          blocks.push(
            <p key={`${si}-p-${li}`} className="font-sans text-[15px] leading-[1.75] text-muted-foreground">
              {renderInline(t, `${si}-${li}`)}
            </p>,
          )
        })
        flush(`${si}-ul-end`)
        return <Fragment key={si}>{blocks}</Fragment>
      })}
    </div>
  )
}
