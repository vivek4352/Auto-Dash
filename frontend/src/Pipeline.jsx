import {useState} from 'react'
const nice2=s=>({time:'Date column',target:'Outcome column',drivers:'Strongest drivers',ranking:'Top-N table',flags:'Yes/No columns',ignored:'Kept out of headlines'}[s]||s),nice=s=>(s||'').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())
const FN={sum:'SUM',mean:'AVG',count:'COUNT',min:'MIN',max:'MAX',median:'MEDIAN'}
export const toSQL=(b,table,tcol)=>{
  const q=v=>`'${String(v).replace(/'/g,"''")}'`,lit=v=>/^-?\d+(\.\d+)?$/.test(String(v))?v:q(v)
  const ex=m=>m.agg==='nunique'?`COUNT(DISTINCT ${m.column})`:m.agg==='count'?'COUNT(*)':m.agg==='rate'?`AVG(CASE WHEN ${m.column} = ${lit(m.positive)} THEN 1.0 ELSE 0.0 END)`:`${FN[m.agg]}(${m.column})`
  const tf={D:'day',M:'month',Q:'quarter',Y:'year'}[b.time_grain||'M'],G=b.group_by||[]
  const sel=[...G.map(c=>c===tcol?`DATE_TRUNC('${tf}', ${c}) AS ${c}`:c),...b.metrics.map(m=>`${ex(m)} AS ${m.column}_${m.agg}`)]
  const w=(b.filters||[]).flatMap(f=>[...(f.values?.length?[`${f.column} IN (${f.values.map(q).join(', ')})`]:[]),...(f.min?[`${f.column} >= '${f.min}'`]:[]),...(f.max?[`${f.column} <= '${f.max}'`]:[])])
  return `SELECT ${sel.join(',\n       ')}\nFROM ${table}`+(w.length?`\nWHERE ${w.join('\n  AND ')}`:'')+(G.length?`\nGROUP BY ${G.map(c=>c===tcol?`DATE_TRUNC('${tf}', ${c})`:c).join(', ')}\nORDER BY ${G[0]===tcol?G[0]+' ASC':b.metrics[0].column+'_'+b.metrics[0].agg+' DESC'}`+(b.limit?`\nLIMIT ${b.limit}`:''):'')+';'
}
const FN2=0
const Step=({n,t,children})=><div className="step"><b>{n}</b><div><h4>{t}</h4>{children}</div></div>

