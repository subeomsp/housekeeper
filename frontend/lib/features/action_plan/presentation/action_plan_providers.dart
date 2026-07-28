import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_providers.dart';
import '../../inventory/domain/inventory_catalog_item.dart';
import '../../inventory/presentation/inventory_providers.dart';
import '../data/action_plan_api.dart';
import '../domain/action_plan.dart';

final actionPlanApiProvider = Provider<ActionPlanApi>((ref) {
  return ActionPlanApi(ref.watch(dioProvider));
});

final actionPlanProvider = FutureProvider.family<ActionPlan, String>((
  ref,
  requestId,
) {
  return ref.watch(actionPlanApiProvider).fetchPlan(requestId);
});

final actionPlanInventoryItemsProvider =
    FutureProvider<List<InventoryCatalogItem>>((ref) async {
      final items = await ref
          .watch(inventoryItemApiProvider)
          .fetchAllItems(includeInactive: false);
      return items.where((item) => item.isActive).toList(growable: false);
    });
