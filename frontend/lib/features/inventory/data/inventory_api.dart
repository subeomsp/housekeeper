import 'package:dio/dio.dart';

import '../../../core/network/dio_client.dart';
import '../domain/inventory_detail.dart';
import '../domain/inventory_item.dart';

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
}
