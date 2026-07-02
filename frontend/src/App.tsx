import { useState } from 'react';
import { Camera, ShieldCheck } from 'lucide-react';
import { Hero } from './components/Hero';
import { UploadPanel } from './components/UploadPanel';
import { ReportCard } from './components/ReportCard';
import type { CivicReport } from './types/report';
export default function App(){const [report,setReport]=useState<CivicReport|null>(null);return <main className="grid-bg min-h-screen overflow-hidden"><nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-6"><div className="display flex items-center gap-2 text-lg font-bold"><span className="rounded-xl bg-cyan-300 p-2 text-slate-950"><Camera size={19}/></span>CivicLens <span className="text-cyan-300">AI</span></div><div className="flex items-center gap-2 text-xs text-slate-400"><ShieldCheck size={15} className="text-emerald-300"/>Drafts only · You stay in control</div></nav><Hero/><div id="analyze" className="mx-auto max-w-4xl px-5 pb-24"><UploadPanel onReport={setReport} onDemo={()=>{}}/>{report&&<ReportCard report={report}/>}</div></main>}
