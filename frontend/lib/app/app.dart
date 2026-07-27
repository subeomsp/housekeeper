import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'router.dart';
import 'theme.dart';

class VoiceInventoryApp extends StatefulWidget {
  const VoiceInventoryApp({super.key});

  @override
  State<VoiceInventoryApp> createState() => _VoiceInventoryAppState();
}

class _VoiceInventoryAppState extends State<VoiceInventoryApp> {
  late final GoRouter _router = buildRouter();

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Voice Inventory',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      routerConfig: _router,
    );
  }
}
