class HistoryEvent {
  const HistoryEvent({
    required this.id,
    required this.itemId,
    required this.eventType,
    required this.quantity,
    required this.signedQuantity,
    required this.unit,
    required this.source,
    required this.note,
    required this.createdAt,
  });

  final String id;
  final String itemId;
  final String eventType;
  final double quantity;
  final double signedQuantity;
  final String unit;
  final String source;
  final String? note;
  final DateTime createdAt;

  bool get isReversal => eventType == 'event_reversal';

  factory HistoryEvent.fromJson(Map<String, dynamic> json) {
    return HistoryEvent(
      id: json['id'] as String,
      itemId: json['item_id'] as String,
      eventType: json['event_type'] as String,
      quantity: (json['quantity'] as num).toDouble(),
      signedQuantity: (json['signed_quantity'] as num).toDouble(),
      unit: json['unit'] as String,
      source: json['source'] as String,
      note: json['note'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class HistoryEventPage {
  const HistoryEventPage({required this.items, required this.total});

  final List<HistoryEvent> items;
  final int total;

  factory HistoryEventPage.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List<dynamic>? ?? const [];
    return HistoryEventPage(
      items: rawItems
          .map((item) => HistoryEvent.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
      total: json['total'] as int? ?? 0,
    );
  }
}

class HistoryItemReference {
  const HistoryItemReference({
    required this.id,
    required this.name,
    required this.unit,
    required this.isActive,
  });

  final String id;
  final String name;
  final String unit;
  final bool isActive;

  factory HistoryItemReference.fromJson(Map<String, dynamic> json) {
    return HistoryItemReference(
      id: json['id'] as String,
      name: json['name'] as String,
      unit: json['default_unit'] as String,
      isActive: json['is_active'] as bool,
    );
  }
}

class HistoryMutationResult {
  const HistoryMutationResult({
    required this.previousQuantity,
    required this.currentQuantity,
  });

  final double previousQuantity;
  final double currentQuantity;
}
