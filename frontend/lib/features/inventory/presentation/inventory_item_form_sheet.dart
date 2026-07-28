import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/format/quantity_format.dart';
import '../domain/inventory_catalog_item.dart';
import '../domain/inventory_detail.dart';
import 'inventory_providers.dart';

String? validateRequiredItemText(String? value, {required String label}) {
  if (value == null || value.trim().isEmpty) {
    return '$label을 입력해 주세요.';
  }
  return null;
}

Future<InventoryCatalogItem?> showInventoryItemFormSheet({
  required BuildContext context,
  InventoryDetail? existing,
}) {
  return showModalBottomSheet<InventoryCatalogItem>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => _InventoryItemFormSheet(existing: existing),
  );
}

class _InventoryItemFormSheet extends ConsumerStatefulWidget {
  const _InventoryItemFormSheet({this.existing});

  final InventoryDetail? existing;

  @override
  ConsumerState<_InventoryItemFormSheet> createState() =>
      _InventoryItemFormSheetState();
}

class _InventoryItemFormSheetState
    extends ConsumerState<_InventoryItemFormSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _unitController;
  late final TextEditingController _categoryController;
  bool _isSubmitting = false;

  bool get _isEditing => widget.existing != null;
  bool get _canChangeUnit => !_isEditing || widget.existing!.quantity == 0;

  @override
  void initState() {
    super.initState();
    final existing = widget.existing;
    _nameController = TextEditingController(text: existing?.name ?? '');
    _unitController = TextEditingController(text: existing?.unit ?? '개');
    _categoryController = TextEditingController(text: existing?.category ?? '');
  }

  @override
  void dispose() {
    _nameController.dispose();
    _unitController.dispose();
    _categoryController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_isSubmitting || !(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _isSubmitting = true);

    try {
      final api = ref.read(inventoryItemApiProvider);
      final item = _isEditing
          ? await api.updateItem(
              itemId: widget.existing!.itemId,
              name: _nameController.text.trim(),
              unit: _unitController.text.trim(),
              category: _categoryController.text.trim(),
            )
          : await api.createItem(
              name: _nameController.text.trim(),
              unit: _unitController.text.trim(),
              category: _categoryController.text.trim(),
            );
      if (mounted) {
        Navigator.of(context).pop(item);
      }
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
              _isEditing ? '품목 정보 수정' : '새 품목 추가',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            if (_isEditing) ...[
              const SizedBox(height: 4),
              Text(
                '현재 ${formatQuantity(widget.existing!.quantity)} '
                '${widget.existing!.unit}',
              ),
            ],
            const SizedBox(height: 20),
            TextFormField(
              controller: _nameController,
              autofocus: true,
              enabled: !_isSubmitting,
              maxLength: 100,
              decoration: const InputDecoration(
                labelText: '품목명',
                border: OutlineInputBorder(),
              ),
              validator: (value) =>
                  validateRequiredItemText(value, label: '품목명'),
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _unitController,
              enabled: !_isSubmitting && _canChangeUnit,
              maxLength: 20,
              decoration: InputDecoration(
                labelText: '기본 단위',
                border: const OutlineInputBorder(),
                helperText: _canChangeUnit
                    ? '예: 개, 캔, 병, g, ml'
                    : '기본 단위는 현재 수량이 0일 때만 바꿀 수 있어요.',
              ),
              validator: (value) =>
                  validateRequiredItemText(value, label: '기본 단위'),
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _categoryController,
              enabled: !_isSubmitting,
              maxLength: 50,
              decoration: const InputDecoration(
                labelText: '카테고리 (선택)',
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
                  : Text(_isEditing ? '수정하기' : '추가하기'),
            ),
          ],
        ),
      ),
    );
  }
}
