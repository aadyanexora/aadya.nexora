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

export function streamChat(message: string, token: string, onMessage: (chunk: string) => void) {
  const evt = new EventSource(`${API_BASE}/api/chat/stream`, { withCredentials: true } as any)
  // EventSource doesn't support POST; instead use fetch and ReadableStream in browser
  const controller = new AbortController()
  fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message }),
    signal: controller.signal,
  }).then(async (res) => {
    if (!res.body) return
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value)
      onMessage(chunk)
    }
  })
  return () => controller.abort()
}
