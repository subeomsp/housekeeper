import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Home tab. In later phases this becomes the voice-entry launcher; for now it
/// is a simple landing screen pointing at the inventory list.
class HomePage extends StatelessWidget {
  const HomePage({super.key});

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
          ],
        ),
      ),
    );
  }
}
