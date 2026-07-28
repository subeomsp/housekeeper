import 'package:dio/dio.dart';

import '../../../core/network/dio_client.dart';
import '../../inventory/data/inventory_api.dart';
import '../domain/history_event.dart';

class HistoryApi {
  HistoryApi(this._dio);

  final Dio _dio;

  Future<HistoryEventPage> fetchEvents({
    String? itemId,
    String? eventType,
    DateTime? from,
    DateTime? to,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/inventory-events',
        queryParameters: {
          if (itemId != null) 'item_id': itemId,
          if (eventType != null) 'event_type': eventType,
          if (from != null) 'from': from.toUtc().toIso8601String(),
          if (to != null) 'to': to.toUtc().toIso8601String(),
          'limit': limit,
          'offset': offset,
        },
      );
      return HistoryEventPage.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Future<List<HistoryItemReference>> fetchAllItems() async {
    const limit = 100;
    var offset = 0;
    final items = <HistoryItemReference>[];
    try {
      while (true) {
        final response = await _dio.get<Map<String, dynamic>>(
          '/inventory-items',
          queryParameters: {
            'include_inactive': true,
            'limit': limit,
            'offset': offset,
          },
        );
        final data = response.data ?? const {};
        final rawItems = data['items'] as List<dynamic>? ?? const [];
        items.addAll(
          rawItems.map(
            (item) =>
                HistoryItemReference.fromJson(item as Map<String, dynamic>),
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

  Future<HistoryMutationResult> correctEvent({
    required String eventId,
    required ManualInventoryEventType eventType,
    required num quantity,
    required String unit,
    String? note,
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/inventory-events/$eventId',
        data: {
          'event_type': eventType.apiValue,
          'quantity': quantity,
          'unit': unit,
          if (note != null && note.isNotEmpty) 'note': note,
        },
      );
      return _mutationResult(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Future<HistoryMutationResult> cancelEvent(String eventId) async {
    try {
      final response = await _dio.delete<Map<String, dynamic>>(
        '/inventory-events/$eventId',
      );
      return _mutationResult(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  HistoryMutationResult _mutationResult(Map<String, dynamic> data) {
    return HistoryMutationResult(
      previousQuantity: (data['previous_quantity'] as num).toDouble(),
      currentQuantity: (data['current_quantity'] as num).toDouble(),
    );
  }
}
