"""
マイグレーション用エンドポイント（本番環境でのみ使用）
"""

from flask import Blueprint, jsonify
from ..utils.db import get_db_connection

bp = Blueprint('migrate', __name__, url_prefix='/migrate')


@bp.route('/add_openai_key')
def add_openai_key():
    """openai_api_keyカラムを追加するマイグレーション"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # PostgreSQLかどうか確認
        is_pg = conn.__class__.__module__.startswith("psycopg2")
        
        if not is_pg:
            return jsonify({
                'status': 'error',
                'message': 'このマイグレーションはPostgreSQLのみ対応しています'
            }), 400
        
        # openai_api_keyカラムが存在するか確認
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'T_管理者' AND column_name = 'openai_api_key'
        """)
        
        if cur.fetchone():
            conn.close()
            return jsonify({
                'status': 'success',
                'message': 'openai_api_keyカラムは既に存在します'
            })
        
        # openai_api_keyカラムを追加
        cur.execute('''
            ALTER TABLE "T_管理者" 
            ADD COLUMN openai_api_key TEXT
        ''')
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'openai_api_keyカラムを追加しました'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'マイグレーション失敗: {str(e)}'
        }), 500



@bp.route('/init_all_tables')
def init_all_tables():
    """すべてのテーブルを作成するマイグレーション"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # PostgreSQLかどうか確認
        is_pg = conn.__class__.__module__.startswith("psycopg2")
        
        if not is_pg:
            return jsonify({
                'status': 'error',
                'message': 'このマイグレーションはPostgreSQLのみ対応しています'
            }), 400
        
        # init_schema()関数を呼び出してすべてのテーブルを作成
        from ..utils.db import init_schema
        init_schema(conn)
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'すべてのテーブルを作成しました'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'マイグレーション失敗: {str(e)}'
        }), 500


@bp.route('/add_admin_columns')
def add_admin_columns():
    """T_管理者テーブルにis_ownerとcan_manage_adminsカラムを追加"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # PostgreSQLかどうか確認
        is_pg = conn.__class__.__module__.startswith("psycopg2")
        
        if not is_pg:
            return jsonify({
                'status': 'error',
                'message': 'このマイグレーションはPostgreSQLのみ対応しています'
            }), 400
        
        # is_ownerカラムを追加
        cur.execute('''
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='T_管理者' AND column_name='is_owner'
        ''')
        if not cur.fetchone():
            cur.execute('ALTER TABLE "T_管理者" ADD COLUMN is_owner INTEGER DEFAULT 0')
            conn.commit()
        
        # can_manage_adminsカラムを追加
        cur.execute('''
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='T_管理者' AND column_name='can_manage_admins'
        ''')
        if not cur.fetchone():
            cur.execute('ALTER TABLE "T_管理者" ADD COLUMN can_manage_admins INTEGER DEFAULT 0')
            conn.commit()
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'is_ownerとcan_manage_adminsカラムを追加しました'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'マイグレーション失敗: {str(e)}'
        }), 500


