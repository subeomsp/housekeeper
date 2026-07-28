import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/history/data/history_api.dart';
import 'package:voice_inventory/features/inventory/data/inventory_api.dart';

void main() {
  group('HistoryApi', () {
    test('sends event filters and pagination using backend aliases', () async {
      final adapter = _QueueAdapter([
        {
          'items': [
            {
              'id': 'event-id',
              'item_id': 'item-id',
              'event_type': 'stock_out',
              'quantity': 2,
              'signed_quantity': -2,
              'unit': '개',
              'source': 'manual',
              'note': null,
              'created_at': '2026-07-28T01:00:00Z',
            },
          ],
          'total': 1,
        },
      ]);
      final api = HistoryApi(_dioWith(adapter));
      final from = DateTime.parse('2026-07-01T00:00:00+09:00');
      final to = DateTime.parse('2026-07-31T23:59:59+09:00');

      final page = await api.fetchEvents(
        itemId: 'item-id',
        eventType: 'stock_out',
        from: from,
        to: to,
        limit: 50,
        offset: 50,
      );

      final request = adapter.requests.single;
      expect(request.path, '/inventory-events');
      expect(request.queryParameters, {
        'item_id': 'item-id',
        'event_type': 'stock_out',
        'from': from.toUtc().toIso8601String(),
        'to': to.toUtc().toIso8601String(),
        'limit': 50,
        'offset': 50,
      });
      expect(page.total, 1);
      expect(page.items.single.signedQuantity, -2);
    });

    test('loads all active and archived item references', () async {
      final adapter = _QueueAdapter([
        {
          'items': [
            {
              'id': 'active',
              'name': '우유',
              'default_unit': '개',
              'is_active': true,
            },
          ],
          'total': 2,
        },
        {
          'items': [
            {
              'id': 'archived',
              'name': '주스',
              'default_unit': '병',
              'is_active': false,
            },
          ],
          'total': 2,
        },
      ]);

      final items = await HistoryApi(_dioWith(adapter)).fetchAllItems();

      expect(items.map((item) => item.name), ['우유', '주스']);
      expect(items.last.isActive, isFalse);
      expect(adapter.requests, hasLength(2));
      expect(adapter.requests.first.queryParameters['include_inactive'], true);
      expect(adapter.requests.last.queryParameters['offset'], 1);
    });

    test('corrects and cancels without modifying the original event', () async {
      final adapter = _QueueAdapter([
        {'previous_quantity': 5, 'current_quantity': 4},
        {'previous_quantity': 4, 'current_quantity': 6},
      ]);
      final api = HistoryApi(_dioWith(adapter));

      final corrected = await api.correctEvent(
        eventId: 'event-id',
        eventType: ManualInventoryEventType.stockOut,
        quantity: 1,
        unit: '개',
        note: '정정',
      );
      final cancelled = await api.cancelEvent('replacement-id');

      expect(adapter.requests.first.method, 'PATCH');
      expect(adapter.requests.first.path, '/inventory-events/event-id');
      expect(adapter.requests.first.data, {
        'event_type': 'stock_out',
        'quantity': 1,
        'unit': '개',
        'note': '정정',
      });
      expect(adapter.requests.last.method, 'DELETE');
      expect(adapter.requests.last.path, '/inventory-events/replacement-id');
      expect(corrected.currentQuantity, 4);
      expect(cancelled.currentQuantity, 6);
    });
  });
}

Dio _dioWith(HttpClientAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'https://example.test/api/v1'));
  dio.httpClientAdapter = adapter;
  return dio;
}

class _QueueAdapter implements HttpClientAdapter {
  _QueueAdapter(this._responses);

  final List<Map<String, dynamic>> _responses;
  final requests = <RequestOptions>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return ResponseBody.fromString(
      jsonEncode(_responses.removeAt(0)),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
