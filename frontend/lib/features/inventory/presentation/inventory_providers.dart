import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_providers.dart';
import '../data/inventory_api.dart';
import '../domain/inventory_detail.dart';
import '../domain/inventory_item.dart';

/// Inventory API client, wired to the shared Dio instance.
final inventoryApiProvider = Provider<InventoryApi>((ref) {
  return InventoryApi(ref.watch(dioProvider));
});

/// Free-text search filter for the inventory list.
class InventorySearchNotifier extends Notifier<String> {
  @override
  String build() => '';

  void set(String value) => state = value;
}

final inventorySearchProvider =
    NotifierProvider<InventorySearchNotifier, String>(
  InventorySearchNotifier.new,
);

/// Current inventory list. Re-fetches whenever the search filter changes.
/// `ref.invalidate(inventoryListProvider)` drives manual/pull-to-refresh.
final inventoryListProvider = FutureProvider<InventoryPage>((ref) async {
  final search = ref.watch(inventorySearchProvider);
  final api = ref.watch(inventoryApiProvider);
  return api.fetchInventory(search: search);
});

/// Item detail (Snapshot + recent events) for a given item id.
final inventoryDetailProvider =
    FutureProvider.family<InventoryDetail, String>((ref, itemId) async {
  final api = ref.watch(inventoryApiProvider);
  return api.fetchDetail(itemId);
});
