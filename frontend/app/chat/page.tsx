"use client"
import { useEffect, useState, useRef } from "react"
import { streamChat } from "../../lib/api"

export default function ChatPage(){
  const [input,setInput]=useState("")
  const [messages,setMessages]=useState<string[]>([])
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  const abortRef = useRef<() => void | null>(null)

  function onMessage(chunk: string){
    setMessages(prev => {
      const copy = [...prev]
      const last = copy.pop() || ""
      return [...copy, last + chunk]
    })
  }

  async function send(){
    if(!input.trim()) return
    setMessages(prev => [...prev, input])
    const t = token || ''
    const cancel = streamChat(input, t, (chunk)=>{
      onMessage(chunk)
    })
    abortRef.current = cancel
    setInput("")
  }

  return (
    <div style={{padding:24}}>
      <h2>Chat</h2>
      <div style={{border:'1px solid #ddd',padding:12,minHeight:200}}>
        {messages.map((m,i)=>(<div key={i} style={{marginBottom:8}}>{m}</div>))}
      </div>
      <div style={{marginTop:12}}>
        <input value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask something..." style={{width:'60%'}} />
        <button onClick={send}>Send</button>
      </div>
    </div>
  )
}
