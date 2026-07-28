import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/format/quantity_format.dart';
import '../../../core/widgets/async_view.dart';
import '../../history/presentation/history_providers.dart';
import '../domain/inventory_item.dart';
import 'inventory_item_form_sheet.dart';
import 'inventory_providers.dart';
import 'inventory_quantity_sheet.dart';

/// Current inventory list (spec §68.6). Reads Snapshot quantities via the API,
/// supports search, manual refresh, and taps through to item detail.
class InventoryListPage extends ConsumerWidget {
  const InventoryListPage({super.key});

  Future<void> _createItem(BuildContext context, WidgetRef ref) async {
    final item = await showInventoryItemFormSheet(context: context);
    if (item == null || !context.mounted) {
      return;
    }
    ref.invalidate(inventoryListProvider);
    ref.invalidate(archivedInventoryItemsProvider);
    ref.invalidate(historyItemsProvider);
    ref.invalidate(historyPageProvider);
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('${item.name}을(를) 추가했어요.')));
  }

  Future<void> _openFilters(
    BuildContext context,
    WidgetRef ref,
    InventoryFilters filters,
  ) async {
    final selected = await showModalBottomSheet<InventoryFilters>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => _InventoryFilterSheet(filters: filters),
    );
    if (selected == null) {
      return;
    }
    ref
        .read(inventoryFiltersProvider.notifier)
        .apply(
          category: selected.category,
          includeZero: selected.includeZero,
          sort: selected.sort,
        );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(inventoryFiltersProvider);
    final listAsync = ref.watch(inventoryListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('재고'),
        actions: [
          IconButton(
            tooltip: '보관된 품목',
            onPressed: () => context.push('/inventory/archived'),
            icon: const Icon(Icons.inventory_2_outlined),
          ),
          IconButton(
            tooltip: '새로고침',
            onPressed: () => ref.invalidate(inventoryListProvider),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _createItem(context, ref),
        icon: const Icon(Icons.add),
        label: const Text('품목 추가'),
      ),
      body: Column(
        children: [
          const _SearchField(),
          _InventoryFilterBar(
            filters: filters,
            pageAsync: listAsync,
            onOpen: () => _openFilters(context, ref, filters),
            onClear: () =>
                ref.read(inventoryFiltersProvider.notifier).clearControls(),
          ),
          const Divider(height: 1),
          Expanded(
            child: AsyncView<InventoryPage>(
              value: listAsync,
              onRetry: () => ref.invalidate(inventoryListProvider),
              isEmpty: (page) => page.items.isEmpty,
              emptyMessage: filters.search.isNotEmpty || filters.activeCount > 0
                  ? '조건에 맞는 재고가 없어요.'
                  : '등록된 재고가 없어요.',
              onData: (page) => RefreshIndicator(
                onRefresh: () async => ref.invalidate(inventoryListProvider),
                child: ListView.separated(
                  physics: const AlwaysScrollableScrollPhysics(),
                  itemCount: page.items.length + 1,
                  separatorBuilder: (_, index) => index < page.items.length - 1
                      ? const Divider(height: 1)
                      : const SizedBox.shrink(),
                  itemBuilder: (context, index) {
                    if (index == page.items.length) {
                      return _InventoryPagination(
                        filters: filters,
                        total: page.total,
                      );
                    }
                    return _InventoryTile(item: page.items[index]);
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

class _SearchField extends ConsumerStatefulWidget {
  const _SearchField();

  @override
  ConsumerState<_SearchField> createState() => _SearchFieldState();
}

class _SearchFieldState extends ConsumerState<_SearchField> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(
      text: ref.read(inventoryFiltersProvider).search,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: TextField(
        controller: _controller,
        textInputAction: TextInputAction.search,
        decoration: InputDecoration(
          hintText: '품목 검색',
          prefixIcon: const Icon(Icons.search),
          border: const OutlineInputBorder(),
          isDense: true,
          suffixIcon: _controller.text.isEmpty
              ? null
              : IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () {
                    _controller.clear();
                    ref.read(inventoryFiltersProvider.notifier).setSearch('');
                  },
                ),
        ),
        onChanged: (value) => setState(() {}),
        onSubmitted: (value) =>
            ref.read(inventoryFiltersProvider.notifier).setSearch(value.trim()),
      ),
    );
  }
}

class _InventoryFilterBar extends StatelessWidget {
  const _InventoryFilterBar({
    required this.filters,
    required this.pageAsync,
    required this.onOpen,
    required this.onClear,
  });

  final InventoryFilters filters;
  final AsyncValue<InventoryPage> pageAsync;
  final VoidCallback onOpen;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final page = pageAsync.value;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      child: Row(
        children: [
          FilledButton.tonalIcon(
            onPressed: onOpen,
            icon: const Icon(Icons.tune),
            label: Text(
              filters.activeCount == 0
                  ? '필터·정렬'
                  : '필터·정렬 ${filters.activeCount}',
            ),
          ),
          if (filters.activeCount > 0) ...[
            const SizedBox(width: 8),
            TextButton(onPressed: onClear, child: const Text('초기화')),
          ],
          const Spacer(),
          if (page != null)
            Text(
              '총 ${page.total}개',
              style: Theme.of(context).textTheme.bodySmall,
            ),
        ],
      ),
    );
  }
}

class _InventoryPagination extends ConsumerWidget {
  const _InventoryPagination({required this.filters, required this.total});

  final InventoryFilters filters;
  final int total;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final page = filters.offset ~/ inventoryPageSize + 1;
    final pageCount = total == 0 ? 1 : ((total - 1) ~/ inventoryPageSize) + 1;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          IconButton(
            tooltip: '이전 페이지',
            onPressed: filters.offset > 0
                ? ref.read(inventoryFiltersProvider.notifier).previousPage
                : null,
            icon: const Icon(Icons.chevron_left),
          ),
          Text('$page / $pageCount'),
          IconButton(
            tooltip: '다음 페이지',
            onPressed: filters.offset + inventoryPageSize < total
                ? ref.read(inventoryFiltersProvider.notifier).nextPage
                : null,
            icon: const Icon(Icons.chevron_right),
          ),
        ],
      ),
    );
  }
}

