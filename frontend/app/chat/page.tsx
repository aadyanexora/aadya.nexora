"use client"
import { useEffect, useState, useRef } from "react"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { streamChat, listConversations, getHistory } from "../../lib/api"

type Message = {
  role: "user" | "assistant" | "meta"
  text: string
  meta?: any
  sources?: any[]
  timestamp?: string
}

type Conversation = { id: number; title: string; created_at: string }

export default function ChatPage(){
  const [input,setInput]=useState("")
  const [messages,setMessages]=useState<Message[]>([])
  const [conversations,setConversations]=useState<Conversation[]>([])
  const [convId,setConvId]=useState<number | null>(null)
  const abortRef = useRef<() => void | null>(null)
  const [waitingFirst, setWaitingFirst] = useState(false)

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
        setWaitingFirst(false)
        return [...prev, {role:"assistant", text:chunk, timestamp: new Date().toISOString()}]
      }
      const upd = [...prev]
      upd[upd.length-1].text += chunk
      return upd
    })
  }

  function onMeta(meta:any){
    // final structured payload with answer/sources
    if (meta && (meta.answer || meta.sources)) {
      setMessages(prev=>{
        if(prev.length===0) return prev
        const upd = [...prev]
        const last = upd[upd.length-1]
        if(last.role === 'assistant'){
          last.sources = meta.sources || []
          last.timestamp = new Date().toISOString()
        } else {
          upd.push({role:'assistant', text: meta.answer || '', sources: meta.sources || [], timestamp: new Date().toISOString()})
        }
        return upd
      })
    } else {
      // generic metadata event: keep for backwards compatibility
      setMessages(prev=>[...prev, {role:"meta", text:JSON.stringify(meta), meta}])
      if(meta.conversation_id){
        setConvId(meta.conversation_id)
      }
    }
  }

  async function send(){
    if(!input.trim()) return
    setMessages(prev => [...prev, {role:'user', text: input}])
    setWaitingFirst(true)
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
                {m.role === 'meta' ? (
                  <em>{m.text}</em>
                ) : m.role === 'assistant' ? (
                  <div>
                    <div className="prose">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Model: Groq | 384-dim RAG | {m.timestamp ? new Date(m.timestamp).toLocaleString() : ''}</div>
                    {m.sources && m.sources.length>0 && (
                      <details className="mt-2 p-2 border rounded">
                        <summary className="cursor-pointer">Sources ({m.sources.length})</summary>
                        <ul className="mt-2 list-disc list-inside text-sm">
                          {m.sources.map((s,si)=> (
                            <li key={si}>
                              <strong>{s.document_title || s.document_id}</strong> — chunk {s.chunk_index}: {s.snippet}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                ) : (
                  m.text
                )}
              </div>
            ))}

            {waitingFirst && (
              <div className="mt-2 text-gray-600">Loading response…</div>
            )}
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
