import './globals.css'
import Credits from './components/Credits'

export const metadata = {
  title: 'Aadya – Nexora AI',
  description: 'Investor demo: RAG chat powered by OpenAI',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="p-4 border-b">
          <div className="max-w-4xl mx-auto flex justify-between items-center">
            <div className="font-semibold">Aadya — Nexora AI</div>
            <Credits />
          </div>
        </header>
        <main className="max-w-4xl mx-auto p-4">{children}</main>
      </body>
    </html>
  )
}
