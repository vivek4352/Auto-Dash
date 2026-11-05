const OPTS=[
 ['html','🌐','Interactive web page','.html',['One file that opens in any browser, fully offline','Hover tooltips, live filters and risk-group analysis','Dark / light toggle and print to PDF'],'Best for: sharing with anyone, no software needed'],
 ['powerbi','🟨','Power BI kit','.zip',['Your cleaned data (CSV) ready to load','Power Query (M) scripts and DAX measures, including outcome rates','Theme file + step-by-step guide that matches every panel'],'Best for: building a real Power BI report in ~5 minutes']]
export default function Download({busy,onPick,onClose}){
  return <><div className="scrim" onClick={onClose}/><div className="modal" style={{width:'min(760px,94vw)'}}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'start'}}><div><h2 style={{margin:0}}>⬇ Download your dashboard</h2><div className="mut">Your current filters, theme and units are included. Choose a format:</div></div><button className="ic" onClick={onClose}>✕</button></div>
    <div className="opts">{OPTS.map(([k,i,t,ext,pts,best])=><div key={k} className="opt">
      <div className="oh"><span style={{fontSize:30}}>{i}</span><div><b>{t}</b> <span className="mut">{ext}</span></div></div>
      <ul>{pts.map(p=><li key={p}>{p}</li>)}</ul><div className="mut" style={{margin:'8px 0'}}>{best}</div>
      <button disabled={!!busy} onClick={()=>onPick(k)}>{busy===k?'⏳ Preparing…':'Download '+ext}</button></div>)}</div></div></>
}
