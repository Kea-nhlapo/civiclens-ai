import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import 'models.dart';

/// The backend on Cloud Run. Override at build time with
/// --dart-define=CIVICLENS_API=http://10.0.2.2:8080 to use a local backend from the Android emulator.
const apiBase = String.fromEnvironment(
  'CIVICLENS_API',
  defaultValue: 'https://civiclens-api-842833677282.us-central1.run.app',
);

/// Something went wrong that the person should be told about in plain words.
class ApiException implements Exception {
  ApiException(this.message);
  final String message;
  @override
  String toString() => message;
}

class CivicLensApi {
  CivicLensApi({http.Client? client, this.base = apiBase}) : _client = client ?? http.Client();

  final http.Client _client;
  final String base;

  /// A sleeping server takes about 20 seconds to load its models, so the app pings it on
  /// launch and the first photo doesn't have to wait as long. Failures don't matter here.
  Future<void> wakeUp() async {
    try {
      await _client.get(Uri.parse('$base/health')).timeout(const Duration(seconds: 45));
    } catch (_) {}
  }

  Future<Report> analyze({
    required List<int> photo,
    required String filename,
    String location = '',
    String notes = '',
    bool streetlightOut = false,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse('$base/api/analyze-report'))
      ..files.add(http.MultipartFile.fromBytes('image', photo, filename: filename, contentType: _typeOf(filename)))
      ..fields['streetlight_out'] = streetlightOut.toString();
    if (location.trim().isNotEmpty) request.fields['location'] = location.trim();
    if (notes.trim().isNotEmpty) request.fields['notes'] = notes.trim();

    final http.Response response;
    try {
      // A cold start plus a slow upload can take a while, so the limit is generous.
      response = await _client
          .send(request)
          .then(http.Response.fromStream)
          .timeout(const Duration(seconds: 90));
    } on TimeoutException {
      throw ApiException('The server took too long to answer. Check your signal and try again.');
    } catch (_) {
      throw ApiException("Couldn't reach CivicLens. Check your internet connection and try again.");
    }

    switch (response.statusCode) {
      case 200:
        return Report.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
      case 429:
        final wait = int.tryParse(response.headers['retry-after'] ?? '');
        throw ApiException('You\'ve sent a lot of photos. Try again ${_inAbout(wait)}.');
      case 422:
        throw ApiException('Keep the location under 200 characters and the note under 500.');
      case 400:
      case 503:
        throw ApiException(_detail(response) ?? 'Something went wrong. Please try again.');
      default:
        throw ApiException('Something went wrong (error ${response.statusCode}). Please try again.');
    }
  }

  static MediaType _typeOf(String filename) {
    final name = filename.toLowerCase();
    if (name.endsWith('.png')) return MediaType('image', 'png');
    if (name.endsWith('.webp')) return MediaType('image', 'webp');
    return MediaType('image', 'jpeg');
  }

  static String? _detail(http.Response response) {
    try {
      final detail = (jsonDecode(response.body) as Map<String, dynamic>)['detail'];
      return detail is String ? detail : null;
    } catch (_) {
      return null;
    }
  }

  static String _inAbout(int? seconds) {
    if (seconds == null) return 'a little later';
    if (seconds < 90) return 'in about a minute';
    if (seconds < 3600) return 'in about ${(seconds / 60).ceil()} minutes';
    final hours = (seconds / 3600).ceil();
    return 'in about $hours hour${hours == 1 ? '' : 's'}';
  }
}
