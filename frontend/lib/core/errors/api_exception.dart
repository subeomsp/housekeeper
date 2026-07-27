/// A normalized error surfaced to the presentation layer.
///
/// The backend uses a common envelope: `{"error": {"code", "message", "details"}}`.
/// Network/timeout failures that never reach the backend are mapped to
/// [ApiException] as well, with a synthetic [code].
class ApiException implements Exception {
  const ApiException({
    required this.code,
    required this.message,
    this.statusCode,
    this.details,
  });

  /// Backend error code (e.g. `ITEM_NOT_FOUND`) or a synthetic transport code
  /// such as `NETWORK_ERROR` / `TIMEOUT` / `UNKNOWN`.
  final String code;

  /// Human-readable message safe to display.
  final String message;

  /// HTTP status code when the request reached the server.
  final int? statusCode;

  /// Optional structured details from the backend envelope.
  final Object? details;

  bool get isNetwork => code == 'NETWORK_ERROR' || code == 'TIMEOUT';

  @override
  String toString() => 'ApiException($code, $message)';
}
