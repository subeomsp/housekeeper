import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/format/date_format.dart';
import '../../../core/format/quantity_format.dart';
import '../../../core/widgets/async_view.dart';
import '../../inventory/presentation/event_display.dart';
import '../../inventory/presentation/inventory_providers.dart';
import '../domain/history_event.dart';
import 'event_correction_sheet.dart';
import 'history_providers.dart';

const _eventTypes = [
  'stock_in',
  'stock_out',
  'adjustment_in',
  'adjustment_out',
  'initial_stock',
  'event_reversal',
];

class HistoryPage extends ConsumerStatefulWidget {
  const HistoryPage({super.key});

  @override
  ConsumerState<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends ConsumerState<HistoryPage> {
  final _pendingEventIds = <String>{};

  void _refresh() {
    ref.invalidate(historyPageProvider);
    ref.invalidate(historyItemsProvider);
  }

  void _refreshAfterMutation(String itemId) {
    ref.invalidate(historyPageProvider);
    ref.invalidate(inventoryListProvider);
    ref.invalidate(inventoryDetailProvider(itemId));
  }

  Future<void> _correct(HistoryEvent event, String itemName) async {
    final message = await showEventCorrectionSheet(
      context: context,
      event: event,
      itemName: itemName,
    );
    if (message == null || !mounted) {
      return;
    }
    _refreshAfterMutation(event.itemId);
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _cancel(HistoryEvent event, String itemName) async {
    if (_pendingEventIds.contains(event.id)) {
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('이 기록을 취소할까요?'),
        content: Text(
          '$itemName ${eventTypeLabel(event.eventType)} '
          '${formatQuantity(event.quantity)} ${event.unit}\n\n'
          '원본은 삭제되지 않고 반대 수량의 되돌림 기록이 추가돼요.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('돌아가기'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('기록 취소'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) {
      return;
    }

    setState(() => _pendingEventIds.add(event.id));
    try {
      final result = await ref.read(historyApiProvider).cancelEvent(event.id);
      if (!mounted) {
        return;
      }
      _refreshAfterMutation(event.itemId);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${formatQuantity(result.currentQuantity)} ${event.unit}로 반영했어요.',
          ),
        ),
      );
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) {
        setState(() => _pendingEventIds.remove(event.id));
      }
    }
  }

  Future<void> _openFilters(
    HistoryFilters filters,
    List<HistoryItemReference> items,
  ) async {
    final selected = await showModalBottomSheet<HistoryFilters>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => _HistoryFilterSheet(filters: filters, items: items),
    );
    if (selected == null) {
      return;
    }
    ref
        .read(historyFiltersProvider.notifier)
        .apply(
          itemId: selected.itemId,
          eventType: selected.eventType,
          from: selected.from,
          to: selected.to,
        );
  }

  @override
  Widget build(BuildContext context) {
    final filters = ref.watch(historyFiltersProvider);
    final pageAsync = ref.watch(historyPageProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('기록'),
        actions: [
          IconButton(
            tooltip: '새로고침',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Column(
        children: [
          _FilterBar(
            filters: filters,
            pageAsync: pageAsync,
            onOpen: _openFilters,
            onClear: () => ref.read(historyFiltersProvider.notifier).clear(),
          ),
          const Divider(height: 1),
          Expanded(
            child: AsyncView<HistoryPageData>(
              value: pageAsync,
              onRetry: _refresh,
              isEmpty: (data) => data.page.items.isEmpty,
              emptyMessage: filters.activeCount > 0
                  ? '조건에 맞는 기록이 없어요.'
                  : '아직 재고 변경 기록이 없어요.',
              onData: (data) => RefreshIndicator(
                onRefresh: () async => _refresh(),
                child: ListView.separated(
                  physics: const AlwaysScrollableScrollPhysics(),
                  itemCount: data.page.items.length + 1,
                  separatorBuilder: (_, index) =>
                      index < data.page.items.length - 1
                      ? const Divider(height: 1)
                      : const SizedBox.shrink(),
                  itemBuilder: (context, index) {
                    if (index == data.page.items.length) {
                      return _Pagination(
                        total: data.page.total,
                        filters: filters,
                      );
                    }
                    final event = data.page.items[index];
                    final item = data.itemsById[event.itemId];
                    return _HistoryTile(
                      event: event,
                      itemName: item?.name ?? '알 수 없는 품목',
                      isPending: _pendingEventIds.contains(event.id),
                      onCorrect: () =>
                          _correct(event, item?.name ?? '알 수 없는 품목'),
                      onCancel: () => _cancel(event, item?.name ?? '알 수 없는 품목'),
                    );
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({
    required this.filters,
    required this.pageAsync,
    required this.onOpen,
    required this.onClear,
  });

  final HistoryFilters filters;
  final AsyncValue<HistoryPageData> pageAsync;
  final Future<void> Function(
    HistoryFilters filters,
    List<HistoryItemReference> items,
  )
  onOpen;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final data = pageAsync.value;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          FilledButton.tonalIcon(
            onPressed: data == null
                ? null
                : () => onOpen(filters, data.itemsById.values.toList()),
            icon: const Icon(Icons.filter_list),
            label: Text(
              filters.activeCount == 0 ? '필터' : '필터 ${filters.activeCount}',
            ),
          ),
          if (filters.activeCount > 0) ...[
            const SizedBox(width: 8),
            TextButton(onPressed: onClear, child: const Text('초기화')),
          ],
          const Spacer(),
          if (data != null)
            Text(
              '총 ${data.page.total}건',
              style: Theme.of(context).textTheme.bodySmall,
            ),
        ],
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({
    required this.event,
    required this.itemName,
    required this.isPending,
    required this.onCorrect,
    required this.onCancel,
  });

  final HistoryEvent event;
  final String itemName;
  final bool isPending;
  final VoidCallback onCorrect;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    final color = eventDeltaColor(event.signedQuantity, context);
    final details = [
      eventTypeLabel(event.eventType),
      _sourceLabel(event.source),
      formatDateTime(event.createdAt),
      if (event.note != null) event.note!,
    ].join(' · ');

    return ListTile(
      leading: isPending
          ? const SizedBox.square(
              dimension: 24,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Icon(
              event.signedQuantity >= 0
                  ? Icons.add_circle_outline
                  : Icons.remove_circle_outline,
              color: color,
            ),
      title: Text(itemName),
      subtitle: Text(details, maxLines: 2, overflow: TextOverflow.ellipsis),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '${signedPrefix(event.signedQuantity)}'
            '${formatQuantity(event.signedQuantity)} ${event.unit}',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (!event.isReversal)
            PopupMenuButton<_HistoryAction>(
              enabled: !isPending,
              tooltip: '기록 관리',
              onSelected: (action) {
                switch (action) {
                  case _HistoryAction.correct:
                    onCorrect();
                    break;
                  case _HistoryAction.cancel:
                    onCancel();
                    break;
                }
              },
              itemBuilder: (_) => const [
                PopupMenuItem(value: _HistoryAction.correct, child: Text('정정')),
                PopupMenuItem(value: _HistoryAction.cancel, child: Text('취소')),
              ],
            ),
        ],
      ),
    );
  }
}

enum _HistoryAction { correct, cancel }

String _sourceLabel(String source) {
  return switch (source) {
    'manual' => '수동',
    'voice' => '음성',
    'system' => '시스템',
    'correction' => '정정',
    _ => source,
  };
}

class _Pagination extends ConsumerWidget {
  const _Pagination({required this.total, required this.filters});

  final int total;
  final HistoryFilters filters;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final page = filters.offset ~/ historyPageSize + 1;
    final pageCount = total == 0 ? 1 : ((total - 1) ~/ historyPageSize) + 1;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          IconButton(
            tooltip: '이전 페이지',
            onPressed: filters.offset > 0
                ? ref.read(historyFiltersProvider.notifier).previousPage
                : null,
            icon: const Icon(Icons.chevron_left),
          ),
          Text('$page / $pageCount'),
          IconButton(
            tooltip: '다음 페이지',
            onPressed: filters.offset + historyPageSize < total
                ? ref.read(historyFiltersProvider.notifier).nextPage
                : null,
            icon: const Icon(Icons.chevron_right),
          ),
        ],
      ),
    );
  }
}

class _HistoryFilterSheet extends StatefulWidget {
  const _HistoryFilterSheet({required this.filters, required this.items});

  final HistoryFilters filters;
  final List<HistoryItemReference> items;

  @override
  State<_HistoryFilterSheet> createState() => _HistoryFilterSheetState();
}

class _HistoryFilterSheetState extends State<_HistoryFilterSheet> {
  late String? _itemId;
  late String? _eventType;
  late DateTimeRange? _dateRange;

  @override
  void initState() {
    super.initState();
    _itemId = widget.filters.itemId;
    _eventType = widget.filters.eventType;
    _dateRange = widget.filters.from == null
        ? null
        : DateTimeRange(
            start: widget.filters.from!.toLocal(),
            end: widget.filters.to!.toLocal(),
          );
  }

  Future<void> _pickDateRange() async {
    final now = DateTime.now();
    final selected = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime(now.year + 1, 12, 31),
      initialDateRange: _dateRange,
    );
    if (selected != null) {
      setState(() => _dateRange = selected);
    }
  }

  void _apply() {
    final start = _dateRange?.start;
    final end = _dateRange == null
        ? null
        : DateTime(
            _dateRange!.end.year,
            _dateRange!.end.month,
            _dateRange!.end.day,
            23,
            59,
            59,
            999,
          );
    Navigator.of(context).pop(
      HistoryFilters(
        itemId: _itemId,
        eventType: _eventType,
        from: start,
        to: end,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = [...widget.items]
      ..sort((left, right) => left.name.compareTo(right.name));
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('기록 필터', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 20),
          DropdownButtonFormField<String?>(
            value: _itemId,
            decoration: const InputDecoration(
              labelText: '품목',
              border: OutlineInputBorder(),
            ),
            items: [
              const DropdownMenuItem(value: null, child: Text('전체 품목')),
              ...items.map(
                (item) => DropdownMenuItem(
                  value: item.id,
                  child: Text(item.isActive ? item.name : '${item.name} (보관됨)'),
                ),
              ),
            ],
            onChanged: (value) => setState(() => _itemId = value),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String?>(
            value: _eventType,
            decoration: const InputDecoration(
              labelText: '기록 유형',
              border: OutlineInputBorder(),
            ),
            items: [
              const DropdownMenuItem(value: null, child: Text('전체 유형')),
              ..._eventTypes.map(
                (type) => DropdownMenuItem(
                  value: type,
                  child: Text(eventTypeLabel(type)),
                ),
              ),
            ],
            onChanged: (value) => setState(() => _eventType = value),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _pickDateRange,
            icon: const Icon(Icons.date_range),
            label: Text(
              _dateRange == null
                  ? '기간 선택'
                  : '${_formatDate(_dateRange!.start)}'
                        ' ~ ${_formatDate(_dateRange!.end)}',
            ),
          ),
          if (_dateRange != null)
            TextButton(
              onPressed: () => setState(() => _dateRange = null),
              child: const Text('기간 지우기'),
            ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _apply, child: const Text('필터 적용')),
        ],
      ),
    );
  }
}

String _formatDate(DateTime date) {
  return '${date.year}.${date.month.toString().padLeft(2, '0')}.'
      '${date.day.toString().padLeft(2, '0')}';
}
