import 'package:material_ui/material_ui.dart';

// Same palette as the web app.
const ink = Color(0xFF07111F);
const panel = Color(0xFF0D1B2E);
const cyan = Color(0xFF67E8F9);
const emerald = Color(0xFF6EE7B7);
const muted = Color(0xFF94A3B8);

ThemeData civicTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: cyan,
    brightness: Brightness.dark,
    surface: ink,
    primary: cyan,
    secondary: emerald,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: ink,
    appBarTheme: const AppBarTheme(backgroundColor: ink, elevation: 0, centerTitle: false),
    cardTheme: CardThemeData(
      color: panel,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: Colors.white.withValues(alpha: .08)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: panel,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: Colors.white.withValues(alpha: .1)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: Colors.white.withValues(alpha: .1)),
      ),
      hintStyle: const TextStyle(color: muted),
    ),
  );
}

Color severityColor(String severity) => switch (severity) {
      'Critical' => const Color(0xFFFDA4AF),
      'High' => const Color(0xFFFDBA74),
      'Medium' => const Color(0xFFFCD34D),
      _ => emerald,
    };
