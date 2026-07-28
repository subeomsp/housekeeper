import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_inventory/features/history/domain/history_event.dart';
import 'package:voice_inventory/features/history/presentation/history_page.dart';
import 'package:voice_inventory/features/history/presentation/history_providers.dart';

void main() {
  testWidgets('history shows current item names and hides reversal actions', (
    tester,
  ) async {
    final normal = HistoryEvent(
      id: 'normal',
      itemId: 'item-id',
      eventType: 'stock_in',
      quantity: 2,
      signedQuantity: 2,
      unit: '개',
      source: 'manual',
      note: null,
      createdAt: DateTime.utc(2026, 7, 28),
    );
    final reversal = HistoryEvent(
      id: 'reversal',
      itemId: 'item-id',
      eventType: 'event_reversal',
      quantity: 2,
      signedQuantity: -2,
      unit: '개',
      source: 'correction',
      note: null,
      createdAt: DateTime.utc(2026, 7, 28, 1),
    );
    final item = HistoryItemReference(
      id: 'item-id',
      name: '우유',
      unit: '개',
      isActive: true,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          historyPageProvider.overrideWith(
            (ref) async => HistoryPageData(
              page: HistoryEventPage(items: [normal, reversal], total: 2),
              itemsById: {'item-id': item},
            ),
          ),
        ],
        child: const MaterialApp(home: HistoryPage()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('우유'), findsNWidgets(2));
    expect(find.text('+2 개'), findsOneWidget);
    expect(find.text('-2 개'), findsOneWidget);
    expect(find.byTooltip('기록 관리'), findsOneWidget);
    expect(find.text('총 2건'), findsOneWidget);
  });
}
