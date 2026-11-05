import {useState} from 'react'
import {LineChart,Line,XAxis,YAxis,Tooltip,ResponsiveContainer,CartesianGrid} from 'recharts'
import {api} from './api.js'
import {S,C,nice,axf,axp,tip} from './fmt.js'

export function Forecast({id,m1}){
  const [d,setD]=useState(null),[meta,setMeta]=useState(''),[err,setErr]=useState('')
  const run=()=>api(`/api/datasets/${id}/forecast`,{method:'POST',body:{}}).then(r=>{setErr('');setMeta(r.method);setD([...r.history.map(h=>({date:h.date,actual:h.value})),...r.forecast.map(x=>({date:x.date,forecast:x.value,lower:x.lower,upper:x.upper}))])}).catch(e=>setErr(e.message))
  return <div className="card"><div style={{display:'flex',justifyContent:'space-between'}}><h3>{nice(m1)} Forecast <span className="mut">{meta&&`· ${meta}`}</span></h3><button onClick={run}>Run forecast</button></div>
    {err&&<p className="mut">{err}</p>}{d&&<div style={{height:240}}><ResponsiveContainer><LineChart data={d}><CartesianGrid stroke={S.cur.grid}/><XAxis dataKey="date" {...axp()}/><YAxis {...axp()} tickFormatter={axf(d,'upper')}/><Tooltip {...tip()}/>
    <Line dataKey="actual" stroke={C[0]} dot={false}/><Line dataKey="forecast" stroke={C[2]} strokeDasharray="5 4" dot={false}/><Line dataKey="upper" stroke="#475569" strokeDasharray="2 3" dot={false}/><Line dataKey="lower" stroke="#475569" strokeDasharray="2 3" dot={false}/></LineChart></ResponsiveContainer></div>}</div>
}
export function Chat({id,example}){
  const [q,setQ]=useState(''),[log,setLog]=useState([])
  const ask=async()=>{if(!q.trim())return;const m=q;setQ('');const r=await api(`/api/datasets/${id}/chat`,{method:'POST',body:{message:m}}).catch(e=>({answer:e.message}));setLog(l=>[...l,{m,a:r.answer}])}
  return <div className="card chat" id="ask"><h3>✨ Ask AI about your data</h3>{log.map((x,i)=><p key={i}><b>{x.m}</b><br/><span className="mut">{x.a}</span></p>)}
    <div className="crow"><input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==='Enter'&&ask()} placeholder={example||'e.g. total sales by region'}/><button onClick={ask}>Ask</button></div></div>
}
