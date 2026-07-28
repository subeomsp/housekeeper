import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../features/action_plan/presentation/action_plan_page.dart';
import '../features/history/presentation/history_page.dart';
import '../features/home/presentation/home_page.dart';
import '../features/inventory/presentation/inventory_detail_page.dart';
import '../features/inventory/presentation/inventory_list_page.dart';
import '../features/inventory/presentation/archived_inventory_items_page.dart';
import '../features/settings/presentation/settings_page.dart';
import '../features/shell/home_shell.dart';

final _rootKey = GlobalKey<NavigatorState>();

/// App router (spec §27.1). A [StatefulShellRoute] hosts the four bottom-nav
/// tabs; item detail is a sub-route of the inventory branch so the nav bar and
/// tab state are preserved.
GoRouter buildRouter() {
  return GoRouter(
    navigatorKey: _rootKey,
    initialLocation: '/home',
    routes: [
      GoRoute(
        path: '/action-plan/:requestId',
        builder: (context, state) =>
            ActionPlanPage(requestId: state.pathParameters['requestId']!),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            HomeShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/home',
                builder: (context, state) => const HomePage(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/inventory',
                builder: (context, state) => const InventoryListPage(),
                routes: [
                  GoRoute(
                    path: 'archived',
                    builder: (context, state) =>
                        const ArchivedInventoryItemsPage(),
                  ),
                  GoRoute(
                    path: ':itemId',
                    builder: (context, state) => InventoryDetailPage(
                      itemId: state.pathParameters['itemId']!,
                    ),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/history',
                builder: (context, state) => const HistoryPage(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/settings',
                builder: (context, state) => const SettingsPage(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
}
