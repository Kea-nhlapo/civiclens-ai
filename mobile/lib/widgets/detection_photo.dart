import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../models.dart';

const _categoryColours = {
  'pothole': Color(0xFFFDBA74),
  'crack': Color(0xFFFCD34D),
  'streetlight': Color(0xFF67E8F9),
  'dumping': Color(0xFFFDA4AF),
};

/// The photo with a box around everything the detectors found.
class DetectionPhoto extends StatelessWidget {
  const DetectionPhoto({super.key, required this.photo, required this.detections});

  final Uint8List photo;
  final List<Detection> detections;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      // The boxes are fractions of the image, so the photo is shown whole (no cropping)
      // and the painter is laid over exactly the same area.
      child: Stack(children: [
        Image.memory(photo, width: double.infinity, fit: BoxFit.fitWidth),
        Positioned.fill(child: CustomPaint(painter: _BoxPainter(detections))),
      ]),
    );
  }
}

class _BoxPainter extends CustomPainter {
  _BoxPainter(this.detections);

  final List<Detection> detections;

  @override
  void paint(Canvas canvas, Size size) {
    for (final d in detections) {
      final colour = _categoryColours[d.category] ?? Colors.white;
      final rect = Rect.fromLTRB(d.x1 * size.width, d.y1 * size.height, d.x2 * size.width, d.y2 * size.height);
      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(6)),
        Paint()
          ..color = colour
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.5,
      );
      final label = TextPainter(
        text: TextSpan(
          text: ' ${d.label} ${(d.confidence * 100).round()}% ',
          style: TextStyle(color: const Color(0xFF07111F), backgroundColor: colour, fontSize: 11, fontWeight: FontWeight.w700),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: size.width);
      final top = rect.top - label.height < 0 ? rect.top : rect.top - label.height;
      final left = rect.left.clamp(0.0, math.max(0.0, size.width - label.width));
      label.paint(canvas, Offset(left, top));
    }
  }

  @override
  bool shouldRepaint(_BoxPainter old) => old.detections != detections;
}
