import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/inventory/domain/inventory_item.dart';
import 'package:voice_inventory/features/inventory/presentation/inventory_list_page.dart';
import 'package:voice_inventory/features/inventory/presentation/inventory_providers.dart';

void main() {
  testWidgets(
    'inventory search, filters, sorting, and pagination update state',
    (tester) async {
      final container = ProviderContainer(
        overrides: [
          inventoryListProvider.overrideWith(
            (ref) async => InventoryPage(
              items: [
                InventoryItem(
                  itemId: 'item-id',
                  name: '우유',
                  quantity: 2,
                  unit: '개',
                  category: '음료',
                  isActive: true,
                  updatedAt: DateTime.utc(2026, 7, 28),
                ),
              ],
              total: 51,
            ),
          ),
        ],
      );
      addTearDown(container.dispose);
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(home: InventoryListPage()),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField).first, '우유');
      await tester.testTextInput.receiveAction(TextInputAction.search);
      await tester.pump();
      expect(container.read(inventoryFiltersProvider).search, '우유');

      await tester.tap(find.text('필터·정렬'));
      await tester.pumpAndSettle();
      await tester.enterText(find.widgetWithText(TextField, '카테고리 (선택)'), '음료');
      await tester.tap(find.text('수량 0인 품목 포함'));
      await tester.tap(find.text('최근 변경순'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('이름순').last);
      await tester.pumpAndSettle();
      await tester.tap(find.text('적용'));
      await tester.pumpAndSettle();

      var filters = container.read(inventoryFiltersProvider);
      expect(filters.category, '음료');
      expect(filters.includeZero, isFalse);
      expect(filters.sort, InventorySortOption.name);
      expect(find.text('필터·정렬 3'), findsOneWidget);

      await tester.tap(find.byTooltip('다음 페이지'));
      await tester.pump();
      filters = container.read(inventoryFiltersProvider);
      expect(filters.offset, inventoryPageSize);
    },
  );
}
