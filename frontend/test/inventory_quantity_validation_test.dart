import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:voice_inventory/features/inventory/presentation/inventory_quantity_sheet.dart';

void main() {
  group('validateQuantityInput', () {
    test('manual stock changes require a positive quantity', () {
      expect(
        validateQuantityInput('0', action: InventoryQuantityAction.stockIn),
        isNotNull,
      );
      expect(
        validateQuantityInput(
          '0.001',
          action: InventoryQuantityAction.stockOut,
        ),
        isNull,
      );
    });

    test('target quantity accepts zero', () {
      expect(
        validateQuantityInput('0', action: InventoryQuantityAction.setQuantity),
        isNull,
      );
    });

    test('rejects more than three decimal places or nine whole digits', () {
      expect(
        validateQuantityInput(
          '1.0001',
          action: InventoryQuantityAction.stockIn,
        ),
        isNotNull,
      );
      expect(
        validateQuantityInput(
          '1234567890',
          action: InventoryQuantityAction.stockIn,
        ),
        isNotNull,
      );
      expect(
        validateQuantityInput(
          '123456789.123',
          action: InventoryQuantityAction.stockIn,
        ),
        isNull,
      );
    });

    test('rejects malformed decimal input', () {
      for (final value in ['', '.', '1.', '.5', '1..2', '-1']) {
        expect(
          validateQuantityInput(
            value,
            action: InventoryQuantityAction.setQuantity,
          ),
          isNotNull,
          reason: value,
        );
      }
    });
  });

  testWidgets('quantity sheet exposes all three manual flows', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: Consumer(
              builder: (context, ref, _) => TextButton(
                onPressed: () => showInventoryQuantitySheet(
                  context: context,
                  ref: ref,
                  itemId: 'item-id',
                  itemName: '우유',
                  unit: '개',
                  currentQuantity: 2,
                  initialAction: InventoryQuantityAction.stockIn,
                ),
                child: const Text('열기'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();

    expect(find.text('우유'), findsOneWidget);
    expect(find.text('현재 2 개'), findsOneWidget);
    expect(find.text('입고'), findsOneWidget);
    expect(find.text('소비'), findsOneWidget);
    expect(find.text('목표 수량'), findsOneWidget);

    await tester.tap(find.text('목표 수량'));
    await tester.pump();
    final quantityField = tester.widget<TextFormField>(
      find.byType(TextFormField).first,
    );
    expect(quantityField.controller?.text, '2');
    expect(find.text('최종 목표 수량'), findsOneWidget);
  });
}
