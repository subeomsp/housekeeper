import 'package:flutter/material.dart';

/// Item detail + recent events. Implemented in step 2-2; placeholder for now.
class InventoryDetailPage extends StatelessWidget {
  const InventoryDetailPage({super.key, required this.itemId});

  final String itemId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('품목 상세')),
      body: Center(child: Text('품목 상세 화면 준비 중\n($itemId)', textAlign: TextAlign.center)),
    );
  }
}
