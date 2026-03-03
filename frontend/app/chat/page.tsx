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
  const abortRef = useRef<() => void | null>(null)

  useEffect(()=>{
    // list all convs without auth
    listConversations('')
      .then(setConversations)
      .catch(()=>{})
  },[])

  async function loadHistory(id: number){
    const hist = await getHistory('', id)
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
    const cancel = streamChat(input, '', {onMessage, onMeta}, convId || undefined)
    abortRef.current = cancel
    setInput("")
  }

  return (
    <div className="p-6">
      <h2 className="text-2xl font-semibold mb-4">Chat</h2>
      <div className="flex gap-6">
        <div className="w-48">
          <h3 className="font-medium mb-2">Conversations</h3>
          {conversations.map(c=>(
            <div key={c.id} onClick={()=>loadHistory(c.id)} className={`cursor-pointer p-2 rounded ${c.id===convId?"border border-black":"border border-gray-300"}`}>
              {c.title} ({new Date(c.created_at).toLocaleString()})
            </div>
          ))}
          <button className="mt-2 px-3 py-1 bg-blue-500 text-white rounded" onClick={()=>{setMessages([]);setConvId(null);}}>New</button>
        </div>
        <div className="flex-1">
          <div className="border border-gray-300 p-4 min-h-[200px]">
            {messages.map((m,i)=>(
              <div key={i} className="mb-2">
                {m.role === 'meta' ? <em>{m.text}</em> : m.text}
              </div>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <input value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask something..." className="flex-1 border p-2 rounded" />
            <button className="px-4 py-2 bg-green-500 text-white rounded" onClick={send}>Send</button>
          </div>
        </div>
      </div>
    </div>
  )
}
