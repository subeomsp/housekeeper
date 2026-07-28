import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/action_plan/data/action_plan_api.dart';
import 'package:voice_inventory/features/action_plan/domain/action_plan.dart';
import 'package:voice_inventory/features/action_plan/presentation/action_plan_edit_sheet.dart';
import 'package:voice_inventory/features/inventory/domain/inventory_catalog_item.dart';

void main() {
  testWidgets('edits an action to set_quantity zero using the official unit', (
    tester,
  ) async {
    final plan = _plan();
    final api = _FakeActionPlanApi(plan);
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: FilledButton(
              onPressed: () => showActionPlanEditSheet(
                context: context,
                api: api,
                requestId: 'request-id',
                action: plan.actions.first,
                items: const [
                  InventoryCatalogItem(
                    id: 'item-id',
                    name: '우유',
                    unit: '개',
                    category: null,
                    isActive: true,
                    currentQuantity: 2,
                  ),
                ],
              ),
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('입고'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('현재 수량 설정').last);
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextFormField, '수량'), '0');
    await tester.tap(find.widgetWithText(FilledButton, '완료'));
    await tester.pumpAndSettle();

    expect(api.updatedType, ActionPlanType.setQuantity);
    expect(api.updatedQuantity, 0);
    expect(api.updatedUnit, '개');
  });
}

ActionPlan _plan() {
  return ActionPlan(
    requestId: 'request-id',
    planId: 'plan-id',
    version: '1.0',
    transcript: '우유 두 개 사왔어.',
    summary: '우유 입고',
    requiresConfirmation: true,
    actions: [
      ActionPlanAction(
        actionId: 'a1',
        type: ActionPlanType.stockIn,
        item: const ActionPlanItemReference(
          rawName: '우유',
          matchedItemId: 'item-id',
          matchedName: '우유',
          isNewItem: false,
        ),
        quantity: const ActionPlanQuantity(
          rawValue: 2,
          rawUnit: '개',
          normalizedValue: 2,
          normalizedUnit: '개',
          conversionApplied: false,
          conversionReason: null,
        ),
        confidence: 0.98,
        warnings: const [],
        requiresUserInput: false,
      ),
    ],
    approved: false,
    executed: false,
    createdAt: DateTime.utc(2026, 7, 28),
  );
}

class _FakeActionPlanApi extends ActionPlanApi {
  _FakeActionPlanApi(this.plan) : super(Dio());

  final ActionPlan plan;
  ActionPlanType? updatedType;
  num? updatedQuantity;
  String? updatedUnit;

  @override
  Future<ActionPlan> updateAction({
    required String requestId,
    required String actionId,
    required ActionPlanType type,
    required String itemId,
    required num quantity,
    required String unit,
  }) async {
    updatedType = type;
    updatedQuantity = quantity;
    updatedUnit = unit;
    return plan;
  }
}
