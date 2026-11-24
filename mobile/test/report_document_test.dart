import 'dart:convert';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:civiclens/models.dart';
import 'package:civiclens/report_document.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fixtures.dart';

void main() {
  final report = Report.fromJson(potholeJson);
  final date = DateTime(2026, 11, 24);
  final photo = MarkedPhoto(Uint8List.fromList(tinyPng), 400, 300);

  Archive unzip(Uint8List docx) => ZipDecoder().decodeBytes(docx);
  String text(Archive zip, String name) => utf8.decode(zip.findFile(name)!.content as List<int>);

  test('the .docx has the parts Word needs, with the photo inside', () {
    final zip = unzip(reportDocx(report, photo, date));
    for (final part in ['[Content_Types].xml', '_rels/.rels', 'word/document.xml', 'word/_rels/document.xml.rels']) {
      expect(zip.findFile(part), isNotNull, reason: part);
    }
    expect(zip.findFile('word/media/photo.png')!.content, tinyPng);
    expect(text(zip, 'word/_rels/document.xml.rels'), contains('Id="rIdPhoto"'));
  });

  test('the document holds the report, and the photo keeps its shape', () {
    final doc = text(unzip(reportDocx(report, photo, date)), 'word/document.xml');
    expect(doc, contains('Pothole on the road'));
    expect(doc, contains('Reported with CivicLens on 24 November 2026'));
    expect(doc, contains('Kempton Park'));
    expect(doc, contains('Roads and Stormwater'));
    expect(doc, contains('Road crack: medium priority'));
    expect(doc, contains('r:embed="rIdPhoto"'));
    // 15 cm wide, so a 4:3 photo is 11.25 cm tall.
    expect(doc, contains('cx="5400000" cy="4050000"'));
  });

  test('text from the API is escaped so it cannot break the document', () {
    final json = jsonDecode(jsonEncode(potholeJson)) as Map<String, dynamic>;
    (json['municipal_report'] as Map<String, dynamic>)['location'] = 'Corner of <Main> & "Long" St';
    final doc = text(unzip(reportDocx(Report.fromJson(json), photo, date)), 'word/document.xml');
    expect(doc, contains('Corner of &lt;Main&gt; &amp; &quot;Long&quot; St'));
  });

  test('the file name says what and when', () {
    expect(reportFileName(report, date), 'CivicLens report - Pothole - 2026-11-24.docx');
  });
}
