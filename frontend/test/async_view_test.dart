import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/core/errors/api_exception.dart';
import 'package:voice_inventory/core/widgets/async_view.dart';

void main() {
  testWidgets('API failure is shown as an error and never as empty data', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: AsyncView<String>(
          value: AsyncValue.error(
            const ApiException(
              code: 'NETWORK_ERROR',
              message: '네트워크를 확인해 주세요.',
            ),
            StackTrace.empty,
          ),
          onData: (value) => Text(value),
          onRetry: () {},
          isEmpty: (_) => true,
          emptyMessage: '비어 있어요.',
        ),
      ),
    );

    expect(find.text('네트워크를 확인해 주세요.'), findsOneWidget);
    expect(find.text('다시 시도'), findsOneWidget);
    expect(find.text('비어 있어요.'), findsNothing);
  });
}
