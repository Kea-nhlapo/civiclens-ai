import type { CivicReport, DemoSample } from '../types/report';
const API_BASE_URL=(import.meta.env.VITE_API_BASE_URL||(import.meta.env.DEV?'http://localhost:8080':'')).replace(/\/$/,'');
// The live site has no detection server (hosting the models costs money), so it is built with VITE_DEMO_MODE=true
// and shows saved results instead. Run the backend locally for real detection on your own photos.
export const DEMO_MODE=import.meta.env.VITE_DEMO_MODE==='true';
export const RUN_LOCALLY_URL='https://github.com/Kea-nhlapo/civiclens-ai#run-it-locally';
export class BackendUnavailable extends Error{}
export async function analyzeReport(image:File,location:string,notes:string,streetlightOut=false):Promise<CivicReport>{if(DEMO_MODE)throw new BackendUnavailable('Live detection needs the backend running. This site shows sample results only.');const body=new FormData();body.append('image',image);if(location.trim())body.append('location',location.trim());if(notes.trim())body.append('notes',notes.trim());if(streetlightOut)body.append('streetlight_out','true');let response:Response;try{response=await fetch(`${API_BASE_URL}/api/analyze-report`,{method:'POST',body})}catch{throw new BackendUnavailable('The detection server is not reachable right now.')}if(!response.ok){const error=await response.json().catch(()=>({detail:'Analysis failed. Please try again.'}));throw new Error(error.detail||'Analysis failed.');}return response.json();}
// Saved results from the real models, run ahead of time (backend/tools/make_demo_samples.py).
export async function loadSamples():Promise<DemoSample[]>{const response=await fetch('/samples/index.json');if(!response.ok)throw new Error('The sample photos could not be loaded.');return response.json();}
export async function loadSampleReport(sample:DemoSample):Promise<CivicReport>{const response=await fetch(sample.result);if(!response.ok)throw new Error('That sample could not be loaded.');return {...await response.json(),analysis_source:'sample'};}
