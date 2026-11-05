import {useState,useEffect,useCallback} from 'react'
import Landing from './Landing.jsx'
import Pipeline from './Pipeline.jsx'
import Download from './Download.jsx'
import {Panel,useQ,mk,periodLabel} from './Panels.jsx'
import {Forecast,Chat} from './Extras.jsx'
import {api,getTok,setTok} from './api.js'
import {S,TH,nice,nf,fv} from './fmt.js'

function View({id,d,user,onReset,onHome,onSignOut,theme,toggle}){
  const {spec,profile}=d,L=spec.layout,panels=spec.panels,t=L.time,grain=L.grain,rl=L.records.label
  const [ind,setInd]=useState(navigator.language.endsWith('IN')); S.ind=ind
  const [open,setOpen]=useState(false),[busy,setBusy]=useState(''),[dlOpen,setDlOpen]=useState(false),[qlog,setQlog]=useState({}),log=useCallback((n,b,ms,rows)=>setQlog(q=>({...q,[n]:{b,ms,rows}})),[])
  const [sel,setSel]=useState({}),[rg,setRg]=useState({min:'',max:''}),[ins,setIns]=useState([]),[segs,setSegs]=useState(null)
  const filters=[...Object.entries(sel).filter(([,v])=>v).map(([column,v])=>({column,values:[v]})),...(t&&(rg.min||rg.max)?[{column:t,...rg}]:[])]
  const fk=JSON.stringify(filters),fmtOf=c=>profile.find(p=>p.name===c)?.fmt
  const metric=k=>({column:k.column,agg:k.agg,...(k.positive!=null?{positive:k.positive}:{})})
  const trendP=panels.find(p=>p.type==='trend'),m1m=trendP?.query.metrics[0],baseM=spec.kpis.map(metric)
  const extra=[{column:L.records.column,agg:'count'},...(L.profit?[{column:L.profit,agg:'sum'}]:[]),...(m1m?[m1m]:[])].filter((m,i,a)=>!baseM.some(b=>mk(b)===mk(m))&&a.findIndex(x=>mk(x)===mk(m))===i)
  const tm=[...baseM,...extra]
  const tot=useQ(id,{metrics:tm,filters},'KPI cards (totals)',log)
  const series=useQ(id,t?{metrics:tm,group_by:[t],time_grain:grain,limit:400,filters}:null,'Change vs previous period',log)
  useEffect(()=>{api(`/api/datasets/${id}/insights`).then(r=>setIns(r.insights)).catch(()=>{})},[id])
  useEffect(()=>{if(L.target)api(`/api/dashboards/${id}/segments`,{method:'POST',body:{filters}}).then(setSegs).catch(()=>setSegs({top:[],bottom:[],overall:0}))},[id,fk])
  const T=tot?.[0]||{},Sr=series||[],n=Sr.length
  const K=grain==='M'?(n>=24?12:n>=6?3:1):grain==='Q'?(n>=8?4:1):Math.max(1,Math.min(30,Math.floor(n/2))),unitName=grain==='M'?'month':grain==='Q'?'quarter':'day'
  const delta=m=>{if(!t||n<2*K)return null;const key=mk(m),g=(a,b)=>Sr.slice(a,b).map(x=>x[key]||0),red=a=>['sum','nunique','count'].includes(m.agg)?a.reduce((s,v)=>s+v,0):a.reduce((s,v)=>s+v,0)/a.length,a=red(g(n-2*K,n-K)),b=red(g(n-K,n));return a?(b-a)/Math.abs(a)*100:null}
  const dtxt=`vs previous ${K>1?K+' '+unitName+'s':unitName}`
  const Dl=({v})=>v==null?null:<span className={v>=0?'up':'dn'}>{v>=0?'▲':'▼'} {Math.abs(v).toFixed(1)}% {dtxt}</span>
  const rateK=spec.kpis.find(k=>k.agg==='rate'),sumK=spec.kpis.find(k=>k.agg==='sum'),best=m1m&&n?Sr.reduce((a,b)=>b[mk(m1m)]>a[mk(m1m)]?b:a):null
  const stripItems=spec.strip.map(k=>{
    if(k==='records')return [rl,nf(T[`${L.records.column}_count`]),'']
    if(k==='rate'&&rateK)return [`Overall ${nice(rateK.column).toLowerCase()} rate`,fv(T[mk(rateK)],'percent'),`${nf(T[`${L.records.column}_count`])} ${rl.toLowerCase()}`]
    if(k==='risk_high'&&segs?.top?.[0])return ['Highest-risk group',(segs.top[0].rate*100).toFixed(1)+'%',segs.top[0].label]
    if(k==='risk_low'&&segs?.bottom?.[0])return ['Lowest-risk group',(segs.bottom[0].rate*100).toFixed(1)+'%',segs.bottom[0].label]
    if(k==='total'&&sumK)return [`Total ${nice(sumK.column)}`,fv(T[mk(sumK)],fmtOf(sumK.column)),'']
    if(k==='growth'&&m1m){const g=delta(m1m);return [`Growth ${dtxt}`,g==null?'–':(g>=0?'+':'')+g.toFixed(1)+'%','']}
    if(k==='margin'&&L.profit&&T[`${L.profit}_sum`]!=null&&sumK&&T[mk(sumK)])return [`${nice(L.profit)} margin`,(T[`${L.profit}_sum`]/T[mk(sumK)]*100).toFixed(1)+'%','']
    if(k==='best'&&best)return ['Best performing period',periodLabel(best[t]),'']
    return null}).filter(Boolean)
  const download=async kind=>{setBusy(kind);try{
    const r=await api(`/api/datasets/${id}/export/${kind}`,{method:'POST',body:{theme,ind,sel,min:rg.min,max:rg.max},raw:true})
    if(!r.ok)throw new Error((await r.json().catch(()=>({}))).detail||'Download failed')
    const b=await r.blob(),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=(d.filename.replace(/\.[^.]+$/,'')||'dashboard')+(kind==='html'?'-dashboard.html':'-powerbi-kit.zip');document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),2000);setDlOpen(false)
  }catch(e){alert(e.message)}setBusy('')}
  const dl=profile.find(p=>p.name===t)?.stats||{},filt=spec.filters.filter(x=>x.type==='multiselect')
  const r1=panels.filter(p=>p.slot!=='row'),r2=panels.filter(p=>p.slot==='row')
  const render=p=><Panel key={p.id} p={p} id={id} filters={filters} log={log} fmtOf={fmtOf} rl={rl} insights={ins} segs={segs}/>
  const mainEx=L.target?`${nice(L.target.column).toLowerCase()} rate by contract`:'total by '+(L.composition||'category')
  return <div className="app">
    <aside className="side"><div className="logo" onClick={onHome} title="Back to home" style={{cursor:'pointer'}}>📊 AutoDash<small>AI Insights for Growth</small></div>
      <div className="nav" onClick={onHome}>🏠 Home & my dashboards</div><div className="nav on">▦ Dashboard</div><div className="nav" onClick={onReset}>＋ New dashboard</div>
      <div className="nav" onClick={()=>document.getElementById('ask')?.scrollIntoView({behavior:'smooth'})}>💬 Ask AI</div><div className="nav" onClick={()=>setOpen(true)}>🔍 How it was built</div>
      <div className="nav dl" onClick={()=>setDlOpen(true)}>⬇ Download dashboard</div><div className="nav" onClick={toggle}>{theme==='dark'?'☀️ Light theme':'🌙 Dark theme'}</div>
      <div className="promo userbox">{user.picture?<img src={user.picture} alt="" referrerPolicy="no-referrer"/>:<span className="av">{(user.name||'?')[0]}</span>}<div style={{minWidth:0}}><b>{user.name}</b><span className="mut" style={{display:'block',overflow:'hidden',textOverflow:'ellipsis'}}>{user.email}</span><a className="so" onClick={onSignOut}>Sign out</a></div></div></aside>
    <main className="main">
      <div className="head"><div><h1>{spec.title}</h1><div className="mut">{d.filename} · {d.rows.toLocaleString(ind?'en-IN':'en-US')} rows{dl.min?` · ${dl.min} to ${dl.max}`:''}</div></div>
        <div className="ctl">{t&&<><input type="date" min={dl.min} max={dl.max} value={rg.min} onChange={e=>setRg({...rg,min:e.target.value})}/><span className="mut">to</span><input type="date" min={dl.min} max={dl.max} value={rg.max} onChange={e=>setRg({...rg,max:e.target.value})}/></>}
          {filt.map(x=><select key={x.column} value={sel[x.column]||''} onChange={e=>setSel({...sel,[x.column]:e.target.value})}><option value="">All {nice(x.column)}</option>{(profile.find(p=>p.name===x.column)?.top_values||[]).map(v=><option key={v}>{v}</option>)}</select>)}
          <button className="ghost" onClick={()=>setInd(!ind)} title="Number units">{ind?'L / Cr':'K / M'}</button><button className="ic" onClick={toggle} title="Toggle theme">{theme==='dark'?'☀️':'🌙'}</button>
          <button className="ghost" onClick={()=>setOpen(true)}>🔍 How it was built</button><button onClick={()=>setDlOpen(true)}>⬇ Download dashboard</button></div></div>
      <div className="kpis">{spec.kpis.map(k=><div className="kpi" key={k.id}><div className="ico">{k.icon||'📊'}</div><div><span className="mut" style={{color:'#cbd5f5'}}>{k.label}</span><b>{fv(T[mk(k)],k.agg==='rate'?'percent':fmtOf(k.column))}</b>{t&&k.agg!=='rate'&&<Dl v={delta(metric(k))}/>}</div></div>)}</div>
      <div className="row r1">{r1.map(render)}</div>{r2.length>0&&<div className="row r2">{r2.map(render)}</div>}
      {stripItems.length>0&&<div className="strip">{stripItems.map((x,i)=><div className="card" key={i}><span className="mut">{x[0]}</span><b>{x[1]}</b>{x[2]&&<small className="mut">{x[2]}</small>}</div>)}</div>}
      <div className="row r3">{spec.forecast?.enabled&&<Forecast id={id} m1={L.m1}/>}<Chat id={id} example={`e.g. ${mainEx}`}/></div>
    </main>{dlOpen&&<Download busy={busy} onPick={download} onClose={()=>setDlOpen(false)}/>}{open&&<Pipeline d={d} qlog={qlog} onClose={()=>setOpen(false)}/>}</div>
}

