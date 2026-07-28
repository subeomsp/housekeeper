import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/inventory/data/inventory_item_api.dart';
import 'package:voice_inventory/features/inventory/domain/inventory_catalog_item.dart';
import 'package:voice_inventory/features/inventory/presentation/archived_inventory_items_page.dart';
import 'package:voice_inventory/features/inventory/presentation/inventory_providers.dart';

void main() {
  testWidgets('archived item can be restored from the archive list', (
    tester,
  ) async {
    const archived = InventoryCatalogItem(
      id: 'item-id',
      name: '우유',
      unit: '개',
      category: null,
      isActive: false,
      currentQuantity: 0,
    );
    final api = _FakeInventoryItemApi();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          inventoryItemApiProvider.overrideWithValue(api),
          archivedInventoryItemsProvider.overrideWith(
            (ref) async => const [archived],
          ),
        ],
        child: const MaterialApp(home: ArchivedInventoryItemsPage()),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('복원'));
    await tester.pumpAndSettle();

    expect(api.restoredItemId, 'item-id');
    expect(find.textContaining('복원했어요'), findsOneWidget);
  });
}

class _FakeInventoryItemApi extends InventoryItemApi {
  _FakeInventoryItemApi() : super(Dio());

  String? restoredItemId;

  @override
  Future<InventoryCatalogItem> restoreItem(String itemId) async {
    restoredItemId = itemId;
    return const InventoryCatalogItem(
      id: 'item-id',
      name: '우유',
      unit: '개',
      category: null,
      isActive: true,
      currentQuantity: 0,
    );
  }
}
