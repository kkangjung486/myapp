import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:idea_vault/main.dart';

void main() {
  testWidgets('Home screen shows app title and empty state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const IdeaVaultApp());
    await tester.pump();

    expect(find.text('아이디어 저장소'), findsOneWidget);
    expect(find.byIcon(Icons.add), findsOneWidget);
  });
}
