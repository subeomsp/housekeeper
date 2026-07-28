import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/action_plan/data/action_plan_api.dart';
import 'package:voice_inventory/features/action_plan/domain/action_plan.dart';
import 'package:voice_inventory/features/action_plan/presentation/action_plan_page.dart';
import 'package:voice_inventory/features/action_plan/presentation/action_plan_providers.dart';

void main() {
  testWidgets('shows transcript, warnings, confidence, and disabled execute', (
    tester,
  ) async {
    final plan = _plan(
      actions: [
        _action(
          actionId: 'a1',
          requiresUserInput: true,
          warnings: const [
            ActionPlanWarning(code: 'CHECK', message: '단위를 확인해 주세요.'),
          ],
        ),
      ],
    );
    await tester.pumpWidget(_app(plan: plan, api: _FakeActionPlanApi(plan)));
    await tester.pumpAndSettle();

    expect(find.text('우유 두 개 사왔어.'), findsOneWidget);
    expect(find.text('수정 필요'), findsOneWidget);
    expect(find.text('단위를 확인해 주세요.'), findsOneWidget);
    expect(find.textContaining('신뢰도: 높음'), findsOneWidget);
    final execute = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, '반영 — 다음 단계에서 연결'),
    );
    expect(execute.onPressed, isNull);
  });

  testWidgets('deletes one action after confirmation', (tester) async {
    final plan = _plan(
      actions: [
        _action(actionId: 'a1'),
        _action(actionId: 'a2'),
      ],
    );
    final api = _FakeActionPlanApi(plan);
    await tester.pumpWidget(_app(plan: plan, api: api));
    await tester.pumpAndSettle();

    await tester.tap(find.text('삭제').first);
    await tester.pumpAndSettle();
    expect(find.text('이 Action을 삭제할까요?'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, '삭제'));
    await tester.pumpAndSettle();

    expect(api.deletedActionId, 'a1');
    expect(find.text('Action을 삭제했어요.'), findsOneWidget);
  });
}

Widget _app({required ActionPlan plan, required ActionPlanApi api}) {
  return ProviderScope(
    overrides: [
      actionPlanProvider('request-id').overrideWith((ref) async => plan),
      actionPlanApiProvider.overrideWithValue(api),
    ],
    child: const MaterialApp(home: ActionPlanPage(requestId: 'request-id')),
  );
}

ActionPlan _plan({required List<ActionPlanAction> actions}) {
  return ActionPlan(
    requestId: 'request-id',
    planId: 'plan-id',
    version: '1.0',
    transcript: '우유 두 개 사왔어.',
    summary: '재고 변경',
    requiresConfirmation: true,
    actions: actions,
    approved: false,
    executed: false,
    createdAt: DateTime.utc(2026, 7, 28),
  );
}

ActionPlanAction _action({
  required String actionId,
  bool requiresUserInput = false,
  List<ActionPlanWarning> warnings = const [],
}) {
  return ActionPlanAction(
    actionId: actionId,
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
    warnings: warnings,
    requiresUserInput: requiresUserInput,
  );
}

class _FakeActionPlanApi extends ActionPlanApi {
  _FakeActionPlanApi(this.plan) : super(Dio());

  final ActionPlan plan;
  String? deletedActionId;

  @override
  Future<ActionPlan> deleteAction({
    required String requestId,
    required String actionId,
  }) async {
    deletedActionId = actionId;
    return plan;
  }
}
