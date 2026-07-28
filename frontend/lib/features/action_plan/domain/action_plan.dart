enum ActionPlanType {
  stockIn('stock_in', '입고', '+'),
  stockOut('stock_out', '소비', '−'),
  setQuantity('set_quantity', '현재 수량 설정', '=');

  const ActionPlanType(this.apiValue, this.label, this.symbol);

  final String apiValue;
  final String label;
  final String symbol;

  static ActionPlanType fromApi(String value) {
    return values.firstWhere((type) => type.apiValue == value);
  }
}

class ActionPlanWarning {
  const ActionPlanWarning({required this.code, required this.message});

  final String code;
  final String message;

  factory ActionPlanWarning.fromJson(Map<String, dynamic> json) {
    return ActionPlanWarning(
      code: json['code'] as String,
      message: json['message'] as String,
    );
  }
}

class ActionPlanItemReference {
  const ActionPlanItemReference({
    required this.rawName,
    required this.matchedItemId,
    required this.matchedName,
    required this.isNewItem,
    this.newItem,
  });

  final String rawName;
  final String? matchedItemId;
  final String? matchedName;
  final bool isNewItem;
  final ActionPlanNewItemDefinition? newItem;

  String get displayName => newItem?.name ?? matchedName ?? rawName;

  factory ActionPlanItemReference.fromJson(Map<String, dynamic> json) {
    return ActionPlanItemReference(
      rawName: json['raw_name'] as String,
      matchedItemId: json['matched_item_id'] as String?,
      matchedName: json['matched_name'] as String?,
      isNewItem: json['is_new_item'] as bool,
      newItem: json['new_item'] == null
          ? null
          : ActionPlanNewItemDefinition.fromJson(
              json['new_item'] as Map<String, dynamic>,
            ),
    );
  }
}

class ActionPlanNewItemDefinition {
  const ActionPlanNewItemDefinition({
    required this.name,
    required this.defaultUnit,
    required this.category,
    required this.rememberAlias,
  });

  final String name;
  final String defaultUnit;
  final String? category;
  final bool rememberAlias;

  factory ActionPlanNewItemDefinition.fromJson(Map<String, dynamic> json) {
    return ActionPlanNewItemDefinition(
      name: json['name'] as String,
      defaultUnit: json['default_unit'] as String,
      category: json['category'] as String?,
      rememberAlias: json['remember_alias'] as bool,
    );
  }
}

class ActionPlanQuantity {
  const ActionPlanQuantity({
    required this.rawValue,
    required this.rawUnit,
    required this.normalizedValue,
    required this.normalizedUnit,
    required this.conversionApplied,
    required this.conversionReason,
  });

  final double rawValue;
  final String rawUnit;
  final double? normalizedValue;
  final String? normalizedUnit;
  final bool conversionApplied;
  final String? conversionReason;

  double get displayValue => normalizedValue ?? rawValue;
  String get displayUnit => normalizedUnit ?? rawUnit;

  factory ActionPlanQuantity.fromJson(Map<String, dynamic> json) {
    return ActionPlanQuantity(
      rawValue: (json['raw_value'] as num).toDouble(),
      rawUnit: json['raw_unit'] as String,
      normalizedValue: (json['normalized_value'] as num?)?.toDouble(),
      normalizedUnit: json['normalized_unit'] as String?,
      conversionApplied: json['conversion_applied'] as bool,
      conversionReason: json['conversion_reason'] as String?,
    );
  }
}

class ActionPlanAction {
  const ActionPlanAction({
    required this.actionId,
    required this.type,
    required this.item,
    required this.quantity,
    required this.confidence,
    required this.warnings,
    required this.requiresUserInput,
  });

  final String actionId;
  final ActionPlanType type;
  final ActionPlanItemReference item;
  final ActionPlanQuantity quantity;
  final double confidence;
  final List<ActionPlanWarning> warnings;
  final bool requiresUserInput;

  String get confidenceLabel {
    if (confidence >= 0.9) return '높음';
    if (confidence >= 0.7) return '보통';
    return '낮음';
  }

  factory ActionPlanAction.fromJson(Map<String, dynamic> json) {
    final rawWarnings = json['warnings'] as List<dynamic>? ?? const [];
    return ActionPlanAction(
      actionId: json['action_id'] as String,
      type: ActionPlanType.fromApi(json['type'] as String),
      item: ActionPlanItemReference.fromJson(
        json['item'] as Map<String, dynamic>,
      ),
      quantity: ActionPlanQuantity.fromJson(
        json['quantity'] as Map<String, dynamic>,
      ),
      confidence: (json['confidence'] as num).toDouble(),
      warnings: rawWarnings
          .map(
            (warning) =>
                ActionPlanWarning.fromJson(warning as Map<String, dynamic>),
          )
          .toList(growable: false),
      requiresUserInput: json['requires_user_input'] as bool,
    );
  }
}

class ActionPlan {
  const ActionPlan({
    required this.requestId,
    required this.planId,
    required this.version,
    required this.transcript,
    required this.summary,
    required this.requiresConfirmation,
    required this.actions,
    required this.approved,
    required this.executed,
    required this.createdAt,
  });

  final String requestId;
  final String planId;
  final String version;
  final String transcript;
  final String summary;
  final bool requiresConfirmation;
  final List<ActionPlanAction> actions;
  final bool approved;
  final bool executed;
  final DateTime createdAt;

  factory ActionPlan.fromJson(Map<String, dynamic> json) {
    final rawActions = json['actions'] as List<dynamic>? ?? const [];
    return ActionPlan(
      requestId: json['request_id'] as String,
      planId: json['plan_id'] as String,
      version: json['version'] as String,
      transcript: json['transcript'] as String,
      summary: json['summary'] as String,
      requiresConfirmation: json['requires_confirmation'] as bool,
      actions: rawActions
          .map(
            (action) =>
                ActionPlanAction.fromJson(action as Map<String, dynamic>),
          )
          .toList(growable: false),
      approved: json['approved'] as bool,
      executed: json['executed'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class ActionPlanExecutionResult {
  const ActionPlanExecutionResult({
    required this.inventoryUpdated,
    required this.eventCount,
    required this.alreadyExecuted,
  });

  final bool inventoryUpdated;
  final int eventCount;
  final bool alreadyExecuted;

  factory ActionPlanExecutionResult.fromJson(Map<String, dynamic> json) {
    return ActionPlanExecutionResult(
      inventoryUpdated: json['inventory_updated'] as bool,
      eventCount: json['event_count'] as int,
      alreadyExecuted: json['already_executed'] as bool,
    );
  }
}
