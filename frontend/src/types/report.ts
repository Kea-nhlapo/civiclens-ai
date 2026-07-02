export type Severity='Low'|'Medium'|'High'|'Critical';
export interface CivicReport{issue_type:string;severity:Severity;confidence:number;summary:string;responsible_department:string;recommended_action:string;municipal_report:{title:string;description:string;location:string;evidence_notes:string;priority:Severity;suggested_department:string};citizen_message:string;next_steps:string[]}
