import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:archive/archive.dart';

import 'models.dart';
import 'widgets/detection_photo.dart';

/// A PNG of the photo with the detection boxes drawn on it.
class MarkedPhoto {
  MarkedPhoto(this.png, this.width, this.height);
  final Uint8List png;
  final int width;
  final int height;
}

/// Draws the boxes onto the photo itself, so the Word report carries the same evidence
/// the app shows. Big photos are scaled down to keep the document small enough for WhatsApp.
Future<MarkedPhoto> markPhoto(Uint8List photo, List<Detection> detections, {int maxSide = 1280}) async {
  final codec = await ui.instantiateImageCodec(photo);
  final image = (await codec.getNextFrame()).image;
  final scale = maxSide / (image.width > image.height ? image.width : image.height);
  final factor = scale < 1 ? scale : 1.0;
  final width = (image.width * factor).round();
  final height = (image.height * factor).round();

  final recorder = ui.PictureRecorder();
  final canvas = ui.Canvas(recorder);
  final size = ui.Size(width.toDouble(), height.toDouble());
  canvas.drawImageRect(
    image,
    ui.Rect.fromLTWH(0, 0, image.width.toDouble(), image.height.toDouble()),
    ui.Offset.zero & size,
    ui.Paint()..filterQuality = ui.FilterQuality.high,
  );
  // Thicker lines and bigger labels than on screen, since the photo is shown smaller in Word.
  paintDetections(canvas, size, detections, strokeWidth: width / 300, fontSize: width / 50);

  final marked = await recorder.endRecording().toImage(width, height);
  final bytes = await marked.toByteData(format: ui.ImageByteFormat.png);
  image.dispose();
  marked.dispose();
  return MarkedPhoto(bytes!.buffer.asUint8List(), width, height);
}

/// Builds a .docx (Word) file for the municipality: the report text and the marked photo.
///
/// A .docx is a zip of XML files. Only the parts Word needs are written here, which keeps
/// this free of a document library.
Uint8List reportDocx(Report report, MarkedPhoto photo, DateTime date) {
  final r = report.municipalReport;
  final body = StringBuffer()
    ..write(_para(r.title, bold: true, size: 32))
    ..write(_para('Reported with CivicLens on ${_date(date)}', size: 20, colour: '64748B'))
    ..write(_field('Location', r.location))
    ..write(_field('Priority', r.priority))
    ..write(_field('Department', r.department))
    ..write(_image(photo))
    ..write(_para('Description', bold: true, size: 26))
    ..write(_para(r.description));
  if (report.issues.isNotEmpty) {
    body.write(_para('What was found', bold: true, size: 26));
    for (final issue in report.issues) {
      body.write(_para('• ${issue.issueType}: ${issue.severity.toLowerCase()} priority, for ${issue.department}'));
    }
  }
  body
    ..write(_para('Evidence', bold: true, size: 26))
    ..write(_para(r.evidenceNotes))
    ..write(_para('Recommended action', bold: true, size: 26))
    ..write(_para(report.recommendedAction));

  final archive = Archive()
    ..addFile(ArchiveFile.string('[Content_Types].xml', _contentTypes))
    ..addFile(ArchiveFile.string('_rels/.rels', _rootRels))
    ..addFile(ArchiveFile.string('word/_rels/document.xml.rels', _documentRels))
    ..addFile(ArchiveFile.string('word/document.xml', _document(body.toString())))
    ..addFile(ArchiveFile.bytes('word/media/photo.png', photo.png));
  return ZipEncoder().encodeBytes(archive);
}

const docxMimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

/// A file name like "CivicLens report - Pothole - 2026-11-24.docx".
String reportFileName(Report report, DateTime date) {
  final issue = report.issueType.replaceAll(RegExp(r'[^A-Za-z0-9 ]'), '').trim();
  return 'CivicLens report - $issue - ${_isoDate(date)}.docx';
}

const _months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

String _date(DateTime d) => '${d.day} ${_months[d.month - 1]} ${d.year}';

String _isoDate(DateTime d) =>
    '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

String _escape(String text) => text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');

/// One paragraph. Sizes are in half-points, so 24 is 12 pt.
String _para(String text, {bool bold = false, int size = 22, String? colour}) {
  final props = StringBuffer();
  if (bold) props.write('<w:b/>');
  if (colour != null) props.write('<w:color w:val="$colour"/>');
  props.write('<w:sz w:val="$size"/>');
  return '<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>'
      '<w:r><w:rPr>$props</w:rPr><w:t xml:space="preserve">${_escape(text)}</w:t></w:r></w:p>';
}

/// "Label: value" with the label in bold.
String _field(String label, String value) => '<w:p><w:pPr><w:spacing w:after="60"/></w:pPr>'
    '<w:r><w:rPr><w:b/><w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">$label: </w:t></w:r>'
    '<w:r><w:rPr><w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">${_escape(value)}</w:t></w:r></w:p>';

/// The photo, 15 cm wide (Word measures in EMUs: 360,000 per cm).
String _image(MarkedPhoto photo) {
  const cx = 15 * 360000;
  final cy = (cx * photo.height / photo.width).round();
  return '<w:p><w:pPr><w:spacing w:before="200" w:after="200"/></w:pPr><w:r><w:drawing>'
      '<wp:inline distT="0" distB="0" distL="0" distR="0">'
      '<wp:extent cx="$cx" cy="$cy"/><wp:docPr id="1" name="Photo"/>'
      '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
      '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
      '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
      '<pic:nvPicPr><pic:cNvPr id="0" name="photo.png"/><pic:cNvPicPr/></pic:nvPicPr>'
      '<pic:blipFill><a:blip r:embed="rIdPhoto"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
      '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="$cx" cy="$cy"/></a:xfrm>'
      '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
      '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>';
}

String _document(String body) => '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
    '<w:body>$body'
    '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>'
    '</w:sectPr></w:body></w:document>';

const _contentTypes = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="png" ContentType="image/png"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>';

const _rootRels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/></Relationships>';

const _documentRels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rIdPhoto" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
    'Target="media/photo.png"/></Relationships>';
