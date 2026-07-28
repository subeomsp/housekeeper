import 'package:dio/dio.dart';

import '../../../core/network/dio_client.dart';
import '../domain/inventory_detail.dart';
import '../domain/inventory_item.dart';

enum ManualInventoryEventType {
  stockIn('stock_in'),
  stockOut('stock_out');

  const ManualInventoryEventType(this.apiValue);

  final String apiValue;
}

/// Thin API client for the inventory endpoints. Converts Dio failures into the
/// app's [ApiException] via [mapDioError] so callers only deal with one type.
class InventoryApi {
  InventoryApi(this._dio);

  final Dio _dio;

  /// GET /inventory — current inventory list for the (fixed) household.
  Future<InventoryPage> fetchInventory({
    String? search,
    String? category,
    bool includeZero = true,
    String sort = 'updated_at',
    String order = 'desc',
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/inventory',
        queryParameters: {
          if (search != null && search.isNotEmpty) 'search': search,
          if (category != null && category.isNotEmpty) 'category': category,
          'include_zero': includeZero,
          'sort': sort,
          'order': order,
          'limit': limit,
          'offset': offset,
        },
      );
      return InventoryPage.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  /// GET /inventory/{itemId} — Snapshot + ten most recent events.
  Future<InventoryDetail> fetchDetail(String itemId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/inventory/$itemId',
      );
      return InventoryDetail.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  /// POST /inventory-events — records a manual stock-in or stock-out delta.
  Future<InventoryMutationResult> createManualEvent({
    required String itemId,
    required ManualInventoryEventType eventType,
    required num quantity,
    required String unit,
    String? note,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/inventory-events',
        data: {
          'item_id': itemId,
          'event_type': eventType.apiValue,
          'quantity': quantity,
          'unit': unit,
          if (note != null && note.isNotEmpty) 'note': note,
        },
      );
      final data = response.data ?? const {};
      return InventoryMutationResult(
        previousQuantity: (data['previous_quantity'] as num).toDouble(),
        currentQuantity: (data['current_quantity'] as num).toDouble(),
        changed: true,
      );
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  /// PUT /inventory/{itemId}/quantity — sets a final target quantity.
  ///
  /// The backend derives and persists an adjustment event; the client never
  /// writes the Snapshot directly.
  Future<InventoryMutationResult> setQuantity({
    required String itemId,
    required num quantity,
    required String unit,
    String? note,
  }) async {
    try {
      final response = await _dio.put<Map<String, dynamic>>(
        '/inventory/$itemId/quantity',
        data: {
          'quantity': quantity,
          'unit': unit,
          if (note != null && note.isNotEmpty) 'note': note,
        },
      );
      final data = response.data ?? const {};
      return InventoryMutationResult(
        previousQuantity: (data['previous_quantity'] as num).toDouble(),
        currentQuantity: (data['current_quantity'] as num).toDouble(),
        changed: data['changed'] as bool,
      );
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }
}

class InventoryMutationResult {
  const InventoryMutationResult({
    required this.previousQuantity,
    required this.currentQuantity,
    required this.changed,
  });

  final double previousQuantity;
  final double currentQuantity;
  final bool changed;
}
