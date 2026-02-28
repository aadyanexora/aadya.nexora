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
    <div style={{padding:32}}>
      <h2>Dashboard</h2>
      <p>Welcome to the admin demo dashboard. Use the chat to interact with your documents.</p>
      <h3>Ingested Documents</h3>
      <ul>
        {docs.map(d=>(
          <li key={d.id} style={{marginBottom:8}}>
            <strong>{d.name || `doc ${d.id}`}</strong> ({d.chunk_count} chunks)
            <ul>
              {d.chunks.map(c=><li key={c.id}>chunk {c.index}</li>)}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  )
}
