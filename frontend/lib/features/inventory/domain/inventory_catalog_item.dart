class InventoryCatalogItem {
  const InventoryCatalogItem({
    required this.id,
    required this.name,
    required this.unit,
    required this.category,
    required this.isActive,
    required this.currentQuantity,
  });

  final String id;
  final String name;
  final String unit;
  final String? category;
  final bool isActive;
  final double currentQuantity;

  factory InventoryCatalogItem.fromJson(Map<String, dynamic> json) {
    return InventoryCatalogItem(
      id: json['id'] as String,
      name: json['name'] as String,
      unit: json['default_unit'] as String,
      category: json['category'] as String?,
      isActive: json['is_active'] as bool,
      currentQuantity: (json['current_quantity'] as num).toDouble(),
    );
  }
}
