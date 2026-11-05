import {useState,useEffect,useRef} from 'react'
const go=id=>document.getElementById(id)?.scrollIntoView({behavior:'smooth',block:'start'})
function useReveal(){useEffect(()=>{const io=new IntersectionObserver(es=>es.forEach(e=>e.isIntersecting&&e.target.classList.add('in')),{threshold:.12});document.querySelectorAll('.reveal').forEach(el=>io.observe(el));return()=>io.disconnect()},[])}
const STEPS=[
 ['📤','1 · Upload','Drop a .csv, .tsv or .xlsx file (up to 25 MB / 200,000 rows). The text encoding and the separator (comma, semicolon, tab) are detected automatically, so you never have to configure anything.'],
 ['🧹','2 · Read & clean','Currency text like ₹1,20,000 becomes a real number. Text dates become real dates (day-first or month-first is detected). Spelling variants such as north / North / NORTH are merged. Your original file is never modified.'],
 ['🔎','3 · Profile every column','Each column is classified as a Measure (numbers you add up), a Dimension (labels you group by), a Time column (dates) or an Identifier (IDs you count). We also record min, max, averages and missing values.'],
 ['🧠','4 · Decide the dashboard','A rule engine reads the column names, types and cardinality, then chooses which column drives each panel. Yes/No columns become rates, an outcome column such as churn gets its own risk analysis, and a chart is only drawn when the data can support it (no date column means no trend).'],
 ['⚙️','5 · Run safe queries','Each chart is a small aggregation, the same idea as SQL GROUP BY. Only whitelisted operations on columns that exist can run, so nothing unexpected is ever executed on your data.'],
 ['🚀','6 · Explore & ask','Filters re-run the queries live. Ask questions in plain English, run a seasonal forecast, download an interactive HTML dashboard or a Power BI kit, and open "How it was built" inside any dashboard to see every query that produced what you see.']]
const COLS=[
 ['order_date','Time','t','Trend charts · date filter · forecast','This is a date, so it becomes the X-axis of trend charts, powers the date-range filter and unlocks forecasting. If a file has several dates (order date and ship date), the order date wins because it describes when the business happened.'],
 ['sales','Measure','m','Summed → KPI card · main area chart','Money-like numbers are added up. Total sales is a KPI card, and sales over time is the main chart. The biggest business measure is always placed first.'],
 ['discount','Measure (rate)','m','Averaged · shown as %','Adding up discounts (0.2 + 0.1 + 0.4) is meaningless, so rates, prices, ratings and scores are averaged, and a value between 0 and 1 is displayed as a percentage.'],
 ['region','Dimension · 4 values','d','Share list · filter dropdown','A label with only a few distinct values is perfect for a share-of-total breakdown and a dropdown filter.'],
 ['product_name','Dimension · 1,850 values','d','Top 5 ranking table','Hundreds of distinct items would make an unreadable pie. So we show the Top 5 as a ranked table with bars instead.'],
 ['churn','Outcome (yes/no)','i','Rate by group · highest-risk table','A yes/no column whose name says it is an outcome becomes the star of the dashboard: the share of rows that are positive, which groups have the highest and lowest rate, and which columns separate them the most.'],
 ['order_id','Identifier','i','Counted, never summed','IDs are labels, not quantities. Counting the distinct values gives "Total Orders", and the column is never charted as a number.']]
const RULES=[
 ['📅','Date column found','Trend line or area + forecast','Time questions ("is it growing?") are answered best left to right.'],
 ['🍩','Few categories (≤ 10)','Donut share chart','A handful of slices shows share of total at a glance.'],
 ['🏆','Hundreds of items','Top 5 ranking table','Too many slices or bars become noise; ranking shows what matters.'],
 ['↔️','Two numbers, different scales','Dual Y-axis','Quantity beside Sales would be a flat line, so each measure gets its own axis.'],
 ['％','Rate / discount / margin','Average, shown as %','Summing percentages is wrong; averaging is right.'],
 ['🆔','ID-like column','Distinct count (Orders, Customers)','IDs identify rows; counting them tells you how many.'],
 ['📈','Several months of data','Growth = last 12 vs previous 12 months','Comparing December with November mostly measures seasonality, not growth.'],
 ['🎯','Yes/No outcome column (churn, attrition, fraud)','Rate + highest-risk groups','Averaging a 0/1 flag is meaningless; the share of rows that are positive, and where it is highest, is what matters.'],['🚫','No date column','No trend, growth or forecast','A chart is only drawn when the data can support it, so nothing is ever shown empty or faked.'],
 ['🗂️','Operational fields (ship mode, status)','Filters only, not headline charts','They rarely explain business results, so they are kept out of the main story.']]
