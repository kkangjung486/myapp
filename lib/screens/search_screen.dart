import 'package:flutter/material.dart';

import '../db/idea_database.dart';
import '../models/idea.dart';
import 'idea_form_screen.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  static const _accentColor = Color(0xFF0080F7);

  final _searchController = TextEditingController();
  List<Idea> _allIdeas = [];
  String _query = '';

  @override
  void initState() {
    super.initState();
    _loadIdeas();
    _searchController.addListener(() {
      setState(() {
        _query = _searchController.text.trim();
      });
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadIdeas() async {
    final ideas = await IdeaDatabase.instance.fetchAllIdeas();
    if (!mounted) return;
    setState(() {
      _allIdeas = ideas;
    });
  }

  Future<void> _openEditScreen(Idea idea) async {
    final updated = await Navigator.of(context).push<Idea>(
      MaterialPageRoute(builder: (_) => IdeaFormScreen(idea: idea)),
    );
    if (updated == null) return;
    await IdeaDatabase.instance.updateIdea(updated);
    await _loadIdeas();
  }

  List<Idea> get _filteredIdeas {
    if (_query.isEmpty) return [];
    final query = _query.toLowerCase();
    return _allIdeas
        .where(
          (idea) =>
              idea.title.toLowerCase().contains(query) ||
              idea.content.toLowerCase().contains(query),
        )
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('검색'),
        backgroundColor: _accentColor,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: '제목이나 내용으로 검색',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(
                    color: _accentColor,
                    width: 2,
                  ),
                ),
              ),
            ),
          ),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_query.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            '찾고 싶은 아이디어를 검색해보세요 🔍',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16, color: Colors.grey),
          ),
        ),
      );
    }

    final results = _filteredIdeas;

    if (results.isEmpty) {
      return const Center(
        child: Text(
          '찾는 아이디어가 없어요',
          style: TextStyle(fontSize: 16, color: Colors.grey),
        ),
      );
    }

    return ListView.separated(
      itemCount: results.length,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final idea = results[index];
        return ListTile(
          title: Text(idea.title, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(
            idea.content,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          onTap: () => _openEditScreen(idea),
        );
      },
    );
  }
}
