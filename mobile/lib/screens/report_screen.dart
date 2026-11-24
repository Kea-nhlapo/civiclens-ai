import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../models.dart';
import '../theme.dart';
import '../widgets/detection_photo.dart';

class ReportScreen extends StatelessWidget {
  const ReportScreen({super.key, required this.report, required this.photo});

  final Report report;
  final Uint8List photo;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final r = report.municipalReport;
    final colour = severityColor(report.severity);
    return Scaffold(
      appBar: AppBar(title: const Text('Report')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 32),
          children: [
            DetectionPhoto(photo: photo, detections: report.detections),
            const SizedBox(height: 18),
            if (report.foundSomething)
              Wrap(spacing: 8, runSpacing: 8, children: [
                _Chip(label: '${report.severity} severity', colour: colour, icon: Icons.warning_amber_rounded),
                _Chip(label: '${(report.confidence * 100).round()}% confidence', colour: cyan, icon: Icons.speed),
              ]),
            const SizedBox(height: 12),
            Text(report.issueType, style: text.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            Text(report.summary, style: text.bodyLarge?.copyWith(height: 1.45)),
            // The summary usually already explains the severity, so only add the reason when it doesn't.
            if (report.severityReason.isNotEmpty && !report.summary.contains(report.severityReason)) ...[
              const SizedBox(height: 8),
              Text('Why ${report.severity}: ${report.severityReason}', style: const TextStyle(color: muted, height: 1.4)),
            ],
            if (report.issues.length > 1) ...[
              const SizedBox(height: 14),
              const Text('Also in this photo', style: TextStyle(fontWeight: FontWeight.w700)),
              for (final issue in report.issues.skip(1))
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text('• ${issue.issueType}, ${issue.severity.toLowerCase()} priority, for ${issue.department}',
                      style: const TextStyle(color: muted)),
                ),
            ],
            const SizedBox(height: 18),
            _Section(icon: Icons.account_balance_outlined, title: 'Who handles it', body: report.department),
            _Section(icon: Icons.build_outlined, title: 'What to do', body: report.recommendedAction),
            if (report.foundSomething) ...[
              const SizedBox(height: 6),
              _MunicipalReportCard(report: r),
            ],
            if (report.nextSteps.isNotEmpty) ...[
              const SizedBox(height: 18),
              const Text('Next steps', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
              for (final (i, step) in report.nextSteps.indexed)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    CircleAvatar(
                      radius: 11,
                      backgroundColor: cyan.withValues(alpha: .15),
                      child: Text('${i + 1}', style: const TextStyle(fontSize: 12, color: cyan)),
                    ),
                    const SizedBox(width: 10),
                    Expanded(child: Text(step, style: const TextStyle(height: 1.4))),
                  ]),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _MunicipalReportCard extends StatelessWidget {
  const _MunicipalReportCard({required this.report});

  final MunicipalReport report;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('REPORT FOR THE MUNICIPALITY',
              style: TextStyle(color: cyan, fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 1.2)),
          const SizedBox(height: 10),
          Text(report.title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
          const SizedBox(height: 6),
          Text(report.description, style: const TextStyle(height: 1.45)),
          const SizedBox(height: 10),
          Text('Location: ${report.location}', style: const TextStyle(color: muted)),
          Text('Priority: ${report.priority}', style: const TextStyle(color: muted)),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(
              child: FilledButton.icon(
                key: const Key('share'),
                onPressed: () => SharePlus.instance.share(ShareParams(text: report.asText(), subject: report.title)),
                icon: const Icon(Icons.share_outlined),
                label: const Text('Share'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: OutlinedButton.icon(
                key: const Key('copy'),
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: report.asText()));
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Report copied')));
                  }
                },
                icon: const Icon(Icons.copy),
                label: const Text('Copy'),
              ),
            ),
          ]),
        ]),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.icon, required this.title, required this.body});

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: cyan, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 2),
            Text(body, style: const TextStyle(color: muted, height: 1.4)),
          ]),
        ),
      ]),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.colour, required this.icon});

  final String label;
  final Color colour;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: colour.withValues(alpha: .12),
        border: Border.all(color: colour.withValues(alpha: .35)),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 15, color: colour),
        const SizedBox(width: 6),
        Text(label, style: TextStyle(color: colour, fontWeight: FontWeight.w700, fontSize: 12)),
      ]),
    );
  }
}
