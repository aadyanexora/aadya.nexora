"use client"
import { useEffect, useState } from 'react'

export default function Credits() {
  const [credits, setCredits] = useState<number | null>(null)

  useEffect(() => {
    const tok = localStorage.getItem('token')
    if (!tok) return
    fetch('/api/auth/me', { headers: { Authorization: `Bearer ${tok}` } })
      .then(r => r.json())
      .then(d => {
        if (d && typeof d.credits !== 'undefined') setCredits(d.credits)
      })
      .catch(() => {})
  }, [])

  if (credits === null) return null
  return (
    <div className="text-sm text-gray-700">Credits: {credits}</div>
  )
}
