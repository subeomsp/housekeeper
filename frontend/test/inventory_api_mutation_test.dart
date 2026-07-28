import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/inventory/data/inventory_api.dart';

void main() {
  group('InventoryApi mutations', () {
    test('forwards every inventory list control to the backend', () async {
      final adapter = _RecordingAdapter({'items': [], 'total': 0});
      final api = InventoryApi(_dioWith(adapter));

      await api.fetchInventory(
        search: '우유',
        category: '음료',
        includeZero: false,
        sort: 'name',
        order: 'asc',
        limit: 50,
        offset: 50,
      );

      expect(adapter.options?.method, 'GET');
      expect(adapter.options?.path, '/inventory');
      expect(adapter.options?.queryParameters, {
        'search': '우유',
        'category': '음료',
        'include_zero': false,
        'sort': 'name',
        'order': 'asc',
        'limit': 50,
        'offset': 50,
      });
    });

    test('creates a stock-in event with the backend contract', () async {
      final adapter = _RecordingAdapter({
        'previous_quantity': 2,
        'current_quantity': 3.5,
      });
      final api = InventoryApi(_dioWith(adapter));

      final result = await api.createManualEvent(
        itemId: 'item-id',
        eventType: ManualInventoryEventType.stockIn,
        quantity: 1.5,
        unit: '개',
        note: '마트',
      );

      expect(adapter.options?.method, 'POST');
      expect(adapter.options?.path, '/inventory-events');
      expect(adapter.options?.data, {
        'item_id': 'item-id',
        'event_type': 'stock_in',
        'quantity': 1.5,
        'unit': '개',
        'note': '마트',
      });
      expect(result.previousQuantity, 2);
      expect(result.currentQuantity, 3.5);
      expect(result.changed, isTrue);
    });

    test('sets a target quantity and preserves changed=false', () async {
      final adapter = _RecordingAdapter({
        'previous_quantity': 3,
        'current_quantity': 3,
        'changed': false,
      });
      final api = InventoryApi(_dioWith(adapter));

      final result = await api.setQuantity(
        itemId: 'item-id',
        quantity: 3,
        unit: '개',
        note: '',
      );

      expect(adapter.options?.method, 'PUT');
      expect(adapter.options?.path, '/inventory/item-id/quantity');
      expect(adapter.options?.data, {'quantity': 3, 'unit': '개'});
      expect(result.changed, isFalse);
    });
  });
}

Dio _dioWith(HttpClientAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'https://example.test/api/v1'));
  dio.httpClientAdapter = adapter;
  return dio;
}

class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter(this.response);

  final Map<String, dynamic> response;
  RequestOptions? options;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    this.options = options;
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
