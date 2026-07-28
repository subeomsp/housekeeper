import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/format/quantity_format.dart';
import '../../inventory/data/inventory_api.dart';
import '../domain/history_event.dart';
import 'history_providers.dart';

Future<String?> showEventCorrectionSheet({
  required BuildContext context,
  required HistoryEvent event,
  required String itemName,
}) {
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => _EventCorrectionSheet(event: event, itemName: itemName),
  );
}

class _EventCorrectionSheet extends ConsumerStatefulWidget {
  const _EventCorrectionSheet({required this.event, required this.itemName});

  final HistoryEvent event;
  final String itemName;

  @override
  ConsumerState<_EventCorrectionSheet> createState() =>
      _EventCorrectionSheetState();
}

class _EventCorrectionSheetState extends ConsumerState<_EventCorrectionSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _quantityController;
  late final TextEditingController _noteController;
  late ManualInventoryEventType _eventType;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _eventType = widget.event.signedQuantity < 0
        ? ManualInventoryEventType.stockOut
        : ManualInventoryEventType.stockIn;
    _quantityController = TextEditingController(
      text: formatQuantity(widget.event.quantity),
    );
    _noteController = TextEditingController(text: widget.event.note ?? '');
  }

  @override
  void dispose() {
    _quantityController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  String? _validateQuantity(String? value) {
    final trimmed = value?.trim() ?? '';
    final parts = trimmed.split('.');
    final validShape =
        parts.length <= 2 &&
        parts.first.isNotEmpty &&
        parts.every((part) => RegExp(r'^\d+$').hasMatch(part));
    final decimals = parts.length == 2 ? parts.last.length : 0;
    if (!validShape || parts.first.length > 9 || decimals > 3) {
      return '수량은 정수 9자리, 소수점 셋째 자리까지 입력해 주세요.';
    }
    final quantity = num.tryParse(trimmed);
    if (quantity == null || quantity <= 0) {
      return '정정 수량은 0보다 커야 해요.';
    }
    return null;
  }

  Future<void> _submit() async {
    if (_isSubmitting || !(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _isSubmitting = true);
    try {
      final result = await ref
          .read(historyApiProvider)
          .correctEvent(
            eventId: widget.event.id,
            eventType: _eventType,
            quantity: num.parse(_quantityController.text.trim()),
            unit: widget.event.unit,
            note: _noteController.text.trim(),
          );
      if (mounted) {
        Navigator.of(context).pop(
          '${formatQuantity(result.currentQuantity)} ${widget.event.unit}로 정정했어요.',
        );
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
            Text('기록 정정', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text('${widget.itemName} · 원본은 보존되고 정정 기록이 추가돼요.'),
            const SizedBox(height: 20),
            SegmentedButton<ManualInventoryEventType>(
              segments: const [
                ButtonSegment(
                  value: ManualInventoryEventType.stockIn,
                  label: Text('입고'),
                  icon: Icon(Icons.add),
                ),
                ButtonSegment(
                  value: ManualInventoryEventType.stockOut,
                  label: Text('소비'),
                  icon: Icon(Icons.remove),
                ),
              ],
              selected: {_eventType},
              onSelectionChanged: _isSubmitting
                  ? null
                  : (selection) => setState(() => _eventType = selection.first),
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
                labelText: '정정 수량',
                suffixText: widget.event.unit,
                border: const OutlineInputBorder(),
              ),
              validator: _validateQuantity,
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
                labelText: '정정 메모 (선택)',
                border: OutlineInputBorder(),
              ),
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
                  : const Text('정정하기'),
            ),
          ],
        ),
      ),
    );
  }
}