@bp.route('/add_cutting_sheet_perimeter_system')
def add_cutting_sheet_perimeter_system():
    """カッティングシート文字周長計算機能のマイグレーション"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # PostgreSQLかどうか確認
        is_pg = conn.__class__.__module__.startswith("psycopg2")
        
        if not is_pg:
            return jsonify({
                'status': 'error',
                'message': 'このマイグレーションはPostgreSQLのみ対応しています'
            }), 400
        
        results = []
        
        # 1. T_文字周長係数テーブルを作成
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'T_文字周長係数'
        """)
        
        if not cur.fetchone():
            cur.execute('''
                CREATE TABLE "T_文字周長係数" (
                    "ID" SERIAL PRIMARY KEY,
                    "テナントID" INTEGER REFERENCES "T_テナント"("id") ON DELETE CASCADE,
                    "文字種類" VARCHAR(50) NOT NULL,
                    "係数" NUMERIC(5, 2) NOT NULL,
                    "説明" TEXT,
                    "作成日時" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    "更新日時" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE("テナントID", "文字種類")
                )
            ''')
            conn.commit()
            results.append('T_文字周長係数テーブルを作成しました')
            
            # デフォルト係数を挿入
            default_coefficients = [
                ('ひらがな', 6.0, 'ひらがなの平均的な周長係数'),
                ('カタカナ', 5.5, 'カタカナの平均的な周長係数'),
                ('漢字（簡単）', 7.0, '画数の少ない漢字（例：一、二、三、人、口）'),
                ('漢字（普通）', 8.5, '一般的な漢字（例：営、業、中、店、休）'),
                ('漢字（複雑）', 10.0, '画数の多い漢字（例：営、議、響、鬱）'),
                ('英数字（大文字）', 4.5, 'A-Z、0-9の大文字'),
                ('英数字（小文字）', 5.0, 'a-zの小文字'),
                ('記号', 6.5, '記号類（例：！、？、＆、＠）')
            ]
            
            for char_type, coeff, desc in default_coefficients:
                cur.execute('''
                    INSERT INTO "T_文字周長係数" ("テナントID", "文字種類", "係数", "説明")
                    VALUES (NULL, %s, %s, %s)
                ''', (char_type, coeff, desc))
            
            conn.commit()
            results.append('デフォルト係数8種類を挿入しました')
        else:
            results.append('T_文字周長係数テーブルは既に存在します')
        
        # 2. T_材質テーブルにsupports_text_processingカラムを追加
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'T_材質' AND column_name = 'supports_text_processing'
        """)
        
        if not cur.fetchone():
            cur.execute('''
                ALTER TABLE "T_材質" 
                ADD COLUMN "supports_text_processing" BOOLEAN DEFAULT FALSE
            ''')
            conn.commit()
            results.append('T_材質テーブルにsupports_text_processingカラムを追加しました')
        else:
            results.append('supports_text_processingカラムは既に存在します')
        
        # 3. T_看板見積もり明細テーブルに文字加工関連カラムを追加
        text_processing_columns = [
            ('文字加工モード', 'VARCHAR(20)'),
            ('文字内容', 'TEXT'),
            ('文字幅', 'NUMERIC(10, 2)'),
            ('文字高さ', 'NUMERIC(10, 2)'),
            ('文字種類ID', 'INTEGER'),
            ('推定周長', 'NUMERIC(10, 2)'),
            ('実測周長', 'NUMERIC(10, 2)'),
            ('周長単価', 'NUMERIC(10, 2)'),
            ('加工賃', 'INTEGER')
        ]
        
        for col_name, col_type in text_processing_columns:
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'T_看板見積もり明細' AND column_name = '{col_name}'
            """)
            
            if not cur.fetchone():
                cur.execute(f'''
                    ALTER TABLE "T_看板見積もり明細" 
                    ADD COLUMN "{col_name}" {col_type}
                ''')
                conn.commit()
                results.append(f'T_看板見積もり明細テーブルに{col_name}カラムを追加しました')
        
        # 4. T_文字明細テーブルを作成（1文字ずつモード用）
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'T_文字明細'
        """)
        
        if not cur.fetchone():
            cur.execute('''
                CREATE TABLE "T_文字明細" (
                    "ID" SERIAL PRIMARY KEY,
                    "見積もり明細ID" INTEGER NOT NULL REFERENCES "T_看板見積もり明細"("ID") ON DELETE CASCADE,
                    "順序" INTEGER NOT NULL,
                    "文字" VARCHAR(10) NOT NULL,
                    "幅" NUMERIC(10, 2) NOT NULL,
                    "高さ" NUMERIC(10, 2) NOT NULL,
                    "文字種類ID" INTEGER NOT NULL REFERENCES "T_文字周長係数"("ID"),
                    "推定周長" NUMERIC(10, 2) NOT NULL,
                    "作成日時" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    "更新日時" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            results.append('T_文字明細テーブルを作成しました')
        else:
            results.append('T_文字明細テーブルは既に存在します')
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'カッティングシート文字周長計算機能のマイグレーションが完了しました',
            'details': results
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'マイグレーション失敗: {str(e)}'
        }), 500
