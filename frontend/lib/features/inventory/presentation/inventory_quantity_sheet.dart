import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/format/quantity_format.dart';
import '../../history/presentation/history_providers.dart';
import '../data/inventory_api.dart';
import 'inventory_providers.dart';

enum InventoryQuantityAction { stockIn, stockOut, setQuantity }

String? validateQuantityInput(
  String value, {
  required InventoryQuantityAction action,
}) {
  final trimmed = value.trim();
  if (trimmed.isEmpty) {
    return '수량을 입력해 주세요.';
  }

  final parts = trimmed.split('.');
  final isDecimalShape =
      parts.length <= 2 &&
      parts.first.isNotEmpty &&
      parts.every((part) => RegExp(r'^\d+$').hasMatch(part));
  final wholeDigits = parts.first.length;
  final decimalDigits = parts.length == 2 ? parts.last.length : 0;
  if (!isDecimalShape || wholeDigits > 9 || decimalDigits > 3) {
    return '수량은 정수 9자리, 소수점 셋째 자리까지 입력해 주세요.';
  }

  final quantity = num.tryParse(trimmed);
  if (quantity == null) {
    return '올바른 수량을 입력해 주세요.';
  }
  if (action == InventoryQuantityAction.setQuantity) {
    if (quantity < 0) {
      return '목표 수량은 0 이상이어야 해요.';
    }
  } else if (quantity <= 0) {
    return '입고·소비 수량은 0보다 커야 해요.';
  }
  return null;
}

Future<void> showInventoryQuantitySheet({
  required BuildContext context,
  required WidgetRef ref,
  required String itemId,
  required String itemName,
  required String unit,
  required double currentQuantity,
  required InventoryQuantityAction initialAction,
}) async {
  final message = await showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => _InventoryQuantitySheet(
      itemId: itemId,
      itemName: itemName,
      unit: unit,
      currentQuantity: currentQuantity,
      initialAction: initialAction,
    ),
  );
  if (message == null || !context.mounted) {
    return;
  }

  ref.invalidate(inventoryDetailProvider(itemId));
  ref.invalidate(inventoryListProvider);
  ref.invalidate(historyPageProvider);
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
}

class _InventoryQuantitySheet extends ConsumerStatefulWidget {
  const _InventoryQuantitySheet({
    required this.itemId,
    required this.itemName,
    required this.unit,
    required this.currentQuantity,
    required this.initialAction,
  });

  final String itemId;
  final String itemName;
  final String unit;
  final double currentQuantity;
  final InventoryQuantityAction initialAction;

  @override
  ConsumerState<_InventoryQuantitySheet> createState() =>
      _InventoryQuantitySheetState();
}

class _InventoryQuantitySheetState
    extends ConsumerState<_InventoryQuantitySheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _quantityController;
  late final TextEditingController _noteController;
  late InventoryQuantityAction _action;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _action = widget.initialAction;
    _quantityController = TextEditingController(
      text: _action == InventoryQuantityAction.setQuantity
          ? formatQuantity(widget.currentQuantity)
          : '',
    );
    _noteController = TextEditingController();
  }

  @override
  void dispose() {
    _quantityController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  void _selectAction(InventoryQuantityAction action) {
    if (_isSubmitting || action == _action) {
      return;
    }
    _formKey.currentState?.reset();
    setState(() {
      _action = action;
      _quantityController.text = action == InventoryQuantityAction.setQuantity
          ? formatQuantity(widget.currentQuantity)
          : '';
    });
  }

  Future<void> _submit() async {
    if (_isSubmitting || !(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _isSubmitting = true);

    final quantity = num.parse(_quantityController.text.trim());
    final note = _noteController.text.trim();
    try {
      final api = ref.read(inventoryApiProvider);
      final result = switch (_action) {
        InventoryQuantityAction.stockIn => await api.createManualEvent(
          itemId: widget.itemId,
          eventType: ManualInventoryEventType.stockIn,
          quantity: quantity,
          unit: widget.unit,
          note: note,
        ),
        InventoryQuantityAction.stockOut => await api.createManualEvent(
          itemId: widget.itemId,
          eventType: ManualInventoryEventType.stockOut,
          quantity: quantity,
          unit: widget.unit,
          note: note,
        ),
        InventoryQuantityAction.setQuantity => await api.setQuantity(
          itemId: widget.itemId,
          quantity: quantity,
          unit: widget.unit,
          note: note,
        ),
      };
      if (!mounted) {
        return;
      }
      final message = !result.changed
          ? '이미 ${formatQuantity(result.currentQuantity)} ${widget.unit}예요.'
          : '${formatQuantity(result.currentQuantity)} ${widget.unit}로 반영했어요.';
      Navigator.of(context).pop(message);
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.message)));
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.viewInsetsOf(context).bottom;
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(20, 20, 20, 20 + bottomInset),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.itemName,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 4),
            Text(
              '현재 ${formatQuantity(widget.currentQuantity)} ${widget.unit}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),
            SegmentedButton<InventoryQuantityAction>(
              segments: const [
                ButtonSegment(
                  value: InventoryQuantityAction.stockIn,
                  label: Text('입고'),
                  icon: Icon(Icons.add),
                ),
                ButtonSegment(
                  value: InventoryQuantityAction.stockOut,
                  label: Text('소비'),
                  icon: Icon(Icons.remove),
                ),
                ButtonSegment(
                  value: InventoryQuantityAction.setQuantity,
                  label: Text('목표 수량'),
                  icon: Icon(Icons.tune),
                ),
              ],
              selected: {_action},
              onSelectionChanged: _isSubmitting
                  ? null
                  : (selection) => _selectAction(selection.first),
            ),
            const SizedBox(height: 20),
            TextFormField(
              controller: _quantityController,
              autofocus: true,
              enabled: !_isSubmitting,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
              ],
              decoration: InputDecoration(
                labelText: _action == InventoryQuantityAction.setQuantity
                    ? '최종 목표 수량'
                    : '변경 수량',
                suffixText: widget.unit,
                border: const OutlineInputBorder(),
              ),
              validator: (value) =>
                  validateQuantityInput(value ?? '', action: _action),
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _noteController,
              enabled: !_isSubmitting,
              maxLength: 1000,
              minLines: 1,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: '메모 (선택)',
                border: OutlineInputBorder(),
              ),
              textInputAction: TextInputAction.done,
              onFieldSubmitted: (_) => _submit(),
            ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: _isSubmitting ? null : _submit,
              child: _isSubmitting
                  ? const SizedBox.square(
                      dimension: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('반영하기'),
            ),
          ],
        ),
      ),
    );
  }
}
