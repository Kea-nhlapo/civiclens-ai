import 'dart:convert';

import 'package:civiclens/api.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'fixtures.dart';

CivicLensApi apiReplying(Future<http.Response> Function(http.Request) handler) =>
    CivicLensApi(client: MockClient(handler), base: 'https://api.test');

void main() {
  test('sends the photo and form fields, and reads the report', () async {
    late http.Request sent;
    final api = apiReplying((request) async {
      sent = request;
      return http.Response(jsonEncode(potholeJson), 200);
    });

    final report = await api.analyze(
      photo: tinyPng,
      filename: 'road.png',
      location: ' Kempton Park ',
      notes: 'Near the school',
      streetlightOut: true,
    );

    expect(sent.url.toString(), 'https://api.test/api/analyze-report');
    final body = latin1.decode(sent.bodyBytes);
    expect(body, contains('name="image"; filename="road.png"'));
    expect(body, contains('content-type: image/png'));
    expect(body, contains('Kempton Park'));
    expect(body, isNot(contains(' Kempton Park ')));
    expect(body, contains('Near the school'));
    expect(body, contains('name="streetlight_out"\r\n\r\ntrue'));

    expect(report.issueType, 'Pothole');
    expect(report.detections, hasLength(2));
    expect(report.issues[1].issueType, 'Road crack');
    expect(report.foundSomething, isTrue);
    expect(report.municipalReport.asText(), contains('Department: Roads and Stormwater'));
  });

  test('leaves out empty location and notes', () async {
    late http.Request sent;
    final api = apiReplying((request) async {
      sent = request;
      return http.Response(jsonEncode(potholeJson), 200);
    });
    await api.analyze(photo: tinyPng, filename: 'a.jpg', location: '   ');
    final body = latin1.decode(sent.bodyBytes);
    expect(body, isNot(contains('name="location"')));
    expect(body, isNot(contains('name="notes"')));
    expect(body, contains('content-type: image/jpeg'));
  });

  test('explains the photo limit using Retry-After', () async {
    final api = apiReplying((_) async => http.Response('{"detail":"Too many"}', 429, headers: {'retry-after': '600'}));
    expect(
      () => api.analyze(photo: tinyPng, filename: 'a.jpg'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('about 10 minutes'))),
    );
  });

  test("passes on the server's own message for a bad photo", () async {
    final api = apiReplying((_) async => http.Response('{"detail":"Upload a JPEG, PNG, or WebP image."}', 400));
    expect(
      () => api.analyze(photo: tinyPng, filename: 'a.gif'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Upload a JPEG, PNG, or WebP image.')),
    );
  });

  test('says what to fix when a field is too long', () async {
    final api = apiReplying((_) async => http.Response('{"detail":[]}', 422));
    expect(
      () => api.analyze(photo: tinyPng, filename: 'a.jpg'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('under 500'))),
    );
  });

  test('turns a network failure into a plain message', () async {
    final api = apiReplying((_) async => throw http.ClientException('no signal'));
    expect(
      () => api.analyze(photo: tinyPng, filename: 'a.jpg'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('internet connection'))),
    );
  });

  test('wakeUp never throws, even when the server is down', () async {
    final api = apiReplying((_) async => throw http.ClientException('down'));
    await api.wakeUp();
  });
}
