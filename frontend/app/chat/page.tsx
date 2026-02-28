"use client"
import { useEffect, useState, useRef } from "react"
import { streamChat, listConversations, getHistory } from "../../lib/api"

type Message = {
  role: "user" | "assistant" | "meta"
  text: string
  meta?: any
}

type Conversation = { id: number; title: string; created_at: string }

export default function ChatPage(){
  const [input,setInput]=useState("")
  const [messages,setMessages]=useState<Message[]>([])
  const [conversations,setConversations]=useState<Conversation[]>([])
  const [convId,setConvId]=useState<number | null>(null)
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  const abortRef = useRef<() => void | null>(null)

  useEffect(()=>{
    if(!token) return
    listConversations(token).then(setConversations)
  },[token])

  async function loadHistory(id: number){
    if(!token) return
    const hist = await getHistory(token, id)
    const msgs: Message[] = hist.map((m:any)=>({role:m.role, text:m.content}))
    setMessages(msgs)
    setConvId(id)
  }

  function onMessage(chunk: string){
    setMessages(prev=>{
      if(prev.length === 0 || prev[prev.length-1].role !== "assistant"){
        return [...prev, {role:"assistant", text:chunk}]
      }
      const upd = [...prev]
      upd[upd.length-1].text += chunk
      return upd
    })
  }

  function onMeta(meta:any){
    // treat metadata as a separate message for now
    setMessages(prev=>[...prev, {role:"meta", text:JSON.stringify(meta), meta}])
    if(meta.conversation_id){
      setConvId(meta.conversation_id)
    }
  }

  async function send(){
    if(!input.trim()) return
    setMessages(prev => [...prev, {role:'user', text: input}])
    const t = token || ''
    const cancel = streamChat(input, t, {onMessage, onMeta}, convId || undefined)
    abortRef.current = cancel
    setInput("")
  }

  return (
    <div style={{padding:24}}>
      <h2>Chat</h2>
      <div style={{display:'flex', gap:24}}>
        <div style={{width:200}}>
          <h3>Conversations</h3>
          {conversations.map(c=>(
            <div key={c.id} onClick={()=>loadHistory(c.id)} style={{cursor:'pointer',padding:4,border:c.id===convId?"1px solid #000":"1px solid #ddd"}}>
              {c.title} ({new Date(c.created_at).toLocaleString()})
            </div>
          ))}
          <button onClick={()=>{setMessages([]);setConvId(null);}}>New</button>
        </div>
        <div style={{flex:1}}>
          <div style={{border:'1px solid #ddd',padding:12,minHeight:200}}>
            {messages.map((m,i)=>(
              <div key={i} style={{marginBottom:8}}>
                {m.role === 'meta' ? <em>{m.text}</em> : m.text}
              </div>
            ))}
          </div>
          <div style={{marginTop:12}}>
            <input value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask something..." style={{width:'60%'}} />
            <button onClick={send}>Send</button>
          </div>
        </div>
      </div>
    </div>
  )
}
