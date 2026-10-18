import React, {useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import ForceGraph2D from "react-force-graph-2d";
import "./style.css";

const API = "http://localhost:8000";
type Endpoint = {e?: Record<string, any>};
type Incident = {i?: Record<string, any>};

function App() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [path, setPath] = useState("/auth/verify");
  const [showFiles, setShowFiles] = useState(true);
  const refresh = async () => {
    setEndpoints(await (await fetch(`${API}/endpoints`)).json());
    setIncidents(await (await fetch(`${API}/incidents`)).json());
  };
  useEffect(()=>{refresh()},[]);
  const simulate = async (mode: string) => {
    await fetch(`${API}/${mode === "failure" ? "simulate-failure" : "simulate-recover"}`, {method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({path})});
    await fetch(`${API}/monitor`, {method:"POST"}); refresh();
  };
  const graph = {nodes:endpoints.map(x=>({id:x.e?.id,label:x.e?.path,status:x.e?.status,importance:x.e?.importance||1})), links:[]};
  return <main>
    <header><strong>DarkMatter</strong><span>Graph-powered on-call intelligence</span><select onChange={e=>setPath(e.target.value)} value={path}><option>/auth/verify</option><option>/inventory</option><option>/payments/charge</option></select><button onClick={()=>simulate("failure")}>SIMULATE FAILURE</button><button onClick={()=>simulate("recover")}>SIMULATE RECOVER</button></header>
    <section className="layout"><div className="graph"><ForceGraph2D graphData={graph} nodeLabel="label" nodeColor={(n:any)=>n.status==="failing"?"#ff4d6d":"#58d6c0"} nodeVal={(n:any)=>5+(n.importance||1)*8}/></div>
    <aside><h2>Incidents</h2>{incidents.map((item,i)=><button className="incident" key={i} onClick={()=>setSelected(item.i)}><b>{item.i?.status||"open"}</b><small>{item.i?.id}</small></button>)}{selected&&<article><h2>Incident detail</h2><p className="sim">SIMULATED / dry-run email</p><pre>{JSON.stringify(selected,null,2)}</pre><button onClick={async()=>{await fetch(`${API}/incidents/${selected.id}/send-email`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({recipients:["oncall@example.com"],subject:"DarkMatter incident",body:"See graph evidence."})})}}>Send alert</button></article>}<label><input type="checkbox" checked={showFiles} onChange={e=>setShowFiles(e.target.checked)}/> show authors/files</label></aside></section>
  </main>
}
createRoot(document.getElementById("root")!).render(<App/>);
