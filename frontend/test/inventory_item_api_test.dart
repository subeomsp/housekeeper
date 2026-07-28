import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/inventory/data/inventory_item_api.dart';

void main() {
  group('InventoryItemApi', () {
    test('loads active and archived items across every page', () async {
      final adapter = _QueueAdapter([
        {
          'items': [_itemJson(id: 'active', isActive: true)],
          'total': 2,
        },
        {
          'items': [_itemJson(id: 'archived', isActive: false)],
          'total': 2,
        },
      ]);

      final items = await InventoryItemApi(_dioWith(adapter)).fetchAllItems();

      expect(items.map((item) => item.id), ['active', 'archived']);
      expect(items.last.isActive, isFalse);
      expect(adapter.requests, hasLength(2));
      expect(adapter.requests.first.queryParameters['include_inactive'], true);
      expect(adapter.requests.last.queryParameters['offset'], 1);
    });

    test(
      'creates and updates item fields including category clearing',
      () async {
        final adapter = _QueueAdapter([
          _itemJson(id: 'created', isActive: true),
          _itemJson(id: 'created', isActive: true),
        ]);
        final api = InventoryItemApi(_dioWith(adapter));

        await api.createItem(name: '우유', unit: '개', category: '음료');
        await api.updateItem(
          itemId: 'created',
          name: '저지방 우유',
          unit: '개',
          category: '',
        );

        expect(adapter.requests.first.method, 'POST');
        expect(adapter.requests.first.path, '/inventory-items');
        expect(adapter.requests.first.data, {
          'name': '우유',
          'default_unit': '개',
          'category': '음료',
        });
        expect(adapter.requests.last.method, 'PATCH');
        expect(adapter.requests.last.path, '/inventory-items/created');
        expect(adapter.requests.last.data, {
          'name': '저지방 우유',
          'default_unit': '개',
          'category': null,
        });
      },
    );

    test('archives and restores through soft-delete endpoints', () async {
      final adapter = _QueueAdapter([
        _itemJson(id: 'item-id', isActive: false),
        _itemJson(id: 'item-id', isActive: true),
      ]);
      final api = InventoryItemApi(_dioWith(adapter));

      final archived = await api.archiveItem('item-id');
      final restored = await api.restoreItem('item-id');

      expect(adapter.requests.first.method, 'DELETE');
      expect(adapter.requests.first.path, '/inventory-items/item-id');
      expect(adapter.requests.last.method, 'POST');
      expect(adapter.requests.last.path, '/inventory-items/item-id/restore');
      expect(archived.isActive, isFalse);
      expect(restored.isActive, isTrue);
    });
  });
}

Map<String, dynamic> _itemJson({required String id, required bool isActive}) {
  return {
    'id': id,
    'name': '우유',
    'default_unit': '개',
    'category': null,
    'is_active': isActive,
    'current_quantity': 0,
  };
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
