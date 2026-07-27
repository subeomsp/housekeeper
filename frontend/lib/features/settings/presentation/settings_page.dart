import 'package:flutter/material.dart';

import '../../../core/config/app_config.dart';

/// 설정 tab. Minimal for Phase 2 — shows which API host the app is talking to,
/// which is handy while pointing the app at Render vs local.
class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: ListView(
        children: [
          const ListTile(
            title: Text('API 서버'),
            subtitle: Text('앱이 연결된 백엔드 주소'),
          ),
          ListTile(
            leading: const Icon(Icons.cloud_outlined),
            title: Text(AppConfig.apiBaseUrl),
            subtitle: Text('${AppConfig.apiPrefix} · Phase 2'),
          ),
        ],
      ),
    );
  }
}
