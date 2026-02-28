const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function register(email: string, password: string) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  return res.json()
}

export async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  return res.json()
}

interface StreamCallbacks {
  onMessage: (chunk: string) => void
  onMeta?: (meta: any) => void
}

export function streamChat(
  message: string,
  token: string,
  callbacks: StreamCallbacks,
  conversation_id?: number
) {
  const { onMessage, onMeta } = callbacks
  const controller = new AbortController()
  const body: any = { message }
  if (conversation_id) body.conversation_id = conversation_id
  fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    signal: controller.signal,
  }).then(async (res) => {
    if (!res.body) return
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ""
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value)
      // split on double newline which separates events
      let parts = buf.split("\n\n")
      buf = parts.pop() || ""
      for (const part of parts) {
        if (!part.startsWith("data:")) continue
        const payload = part.slice(5).trim()
        try {
          const obj = JSON.parse(payload)
          // metadata event
          if (onMeta) onMeta(obj)
        } catch (e) {
          onMessage(payload)
        }
      }
    }
  })
  return () => controller.abort()
}

export async function listConversations(token: string) {
  const res = await fetch(`${API_BASE}/api/chat/conversations`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return res.json()
}

export async function getHistory(token: string, conversation_id: number) {
  const res = await fetch(`${API_BASE}/api/chat/history/${conversation_id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return res.json()
}

export async function listDocuments(token: string) {
  const res = await fetch(`${API_BASE}/api/admin/documents`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return res.json()
}
