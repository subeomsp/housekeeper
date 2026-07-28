import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/format/quantity_format.dart';
import '../../../core/widgets/async_view.dart';
import '../domain/inventory_item.dart';
import 'inventory_providers.dart';
import 'inventory_quantity_sheet.dart';

/// Current inventory list (spec §68.6). Reads Snapshot quantities via the API,
/// supports search, manual refresh, and taps through to item detail.
class InventoryListPage extends ConsumerWidget {
  const InventoryListPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listAsync = ref.watch(inventoryListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('재고'),
        actions: [
          IconButton(
            tooltip: '새로고침',
            onPressed: () => ref.invalidate(inventoryListProvider),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Column(
        children: [
          const _SearchField(),
          Expanded(
            child: AsyncView<InventoryPage>(
              value: listAsync,
              onRetry: () => ref.invalidate(inventoryListProvider),
              isEmpty: (page) => page.items.isEmpty,
              emptyMessage: '등록된 재고가 없어요.',
              onData: (page) => RefreshIndicator(
                onRefresh: () async => ref.invalidate(inventoryListProvider),
                child: ListView.separated(
                  physics: const AlwaysScrollableScrollPhysics(),
                  itemCount: page.items.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, index) =>
                      _InventoryTile(item: page.items[index]),
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
      text: ref.read(inventorySearchProvider),
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
                    ref.read(inventorySearchProvider.notifier).set('');
                  },
                ),
        ),
        onChanged: (value) => setState(() {}),
        onSubmitted: (value) =>
            ref.read(inventorySearchProvider.notifier).set(value.trim()),
      ),
    );
  }
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
