import 'dart:typed_data';

import 'package:civiclens/api.dart';
import 'package:civiclens/models.dart';
import 'package:civiclens/screens/home_screen.dart';
import 'package:civiclens/screens/report_screen.dart';
import 'package:civiclens/theme.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'fixtures.dart';

Widget wrap(Widget child) => MaterialApp(theme: civicTheme(), home: child);

void main() {
  testWidgets('home shows both photo buttons and asks for a photo first', (tester) async {
    var calls = 0;
    final api = CivicLensApi(
      client: MockClient((_) async {
        calls++;
        return http.Response('{}', 200);
      }),
      base: 'https://api.test',
    );
    await tester.pumpWidget(wrap(HomeScreen(api: api)));

    expect(find.text('Take a photo'), findsOneWidget);
    expect(find.text('Choose photo'), findsOneWidget);

    // The button is below the fold on a phone, so scroll to it like a person would.
    // The text fields scroll too, so name the page's own list.
    final page = find.byType(Scrollable).first;
    await tester.scrollUntilVisible(find.byKey(const Key('analyze')), 200, scrollable: page);
    await tester.tap(find.byKey(const Key('analyze')));
    await tester.pump();

    expect(find.text('Add a photo first.'), findsOneWidget);
    expect(calls, 0);
  });

  testWidgets('report screen shows the findings and the municipal report', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(wrap(ReportScreen(
      report: Report.fromJson(potholeJson),
      photo: Uint8List.fromList(tinyPng),
    )));

    expect(find.text('Pothole'), findsOneWidget);
    expect(find.text('High severity'), findsOneWidget);
    expect(find.text('87% confidence'), findsOneWidget);
    expect(find.textContaining('Road crack'), findsOneWidget);
    expect(find.text('REPORT FOR THE MUNICIPALITY'), findsOneWidget);
    expect(find.byKey(const Key('share')), findsOneWidget);
  });
}
