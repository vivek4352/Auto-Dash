export const TH={dark:{ax:'#8a97b8',grid:'#1b2748',bg:'#0a1228',bd:'#1b2748',fg:'#eef2ff'},light:{ax:'#5b6785',grid:'#e6eaf3',bg:'#ffffff',bd:'#e1e6f1',fg:'#121933'}}
export const S={ind:true,cur:TH.dark}   // shared display settings, set by the app on every render
export const C=['#2f6bff','#22c55e','#f59e0b','#ec4899','#8b5cf6','#94a3b8']
const ACR=new Set(['tv','id','ip','crm','sku','ui','roi','kpi','usd','api','url','vip','gps','sms','upi'])
export const nice=s=>String(s||'').split('_').filter(Boolean).map(w=>ACR.has(w.toLowerCase())?w.toUpperCase():w.charAt(0).toUpperCase()+w.slice(1)).join(' ')
export const nf=v=>typeof v==='number'&&isFinite(v)?v.toLocaleString(S.ind?'en-IN':'en-US',{maximumFractionDigits:2}):'–'
const unit=m=>S.ind?(m>=1e7?[1e7,' Cr']:m>=1e5?[1e5,' L']:m>=1e3?[1e3,'K']:[1,'']):(m>=1e9?[1e9,'B']:m>=1e6?[1e6,'M']:m>=1e3?[1e3,'K']:[1,''])
export const fv=(v,fmt)=>typeof v!=='number'||!isFinite(v)?'–':fmt==='percent'?(v*100).toFixed(1)+'%':nf(v)
export const sh=(v,fmt)=>{if(typeof v!=='number'||!isFinite(v))return '–';if(fmt==='percent')return (v*100).toFixed(1)+'%';const [d,s]=unit(Math.abs(v));return (v/d).toFixed(d===1?(Number.isInteger(v)?0:2):1)+s}
export const axf=(rows,key,fmt)=>{if(fmt==='percent')return v=>(v*100).toFixed(0)+'%';const mx=Math.max(0,...(rows||[]).map(r=>Math.abs(r[key]||0)));const [d,s]=unit(mx);return v=>parseFloat((v/d).toFixed(1))+s}
export const axp=()=>({stroke:S.cur.ax,fontSize:11})
export const tip=fm=>({contentStyle:{background:S.cur.bg,border:'1px solid '+S.cur.bd,borderRadius:8,color:S.cur.fg},itemStyle:{color:S.cur.fg},labelStyle:{color:S.cur.fg},formatter:(v,n)=>fv(v,fm?.[n])})
