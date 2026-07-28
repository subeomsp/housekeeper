import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_providers.dart';
import '../data/inventory_api.dart';
import '../data/inventory_item_api.dart';
import '../domain/inventory_catalog_item.dart';
import '../domain/inventory_detail.dart';
import '../domain/inventory_item.dart';

/// Inventory API client, wired to the shared Dio instance.
final inventoryApiProvider = Provider<InventoryApi>((ref) {
  return InventoryApi(ref.watch(dioProvider));
});

final inventoryItemApiProvider = Provider<InventoryItemApi>((ref) {
  return InventoryItemApi(ref.watch(dioProvider));
});

const inventoryPageSize = 50;

enum InventorySortOption {
  recentlyUpdated('updated_at', 'desc'),
  name('name', 'asc'),
  quantityDesc('quantity', 'desc'),
  quantityAsc('quantity', 'asc');

  const InventorySortOption(this.apiSort, this.apiOrder);

  final String apiSort;
  final String apiOrder;
}

class InventoryFilters {
  const InventoryFilters({
    this.search = '',
    this.category,
    this.includeZero = true,
    this.sort = InventorySortOption.recentlyUpdated,
    this.offset = 0,
  });

  final String search;
  final String? category;
  final bool includeZero;
  final InventorySortOption sort;
  final int offset;

  int get activeCount =>
      (category == null ? 0 : 1) +
      (includeZero ? 0 : 1) +
      (sort == InventorySortOption.recentlyUpdated ? 0 : 1);
}

class InventoryFiltersNotifier extends Notifier<InventoryFilters> {
  @override
  InventoryFilters build() => const InventoryFilters();

  void setSearch(String value) {
    state = InventoryFilters(
      search: value,
      category: state.category,
      includeZero: state.includeZero,
      sort: state.sort,
    );
  }

  void apply({
    String? category,
    required bool includeZero,
    required InventorySortOption sort,
  }) {
    state = InventoryFilters(
      search: state.search,
      category: category,
      includeZero: includeZero,
      sort: sort,
    );
  }

  void clearControls() {
    state = InventoryFilters(search: state.search);
  }

  void nextPage() {
    state = InventoryFilters(
      search: state.search,
      category: state.category,
      includeZero: state.includeZero,
      sort: state.sort,
      offset: state.offset + inventoryPageSize,
    );
  }

  void previousPage() {
    state = InventoryFilters(
      search: state.search,
      category: state.category,
      includeZero: state.includeZero,
      sort: state.sort,
      offset: state.offset >= inventoryPageSize
          ? state.offset - inventoryPageSize
          : 0,
    );
  }
}

final inventoryFiltersProvider =
    NotifierProvider<InventoryFiltersNotifier, InventoryFilters>(
      InventoryFiltersNotifier.new,
    );

/// Current inventory list. Re-fetches whenever search/filter/page changes.
/// `ref.invalidate(inventoryListProvider)` drives manual/pull-to-refresh.
final inventoryListProvider = FutureProvider<InventoryPage>((ref) async {
  final filters = ref.watch(inventoryFiltersProvider);
  final api = ref.watch(inventoryApiProvider);
  return api.fetchInventory(
    search: filters.search,
    category: filters.category,
    includeZero: filters.includeZero,
    sort: filters.sort.apiSort,
    order: filters.sort.apiOrder,
    limit: inventoryPageSize,
    offset: filters.offset,
  );
});

/// Item detail (Snapshot + recent events) for a given item id.
final inventoryDetailProvider = FutureProvider.family<InventoryDetail, String>((
  ref,
  itemId,
) async {
  final api = ref.watch(inventoryApiProvider);
  return api.fetchDetail(itemId);
});

final archivedInventoryItemsProvider =
    FutureProvider<List<InventoryCatalogItem>>((ref) async {
      final items = await ref.watch(inventoryItemApiProvider).fetchAllItems();
      return items.where((item) => !item.isActive).toList(growable: false);
    });