const FLOW=[['📄','File','csv / xlsx'],['📖','Reader','encoding, delimiter'],['🧹','Cleaner','numbers, dates, case'],['🔎','Profiler','roles & stats'],['🧠','Layout engine','picks columns'],['⚙️','Query engine','safe aggregations'],['📊','Charts','recharts']]
const FEAT=[['🎯','Smart KPI cards','Totals, averages and distinct counts, each with a change vs the previous period.'],['💡','Automatic insights','Growth, seasonality, margins, loss-makers and the discount effect, all computed with real numbers.'],['💬','Ask in plain English','"top 5 products by profit" is translated into a safe query.'],['🔮','Seasonal forecast','Linear trend plus month-of-year seasonality, with a confidence band.'],['🎛️','Live filters','Date range and category filters re-run every chart instantly.'],['⬇','HTML & Power BI export','An interactive offline HTML dashboard, and a Power BI kit with your data, M scripts and DAX measures.'],['🔍','Fully explainable','See the pipeline, every decision, and the exact SQL behind each chart.']]
const FAQ=[['Why do I need to sign in?','So your dashboards are saved to your own account and only you can open them. Sign in with Google: we receive your name and email, never your password. Your files are stored on the server under your account until you delete them.'],
 ['Is my data sent to an AI?','By default no: everything is computed on the server with pandas. If you configure a Gemini key, only column names, types and statistics are sent, never your rows, and the AI can only rephrase insights or understand chat questions; it never chooses or invents numbers.'],
 ['What file types and sizes work?','CSV, TSV, XLSX and XLS up to 25 MB and 200,000 rows by default (both limits are configurable on the server).'],
 ['Why did it choose these charts?','Open "How it was built" in any dashboard. The Decisions tab states, in plain words, why each column was picked for each panel.'],
 ['Can I change what it picked?','Not yet: column role overrides are on the roadmap. Meanwhile you can filter by any category and ask custom questions in the chat.'],
 ['How reliable is the forecast?','It is a simple, transparent model (trend + monthly seasonality) with a 95% band. It needs at least 4 months of data, and 24+ months to model seasonality. Use it as a guide, not a guarantee.']]

