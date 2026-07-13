class Idea {
  final int? id;
  final String title;
  final String content;
  final bool isFavorite;
  final DateTime createdAt;

  const Idea({
    this.id,
    required this.title,
    required this.content,
    this.isFavorite = false,
    required this.createdAt,
  });

  Idea copyWith({
    int? id,
    String? title,
    String? content,
    bool? isFavorite,
    DateTime? createdAt,
  }) {
    return Idea(
      id: id ?? this.id,
      title: title ?? this.title,
      content: content ?? this.content,
      isFavorite: isFavorite ?? this.isFavorite,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  Map<String, Object?> toMap() {
    return {
      'id': id,
      'title': title,
      'content': content,
      'isFavorite': isFavorite ? 1 : 0,
      'createdAt': createdAt.toIso8601String(),
    };
  }

  factory Idea.fromMap(Map<String, Object?> map) {
    return Idea(
      id: map['id'] as int?,
      title: map['title'] as String,
      content: map['content'] as String,
      isFavorite: (map['isFavorite'] as int) == 1,
      createdAt: DateTime.parse(map['createdAt'] as String),
    );
  }
}
