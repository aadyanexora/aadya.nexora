"use client"
import { useState } from "react"
import { register, login } from "../../lib/api"
import { useRouter } from "next/navigation"

export default function LoginPage(){
  const [email,setEmail]=useState("")
  const [password,setPassword]=useState("")
  const router = useRouter()

  async function handleRegister(){
    const res = await register(email,password)
    if(res?.access_token){
      localStorage.setItem('token',res.access_token)
      router.push('/chat')
    }
  }

  async function handleLogin(){
    const res = await login(email,password)
    if(res?.access_token){
      localStorage.setItem('token',res.access_token)
      router.push('/chat')
    }
  }

  return (
    <div style={{padding:32}}>
      <h2>Login / Register</h2>
      <input placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} />
      <br />
      <input placeholder="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
      <br />
      <button onClick={handleLogin}>Login</button>
      <button onClick={handleRegister}>Register</button>
    </div>
  )
}
