import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_exception.dart';
import '../../action_plan/presentation/action_plan_providers.dart';

/// Home tab. In later phases this becomes the voice-entry launcher; for now it
/// is a simple landing screen pointing at the inventory list.
class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  bool _planning = false;

  Future<void> _startTextPlan() async {
    if (_planning) return;
    final controller = TextEditingController();
    final transcript = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('텍스트로 음성 흐름 테스트'),
        content: TextField(
          controller: controller,
          autofocus: true,
          minLines: 2,
          maxLines: 4,
          decoration: const InputDecoration(
            hintText: '예: 우유 두 개 사왔어.',
            labelText: '말한 내용',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () {
              final value = controller.text.trim();
              if (value.isNotEmpty) Navigator.of(dialogContext).pop(value);
            },
            child: const Text('Plan 만들기'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (transcript == null || !mounted) return;

    setState(() => _planning = true);
    try {
      final plan = await ref
          .read(actionPlanApiProvider)
          .createFromTranscript(transcript);
      if (mounted) context.push('/action-plan/${plan.requestId}');
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _planning = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('홈')),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.kitchen_outlined, size: 64),
            const SizedBox(height: 12),
            const Text('재고를 확인하고 기록해 보세요.'),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: () => context.go('/inventory'),
              icon: const Icon(Icons.inventory_2),
              label: const Text('재고 보기'),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _planning ? null : _startTextPlan,
              icon: _planning
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.mic_none),
              label: Text(_planning ? 'Plan 생성 중' : '텍스트로 음성 흐름 테스트'),
            ),
          ],
        ),
      ),
    );
  }
}
