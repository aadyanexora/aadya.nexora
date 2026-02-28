import Link from "next/link"

export default function Home() {
  return (
    <main style={{padding:40,fontFamily:'Inter, Arial'}}>
      <h1>Aadya — Nexora AI</h1>
      <p>Lightweight demo: secure chat with RAG and OpenAI.</p>
      <div style={{display:'flex',gap:12}}>
        <Link href="/login"><button>Login / Register</button></Link>
        <Link href="/dashboard"><button>Dashboard</button></Link>
      </div>
    </main>
  )
}
