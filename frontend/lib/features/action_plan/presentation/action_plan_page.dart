import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/format/quantity_format.dart';
import '../../../core/widgets/async_view.dart';
import '../../history/presentation/history_providers.dart';
import '../../inventory/presentation/inventory_providers.dart';
import '../domain/action_plan.dart';
import 'action_plan_edit_sheet.dart';
import 'action_plan_providers.dart';

class ActionPlanPage extends ConsumerStatefulWidget {
  const ActionPlanPage({super.key, required this.requestId});

  final String requestId;

  @override
  ConsumerState<ActionPlanPage> createState() => _ActionPlanPageState();
}

class _ActionPlanPageState extends ConsumerState<ActionPlanPage> {
  String? _mutatingActionId;
  bool _executing = false;
  ActionPlanExecutionResult? _executionResult;

  void _refresh() => ref.invalidate(actionPlanProvider(widget.requestId));

  Future<void> _edit(ActionPlanAction action) async {
    if (_mutatingActionId != null) return;
    setState(() => _mutatingActionId = action.actionId);
    try {
      final items = await ref.read(actionPlanInventoryItemsProvider.future);
      if (!mounted) return;
      if (items.isEmpty) {
        throw const ApiException(
          code: 'NO_ACTIVE_ITEMS',
          message: '수정에 사용할 활성 품목이 없어요.',
        );
      }
      final result = await showActionPlanEditSheet(
        context: context,
        api: ref.read(actionPlanApiProvider),
        requestId: widget.requestId,
        action: action,
        items: items,
      );
      if (result != null && mounted) {
        _refresh();
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Action을 수정했어요.')));
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _mutatingActionId = null);
    }
  }

  Future<void> _delete(ActionPlan plan, ActionPlanAction action) async {
    if (_mutatingActionId != null) return;
    if (plan.actions.length == 1) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('마지막 Action은 삭제할 수 없어요. 전체 취소를 사용해 주세요.')),
      );
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('이 Action을 삭제할까요?'),
        content: Text('${action.item.displayName} 변경만 Plan에서 제외합니다.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('돌아가기'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('삭제'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _mutatingActionId = action.actionId);
    try {
      await ref
          .read(actionPlanApiProvider)
          .deleteAction(requestId: widget.requestId, actionId: action.actionId);
      if (mounted) {
        _refresh();
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Action을 삭제했어요.')));
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _mutatingActionId = null);
    }
  }

  void _cancel() {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/home');
    }
  }

  Future<void> _execute(ActionPlan plan) async {
    if (_executing || _mutatingActionId != null || plan.executed) return;
    if (plan.actions.any((action) => action.requiresUserInput)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('수정이 필요한 Action을 먼저 확인해 주세요.')),
      );
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('재고에 반영할까요?'),
        content: Text(
          '${plan.actions.length}개의 Action을 순서대로 실행합니다. '
          '실행 결과는 재고 기록에 남습니다.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('돌아가기'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('반영'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _executing = true);
    try {
      final result = await ref
          .read(actionPlanApiProvider)
          .executePlan(widget.requestId);
      if (!mounted) return;
      setState(() => _executionResult = result);
      _refresh();
      ref.invalidate(inventoryListProvider);
      ref.invalidate(historyItemsProvider);
      ref.invalidate(historyPageProvider);
      for (final action in plan.actions) {
        final itemId = action.item.matchedItemId;
        if (itemId != null) ref.invalidate(inventoryDetailProvider(itemId));
      }
      final message = result.alreadyExecuted
          ? '이미 반영된 Plan이에요. 재고를 중복 변경하지 않았습니다.'
          : result.eventCount == 0
          ? '현재 수량과 같아 새 기록 없이 반영을 완료했어요.'
          : '재고 기록 ${result.eventCount}건을 반영했어요.';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _executing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final planAsync = ref.watch(actionPlanProvider(widget.requestId));
    return Scaffold(
      appBar: AppBar(
        title: const Text('확인해 주세요'),
        actions: [
          IconButton(
            tooltip: '새로고침',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: AsyncView<ActionPlan>(
        value: planAsync,
        onRetry: _refresh,
        onData: (plan) {
          final completed = plan.executed || _executionResult != null;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                '이렇게 이해했습니다.',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '원본 Transcript',
                        style: Theme.of(context).textTheme.labelLarge,
                      ),
                      const SizedBox(height: 6),
                      Text(plan.transcript),
                      const SizedBox(height: 12),
                      Text(
                        plan.summary,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 8),
              if (completed)
                Card(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  child: const ListTile(
                    leading: Icon(Icons.check_circle_outline),
                    title: Text('재고 반영을 완료했습니다.'),
                  ),
                ),
              ...plan.actions.map(
                (action) => _ActionCard(
                  action: action,
                  mutating: _mutatingActionId == action.actionId,
                  onEdit: completed || _executing ? null : () => _edit(action),
                  onDelete: completed || _executing
                      ? null
                      : () => _delete(plan, action),
                ),
              ),
              const SizedBox(height: 16),
              OutlinedButton(
                onPressed:
                    _mutatingActionId == null && !_executing && !completed
                    ? _cancel
                    : null,
                child: const Text('전체 취소'),
              ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed:
                    _mutatingActionId == null && !_executing && !completed
                    ? () => _execute(plan)
                    : null,
                child: _executing
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(completed ? '반영 완료' : '재고에 반영'),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.action,
    required this.mutating,
    required this.onEdit,
    required this.onDelete,
  });

  final ActionPlanAction action;
  final bool mutating;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final needsAttention =
        action.requiresUserInput || action.warnings.isNotEmpty;
    return Card(
      margin: const EdgeInsets.only(top: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  action.type.symbol,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    action.item.displayName,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                if (needsAttention)
                  const Chip(
                    label: Text('수정 필요'),
                    visualDensity: VisualDensity.compact,
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text('작업: ${action.type.label}'),
            Text(
              '수량: ${formatQuantity(action.quantity.displayValue)}'
              '${action.quantity.displayUnit}',
            ),
            Text(
              '신뢰도: ${action.confidenceLabel} '
              '(${(action.confidence * 100).round()}%)',
            ),
            for (final warning in action.warnings)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  warning.message,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            if (action.item.isNewItem)
              const Padding(
                padding: EdgeInsets.only(top: 6),
                child: Text('기존 품목을 선택하거나 신규 품목 확인이 필요해요.'),
              ),
            const SizedBox(height: 10),
            if (mutating)
              const Center(child: CircularProgressIndicator())
            else
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    onPressed: onEdit,
                    icon: const Icon(Icons.edit_outlined),
                    label: const Text('수정'),
                  ),
                  TextButton.icon(
                    onPressed: onDelete,
                    icon: const Icon(Icons.delete_outline),
                    label: const Text('삭제'),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}