function Dashboard({id,user,onReset,onHome,onSignOut,theme,toggle}){
  const [d,setD]=useState(null),[err,setErr]=useState('')
  useEffect(()=>{setD(null);api(`/api/dashboards/${id}`).then(r=>r.spec?.panels?setD(r):setErr('This dashboard was created by an older version. Please upload the file again.')).catch(e=>setErr(e.message))},[id])
  if(err)return <div className="drop"><p>{err}</p><button onClick={onHome}>Back to my dashboards</button></div>
  return d?<View id={id} d={d} user={user} onReset={onReset} onHome={onHome} onSignOut={onSignOut} theme={theme} toggle={toggle}/>:<div className="drop">Loading…</div>
}

export default function App(){
  const [theme,setTheme]=useState(localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'))
  S.cur=TH[theme]
  useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('theme',theme)},[theme])
  const toggle=()=>setTheme(theme==='dark'?'light':'dark')
  const [cfg,setCfg]=useState({}),[user,setUser]=useState(null),[ready,setReady]=useState(false),[datasets,setDatasets]=useState([])
  const [id,setId]=useState(null),[view,setView]=useState('home'),[busy,setBusy]=useState(false),[err,setErr]=useState('')
 useEffect(() => {
  // Load Google authentication configuration
  api('/api/auth/config')
    .then(config => {
      console.log('Auth configuration loaded:', config);

      if (!config.google_client_id) {
        console.error('Google Client ID missing from backend config');
      }

      setCfg(config);
    })
    .catch(error => {
      console.error('Failed to load auth configuration:', error);
      setErr('Unable to connect to the authentication server.');
    });

  // Restore existing session
  (getTok()
    ? api('/api/me')
        .then(setUser)
        .catch(() => setTok(null))
    : Promise.resolve()
  ).finally(() => setReady(true));

  const ex = () => {
    setUser(null);
    setId(null);
    setView('home');
  };

  window.addEventListener('auth-expired', ex);

  return () => window.removeEventListener('auth-expired', ex);
}, []);
  const refresh=useCallback(()=>api('/api/datasets').then(r=>setDatasets(r.datasets)).catch(()=>{}),[])
  useEffect(()=>{if(user)refresh();else setDatasets([])},[user])
  const session=async(path,body)=>{setErr('');try{const r=await api(path,{method:'POST',body});setTok(r.token);setUser(r.user)}catch(e){setErr(e.message)}}
  const top=()=>window.scrollTo(0,0),open=i=>{setId(i);setView('dash');top()}
  const signOut=()=>{setTok(null);setUser(null);setId(null);setView('home');top()}
  const up=async fl=>{if(!fl)return;setBusy(true);setErr('');const form=new FormData();form.append('file',fl)
    try{const r=await api('/api/datasets/upload',{method:'POST',form});await refresh();open(r.id)}catch(e){setErr(e.message)}setBusy(false)}
  const del=async i=>{if(!confirm('Delete this dashboard and its data permanently?'))return;await api(`/api/datasets/${i}`,{method:'DELETE'}).catch(()=>{});if(id===i)setId(null);refresh()}
  if(!ready)return <div className="drop">Loading…</div>
  if(user&&id&&view==='dash')return <Dashboard id={id} user={user} theme={theme} toggle={toggle} onSignOut={signOut} onHome={()=>{setView('home');refresh();top()}} onReset={()=>{setId(null);setView('home');top()}}/>
  return <Landing user={user} cfg={cfg} datasets={datasets} onCredential={c=>session('/api/auth/google',{credential:c})} onDev={e=>session('/api/auth/dev',{email:e})} onSignOut={signOut} onOpen={open} onDelete={del} onFile={up} busy={busy} err={err} theme={theme} toggle={toggle} resume={!!id} onResume={()=>{setView('dash');top()}}/>
}
