import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../api.dart';
import '../theme.dart';
import 'report_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.api, this.picker});

  final CivicLensApi api;

  /// Swapped out in tests.
  final ImagePicker? picker;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final ImagePicker _picker = widget.picker ?? ImagePicker();
  final _location = TextEditingController();
  final _notes = TextEditingController();

  Uint8List? _photo;
  String _filename = 'photo.jpg';
  bool _streetlightOut = false;
  bool _busy = false;
  bool _slow = false;
  String? _error;

  @override
  void dispose() {
    _location.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _pick(ImageSource source) async {
    try {
      // Phone photos are often 5+ MB. Scaling down keeps uploads quick on mobile data,
      // and the detectors work at well under this size anyway.
      final file = await _picker.pickImage(source: source, maxWidth: 2048, maxHeight: 2048, imageQuality: 85);
      if (file == null) return;
      final bytes = await file.readAsBytes();
      setState(() {
        _photo = bytes;
        _filename = file.name;
        _error = null;
      });
    } catch (_) {
      setState(() => _error = source == ImageSource.camera
          ? "Couldn't open the camera. Check that CivicLens is allowed to use it."
          : "Couldn't open that photo. Try another one.");
    }
  }

  Future<void> _analyze() async {
    final photo = _photo;
    if (photo == null) {
      setState(() => _error = 'Add a photo first.');
      return;
    }
    setState(() {
      _busy = true;
      _slow = false;
      _error = null;
    });
    // If the server was asleep, say so instead of looking stuck.
    final slowTimer = Timer(const Duration(seconds: 5), () {
      if (mounted) setState(() => _slow = true);
    });
    try {
      final report = await widget.api.analyze(
        photo: photo,
        filename: _filename,
        location: _location.text,
        notes: _notes.text,
        streetlightOut: _streetlightOut,
      );
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => ReportScreen(report: report, photo: photo)),
      );
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Something went wrong reading the result. Please try again.');
    } finally {
      slowTimer.cancel();
      if (mounted) {
        setState(() {
          _busy = false;
          _slow = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(
        title: const Row(children: [
          Icon(Icons.center_focus_strong, color: cyan),
          SizedBox(width: 10),
          Text('CivicLens', style: TextStyle(fontWeight: FontWeight.w700)),
        ]),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
          children: [
            Text('What needs fixing?', style: text.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Text(
              'Take a photo of a pothole, a cracked road or illegal dumping. '
              'CivicLens finds the problem and writes the report for your municipality.',
              style: text.bodyMedium?.copyWith(color: muted, height: 1.4),
            ),
            const SizedBox(height: 20),
            _PhotoArea(photo: _photo, onClear: _busy ? null : () => setState(() => _photo = null)),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: FilledButton.tonalIcon(
                  key: const Key('camera'),
                  onPressed: _busy ? null : () => _pick(ImageSource.camera),
                  icon: const Icon(Icons.photo_camera_outlined),
                  label: const Text('Take a photo'),
                  style: _buttonStyle,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  key: const Key('gallery'),
                  onPressed: _busy ? null : () => _pick(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library_outlined),
                  label: const Text('Choose photo'),
                  style: _buttonStyle,
                ),
              ),
            ]),
            const SizedBox(height: 20),
            TextField(
              controller: _location,
              enabled: !_busy,
              maxLength: 200,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(
                hintText: 'Location (optional)',
                prefixIcon: Icon(Icons.place_outlined),
                counterText: '',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _notes,
              enabled: !_busy,
              maxLength: 500,
              maxLines: 2,
              minLines: 1,
              decoration: const InputDecoration(
                hintText: 'Short note (optional)',
                prefixIcon: Icon(Icons.notes),
                counterText: '',
              ),
            ),
            const SizedBox(height: 4),
            CheckboxListTile(
              value: _streetlightOut,
              onChanged: _busy ? null : (v) => setState(() => _streetlightOut = v ?? false),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              title: const Text('This streetlight is not working'),
              subtitle: const Text("A photo can't show this, so tell us", style: TextStyle(color: muted)),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, key: const Key('error'), style: const TextStyle(color: Color(0xFFFDA4AF))),
            ],
            const SizedBox(height: 16),
            _AnalyzeButton(busy: _busy, slow: _slow, onPressed: _analyze),
          ],
        ),
      ),
    );
  }
}

final _buttonStyle = ButtonStyle(
  minimumSize: const WidgetStatePropertyAll(Size.fromHeight(52)),
  shape: WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
);

class _PhotoArea extends StatelessWidget {
  const _PhotoArea({required this.photo, required this.onClear});

  final Uint8List? photo;
  final VoidCallback? onClear;

  @override
  Widget build(BuildContext context) {
    final photo = this.photo;
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: Container(
        height: 260,
        decoration: BoxDecoration(
          color: panel,
          border: Border.all(color: cyan.withValues(alpha: .25)),
          borderRadius: BorderRadius.circular(20),
        ),
        child: photo == null
            ? const Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.add_a_photo_outlined, size: 40, color: cyan),
                  SizedBox(height: 12),
                  Text('No photo yet', style: TextStyle(fontWeight: FontWeight.w600)),
                  SizedBox(height: 4),
                  Text('Use the buttons below', style: TextStyle(color: muted)),
                ],
              )
            : Stack(fit: StackFit.expand, children: [
                Image.memory(photo, fit: BoxFit.cover),
                Positioned(
                  top: 10,
                  right: 10,
                  child: IconButton.filledTonal(
                    tooltip: 'Remove photo',
                    onPressed: onClear,
                    icon: const Icon(Icons.close),
                  ),
                ),
              ]),
      ),
    );
  }
}

class _AnalyzeButton extends StatelessWidget {
  const _AnalyzeButton({required this.busy, required this.slow, required this.onPressed});

  final bool busy;
  final bool slow;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [cyan, emerald]),
        borderRadius: BorderRadius.circular(14),
      ),
      child: TextButton(
        key: const Key('analyze'),
        onPressed: busy ? null : onPressed,
        style: TextButton.styleFrom(
          minimumSize: const Size.fromHeight(56),
          foregroundColor: ink,
          disabledForegroundColor: ink,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
        child: busy
            ? Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2.4, color: ink),
                ),
                const SizedBox(width: 12),
                Flexible(
                  child: Text(
                    slow ? 'Waking up the server, the first photo can take 30 seconds…' : 'Checking the photo…',
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              ])
            : const Text('Generate report', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
      ),
    );
  }
}
