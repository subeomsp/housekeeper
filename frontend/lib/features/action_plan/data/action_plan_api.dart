import 'package:dio/dio.dart';

import '../../../core/network/dio_client.dart';
import '../domain/action_plan.dart';

class ActionPlanApi {
  ActionPlanApi(this._dio);

  final Dio _dio;

  Future<ActionPlan> createFromTranscript(String transcript) async {
    try {
      final requestResponse = await _dio.post<Map<String, dynamic>>(
        '/voice-requests/text',
        data: {'transcript': transcript},
      );
      final requestId = requestResponse.data?['request_id'] as String;
      final planResponse = await _dio.post<Map<String, dynamic>>(
        '/voice-requests/$requestId/action-plan',
      );
      return ActionPlan.fromJson(planResponse.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Future<ActionPlan> fetchPlan(String requestId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/action-plan/$requestId',
      );
      return ActionPlan.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Future<ActionPlan> updateAction({
    required String requestId,
    required String actionId,
    required ActionPlanType type,
    required String itemId,
    required num quantity,
    required String unit,
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/action-plan/$requestId/actions/$actionId',
        data: {
          'type': type.apiValue,
          'item_id': itemId,
          'quantity': quantity,
          'unit': unit,
        },
      );
      return ActionPlan.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }

  Future<ActionPlan> deleteAction({
    required String requestId,
    required String actionId,
  }) async {
    try {
      final response = await _dio.delete<Map<String, dynamic>>(
        '/action-plan/$requestId/actions/$actionId',
      );
      return ActionPlan.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw mapDioError(error);
    }
  }
}
