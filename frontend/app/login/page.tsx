"use client"
import { useState } from "react"
import { register, login } from "../../lib/api"
import { useRouter } from "next/navigation"

export default function LoginPage(){
  const [email,setEmail]=useState("")
  const [password,setPassword]=useState("")
  const [loading,setLoading]=useState(false)
  const [error,setError]=useState("")
  const router = useRouter()

  async function handleRegister(){
    if(!email || !password){
      setError("Email and password required")
      return
    }
    setLoading(true)
    setError("")
    try{
      const res = await register(email,password)
      if(res?.access_token){
        localStorage.setItem('token',res.access_token)
        router.push('/chat')
      } else {
        setError(res?.detail || "Registration failed")
      }
    } catch(err:any){
      setError(err?.message || "Network error")
    } finally{
      setLoading(false)
    }
  }

  async function handleLogin(){
    if(!email || !password){
      setError("Email and password required")
      return
    }
    setLoading(true)
    setError("")
    try{
      const res = await login(email,password)
      if(res?.access_token){
        localStorage.setItem('token',res.access_token)
        router.push('/chat')
      } else {
        setError(res?.detail || "Login failed")
      }
    } catch(err:any){
      setError(err?.message || "Network error")
    } finally{
      setLoading(false)
    }
  }

  return (
    <div style={{padding:32}}>
      <h2>Login / Register</h2>
      <div style={{marginBottom:16}}>
        <input 
          placeholder="email" 
          value={email} 
          onChange={e=>setEmail(e.target.value)}
          style={{padding:8, width:200}}
        />
      </div>
      <div style={{marginBottom:16}}>
        <input 
          placeholder="password" 
          type="password" 
          value={password} 
          onChange={e=>setPassword(e.target.value)}
          style={{padding:8, width:200}}
        />
      </div>
      {error && <div style={{color:'red', marginBottom:16}}>{error}</div>}
      <div>
        <button onClick={handleLogin} disabled={loading} style={{padding:8, marginRight:8}}>
          {loading ? "Loading..." : "Login"}
        </button>
        <button onClick={handleRegister} disabled={loading} style={{padding:8}}>
          {loading ? "Loading..." : "Register"}
        </button>
      </div>
    </div>
  )
}

