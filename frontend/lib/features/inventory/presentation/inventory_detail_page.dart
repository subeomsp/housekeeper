import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/format/date_format.dart';
import '../../../core/format/quantity_format.dart';
import '../../../core/widgets/async_view.dart';
import '../domain/inventory_detail.dart';
import 'event_display.dart';
import 'inventory_providers.dart';
import 'inventory_quantity_sheet.dart';

/// Item detail: current Snapshot header + recent event history (spec §68.7).
class InventoryDetailPage extends ConsumerWidget {
  const InventoryDetailPage({super.key, required this.itemId});

  final String itemId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(inventoryDetailProvider(itemId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('품목 상세'),
        actions: [
          IconButton(
            tooltip: '새로고침',
            onPressed: () => ref.invalidate(inventoryDetailProvider(itemId)),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: AsyncView<InventoryDetail>(
        value: detailAsync,
        onRetry: () => ref.invalidate(inventoryDetailProvider(itemId)),
        onData: (detail) => RefreshIndicator(
          onRefresh: () async =>
              ref.invalidate(inventoryDetailProvider(itemId)),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            children: [
              _Header(detail: detail),
              if (detail.isActive)
                _QuantityActions(detail: detail, ref: ref)
              else
                const Padding(
                  padding: EdgeInsets.fromLTRB(16, 0, 16, 16),
                  child: Text('보관된 품목은 수량을 변경할 수 없어요.'),
                ),
              const Divider(height: 1),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Text(
                  '최근 기록',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              if (detail.recentEvents.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: Text('아직 기록이 없어요.')),
                )
              else
                ...detail.recentEvents.map((e) => _EventTile(event: e)),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuantityActions extends StatelessWidget {
  const _QuantityActions({required this.detail, required this.ref});

  final InventoryDetail detail;
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) {
    Future<void> open(InventoryQuantityAction action) {
      return showInventoryQuantitySheet(
        context: context,
        ref: ref,
        itemId: detail.itemId,
        itemName: detail.name,
        unit: detail.unit,
        currentQuantity: detail.quantity,
        initialAction: action,
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: FilledButton.tonalIcon(
                  onPressed: () => open(InventoryQuantityAction.stockIn),
                  icon: const Icon(Icons.add),
                  label: const Text('입고'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton.tonalIcon(
                  onPressed: () => open(InventoryQuantityAction.stockOut),
                  icon: const Icon(Icons.remove),
                  label: const Text('소비'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => open(InventoryQuantityAction.setQuantity),
              icon: const Icon(Icons.tune),
              label: const Text('목표 수량 설정'),
            ),
          ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.detail});

  final InventoryDetail detail;

  @override
  Widget build(BuildContext context) {
    final isZero = detail.quantity <= 0;
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  detail.name,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              if (!detail.isActive)
                const Chip(
                  label: Text('보관됨'),
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
          if (detail.category != null) ...[
            const SizedBox(height: 4),
            Text(
              detail.category!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                formatQuantity(detail.quantity),
                style: Theme.of(context).textTheme.displaySmall?.copyWith(
                  color: isZero ? Colors.redAccent : null,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(width: 6),
              Text(detail.unit, style: Theme.of(context).textTheme.titleMedium),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '최근 업데이트 ${formatDateTime(detail.updatedAt)}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _EventTile extends StatelessWidget {
  const _EventTile({required this.event});

  final RecentEvent event;

  @override
  Widget build(BuildContext context) {
    final color = eventDeltaColor(event.signedQuantity, context);
    return ListTile(
      dense: true,
      leading: Icon(
        event.signedQuantity >= 0
            ? Icons.add_circle_outline
            : Icons.remove_circle_outline,
        color: color,
      ),
      title: Text(eventTypeLabel(event.eventType)),
      subtitle: Text(formatDateTime(event.createdAt)),
      trailing: Text(
        '${signedPrefix(event.signedQuantity)}${formatQuantity(event.signedQuantity)} ${event.unit}',
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
          color: color,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
