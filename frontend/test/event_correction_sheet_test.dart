import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/history/domain/history_event.dart';
import 'package:voice_inventory/features/history/presentation/event_correction_sheet.dart';

void main() {
  testWidgets(
    'correction sheet starts from the original direction and amount',
    (tester) async {
      final event = HistoryEvent(
        id: 'event-id',
        itemId: 'item-id',
        eventType: 'stock_out',
        quantity: 2,
        signedQuantity: -2,
        unit: '개',
        source: 'manual',
        note: '기존 메모',
        createdAt: DateTime.utc(2026, 7, 28),
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: Scaffold(
              body: Builder(
                builder: (context) => TextButton(
                  onPressed: () => showEventCorrectionSheet(
                    context: context,
                    event: event,
                    itemName: '우유',
                  ),
                  child: const Text('열기'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('열기'));
      await tester.pumpAndSettle();

      expect(find.text('기록 정정'), findsOneWidget);
      expect(find.textContaining('원본은 보존'), findsOneWidget);
      expect(find.text('소비'), findsOneWidget);
      final fields = tester.widgetList<TextFormField>(
        find.byType(TextFormField),
      );
      expect(fields.first.controller?.text, '2');
      expect(fields.last.controller?.text, '기존 메모');
    },
  );
}
