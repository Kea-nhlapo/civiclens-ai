export type Severity='Low'|'Medium'|'High'|'Critical';
export type IssueCategory='pothole'|'crack'|'streetlight';
export interface DetectionBox{label:string;category:IssueCategory;confidence:number;x1:number;y1:number;x2:number;y2:number}
export interface IssueSummary{category:IssueCategory;issue_type:string;department:string;severity:Severity;confidence:number;count:number;coverage:number;reason:string}
export interface CivicReport{issue_type:string;severity:Severity;confidence:number;summary:string;responsible_department:string;recommended_action:string;municipal_report:{title:string;description:string;location:string;evidence_notes:string;priority:Severity;suggested_department:string};citizen_message:string;next_steps:string[];detections?:DetectionBox[];issues?:IssueSummary[];pothole_count?:number;coverage?:number;severity_reason?:string;image_width?:number;image_height?:number;models?:string[];analysis_source?:'detector'|'detector+gemini'|'demo'}
