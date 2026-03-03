"use client"

import { useEffect, useState } from "react"
import { listDocuments } from "../../lib/api"

type Doc = { id: number; name: string | null; chunk_count: number; chunks: {id:number;index:number}[] }


export default function Dashboard(){
  const [docs,setDocs] = useState<Doc[]>([])
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null

  useEffect(()=>{
    if(!token) return
    listDocuments(token).then(setDocs)
  },[token])

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
      <p className="mb-6">Welcome to the admin demo dashboard. Use the chat to interact with your documents.</p>
      <h3 className="text-xl font-semibold mb-2">Ingested Documents</h3>
      <ul className="space-y-4">
        {docs.map(d=>(
          <li key={d.id} className="border p-4 rounded">
            <strong>{d.name || `doc ${d.id}`}</strong> ({d.chunk_count} chunks)
            <ul className="list-disc ml-5 mt-2">
              {d.chunks.map(c=><li key={c.id}>chunk {c.index}</li>)}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  )
}
