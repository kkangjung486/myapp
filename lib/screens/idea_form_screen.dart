import 'package:flutter/material.dart';

import '../models/idea.dart';

class IdeaFormScreen extends StatefulWidget {
  const IdeaFormScreen({super.key, this.idea});

  final Idea? idea;

  @override
  State<IdeaFormScreen> createState() => _IdeaFormScreenState();
}

class _IdeaFormScreenState extends State<IdeaFormScreen> {
  static const _accentColor = Color(0xFF0080F7);

  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _titleController;
  late final TextEditingController _contentController;

  bool get _isEditing => widget.idea != null;

  @override
  void initState() {
    super.initState();
    _titleController = TextEditingController(text: widget.idea?.title ?? '');
    _contentController = TextEditingController(
      text: widget.idea?.content ?? '',
    );
  }

  @override
  void dispose() {
    _titleController.dispose();
    _contentController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    final now = DateTime.now();
    final result = (widget.idea ?? Idea(title: '', content: '', createdAt: now))
        .copyWith(
      title: _titleController.text.trim(),
      content: _contentController.text.trim(),
    );

    await _showSavedDialog();
    if (!mounted) return;
    Navigator.of(context).pop(result);
  }

  Future<void> _showSavedDialog() {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => PopScope(
        canPop: false,
        child: AlertDialog(
          icon: const Icon(
            Icons.check_circle,
            color: Color(0xFF2E7D32),
            size: 48,
          ),
          content: const Text(
            '저장되었습니다!',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          actionsAlignment: MainAxisAlignment.center,
          actions: [
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('확인', style: TextStyle(fontSize: 16)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_isEditing ? '아이디어 수정' : '새 아이디어'),
        actions: [
          IconButton(
            onPressed: _save,
            icon: const Icon(Icons.check, color: _accentColor),
            tooltip: '저장',
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _titleController,
              decoration: const InputDecoration(
                labelText: '제목',
                border: OutlineInputBorder(
                  borderSide: BorderSide(color: _accentColor),
                ),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: _accentColor),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: _accentColor, width: 2),
                ),
              ),
              textInputAction: TextInputAction.next,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return '제목을 입력해 주세요';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _contentController,
              decoration: const InputDecoration(
                labelText: '내용',
                border: OutlineInputBorder(
                  borderSide: BorderSide(color: _accentColor),
                ),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: _accentColor),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: _accentColor, width: 2),
                ),
                alignLabelWithHint: true,
              ),
              minLines: 6,
              maxLines: 12,
              textInputAction: TextInputAction.newline,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return '내용을 입력해 주세요';
                }
                return null;
              },
            ),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              OutlinedButton(
                onPressed: () => Navigator.of(context).pop(),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Theme.of(context).colorScheme.error,
                  side: BorderSide(color: Theme.of(context).colorScheme.error),
                ),
                child: const Text('이전'),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _accentColor,
                  foregroundColor: Colors.white,
                ),
                child: const Text('저장'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
