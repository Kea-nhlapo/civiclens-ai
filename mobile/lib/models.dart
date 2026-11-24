/// What the API sends back for one photo. Mirrors AnalysisReport in backend/app/models/schemas.py.
class Report {
  Report({
    required this.issueType,
    required this.severity,
    required this.confidence,
    required this.summary,
    required this.severityReason,
    required this.department,
    required this.recommendedAction,
    required this.municipalReport,
    required this.nextSteps,
    required this.detections,
    required this.issues,
  });

  final String issueType;
  final String severity;
  final double confidence;
  final String summary;
  final String severityReason;
  final String department;
  final String recommendedAction;
  final MunicipalReport municipalReport;
  final List<String> nextSteps;
  final List<Detection> detections;
  final List<Issue> issues;

  /// "No issue detected" comes back as a normal report with nothing found.
  bool get foundSomething => detections.isNotEmpty || issues.isNotEmpty;

  factory Report.fromJson(Map<String, dynamic> json) => Report(
        issueType: json['issue_type'] as String,
        severity: json['severity'] as String,
        confidence: (json['confidence'] as num).toDouble(),
        summary: json['summary'] as String,
        severityReason: json['severity_reason'] as String? ?? '',
        department: json['responsible_department'] as String,
        recommendedAction: json['recommended_action'] as String,
        municipalReport: MunicipalReport.fromJson(json['municipal_report'] as Map<String, dynamic>),
        nextSteps: (json['next_steps'] as List).cast<String>(),
        detections: [
          for (final d in json['detections'] as List? ?? const []) Detection.fromJson(d as Map<String, dynamic>),
        ],
        issues: [
          for (final i in json['issues'] as List? ?? const []) Issue.fromJson(i as Map<String, dynamic>),
        ],
      );
}

class MunicipalReport {
  MunicipalReport({
    required this.title,
    required this.description,
    required this.location,
    required this.evidenceNotes,
    required this.priority,
    required this.department,
  });

  final String title;
  final String description;
  final String location;
  final String evidenceNotes;
  final String priority;
  final String department;

  factory MunicipalReport.fromJson(Map<String, dynamic> json) => MunicipalReport(
        title: json['title'] as String,
        description: json['description'] as String,
        location: json['location'] as String,
        evidenceNotes: json['evidence_notes'] as String,
        priority: json['priority'] as String,
        department: json['suggested_department'] as String,
      );

  /// Plain text a person can paste into an email or WhatsApp to the municipality.
  String asText() => '$title\n\n$description\n\n'
      'Location: $location\n'
      'Evidence: $evidenceNotes\n'
      'Priority: $priority\n'
      'Department: $department';
}

/// One box the detectors drew. Coordinates are fractions of the photo's width and height.
class Detection {
  Detection({
    required this.label,
    required this.category,
    required this.confidence,
    required this.x1,
    required this.y1,
    required this.x2,
    required this.y2,
  });

  final String label;
  final String category;
  final double confidence;
  final double x1, y1, x2, y2;

  factory Detection.fromJson(Map<String, dynamic> json) => Detection(
        label: json['label'] as String,
        category: json['category'] as String,
        confidence: (json['confidence'] as num).toDouble(),
        x1: (json['x1'] as num).toDouble(),
        y1: (json['y1'] as num).toDouble(),
        x2: (json['x2'] as num).toDouble(),
        y2: (json['y2'] as num).toDouble(),
      );
}

class Issue {
  Issue({required this.category, required this.issueType, required this.severity, required this.department});

  final String category;
  final String issueType;
  final String severity;
  final String department;

  factory Issue.fromJson(Map<String, dynamic> json) => Issue(
        category: json['category'] as String,
        issueType: json['issue_type'] as String,
        severity: json['severity'] as String,
        department: json['department'] as String,
      );
}
