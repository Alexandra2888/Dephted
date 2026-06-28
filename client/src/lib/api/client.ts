import { createClient } from "@/lib/supabase/client";
import type { SSEEvent } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

async function getAuthHeaders(): Promise<HeadersInit> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) throw new Error("No active session");

  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.access_token}`,
  };
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

export async function apiGet<T>(path: string): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, { headers });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

/**
 * Consume a `text/event-stream` SSE endpoint, parsing each `data:` line as a typed
 * {@link SSEEvent} and dispatching it to `onEvent`. Resolves when the stream closes.
 */
export async function streamSSE(
  path: string,
  body: unknown,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body)
    throw new Error(`Stream ${path} failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const flush = (chunk: string) => {
    buffer += chunk.replace(/\r/g, "");
    // SSE events are separated by a blank line; each event may have multiple
    // `data:` lines that concatenate.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const data = raw
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).replace(/^ /, ""))
        .join("");
      if (!data) continue;
      try {
        onEvent(JSON.parse(data) as SSEEvent);
      } catch {
        // ignore keep-alives / non-JSON comments
      }
    }
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        // Drain any buffered bytes, then terminate a trailing event that wasn't
        // followed by a blank line so the final done/error event isn't dropped.
        flush(decoder.decode());
        flush("\n\n");
        break;
      }
      flush(decoder.decode(value, { stream: true }));
    }
  } finally {
    // Release the lock and tear down the underlying connection if the caller
    // aborted (navigated away) mid-stream, instead of leaking it.
    reader.cancel().catch(() => {});
  }
}
