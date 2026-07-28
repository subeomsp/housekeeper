import 'package:dio/dio.dart';

import '../../../core/network/dio_client.dart';
import '../domain/inventory_catalog_item.dart';

class InventoryItemApi {
  InventoryItemApi(this._dio);

  final Dio _dio;

  Future<List<InventoryCatalogItem>> fetchAllItems({
    bool includeInactive = true,
  }) async {
    const limit = 100;
    var offset = 0;
    final items = <InventoryCatalogItem>[];
    try {
      while (true) {
        final response = await _dio.get<Map<String, dynamic>>(
          '/inventory-items',
          queryParameters: {
            'include_inactive': includeInactive,
            'limit': limit,
            'offset': offset,
          },
        );
        final data = response.data ?? const {};
        final rawItems = data['items'] as List<dynamic>? ?? const [];
        items.addAll(
          rawItems.map(
            (item) =>
                InventoryCatalogItem.fromJson(item as Map<String, dynamic>),
          ),
        );
        final total = data['total'] as int? ?? items.length;
        if (items.length >= total || rawItems.isEmpty) {
          return List.unmodifiable(items);
        }
        offset += rawItems.length;
      }
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Future<InventoryCatalogItem> createItem({
    required String name,
    required String unit,
    String? category,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/inventory-items',
        data: _itemBody(name: name, unit: unit, category: category),
      );
      return InventoryCatalogItem.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Future<InventoryCatalogItem> updateItem({
    required String itemId,
    required String name,
    required String unit,
    String? category,
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/inventory-items/$itemId',
        data: _itemBody(name: name, unit: unit, category: category),
      );
      return InventoryCatalogItem.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Future<InventoryCatalogItem> archiveItem(String itemId) async {
    try {
      final response = await _dio.delete<Map<String, dynamic>>(
        '/inventory-items/$itemId',
      );
      return InventoryCatalogItem.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Future<InventoryCatalogItem> restoreItem(String itemId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/inventory-items/$itemId/restore',
      );
      return InventoryCatalogItem.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Map<String, dynamic> _itemBody({
    required String name,
    required String unit,
    String? category,
  }) {
    return {
      'name': name,
      'default_unit': unit,
      'category': category == null || category.isEmpty ? null : category,
    };
  }
}
