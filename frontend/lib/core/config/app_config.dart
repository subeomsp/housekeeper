/// Application-wide configuration.
///
/// The API base URL is provided at build/run time via a Dart define so the
/// same binary can point at local, Render, or a future production host:
///
///   flutter run -d macos --dart-define=API_BASE_URL=https://your-app.onrender.com
///
/// When no define is supplied, it falls back to [_defaultBaseUrl] below.
class AppConfig {
  const AppConfig._();

  /// Edit this to your Render URL, or override with --dart-define=API_BASE_URL.
  static const String _defaultBaseUrl = 'https://housekeeper-vo2q.onrender.com';

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: _defaultBaseUrl,
  );

  /// Versioned API prefix used by the FastAPI backend.
  static const String apiPrefix = '/api/v1';
}