class _InventoryFilterSheet extends StatefulWidget {
  const _InventoryFilterSheet({required this.filters});

  final InventoryFilters filters;

  @override
  State<_InventoryFilterSheet> createState() => _InventoryFilterSheetState();
}

class _InventoryFilterSheetState extends State<_InventoryFilterSheet> {
  late final TextEditingController _categoryController;
  late bool _includeZero;
  late InventorySortOption _sort;

  @override
  void initState() {
    super.initState();
    _categoryController = TextEditingController(
      text: widget.filters.category ?? '',
    );
    _includeZero = widget.filters.includeZero;
    _sort = widget.filters.sort;
  }

  @override
  void dispose() {
    _categoryController.dispose();
    super.dispose();
  }

  void _apply() {
    final category = _categoryController.text.trim();
    Navigator.of(context).pop(
      InventoryFilters(
        search: widget.filters.search,
        category: category.isEmpty ? null : category,
        includeZero: _includeZero,
        sort: _sort,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('재고 필터·정렬', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 20),
          TextField(
            controller: _categoryController,
            maxLength: 50,
            decoration: const InputDecoration(
              labelText: '카테고리 (선택)',
              border: OutlineInputBorder(),
            ),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('수량 0인 품목 포함'),
            value: _includeZero,
            onChanged: (value) => setState(() => _includeZero = value),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<InventorySortOption>(
            value: _sort,
            decoration: const InputDecoration(
              labelText: '정렬',
              border: OutlineInputBorder(),
            ),
            items: InventorySortOption.values
                .map(
                  (option) => DropdownMenuItem(
                    value: option,
                    child: Text(_inventorySortLabel(option)),
                  ),
                )
                .toList(growable: false),
            onChanged: (value) {
              if (value != null) {
                setState(() => _sort = value);
              }
            },
          ),
          const SizedBox(height: 20),
          FilledButton(onPressed: _apply, child: const Text('적용')),
        ],
      ),
    );
  }
}

String _inventorySortLabel(InventorySortOption option) {
  return switch (option) {
    InventorySortOption.recentlyUpdated => '최근 변경순',
    InventorySortOption.name => '이름순',
    InventorySortOption.quantityDesc => '수량 많은순',
    InventorySortOption.quantityAsc => '수량 적은순',
  };
}

class _InventoryTile extends ConsumerWidget {
  const _InventoryTile({required this.item});

  final InventoryItem item;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isZero = item.quantity <= 0;
    return ListTile(
      title: Text(item.name),
      subtitle: item.category == null ? null : Text(item.category!),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '${formatQuantity(item.quantity)} ${item.unit}',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: isZero ? Colors.redAccent : null,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (item.isActive)
            PopupMenuButton<InventoryQuantityAction>(
              tooltip: '수량 변경',
              onSelected: (action) => showInventoryQuantitySheet(
                context: context,
                ref: ref,
                itemId: item.itemId,
                itemName: item.name,
                unit: item.unit,
                currentQuantity: item.quantity,
                initialAction: action,
              ),
              itemBuilder: (_) => const [
                PopupMenuItem(
                  value: InventoryQuantityAction.stockIn,
                  child: Text('입고'),
                ),
                PopupMenuItem(
                  value: InventoryQuantityAction.stockOut,
                  child: Text('소비'),
                ),
                PopupMenuItem(
                  value: InventoryQuantityAction.setQuantity,
                  child: Text('목표 수량 설정'),
                ),
              ],
            ),
        ],
      ),
      onTap: () => context.push('/inventory/${item.itemId}'),
    );
  }
}
