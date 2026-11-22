import { useEffect, useState } from 'react';
import { Camera } from 'lucide-react';
import { Hero } from './components/Hero';
import { UploadPanel } from './components/UploadPanel';
import { ReportCard } from './components/ReportCard';
import type { CivicReport } from './types/report';
import { DemoStats } from './components/DemoStats';
import { Footer } from './components/Footer';
import { wakeBackend } from './services/api';
export default function App(){const [report,setReport]=useState<CivicReport|null>(null),[photo,setPhoto]=useState('');const show=(r:CivicReport,p:string)=>{setReport(r);setPhoto(p)};useEffect(()=>{wakeBackend()},[]);return <main className="grid-bg min-h-screen overflow-hidden"><nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-6"><div className="display flex items-center gap-2 text-lg font-bold"><span className="rounded-xl bg-cyan-300 p-2 text-slate-950"><Camera size={19}/></span>CivicLens <span className="text-cyan-300">AI</span></div></nav><Hero/><DemoStats/><div id="analyze" className="mx-auto max-w-4xl px-5 pb-24"><UploadPanel onReport={show}/>{report&&<ReportCard report={report} photo={photo}/>}</div><Footer/></main>}
