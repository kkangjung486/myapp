import 'package:flutter/material.dart';

import 'screens/splash_screen.dart';

void main() {
  runApp(const IdeaVaultApp());
}

class IdeaVaultApp extends StatelessWidget {
  const IdeaVaultApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '아이디어 저장소',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const SplashScreen(),
    );
  }
}
