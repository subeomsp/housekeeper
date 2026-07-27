import 'package:dio/dio.dart';

import '../config/app_config.dart';
import '../errors/api_exception.dart';

/// Builds the shared [Dio] instance and maps transport/backend failures into a
/// single [ApiException] type so the rest of the app never touches Dio errors.
Dio buildDio() {
  final dio = Dio(
    BaseOptions(
      baseUrl: '${AppConfig.apiBaseUrl}${AppConfig.apiPrefix}',
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 20),
      sendTimeout: const Duration(seconds: 20),
      headers: {'content-type': 'application/json'},
      // We inspect status codes ourselves; do not throw on non-2xx.
      validateStatus: (status) => status != null && status < 500,
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onResponse: (response, handler) {
        final status = response.statusCode ?? 0;
        if (status >= 200 && status < 300) {
          handler.next(response);
          return;
        }
        handler.reject(_asDioError(response.requestOptions, response));
      },
      onError: (error, handler) {
        handler.reject(error);
      },
    ),
  );

  return dio;
}

DioException _asDioError(RequestOptions options, Response<dynamic> response) {
  return DioException(
    requestOptions: options,
    response: response,
    type: DioExceptionType.badResponse,
  );
}

/// Translates a [DioException] into the app's [ApiException].
ApiException mapDioError(DioException error) {
  switch (error.type) {
    case DioExceptionType.connectionTimeout:
    case DioExceptionType.sendTimeout:
    case DioExceptionType.receiveTimeout:
    case DioExceptionType.transformTimeout:
      return const ApiException(
        code: 'TIMEOUT',
        message: '서버 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요.',
      );
    case DioExceptionType.connectionError:
    case DioExceptionType.unknown:
      return const ApiException(
        code: 'NETWORK_ERROR',
        message: '서버에 연결할 수 없어요. 네트워크 상태를 확인해 주세요.',
      );
    case DioExceptionType.badResponse:
      return _fromResponse(error.response);
    case DioExceptionType.cancel:
      return const ApiException(code: 'CANCELLED', message: '요청이 취소되었어요.');
    case DioExceptionType.badCertificate:
      return const ApiException(
        code: 'NETWORK_ERROR',
        message: '보안 연결에 실패했어요.',
      );
  }
}

ApiException _fromResponse(Response<dynamic>? response) {
  final status = response?.statusCode;
  final data = response?.data;
  if (data is Map && data['error'] is Map) {
    final envelope = data['error'] as Map;
    return ApiException(
      code: (envelope['code'] as String?) ?? 'UNKNOWN',
      message: (envelope['message'] as String?) ?? '알 수 없는 오류가 발생했어요.',
      statusCode: status,
      details: envelope['details'],
    );
  }
  return ApiException(
    code: 'UNKNOWN',
    message: '알 수 없는 오류가 발생했어요. (HTTP ${status ?? '?'})',
    statusCode: status,
  );
}
