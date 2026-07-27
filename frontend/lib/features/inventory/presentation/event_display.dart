import 'package:flutter/material.dart';

/// Human-readable Korean label for a backend event type.
String eventTypeLabel(String eventType) {
  switch (eventType) {
    case 'stock_in':
      return '입고';
    case 'stock_out':
      return '소비';
    case 'adjustment_in':
      return '조정 증가';
    case 'adjustment_out':
      return '조정 감소';
    case 'initial_stock':
      return '초기 재고';
    case 'event_reversal':
      return '취소·되돌림';
    default:
      return eventType;
  }
}

/// Color cue for an event based on the sign of its quantity delta.
Color eventDeltaColor(double signedQuantity, BuildContext context) {
  if (signedQuantity > 0) return Colors.green.shade700;
  if (signedQuantity < 0) return Colors.redAccent;
  return Theme.of(context).colorScheme.onSurfaceVariant;
}

/// A signed prefix for display, e.g. `+2`, `-1`, `0`.
String signedPrefix(double signedQuantity) {
  if (signedQuantity > 0) return '+';
  return '';
}
