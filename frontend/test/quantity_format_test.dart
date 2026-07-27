import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/core/format/quantity_format.dart';

void main() {
  group('formatQuantity', () {
    test('drops trailing zeros on whole numbers', () {
      expect(formatQuantity(3), '3');
      expect(formatQuantity(0), '0');
    });

    test('keeps significant decimals, trims trailing zeros', () {
      expect(formatQuantity(1.5), '1.5');
      expect(formatQuantity(1.250), '1.25');
    });
  });
}