export default function Pipeline({d,qlog,onClose}){
  const [tab,setTab]=useState('pipe'),[copied,setCopied]=useState('')
  const {spec,profile,pipeline:P}=d,L=spec.layout||{},R=L.reasons||{}
  const table=d.filename.replace(/\.[^.]+$/,'').toLowerCase().replace(/[^a-z0-9]+/g,'_'),tcol=L.time
  const role=r=>profile.filter(p=>p.role===r)
  const copy=(k,s)=>{navigator.clipboard?.writeText(s);setCopied(k);setTimeout(()=>setCopied(''),1200)}
  const Chips=({r,c})=>role(r).map(p=><span key={p.name} className={'chip '+c}>{p.name}</span>)
  const extraR=Object.entries(R).filter(([k])=>['time','target','drivers','ranking','flags','ignored'].includes(k)).map(([k,v])=>[nice2(k),'—',v])
  const rows=[...spec.panels.filter(p=>p.why).map(p=>[p.title,(p.query?.group_by||[]).join(', ')||(p.type==='segments'?L.target?.column:'—'),p.why]),...spec.kpis.map(k=>['KPI: '+k.label,`${k.agg}(${k.column})`,k.why]),...extraR].filter(r=>r[2])
  const Q=Object.entries(qlog)
  return <><div className="scrim" onClick={onClose}/><aside className="drawer">
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'start'}}><div><h2 style={{margin:0}}>🔍 How this dashboard was built</h2><div className="mut">Everything AutoDash did with <b>{d.filename}</b>, in order.</div></div><button className="ic" onClick={onClose}>✕</button></div>
    <div className="tabs">{[['pipe','Pipeline'],['dec','Decisions'],['q',`Queries (${Q.length})`]].map(([k,l])=><button key={k} className={tab===k?'on':''} onClick={()=>setTab(k)}>{l}</button>)}</div>

    {tab==='pipe'&&<div>
      <Step n="1" t="Read the file"><p>Format <b>.{P?.format}</b> · {P?.raw_rows?.toLocaleString()} rows × {P?.raw_cols} columns{P?.truncated?' (truncated to the row limit)':''}. Encoding and separator were detected automatically.</p></Step>
      <Step n="2" t="Clean (your original file is untouched)"><p>{(P?.cleaning||[]).map((c,i)=><span key={i}>• {c}<br/></span>)}{P?.duplicates?`• ${P.duplicates} fully duplicated row(s) detected (kept, flagged in insights)`:''}</p></Step>
      <Step n="3" t="Profile: every column gets a role"><p>Measures are added or averaged, dimensions are grouped by, time columns become axes, identifiers are counted.</p>
        <div><Chips r="measure" c="m"/><Chips r="time" c="t"/><Chips r="dimension" c="d"/><Chips r="identifier" c="i"/></div>
        <p><span className="chip m">measure</span><span className="chip t">time</span><span className="chip d">dimension</span><span className="chip i">identifier</span></p></Step>
      <Step n="4" t="Detect the domain"><p>Looks like <b>{nice(P?.domain?.domain)}</b> data ({Math.round((P?.domain?.confidence||0)*100)}% confidence from column-name keywords){P?.domain?.alternatives?.length?`; alternatives: ${P.domain.alternatives.join(', ')}`:''}. This sets the dashboard title and insight focus.</p></Step>
      <Step n="5" t="Choose the panels"><p>A rule engine decided which panels the data can support (for example, no date column means no trend, growth or forecast). Every title is generated from its own query. See the <a style={{color:'var(--ac)',cursor:'pointer'}} onClick={()=>setTab('dec')}>Decisions tab</a> for the reason behind each choice.</p></Step>
      <Step n="6" t="Run queries"><p>{Q.length} aggregation queries ran against your data to fill the panels, each re-running when you change a filter. See the <a style={{color:'var(--ac)',cursor:'pointer'}} onClick={()=>setTab('q')}>Queries tab</a> for the SQL.</p></Step>
      <Step n="7" t="Insights, forecast and chat"><p>Insights are computed in pandas from real numbers (an AI may only rephrase them, never invent figures). The forecast fits a trend plus monthly seasonality. Chat questions are converted to the same kind of whitelisted query.</p></Step></div>}

    {tab==='dec'&&<div className="card" style={{padding:0,overflow:'auto'}}><table><thead><tr><th style={{padding:10}}>Panel</th><th>Column</th><th>Why</th></tr></thead><tbody>
      {rows.map(([a,b,c],i)=><tr key={i}><td style={{padding:10,fontWeight:600}}>{a}</td><td><code>{b}</code></td><td className="mut" style={{lineHeight:1.5}}>{c}</td></tr>)}</tbody></table></div>}

    {tab==='q'&&<div><p className="mut">These are the real queries behind the charts right now (they update when you change filters). The SQL is the equivalent of the aggregation AutoDash runs in pandas.</p>
      {Q.map(([name,{b,ms,rows}])=>{const sql=toSQL(b,table,tcol);return <div key={name} className="card" style={{marginBottom:12}}>
        <div style={{display:'flex',justifyContent:'space-between',gap:8}}><b>{name}</b><span className="mut">{rows} row{rows===1?'':'s'} · {ms.toFixed(0)} ms</span></div>
        <pre>{sql}</pre><div style={{display:'flex',gap:8}}><button className="ghost" onClick={()=>copy(name,sql)}>{copied===name?'✓ Copied':'Copy SQL'}</button></div>
        <details><summary>Show the API request (JSON)</summary><pre>POST /api/dashboards/{'{id}'}/query{'\n'+JSON.stringify(b,null,2)}</pre></details></div>})}
      {!Q.length&&<p className="mut">No queries yet.</p>}</div>}
  </aside></>
}
