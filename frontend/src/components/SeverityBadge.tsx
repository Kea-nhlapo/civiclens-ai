import { AlertTriangle } from 'lucide-react';
import type { Severity } from '../types/report';
const colors:Record<Severity,string>={Low:'border-emerald-300/30 bg-emerald-300/10 text-emerald-200',Medium:'border-amber-300/30 bg-amber-300/10 text-amber-200',High:'border-orange-300/30 bg-orange-300/10 text-orange-200',Critical:'border-rose-300/30 bg-rose-300/10 text-rose-200'};
export function SeverityBadge({severity}:{severity:Severity}){return <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${colors[severity]}`}><AlertTriangle size={13}/>{severity} severity</span>}
