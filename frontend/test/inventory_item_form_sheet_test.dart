import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/inventory/domain/inventory_detail.dart';
import 'package:voice_inventory/features/inventory/presentation/inventory_item_form_sheet.dart';

void main() {
  test('required item text rejects blank values', () {
    expect(validateRequiredItemText('  ', label: '품목명'), isNotNull);
    expect(validateRequiredItemText('우유', label: '품목명'), isNull);
  });

  testWidgets('new item form starts with the reviewed default unit', (
    tester,
  ) async {
    await tester.pumpWidget(_host(existing: null));
    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();

    expect(find.text('새 품목 추가'), findsOneWidget);
    final fields = tester.widgetList<TextFormField>(find.byType(TextFormField));
    expect(fields.elementAt(1).controller?.text, '개');
  });

  testWidgets('editing with stock explains and locks unit changes', (
    tester,
  ) async {
    final detail = InventoryDetail(
      itemId: 'item-id',
      name: '우유',
      quantity: 2,
      unit: '개',
      category: '음료',
      isActive: true,
      updatedAt: DateTime.utc(2026, 7, 28),
      recentEvents: const [],
    );
    await tester.pumpWidget(_host(existing: detail));
    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();

    expect(find.text('품목 정보 수정'), findsOneWidget);
    expect(find.textContaining('현재 수량이 0일 때만'), findsOneWidget);
    final fields = tester.widgetList<TextFormField>(find.byType(TextFormField));
    expect(fields.elementAt(1).enabled, isFalse);
  });
}

Widget _host({required InventoryDetail? existing}) {
  return ProviderScope(
    child: MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) => TextButton(
            onPressed: () => showInventoryItemFormSheet(
              context: context,
              existing: existing,
            ),
            child: const Text('열기'),
          ),
        ),
      ),
    ),
  );
}
