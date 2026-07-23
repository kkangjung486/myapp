import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

import '../models/idea.dart';

class IdeaDatabase {
  IdeaDatabase._internal();

  static final IdeaDatabase instance = IdeaDatabase._internal();

  static const _databaseName = 'idea_vault.db';
  static const _databaseVersion = 1;
  static const table = 'ideas';

  Database? _database;

  Future<Database> get database async {
    _database ??= await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    final path = join(await getDatabasesPath(), _databaseName);
    return openDatabase(
      path,
      version: _databaseVersion,
      onCreate: (db, version) {
        return db.execute('''
          CREATE TABLE $table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            isFavorite INTEGER NOT NULL DEFAULT 0,
            createdAt TEXT NOT NULL
          )
        ''');
      },
    );
  }

  Future<Idea> insertIdea(Idea idea) async {
    final db = await database;
    final id = await db.insert(table, idea.toMap()..remove('id'));
    return idea.copyWith(id: id);
  }

  Future<int> updateIdea(Idea idea) async {
    final db = await database;
    return db.update(
      table,
      idea.toMap(),
      where: 'id = ?',
      whereArgs: [idea.id],
    );
  }

  Future<int> deleteIdea(int id) async {
    final db = await database;
    return db.delete(table, where: 'id = ?', whereArgs: [id]);
  }

  Future<int> deleteAllIdeas() async {
    final db = await database;
    return db.delete(table);
  }

  Future<List<Idea>> fetchAllIdeas() async {
    final db = await database;
    final maps = await db.query(table, orderBy: 'createdAt DESC');
    return maps.map(Idea.fromMap).toList();
  }
}
