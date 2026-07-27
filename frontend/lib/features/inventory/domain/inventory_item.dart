/// Business model for a current-inventory row (Snapshot-backed).
class InventoryItem {
  const InventoryItem({
    required this.itemId,
    required this.name,
    required this.quantity,
    required this.unit,
    required this.category,
    required this.isActive,
    required this.updatedAt,
  });

  final String itemId;
  final String name;
  final double quantity;
  final String unit;
  final String? category;
  final bool isActive;
  final DateTime updatedAt;

  factory InventoryItem.fromJson(Map<String, dynamic> json) {
    return InventoryItem(
      itemId: json['item_id'] as String,
      name: json['name'] as String,
      quantity: (json['quantity'] as num).toDouble(),
      unit: json['unit'] as String,
      category: json['category'] as String?,
      isActive: json['is_active'] as bool,
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}

/// A page of current inventory plus the total count for the household.
class InventoryPage {
  const InventoryPage({required this.items, required this.total});

  final List<InventoryItem> items;
  final int total;

  factory InventoryPage.fromJson(Map<String, dynamic> json) {
    final rawItems = (json['items'] as List<dynamic>? ?? const []);
    return InventoryPage(
      items: rawItems
          .map((e) => InventoryItem.fromJson(e as Map<String, dynamic>))
          .toList(growable: false),
      total: json['total'] as int? ?? 0,
    );
  }
}
