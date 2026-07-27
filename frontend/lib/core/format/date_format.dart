import 'package:intl/intl.dart';

final _dateTime = DateFormat('yyyy.MM.dd HH:mm');

/// Formats a UTC timestamp from the API in the device's local time.
String formatDateTime(DateTime value) => _dateTime.format(value.toLocal());
