#!/usr/bin/env python3
"""
マイグレーション自動実行スクリプト
Herokuのrelease phaseで実行される
"""
import os
import psycopg2
from pathlib import Path

def get_db_connection():
    """データベース接続を取得"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception('DATABASE_URL environment variable is not set')
    
    # Heroku PostgreSQL URLの形式を修正（postgres:// -> postgresql://）
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return psycopg2.connect(database_url, sslmode='require')

def create_migration_table(conn):
    """マイグレーション履歴テーブルを作成"""
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS "_migrations" (
                "id" SERIAL PRIMARY KEY,
                "filename" VARCHAR(255) NOT NULL UNIQUE,
                "executed_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        print("✓ マイグレーション履歴テーブルを作成しました")

def get_executed_migrations(conn):
    """実行済みマイグレーションのリストを取得"""
    with conn.cursor() as cur:
        cur.execute('SELECT "filename" FROM "_migrations" ORDER BY "id"')
        return {row[0] for row in cur.fetchall()}

def get_migration_files():
    """migrationsディレクトリ内のSQLファイルを取得"""
    migrations_dir = Path(__file__).parent / 'migrations'
    if not migrations_dir.exists():
        print(f"⚠ migrationsディレクトリが見つかりません: {migrations_dir}")
        return []
    
    sql_files = sorted(migrations_dir.glob('*.sql'))
    # README.mdなどを除外
    sql_files = [f for f in sql_files if f.name != 'README.md']
    return sql_files

def execute_migration(conn, filepath):
    """マイグレーションファイルを実行"""
    filename = filepath.name
    print(f"実行中: {filename}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        with conn.cursor() as cur:
            # SQLを実行
            cur.execute(sql)
            
            # 実行履歴を記録
            cur.execute(
                'INSERT INTO "_migrations" ("filename") VALUES (%s)',
                (filename,)
            )
            conn.commit()
            print(f"✓ {filename} を実行しました")
            return True
    except Exception as e:
        conn.rollback()
        print(f"✗ {filename} の実行に失敗しました: {e}")
        raise

def run_migrations():
    """未実行のマイグレーションを実行"""
    print("=" * 60)
    print("マイグレーション自動実行を開始します")
    print("=" * 60)
    
    try:
        # データベース接続
        conn = get_db_connection()
        print("✓ データベースに接続しました")
        
        # マイグレーション履歴テーブルを作成
        create_migration_table(conn)
        
        # 実行済みマイグレーションを取得
        executed = get_executed_migrations(conn)
        print(f"実行済みマイグレーション: {len(executed)}件")
        
        # マイグレーションファイルを取得
        migration_files = get_migration_files()
        print(f"マイグレーションファイル: {len(migration_files)}件")
        
        # 未実行のマイグレーションを実行
        pending = [f for f in migration_files if f.name not in executed]
        
        if not pending:
            print("✓ 実行すべきマイグレーションはありません")
        else:
            print(f"\n未実行のマイグレーション: {len(pending)}件")
            for filepath in pending:
                execute_migration(conn, filepath)
        
        conn.close()
        print("\n" + "=" * 60)
        print("マイグレーション完了")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ マイグレーションエラー: {e}")
        raise

if __name__ == '__main__':
    run_migrations()
