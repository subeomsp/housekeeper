import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/inventory/domain/inventory_detail.dart';
import 'package:voice_inventory/features/inventory/presentation/inventory_detail_page.dart';
import 'package:voice_inventory/features/inventory/presentation/inventory_providers.dart';

void main() {
  testWidgets('item with stock explains why it cannot be archived', (
    tester,
  ) async {
    final detail = InventoryDetail(
      itemId: 'item-id',
      name: '우유',
      quantity: 2,
      unit: '개',
      category: null,
      isActive: true,
      updatedAt: DateTime.utc(2026, 7, 28),
      recentEvents: const [],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          inventoryDetailProvider(
            'item-id',
          ).overrideWith((ref) async => detail),
        ],
        child: const MaterialApp(home: InventoryDetailPage(itemId: 'item-id')),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('품목 보관'));
    await tester.pump();

    expect(find.textContaining('현재 수량을 0으로 설정'), findsOneWidget);
  });

  testWidgets('zero-stock archive confirmation explains soft delete', (
    tester,
  ) async {
    final detail = InventoryDetail(
      itemId: 'item-id',
      name: '우유',
      quantity: 0,
      unit: '개',
      category: null,
      isActive: true,
      updatedAt: DateTime.utc(2026, 7, 28),
      recentEvents: const [],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          inventoryDetailProvider(
            'item-id',
          ).overrideWith((ref) async => detail),
        ],
        child: const MaterialApp(home: InventoryDetailPage(itemId: 'item-id')),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('품목 보관'));
    await tester.pumpAndSettle();

    expect(find.text('이 품목을 보관할까요?'), findsOneWidget);
    expect(find.textContaining('Snapshot과 기존 기록은 삭제되지'), findsOneWidget);
  });
}
