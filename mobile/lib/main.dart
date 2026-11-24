import 'package:flutter/material.dart';

import 'api.dart';
import 'screens/home_screen.dart';
import 'theme.dart';

void main() {
  final api = CivicLensApi();
  api.wakeUp();
  runApp(CivicLensApp(api: api));
}

class CivicLensApp extends StatelessWidget {
  const CivicLensApp({super.key, required this.api});

  final CivicLensApi api;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CivicLens',
      debugShowCheckedModeBanner: false,
      theme: civicTheme(),
      home: HomeScreen(api: api),
    );
  }
}
