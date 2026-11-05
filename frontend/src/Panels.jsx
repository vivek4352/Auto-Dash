import {useState,useEffect} from 'react'
import {ComposedChart,Area,Bar,Line,PieChart,Pie,Cell,XAxis,YAxis,Tooltip,Legend,ResponsiveContainer,CartesianGrid} from 'recharts'
import {api} from './api.js'
import {S,C,nice,nf,fv,sh,axf,axp,tip} from './fmt.js'

export function useQ(id,body,name,log){
  const [r,setR]=useState(null),k=JSON.stringify(body)
  useEffect(()=>{if(!body){setR([]);return}let off=false,t0=performance.now()
    api(`/api/dashboards/${id}/query`,{method:'POST',body}).then(d=>{if(off)return;setR(d.rows);log&&log(name,body,performance.now()-t0,d.rows.length)}).catch(()=>!off&&setR([]));return()=>{off=true}},[id,k])
  return r
}
export const mk=m=>`${m.column}_${m.agg}`
export const mlabel=(m,rl)=>m.agg==='rate'?`${nice(m.column)} rate`:m.agg==='count'?rl:(m.agg==='mean'?'Average ':'')+nice(m.column)
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
export const periodLabel=s=>{s=String(s);if(s.length===10){const d=new Date(s);return d.getDate()+' '+MON[d.getMonth()]}if(s.includes('Q'))return s.replace(/^(\d{4})Q(\d)$/,'Q$2 $1');if(/^\d{4}$/.test(s))return s;const d=new Date(s+'-01');return isNaN(d)?s:MON[d.getMonth()]+" '"+String(d.getFullYear()).slice(2)}

function BarList({items,fmt,share}){
  const mx=Math.max(...items.map(x=>x.v),1e-9),tot=items.reduce((a,b)=>a+b.v,0)
  return <div className="bl">{items.map((x,i)=><div className="b" key={i} title={`${x.name}: ${fv(x.v,fmt)}${share&&tot?` (${(x.v/tot*100).toFixed(1)}%)`:''}`}>
    <span className="nm">{x.name}</span><div className="bar"><u style={{width:Math.max(2,x.v/mx*100)+'%',background:C[i%6]}}/></div><span className="v">{share&&fmt!=='percent'?(tot?(x.v/tot*100).toFixed(1)+'%':''):fv(x.v,fmt)}</span></div>)}</div>
}
export function Segments({segs}){
  if(!segs)return <p className="mut">Loading…</p>
  if(!segs.top.length)return <p className="mut">Not enough rows in this selection.</p>
  return <><table><thead><tr><th>Group</th><th className="rt">Rows</th><th className="rt">Rate</th><th className="rt">vs avg</th></tr></thead><tbody>
    {segs.top.map((r,i)=><tr key={i}><td className="tr" title={r.label}>{r.label}</td><td className="rt">{nf(r.n)}</td><td className="rt"><b>{(r.rate*100).toFixed(1)}%</b></td><td className="rt">{r.lift.toFixed(1)}x</td></tr>)}</tbody></table>
    <p className="mut" style={{marginTop:8}}>Overall rate {(segs.overall*100).toFixed(1)}% · groups under 1% of rows are ignored</p></>
}

/** One dashboard panel. The title, the query and the chart all come from the same definition, so they can never disagree. */
export function Panel({p,id,filters,log,fmtOf,rl,insights,segs}){
  const q=p.query,rows=useQ(id,q?{...q,filters}:null,p.title,log),mf=m=>m.agg==='rate'?'percent':fmtOf(m.column)
  let body
  if(p.type==='insights')body=<div className="ins">{insights.slice(0,8).map((x,i)=><div key={i}>{x}</div>)}</div>
  else if(p.type==='segments')body=<Segments segs={segs}/>
  else if(rows===null)body=<p className="mut">Loading…</p>
  else if(!rows.length)body=<p className="mut">No data for the current filters.</p>
  else if(p.type==='trend'||p.type==='yearly'){
    const [a,b]=q.metrics,x=q.group_by[0],data=rows.map(r=>({...r,_l:periodLabel(r[x])}))
    body=<div style={{height:p.type==='yearly'?220:250}}><ResponsiveContainer><ComposedChart data={data}><defs><linearGradient id={'g'+p.id} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C[0]} stopOpacity=".5"/><stop offset="100%" stopColor={C[0]} stopOpacity="0"/></linearGradient></defs>
      <CartesianGrid stroke={S.cur.grid}/><XAxis dataKey="_l" {...axp()} minTickGap={30}/><YAxis yAxisId="l" {...axp()} tickFormatter={axf(data,mk(a),mf(a))}/>{b&&<YAxis yAxisId="r" orientation="right" {...axp()} tickFormatter={axf(data,mk(b),mf(b))}/>}
      <Tooltip {...tip({[mlabel(a,rl)]:mf(a),...(b?{[mlabel(b,rl)]:mf(b)}:{})})}/><Legend/>
      {p.type==='yearly'?<Bar yAxisId="l" dataKey={mk(a)} name={mlabel(a,rl)} fill={C[0]} radius={[4,4,0,0]}/>:<Area yAxisId="l" dataKey={mk(a)} name={mlabel(a,rl)} stroke={C[0]} fill={`url(#g${p.id})`}/>}
      {b&&<Line yAxisId="r" dataKey={mk(b)} name={mlabel(b,rl)} stroke={C[1]} dot={p.type==='yearly'} strokeWidth={2}/>}</ComposedChart></ResponsiveContainer></div>
  }else{
    const m=q.metrics[0],x=q.group_by[0],items=rows.map(r=>({name:String(r[x]),v:r[mk(m)]})),tot=items.reduce((s,i)=>s+i.v,0)
    if(p.type==='donut')body=<div className="donut"><div className="c"><ResponsiveContainer><PieChart><Pie data={items} dataKey="v" nameKey="name" innerRadius={55} outerRadius={82} stroke="none">{items.map((_,i)=><Cell key={i} fill={C[i%6]}/>)}</Pie><Tooltip {...tip({v:mf(m)})}/></PieChart></ResponsiveContainer><div className="mid"><b>{sh(tot,mf(m))}</b>{p.total_label||'Total'}</div></div>
      <div className="leg">{items.map((it,i)=><div key={i}><span className="dot" style={{background:C[i%6]}}/><span>{it.name}</span><span>{tot?(it.v/tot*100).toFixed(1)+'%':''}</span></div>)}</div></div>
    else if(p.type==='top')body=<table><thead><tr><th>#</th><th>{nice(x)}</th>{q.metrics.map(mm=><th key={mk(mm)} className="rt">{mlabel(mm,rl)}</th>)}</tr></thead><tbody>
      {rows.map((r,i)=><tr key={i}><td>{i+1}</td><td className="tr" title={String(r[x])}>{String(r[x])}</td>{q.metrics.map(mm=><td key={mk(mm)} className="rt">{sh(r[mk(mm)],mf(mm))}</td>)}</tr>)}</tbody></table>
    else body=<BarList items={items} fmt={mf(m)} share={p.type==='list'&&!!p.share}/>
  }
  return <div className="card"><h3>{p.title}</h3>{body}</div>
}
