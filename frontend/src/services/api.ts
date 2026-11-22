import type { CivicReport, DemoSample } from '../types/report';
const API_BASE_URL=(import.meta.env.VITE_API_BASE_URL||(import.meta.env.DEV?'http://localhost:8080':'')).replace(/\/$/,'');
// Set VITE_DEMO_MODE=true only for a sample-only build without a live backend.
export const DEMO_MODE=import.meta.env.VITE_DEMO_MODE==='true';
export const RUN_LOCALLY_URL='https://github.com/Kea-nhlapo/civiclens-ai#run-it-locally';
export class BackendUnavailable extends Error{}
// Generous, because a cold Cloud Run start loads four models (about 20 to 30 s) before the first photo.
const ANALYZE_TIMEOUT_MS=90_000;
// Fire and forget on page load, so the server is already waking up by the time someone picks a photo.
// Once /health has answered, the models are loaded and a slow photo is just a slow photo, not a cold start.
let awake=false;
export const backendAwake=()=>awake;
export function wakeBackend(){if(DEMO_MODE)return;fetch(`${API_BASE_URL}/health`).then(r=>{awake=r.ok}).catch(()=>{})}
export async function analyzeReport(image:File,location:string,notes:string,streetlightOut=false):Promise<CivicReport>{if(DEMO_MODE)throw new BackendUnavailable('Live detection needs the backend running. This site shows sample results only.');const body=new FormData();body.append('image',image);if(location.trim())body.append('location',location.trim());if(notes.trim())body.append('notes',notes.trim());if(streetlightOut)body.append('streetlight_out','true');let response:Response;try{response=await fetch(`${API_BASE_URL}/api/analyze-report`,{method:'POST',body,signal:AbortSignal.timeout(ANALYZE_TIMEOUT_MS)})}catch(e){throw new BackendUnavailable(e instanceof DOMException&&e.name==='TimeoutError'?'The detection server took too long to answer. Please try again.':'The detection server is not reachable right now.')}if(!response.ok){const error=await response.json().catch(()=>({detail:'Analysis failed. Please try again.'}));throw new Error(error.detail||'Analysis failed.');}return response.json();}
// Saved results from the real models, run ahead of time (backend/tools/make_demo_samples.py).
export async function loadSamples():Promise<DemoSample[]>{const response=await fetch('/samples/index.json');if(!response.ok)throw new Error('The sample photos could not be loaded.');return response.json();}
export async function loadSampleReport(sample:DemoSample):Promise<CivicReport>{const response=await fetch(sample.result);if(!response.ok)throw new Error('That sample could not be loaded.');return {...await response.json(),analysis_source:'sample'};}
