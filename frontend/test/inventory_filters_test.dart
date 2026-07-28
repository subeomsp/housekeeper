import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/inventory/presentation/inventory_providers.dart';

void main() {
  test(
    'inventory controls reset pagination and preserve search independently',
    () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(inventoryFiltersProvider.notifier);

      notifier.nextPage();
      expect(
        container.read(inventoryFiltersProvider).offset,
        inventoryPageSize,
      );

      notifier.setSearch('우유');
      var filters = container.read(inventoryFiltersProvider);
      expect(filters.search, '우유');
      expect(filters.offset, 0);

      notifier.apply(
        category: '음료',
        includeZero: false,
        sort: InventorySortOption.name,
      );
      filters = container.read(inventoryFiltersProvider);
      expect(filters.search, '우유');
      expect(filters.category, '음료');
      expect(filters.includeZero, isFalse);
      expect(filters.sort, InventorySortOption.name);
      expect(filters.activeCount, 3);
      expect(filters.offset, 0);

      notifier.clearControls();
      filters = container.read(inventoryFiltersProvider);
      expect(filters.search, '우유');
      expect(filters.category, isNull);
      expect(filters.includeZero, isTrue);
      expect(filters.sort, InventorySortOption.recentlyUpdated);
    },
  );
}