function GoogleBtn({clientId,onCredential,theme}){
  const ref=useRef(null)
  useEffect(()=>{const init=()=>{if(!ref.current)return;window.google.accounts.id.initialize({client_id:clientId,callback:r=>onCredential(r.credential)});window.google.accounts.id.renderButton(ref.current,{theme:theme==='dark'?'filled_black':'outline',size:'large',shape:'pill',text:'signin_with',width:280})}
    if(window.google?.accounts?.id)init();else{const s=document.createElement('script');s.src='https://accounts.google.com/gsi/client';s.async=true;s.onload=init;document.head.appendChild(s)}},[clientId,theme])
  return <div ref={ref} style={{minHeight:44}}/>
}
function SignIn({cfg,onCredential,onDev,theme,err}){
  const [email,setEmail]=useState('demo@example.com')
  return <div className="signin"><b style={{fontSize:18}}>🔐 Sign in to upload your data</b>
    <p className="mut">Your dashboards are saved to your Google account, so you can come back to them any time. Only you can see them.</p>
    {cfg.google_client_id&&<GoogleBtn clientId={cfg.google_client_id} onCredential={onCredential} theme={theme}/>}
    {cfg.dev_mode&&<div className="crow"><input value={email} onChange={e=>setEmail(e.target.value)}/><button onClick={()=>onDev(email)}>Continue as demo user</button></div>}
    {!cfg.google_client_id&&!cfg.dev_mode&&<p className="err">Google sign-in is not configured yet. Add your GOOGLE_CLIENT_ID to backend/.env and restart the backend (see README, "Google login").</p>}
    {cfg.dev_mode&&<p className="mut" style={{fontSize:12}}>Demo sign-in is for local testing only (AUTH_DEV_MODE=1).</p>}
    {err&&<div className="err">⚠ {err}</div>}</div>
}
export default function Landing({user,cfg,datasets,onCredential,onDev,onSignOut,onOpen,onDelete,onFile,busy,err,theme,toggle,resume,onResume}){
  useReveal()
  const [drag,setDrag]=useState(false),[sel,setSel]=useState(0),S=COLS[sel]
  return <div className="lp">
    <header className="lnav"><div className="wrap"><b style={{fontSize:18,cursor:'pointer'}} onClick={()=>window.scrollTo({top:0,behavior:'smooth'})}>📊 AutoDash</b><span className="sp"/>
      {[['how','How it works'],['decide','How it decides'],['features','Features'],['faq','FAQ']].map(([i,l])=><a key={i} className="hide" onClick={()=>go(i)}>{l}</a>)}
      {user&&<a className="hide" onClick={()=>go('mine')}>My dashboards</a>}
      {resume&&<button onClick={onResume}>↩ Your dashboard</button>}<button className="ic" onClick={toggle} title="Toggle theme">{theme==='dark'?'☀️':'🌙'}</button>
      {user&&<span className="uchip">{user.picture?<img src={user.picture} alt="" referrerPolicy="no-referrer"/>:<span className="av">{(user.name||'?')[0]}</span>}<span className="hide">{user.name}</span><a onClick={onSignOut}>Sign out</a></span>}</div></header>
    <div className="wrap">
      <section className="hero"><div>
        <span className="badge">✨ No setup · Works with any CSV or Excel file</span>
        <h1>Turn any spreadsheet into a <span className="grad">smart dashboard</span> in seconds</h1>
        <p className="lead">Drop your file. AutoDash understands what every column means, builds only the charts your data can support, and then shows you exactly <b>how and why</b> it decided.</p>
        {!user?<SignIn cfg={cfg} onCredential={onCredential} onDev={onDev} theme={theme} err={err}/>:<>
          <label className={'dz'+(drag?' on':'')} onDragOver={e=>{e.preventDefault();setDrag(true)}} onDragLeave={()=>setDrag(false)} onDrop={e=>{e.preventDefault();setDrag(false);onFile(e.dataTransfer.files[0])}}>
            <input type="file" hidden accept=".csv,.tsv,.xlsx,.xls" onChange={e=>onFile(e.target.files[0])}/><b>{busy?'⏳ Analyzing your data…':'📂 Drop your file here'}</b><span>{busy?'Reading, cleaning and profiling columns':'or click to browse · CSV, TSV, XLSX · saved to your account'}</span></label>
          {err&&<div className="err">⚠ {err}</div>}</>}
        <div style={{marginTop:16,display:'flex',gap:10,flexWrap:'wrap'}}>{resume&&<button onClick={onResume}>↩ Resume your last dashboard</button>}<button className="ghost" onClick={()=>go('how')}>See how it works ↓</button></div></div>
      <div className="mock"><div className="mk-k"><i/><i/><i/></div><div className="mk-bars">{[40,65,50,80,60,95,75,110].map((h,i)=><i key={i} style={{'--h':h+'px','--d':i*90+'ms'}}/>)}</div>
        <div className="mk-row"><div className="ring"/><div style={{flex:1,display:'grid',gap:8}}><u/><u style={{width:'70%'}}/><u style={{width:'45%'}}/></div></div></div></section>

      {user&&<section id="mine" className="sect" style={{paddingTop:20}}><div className="eyebrow">Your account</div><h2>Your saved dashboards</h2>
        {datasets.length===0?<p className="sub">Nothing here yet. Upload a file above and it will be saved to your account automatically.</p>:
        <div className="g3" style={{marginTop:18}}>{datasets.map(d=><div key={d.id} className="rule mine"><div className="ico2">📊</div><h4 style={{marginBottom:4}}>{d.title}</h4><p style={{wordBreak:'break-all'}}>{d.filename}</p>
          <small className="mut" style={{display:'block',margin:'8px 0 12px'}}>{d.rows.toLocaleString()} rows · saved {new Date(d.created_at+'Z').toLocaleDateString()}</small>
          <div style={{display:'flex',gap:8}}><button onClick={()=>onOpen(d.id)}>Open</button><button className="ghost" onClick={()=>onDelete(d.id)}>Delete</button></div></div>)}</div>}</section>}

      <section id="how" className="sect"><div className="eyebrow reveal">How it works</div><h2 className="reveal">From a raw file to a dashboard in six steps</h2>
        <p className="sub reveal">No configuration and no formulas. Here is exactly what happens the moment you drop a file.</p>
        <div className="tl">{STEPS.map(([i,t,p])=><div key={t} className="tli reveal"><div className="num">{i}</div><div><h3>{t}</h3><p>{p}</p></div></div>)}</div></section>

      <section id="decide" className="sect"><div className="eyebrow reveal">How it decides</div><h2 className="reveal">Every column gets a role. The role picks the chart.</h2>
        <p className="sub reveal">Click a column to see how AutoDash treats it. These examples come from typical sales and customer files.</p>
        <div className="demo reveal"><div className="cols">{COLS.map((c,i)=><button key={c[0]} className={'cb'+(sel===i?' on':'')} onClick={()=>setSel(i)}><code>{c[0]}</code><span className={'chip '+c[2]}>{c[1]}</span></button>)}</div>
          <div className="out"><span className={'chip '+S[2]}>{S[1]}</span><h3>{S[0]}</h3><p>{S[4]}</p><div className="arrow"><span className="mut">Becomes →</span><span className="chip">{S[3]}</span></div></div></div>
        <h2 style={{marginTop:60}} className="reveal">The decision rules</h2><p className="sub reveal">Plain rules, no black box. The same logic runs on every file you upload.</p>
        <div className="g3">{RULES.map(([i,a,b,c])=><div key={a} className="rule reveal"><div className="ico2">{i}</div><small>If we see</small><h4>{a}</h4><small>We draw</small><h4 style={{color:'var(--ac)'}}>{b}</h4><p>{c}</p></div>)}</div></section>

      <section className="sect"><div className="eyebrow reveal">Under the hood</div><h2 className="reveal">The visualization pipeline</h2>
        <p className="sub reveal">Open <b>🔍 How it was built</b> inside any dashboard to watch this pipeline's real results for your file, including the SQL for every chart.</p>
        <div className="flow reveal">{FLOW.map(([i,t,s],k)=><span key={t} style={{display:'contents'}}><div className="fb">{i} {t}<small>{s}</small></div>{k<FLOW.length-1&&<span className="fa">→</span>}</span>)}</div></section>

      <section id="features" className="sect"><div className="eyebrow reveal">Features</div><h2 className="reveal">Everything you need to understand your data</h2><br/>
        <div className="g3">{FEAT.map(([i,t,p])=><div key={t} className="rule reveal"><div className="ico2">{i}</div><h4>{t}</h4><p>{p}</p></div>)}</div></section>

      <section id="faq" className="sect faq"><div className="eyebrow reveal">FAQ</div><h2 className="reveal">Questions, answered</h2><br/>{FAQ.map(([q,a])=><details key={q} className="reveal"><summary>{q}</summary><p>{a}</p></details>)}</section>

      <section className="sect"><div className="cta reveal"><h2 style={{margin:0,color:'#fff'}}>Ready to see your data?</h2><p style={{opacity:.9}}>It takes about five seconds.</p><button onClick={()=>window.scrollTo({top:0,behavior:'smooth'})}>Upload a file ↑</button></div></section>
      <footer className="foot">AutoDash · FastAPI + pandas + React + Recharts · Your original file is never modified</footer></div></div>
}
