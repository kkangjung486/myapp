import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../db/idea_database.dart';
import '../models/idea.dart';
import 'idea_form_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _dateFormat = DateFormat('yyyy.MM.dd HH:mm');
  late Future<List<Idea>> _ideasFuture;

  @override
  void initState() {
    super.initState();
    _loadIdeas();
  }

  void _loadIdeas() {
    _ideasFuture = IdeaDatabase.instance.fetchAllIdeas();
  }

  Future<void> _refresh() async {
    setState(_loadIdeas);
    await _ideasFuture;
  }

  Future<void> _openAddScreen() async {
    final newIdea = await Navigator.of(context).push<Idea>(
      MaterialPageRoute(builder: (_) => const IdeaFormScreen()),
    );
    if (newIdea == null) return;
    await IdeaDatabase.instance.insertIdea(newIdea);
    await _refresh();
  }

  Future<void> _openEditScreen(Idea idea) async {
    final updated = await Navigator.of(context).push<Idea>(
      MaterialPageRoute(builder: (_) => IdeaFormScreen(idea: idea)),
    );
    if (updated == null) return;
    await IdeaDatabase.instance.updateIdea(updated);
    await _refresh();
  }

  Future<void> _toggleFavorite(Idea idea) async {
    await IdeaDatabase.instance.updateIdea(
      idea.copyWith(isFavorite: !idea.isFavorite),
    );
    await _refresh();
  }

  Future<bool> _confirmDelete(Idea idea) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('아이디어 삭제'),
        content: Text('\'${idea.title}\' 아이디어를 삭제할까요?\n삭제하면 되돌릴 수 없습니다.'),
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
    return confirmed ?? false;
  }

  Future<void> _deleteIdea(Idea idea) async {
    await IdeaDatabase.instance.deleteIdea(idea.id!);
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('아이디어 저장소')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<Idea>>(
          future: _ideasFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }

            final ideas = snapshot.data ?? [];

            if (ideas.isEmpty) {
              return LayoutBuilder(
                builder: (context, constraints) => SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      minHeight: constraints.maxHeight,
                    ),
                    child: const Center(
                      child: Padding(
                        padding: EdgeInsets.all(24),
                        child: Text(
                          '아직 저장된 아이디어가 없어요.\n오른쪽 아래 + 버튼을 눌러 첫 아이디어를 남겨보세요.',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 16, color: Colors.grey),
                        ),
                      ),
                    ),
                  ),
                ),
              );
            }

            return ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              itemCount: ideas.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final idea = ideas[index];
                return Dismissible(
                  key: ValueKey(idea.id),
                  direction: DismissDirection.horizontal,
                  background: _buildDismissBackground(Alignment.centerLeft),
                  secondaryBackground: _buildDismissBackground(
                    Alignment.centerRight,
                  ),
                  confirmDismiss: (_) => _confirmDelete(idea),
                  onDismissed: (_) => _deleteIdea(idea),
                  child: ListTile(
                    title: Text(
                      idea.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          idea.content,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _dateFormat.format(idea.createdAt),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                    isThreeLine: true,
                    trailing: IconButton(
                      icon: Icon(
                        idea.isFavorite ? Icons.star : Icons.star_border,
                        color: idea.isFavorite ? Colors.amber : null,
                      ),
                      onPressed: () => _toggleFavorite(idea),
                      tooltip: '즐겨찾기',
                    ),
                    onTap: () => _openEditScreen(idea),
                    onLongPress: () async {
                      final confirmed = await _confirmDelete(idea);
                      if (confirmed) await _deleteIdea(idea);
                    },
                  ),
                );
              },
            );
          },
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _openAddScreen,
        tooltip: '새 아이디어 추가',
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildDismissBackground(Alignment alignment) {
    return Container(
      color: Colors.red,
      alignment: alignment,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: const Icon(Icons.delete, color: Colors.white),
    );
  }
}
