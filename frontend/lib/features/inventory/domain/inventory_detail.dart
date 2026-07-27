/// A single recent Inventory Event shown on the detail screen.
class RecentEvent {
  const RecentEvent({
    required this.id,
    required this.eventType,
    required this.quantity,
    required this.signedQuantity,
    required this.unit,
    required this.createdAt,
  });

  final String id;
  final String eventType;
  final double quantity;

  /// Backend-computed signed delta (positive = in, negative = out).
  final double signedQuantity;
  final String unit;
  final DateTime createdAt;

  factory RecentEvent.fromJson(Map<String, dynamic> json) {
    return RecentEvent(
      id: json['id'] as String,
      eventType: json['event_type'] as String,
      quantity: (json['quantity'] as num).toDouble(),
      signedQuantity: (json['signed_quantity'] as num).toDouble(),
      unit: json['unit'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

/// Item detail = current Snapshot + the ten most recent events (spec §68.7).
class InventoryDetail {
  const InventoryDetail({
    required this.itemId,
    required this.name,
    required this.quantity,
    required this.unit,
    required this.category,
    required this.isActive,
    required this.updatedAt,
    required this.recentEvents,
  });

  final String itemId;
  final String name;
  final double quantity;
  final String unit;
  final String? category;
  final bool isActive;
  final DateTime updatedAt;
  final List<RecentEvent> recentEvents;

  factory InventoryDetail.fromJson(Map<String, dynamic> json) {
    final rawEvents = (json['recent_events'] as List<dynamic>? ?? const []);
    return InventoryDetail(
      itemId: json['item_id'] as String,
      name: json['name'] as String,
      quantity: (json['quantity'] as num).toDouble(),
      unit: json['unit'] as String,
      category: json['category'] as String?,
      isActive: json['is_active'] as bool,
      updatedAt: DateTime.parse(json['updated_at'] as String),
      recentEvents: rawEvents
          .map((e) => RecentEvent.fromJson(e as Map<String, dynamic>))
          .toList(growable: false),
    );
  }
}
