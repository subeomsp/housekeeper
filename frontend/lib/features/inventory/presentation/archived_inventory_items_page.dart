import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/format/quantity_format.dart';
import '../../../core/widgets/async_view.dart';
import '../../history/presentation/history_providers.dart';
import '../domain/inventory_catalog_item.dart';
import 'inventory_providers.dart';

class ArchivedInventoryItemsPage extends ConsumerStatefulWidget {
  const ArchivedInventoryItemsPage({super.key});

  @override
  ConsumerState<ArchivedInventoryItemsPage> createState() =>
      _ArchivedInventoryItemsPageState();
}

class _ArchivedInventoryItemsPageState
    extends ConsumerState<ArchivedInventoryItemsPage> {
  final _restoringIds = <String>{};

  void _refresh() => ref.invalidate(archivedInventoryItemsProvider);

  Future<void> _restore(InventoryCatalogItem item) async {
    if (_restoringIds.contains(item.id)) {
      return;
    }
    setState(() => _restoringIds.add(item.id));
    try {
      await ref.read(inventoryItemApiProvider).restoreItem(item.id);
      if (!mounted) {
        return;
      }
      ref.invalidate(archivedInventoryItemsProvider);
      ref.invalidate(inventoryListProvider);
      ref.invalidate(inventoryDetailProvider(item.id));
      ref.invalidate(historyItemsProvider);
      ref.invalidate(historyPageProvider);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('${item.name}을(를) 복원했어요.')));
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) {
        setState(() => _restoringIds.remove(item.id));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final itemsAsync = ref.watch(archivedInventoryItemsProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('보관된 품목'),
        actions: [
          IconButton(
            tooltip: '새로고침',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: AsyncView<List<InventoryCatalogItem>>(
        value: itemsAsync,
        onRetry: _refresh,
        isEmpty: (items) => items.isEmpty,
        emptyMessage: '보관된 품목이 없어요.',
        onData: (items) => RefreshIndicator(
          onRefresh: () async => _refresh(),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            itemCount: items.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final item = items[index];
              final isRestoring = _restoringIds.contains(item.id);
              return ListTile(
                leading: const Icon(Icons.archive_outlined),
                title: Text(item.name),
                subtitle: Text(
                  [
                    if (item.category != null) item.category!,
                    '${formatQuantity(item.currentQuantity)} ${item.unit}',
                  ].join(' · '),
                ),
                trailing: isRestoring
                    ? const SizedBox.square(
                        dimension: 24,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : TextButton.icon(
                        onPressed: () => _restore(item),
                        icon: const Icon(Icons.unarchive_outlined),
                        label: const Text('복원'),
                      ),
                onTap: () => context.push('/inventory/${item.id}'),
              );
            },
          ),
        ),
      ),
    );
  }
}
