import 'package:flutter/material.dart';

import '../db/idea_database.dart';
import '../models/idea.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  static const _accentColor = Color(0xFF0080F7);

  late Future<List<Idea>> _ideasFuture;

  @override
  void initState() {
    super.initState();
    _loadIdeas();
  }

  void _loadIdeas() {
    _ideasFuture = IdeaDatabase.instance.fetchAllIdeas();
  }

  Future<void> _confirmDeleteAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('전체 삭제'),
        content: const Text('정말 다 지울까요?\n삭제하면 되돌릴 수 없습니다.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('삭제'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await IdeaDatabase.instance.deleteAllIdeas();
      setState(_loadIdeas);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('설정'),
        backgroundColor: _accentColor,
        foregroundColor: Colors.white,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '아이디어 저장소',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            FutureBuilder<List<Idea>>(
              future: _ideasFuture,
              builder: (context, snapshot) {
                final count = snapshot.data?.length ?? 0;
                return Text(
                  '저장된 아이디어: $count개',
                  style: const TextStyle(fontSize: 16, color: Colors.grey),
                );
              },
            ),
            const Spacer(),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _confirmDeleteAll,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  foregroundColor: Colors.white,
                ),
                child: const Text('전체 삭제'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
