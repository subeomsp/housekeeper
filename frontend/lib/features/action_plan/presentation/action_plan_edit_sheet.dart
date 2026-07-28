import 'package:flutter/material.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/format/quantity_format.dart';
import '../../inventory/domain/inventory_catalog_item.dart';
import '../data/action_plan_api.dart';
import '../domain/action_plan.dart';

Future<ActionPlan?> showActionPlanEditSheet({
  required BuildContext context,
  required ActionPlanApi api,
  required String requestId,
  required ActionPlanAction action,
  required List<InventoryCatalogItem> items,
}) {
  return showModalBottomSheet<ActionPlan>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => _ActionPlanEditSheet(
      api: api,
      requestId: requestId,
      action: action,
      items: items,
    ),
  );
}

class _ActionPlanEditSheet extends StatefulWidget {
  const _ActionPlanEditSheet({
    required this.api,
    required this.requestId,
    required this.action,
    required this.items,
  });

  final ActionPlanApi api;
  final String requestId;
  final ActionPlanAction action;
  final List<InventoryCatalogItem> items;

  @override
  State<_ActionPlanEditSheet> createState() => _ActionPlanEditSheetState();
}

class _ActionPlanEditSheetState extends State<_ActionPlanEditSheet> {
  final _formKey = GlobalKey<FormState>();
  late ActionPlanType _type = widget.action.type;
  late String? _itemId =
      widget.action.item.matchedItemId ??
      (widget.items.isEmpty ? null : widget.items.first.id);
  late final _quantityController = TextEditingController(
    text: formatQuantity(widget.action.quantity.displayValue),
  );
  bool _submitting = false;
  String? _errorMessage;

  InventoryCatalogItem? get _selectedItem {
    for (final item in widget.items) {
      if (item.id == _itemId) return item;
    }
    return null;
  }

  @override
  void dispose() {
    _quantityController.dispose();
    super.dispose();
  }

  String? _validateQuantity(String? value) {
    final text = value?.trim() ?? '';
    if (!RegExp(r'^\d{1,9}(?:\.\d{1,3})?$').hasMatch(text)) {
      return '정수 9자리와 소수 3자리 이내로 입력해 주세요.';
    }
    final quantity = double.parse(text);
    if (_type != ActionPlanType.setQuantity && quantity <= 0) {
      return '입고와 소비 수량은 0보다 커야 해요.';
    }
    return null;
  }

  Future<void> _submit() async {
    if (_submitting || !_formKey.currentState!.validate()) return;
    final item = _selectedItem;
    if (item == null) return;
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });
    try {
      final result = await widget.api.updateAction(
        requestId: widget.requestId,
        actionId: widget.action.actionId,
        type: _type,
        itemId: item.id,
        quantity: double.parse(_quantityController.text.trim()),
        unit: item.unit,
      );
      if (mounted) Navigator.of(context).pop(result);
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _submitting = false;
          _errorMessage = error.message;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final item = _selectedItem;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        20,
        20,
        20 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Action 수정', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _itemId,
              decoration: const InputDecoration(labelText: '품목'),
              items: widget.items
                  .map(
                    (item) => DropdownMenuItem(
                      value: item.id,
                      child: Text(item.name),
                    ),
                  )
                  .toList(growable: false),
              onChanged: _submitting
                  ? null
                  : (value) => setState(() => _itemId = value),
              validator: (value) => value == null ? '품목을 선택해 주세요.' : null,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<ActionPlanType>(
              value: _type,
              decoration: const InputDecoration(labelText: '작업'),
              items: ActionPlanType.values
                  .map(
                    (type) =>
                        DropdownMenuItem(value: type, child: Text(type.label)),
                  )
                  .toList(growable: false),
              onChanged: _submitting
                  ? null
                  : (value) => setState(() => _type = value ?? _type),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _quantityController,
              enabled: !_submitting,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(labelText: '수량'),
              validator: _validateQuantity,
            ),
            const SizedBox(height: 12),
            TextFormField(
              key: ValueKey(item?.unit),
              initialValue: item?.unit ?? '',
              readOnly: true,
              decoration: const InputDecoration(
                labelText: '단위',
                helperText: '현재는 품목의 기본 단위만 사용할 수 있어요.',
              ),
            ),
            if (_errorMessage != null) ...[
              const SizedBox(height: 10),
              Text(
                _errorMessage!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _submitting || item == null ? null : _submit,
              child: _submitting
                  ? const SizedBox.square(
                      dimension: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('완료'),
            ),
          ],
        ),
      ),
    );
  }
}
