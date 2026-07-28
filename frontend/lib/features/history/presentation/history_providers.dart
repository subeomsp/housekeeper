import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_providers.dart';
import '../data/history_api.dart';
import '../domain/history_event.dart';

const historyPageSize = 50;

class HistoryFilters {
  const HistoryFilters({
    this.itemId,
    this.eventType,
    this.from,
    this.to,
    this.offset = 0,
  });

  final String? itemId;
  final String? eventType;
  final DateTime? from;
  final DateTime? to;
  final int offset;

  int get activeCount =>
      [itemId, eventType, from].where((value) => value != null).length;
}

class HistoryFiltersNotifier extends Notifier<HistoryFilters> {
  @override
  HistoryFilters build() => const HistoryFilters();

  void apply({
    String? itemId,
    String? eventType,
    DateTime? from,
    DateTime? to,
  }) {
    state = HistoryFilters(
      itemId: itemId,
      eventType: eventType,
      from: from,
      to: to,
    );
  }

  void clear() => state = const HistoryFilters();

  void nextPage() {
    state = HistoryFilters(
      itemId: state.itemId,
      eventType: state.eventType,
      from: state.from,
      to: state.to,
      offset: state.offset + historyPageSize,
    );
  }

  void previousPage() {
    state = HistoryFilters(
      itemId: state.itemId,
      eventType: state.eventType,
      from: state.from,
      to: state.to,
      offset: state.offset >= historyPageSize
          ? state.offset - historyPageSize
          : 0,
    );
  }
}

final historyApiProvider = Provider<HistoryApi>((ref) {
  return HistoryApi(ref.watch(dioProvider));
});

final historyFiltersProvider =
    NotifierProvider<HistoryFiltersNotifier, HistoryFilters>(
      HistoryFiltersNotifier.new,
    );

final historyItemsProvider = FutureProvider<List<HistoryItemReference>>((
  ref,
) async {
  return ref.watch(historyApiProvider).fetchAllItems();
});

class HistoryPageData {
  const HistoryPageData({required this.page, required this.itemsById});

  final HistoryEventPage page;
  final Map<String, HistoryItemReference> itemsById;
}

final historyPageProvider = FutureProvider<HistoryPageData>((ref) async {
  final filters = ref.watch(historyFiltersProvider);
  final api = ref.watch(historyApiProvider);
  final items = await ref.watch(historyItemsProvider.future);
  final page = await api.fetchEvents(
    itemId: filters.itemId,
    eventType: filters.eventType,
    from: filters.from,
    to: filters.to,
    limit: historyPageSize,
    offset: filters.offset,
  );
  return HistoryPageData(
    page: page,
    itemsById: {for (final item in items) item.id: item},
  );
});
