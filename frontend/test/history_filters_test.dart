import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/history/presentation/history_providers.dart';

void main() {
  test('history filters reset pagination when applied or cleared', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final notifier = container.read(historyFiltersProvider.notifier);

    notifier.nextPage();
    expect(container.read(historyFiltersProvider).offset, historyPageSize);

    notifier.apply(itemId: 'item-id', eventType: 'stock_in');
    final filtered = container.read(historyFiltersProvider);
    expect(filtered.itemId, 'item-id');
    expect(filtered.eventType, 'stock_in');
    expect(filtered.offset, 0);
    expect(filtered.activeCount, 2);

    notifier.clear();
    final cleared = container.read(historyFiltersProvider);
    expect(cleared.activeCount, 0);
    expect(cleared.offset, 0);
  });
}
