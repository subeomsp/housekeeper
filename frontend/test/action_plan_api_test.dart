import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/action_plan/data/action_plan_api.dart';
import 'package:voice_inventory/features/action_plan/domain/action_plan.dart';

void main() {
  test('text flow creates a request and then generates its plan', () async {
    final adapter = _ActionPlanAdapter();
    final api = ActionPlanApi(_dioWith(adapter));

    final plan = await api.createFromTranscript('우유 두 개 사왔어.');

    expect(adapter.requests, hasLength(2));
    expect(adapter.requests[0].method, 'POST');
    expect(adapter.requests[0].path, '/voice-requests/text');
    expect(adapter.requests[0].data, {'transcript': '우유 두 개 사왔어.'});
    expect(adapter.requests[1].path, '/voice-requests/request-id/action-plan');
    expect(plan.requestId, 'request-id');
  });

  test('fetches, edits, and deletes through the backend contracts', () async {
    final adapter = _ActionPlanAdapter();
    final api = ActionPlanApi(_dioWith(adapter));

    await api.fetchPlan('request-id');
    await api.updateAction(
      requestId: 'request-id',
      actionId: 'a1',
      type: ActionPlanType.setQuantity,
      itemId: 'item-id',
      quantity: 0,
      unit: '개',
    );
    await api.resolveNewItem(
      requestId: 'request-id',
      actionId: 'a1',
      type: ActionPlanType.stockIn,
      name: '아몬드브리즈',
      defaultUnit: '개',
      category: '음료',
      quantity: 2,
      rememberAlias: true,
    );
    await api.deleteAction(requestId: 'request-id', actionId: 'a2');

    expect(adapter.requests[0].method, 'GET');
    expect(adapter.requests[0].path, '/action-plan/request-id');
    expect(adapter.requests[1].method, 'PATCH');
    expect(adapter.requests[1].path, '/action-plan/request-id/actions/a1');
    expect(adapter.requests[1].data, {
      'type': 'set_quantity',
      'item_id': 'item-id',
      'quantity': 0,
      'unit': '개',
      'remember_alias': false,
    });
    expect(adapter.requests[2].method, 'POST');
    expect(
      adapter.requests[2].path,
      '/action-plan/request-id/actions/a1/new-item',
    );
    expect(adapter.requests[2].data, {
      'type': 'stock_in',
      'name': '아몬드브리즈',
      'default_unit': '개',
      'category': '음료',
      'quantity': 2,
      'remember_alias': true,
    });
    expect(adapter.requests[3].method, 'DELETE');
    expect(adapter.requests[3].path, '/action-plan/request-id/actions/a2');
  });
}

Map<String, dynamic> planJson() {
  return {
    'request_id': 'request-id',
    'plan_id': 'plan-id',
    'version': '1.0',
    'transcript': '우유 두 개 사왔어.',
    'summary': '우유 2개 입고',
    'requires_confirmation': true,
    'actions': [
      {
        'action_id': 'a1',
        'type': 'stock_in',
        'item': {
          'raw_name': '우유',
          'matched_item_id': 'item-id',
          'matched_name': '우유',
          'is_new_item': false,
        },
        'quantity': {
          'raw_value': 2,
          'raw_unit': '개',
          'normalized_value': 2,
          'normalized_unit': '개',
          'conversion_applied': false,
          'conversion_reason': null,
        },
        'confidence': 0.98,
        'warnings': [],
        'requires_user_input': false,
      },
    ],
    'approved': false,
    'executed': false,
    'created_at': '2026-07-28T14:00:00Z',
  };
}

Dio _dioWith(HttpClientAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'https://example.test/api/v1'));
  dio.httpClientAdapter = adapter;
  return dio;
}

class _ActionPlanAdapter implements HttpClientAdapter {
  final requests = <RequestOptions>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    final response = options.path == '/voice-requests/text'
        ? {
            'request_id': 'request-id',
            'transcript': '우유 두 개 사왔어.',
            'status': 'planning',
            'created_at': '2026-07-28T14:00:00Z',
          }
        : planJson();
    return ResponseBody.fromString(
      jsonEncode(response),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
