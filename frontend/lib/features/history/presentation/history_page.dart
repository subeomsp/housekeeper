import 'package:flutter/material.dart';

/// 기록 tab — Inventory Event history. Implemented in step 2-4.
class HistoryPage extends StatelessWidget {
  const HistoryPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('기록')),
      body: const Center(child: Text('기록 화면은 준비 중이에요.')),
    );
  }
}
