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

  testWidgets('confirms an unresolved action as a remembered new item', (
    tester,
  ) async {
    final plan = _newItemPlan();
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
                items: const [],
              ),
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, '새 품목 이름'),
      '아몬드브리즈',
    );
    await tester.enterText(find.widgetWithText(TextFormField, '기본 단위'), '개');
    await tester.enterText(find.widgetWithText(TextFormField, '카테고리'), '음료');
    await tester.ensureVisible(find.byType(Checkbox));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(Checkbox));
    await tester.ensureVisible(find.widgetWithText(FilledButton, '완료'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '완료'));
    await tester.pumpAndSettle();

    expect(api.newItemName, '아몬드브리즈');
    expect(api.newItemUnit, '개');
    expect(api.newItemCategory, '음료');
    expect(api.rememberAlias, isTrue);
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

ActionPlan _newItemPlan() {
  final plan = _plan();
  return ActionPlan(
    requestId: plan.requestId,
    planId: plan.planId,
    version: plan.version,
    transcript: '아몬드 두 개 사왔어.',
    summary: '신규 품목 확인 필요',
    requiresConfirmation: true,
    actions: [
      ActionPlanAction(
        actionId: 'a1',
        type: ActionPlanType.stockIn,
        item: const ActionPlanItemReference(
          rawName: '아몬드',
          matchedItemId: null,
          matchedName: null,
          isNewItem: true,
        ),
        quantity: const ActionPlanQuantity(
          rawValue: 2,
          rawUnit: '개',
          normalizedValue: null,
          normalizedUnit: null,
          conversionApplied: false,
          conversionReason: null,
        ),
        confidence: 0.6,
        warnings: const [],
        requiresUserInput: true,
      ),
    ],
    approved: false,
    executed: false,
    createdAt: plan.createdAt,
  );
}

class _FakeActionPlanApi extends ActionPlanApi {
  _FakeActionPlanApi(this.plan) : super(Dio());

  final ActionPlan plan;
  ActionPlanType? updatedType;
  num? updatedQuantity;
  String? updatedUnit;
  String? newItemName;
  String? newItemUnit;
  String? newItemCategory;
  bool? rememberAlias;

  @override
  Future<ActionPlan> updateAction({
    required String requestId,
    required String actionId,
    required ActionPlanType type,
    required String itemId,
    required num quantity,
    required String unit,
    bool rememberAlias = false,
  }) async {
    updatedType = type;
    updatedQuantity = quantity;
    updatedUnit = unit;
    return plan;
  }

  @override
  Future<ActionPlan> resolveNewItem({
    required String requestId,
    required String actionId,
    required ActionPlanType type,
    required String name,
    required String defaultUnit,
    required num quantity,
    String? category,
    bool rememberAlias = false,
  }) async {
    newItemName = name;
    newItemUnit = defaultUnit;
    newItemCategory = category;
    this.rememberAlias = rememberAlias;
    return plan;
  }
}
