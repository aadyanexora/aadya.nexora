import './globals.css'

export const metadata = {
  title: 'Aadya – Nexora AI',
  description: 'Investor demo: RAG chat powered by OpenAI',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
