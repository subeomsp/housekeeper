/// Formats a decimal quantity for display: trims trailing zeros so `3.000`
/// shows as `3` and `1.500` as `1.5`, while keeping up to 3 decimal places.
String formatQuantity(double value) {
  if (value == value.roundToDouble()) {
    return value.toStringAsFixed(0);
  }
  var text = value.toStringAsFixed(3);
  text = text.replaceFirst(RegExp(r'0+$'), '');
  text = text.replaceFirst(RegExp(r'\.$'), '');
  return text;
}
