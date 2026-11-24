/// A pothole report shaped like the real API response.
const potholeJson = {
  'issue_type': 'Pothole',
  'severity': 'High',
  'confidence': 0.87,
  'summary': 'Two potholes were found covering about 9% of the road in the photo.',
  'responsible_department': 'Roads and Stormwater',
  'recommended_action': 'Patch the potholes and check the road edge for water damage.',
  'municipal_report': {
    'title': 'Pothole on the road',
    'description': 'Two potholes were detected in the attached photo.',
    'location': 'Kempton Park',
    'evidence_notes': 'Detector found 2 potholes.',
    'priority': 'High',
    'suggested_department': 'Roads and Stormwater',
  },
  'citizen_message': 'Thanks for reporting.',
  'next_steps': ['Send the report to the municipality.', 'Keep the reference number.'],
  'detections': [
    {'label': 'pothole', 'category': 'pothole', 'confidence': 0.87, 'x1': 0.1, 'y1': 0.5, 'x2': 0.4, 'y2': 0.8},
    {'label': 'pothole', 'category': 'pothole', 'confidence': 0.71, 'x1': 0.6, 'y1': 0.6, 'x2': 0.9, 'y2': 0.9},
  ],
  'issues': [
    {
      'category': 'pothole',
      'issue_type': 'Pothole',
      'department': 'Roads and Stormwater',
      'severity': 'High',
      'confidence': 0.87,
      'count': 2,
      'coverage': 0.09,
      'reason': 'Large potholes',
    },
    {
      'category': 'crack',
      'issue_type': 'Road crack',
      'department': 'Roads and Stormwater',
      'severity': 'Medium',
      'confidence': 0.6,
      'count': 1,
      'coverage': 0.02,
      'reason': 'One crack',
    },
  ],
  'pothole_count': 2,
  'coverage': 0.09,
  'severity_reason': 'The potholes cover a large part of the lane.',
  'image_width': 1024,
  'image_height': 768,
  'models': ['rf-detr-nano-potholes'],
  'analysis_source': 'detector',
};

/// A 1x1 PNG, enough for Image.memory in tests.
const tinyPng = <int>[
  0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, //
  0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
  0x89, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
  0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
  0x42, 0x60, 0x82,
];
