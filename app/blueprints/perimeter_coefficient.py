"""
文字周長係数マスタ管理Blueprint
カッティングシート文字の周長計算用の係数を管理
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.utils.decorators import require_roles, require_app_enabled
from app.utils.db import get_db_connection

perimeter_coefficient_bp = Blueprint('perimeter_coefficient', __name__, url_prefix='/perimeter_coefficient')

@perimeter_coefficient_bp.route('/')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def index():
    """文字周長係数一覧"""
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('ログインが必要です', 'error')
        return redirect(url_for('select_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # デフォルト係数（全テナント共通）とテナント固有の係数を取得
    cur.execute('''
        SELECT "ID", "文字種類", "係数", "説明", "テナントID", "更新日時"
        FROM "T_文字周長係数"
        WHERE "テナントID" IS NULL OR "テナントID" = %s
        ORDER BY 
            CASE "文字種類"
                WHEN 'ひらがな' THEN 1
                WHEN 'カタカナ' THEN 2
                WHEN '漢字（簡単）' THEN 3
                WHEN '漢字（普通）' THEN 4
                WHEN '漢字（複雑）' THEN 5
                WHEN '英数字（大文字）' THEN 6
                WHEN '英数字（小文字）' THEN 7
                WHEN '記号' THEN 8
                ELSE 99
            END,
            "テナントID" NULLS FIRST
    ''', (tenant_id,))
    
    coefficients = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('perimeter_coefficient_list.html', coefficients=coefficients)

@perimeter_coefficient_bp.route('/new', methods=['GET', 'POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def new():
    """文字周長係数新規作成"""
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('ログインが必要です', 'error')
        return redirect(url_for('select_login'))
    
    if request.method == 'POST':
        char_type = request.form.get('char_type')
        coefficient = request.form.get('coefficient')
        description = request.form.get('description', '')
        
        if not char_type or not coefficient:
            flash('文字種類と係数は必須です', 'error')
            return redirect(url_for('perimeter_coefficient.new'))
        
        try:
            coefficient = float(coefficient)
            if coefficient <= 0:
                flash('係数は正の数値を入力してください', 'error')
                return redirect(url_for('perimeter_coefficient.new'))
        except ValueError:
            flash('係数は数値を入力してください', 'error')
            return redirect(url_for('perimeter_coefficient.new'))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID")
                VALUES (%s, %s, %s, %s)
            ''', (char_type, coefficient, description, tenant_id))
            
            conn.commit()
            flash('文字周長係数を登録しました', 'success')
            return redirect(url_for('perimeter_coefficient.index'))
        except Exception as e:
            conn.rollback()
            flash(f'エラーが発生しました: {str(e)}', 'error')
            return redirect(url_for('perimeter_coefficient.new'))
        finally:
            cur.close()
            conn.close()
    
    return render_template('perimeter_coefficient_new.html')

@perimeter_coefficient_bp.route('/edit/<int:coefficient_id>', methods=['GET', 'POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def edit(coefficient_id):
    """文字周長係数編集"""
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('ログインが必要です', 'error')
        return redirect(url_for('select_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        char_type = request.form.get('char_type')
        coefficient = request.form.get('coefficient')
        description = request.form.get('description', '')
        
        if not char_type or not coefficient:
            flash('文字種類と係数は必須です', 'error')
            return redirect(url_for('perimeter_coefficient.edit', coefficient_id=coefficient_id))
        
        try:
            coefficient = float(coefficient)
            if coefficient <= 0:
                flash('係数は正の数値を入力してください', 'error')
                return redirect(url_for('perimeter_coefficient.edit', coefficient_id=coefficient_id))
        except ValueError:
            flash('係数は数値を入力してください', 'error')
            return redirect(url_for('perimeter_coefficient.edit', coefficient_id=coefficient_id))
        
        try:
            # テナント固有の係数のみ編集可能（デフォルト係数は編集不可）
            cur.execute('''
                UPDATE "T_文字周長係数"
                SET "文字種類" = %s, "係数" = %s, "説明" = %s, "更新日時" = CURRENT_TIMESTAMP
                WHERE "ID" = %s AND "テナントID" = %s
            ''', (char_type, coefficient, description, coefficient_id, tenant_id))
            
            if cur.rowcount == 0:
                flash('デフォルト係数は編集できません。新規作成してください。', 'error')
                return redirect(url_for('perimeter_coefficient.index'))
            
            conn.commit()
            flash('文字周長係数を更新しました', 'success')
            return redirect(url_for('perimeter_coefficient.index'))
        except Exception as e:
            conn.rollback()
            flash(f'エラーが発生しました: {str(e)}', 'error')
            return redirect(url_for('perimeter_coefficient.edit', coefficient_id=coefficient_id))
        finally:
            cur.close()
            conn.close()
    
    # GET: 係数情報を取得
    cur.execute('''
        SELECT "ID", "文字種類", "係数", "説明", "テナントID"
        FROM "T_文字周長係数"
        WHERE "ID" = %s AND ("テナントID" IS NULL OR "テナントID" = %s)
    ''', (coefficient_id, tenant_id))
    
    coefficient_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not coefficient_data:
        flash('文字周長係数が見つかりません', 'error')
        return redirect(url_for('perimeter_coefficient.index'))
    
    # デフォルト係数（テナントIDがNULL）の場合は編集不可
    if coefficient_data[4] is None:
        flash('デフォルト係数は編集できません。新規作成してカスタマイズしてください。', 'warning')
        return redirect(url_for('perimeter_coefficient.index'))
    
    return render_template('perimeter_coefficient_edit.html', coefficient=coefficient_data)

@perimeter_coefficient_bp.route('/delete/<int:coefficient_id>', methods=['POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def delete(coefficient_id):
    """文字周長係数削除"""
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('ログインが必要です', 'error')
        return redirect(url_for('select_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # テナント固有の係数のみ削除可能（デフォルト係数は削除不可）
        cur.execute('''
            DELETE FROM "T_文字周長係数"
            WHERE "ID" = %s AND "テナントID" = %s
        ''', (coefficient_id, tenant_id))
        
        if cur.rowcount == 0:
            flash('デフォルト係数は削除できません', 'error')
        else:
            conn.commit()
            flash('文字周長係数を削除しました', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'エラーが発生しました: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('perimeter_coefficient.index'))

@perimeter_coefficient_bp.route('/api/coefficients', methods=['GET'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def api_coefficients():
    """文字周長係数API（見積もり作成画面で使用）"""
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        return jsonify({'success': False, 'error': 'ログインが必要です'}), 401
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # テナント固有の係数を優先、なければデフォルト係数を使用
    cur.execute('''
        WITH ranked_coefficients AS (
            SELECT 
                "文字種類",
                "係数",
                "説明",
                ROW_NUMBER() OVER (PARTITION BY "文字種類" ORDER BY "テナントID" DESC NULLS LAST) as rn
            FROM "T_文字周長係数"
            WHERE "テナントID" IS NULL OR "テナントID" = %s
        )
        SELECT "文字種類", "係数", "説明"
        FROM ranked_coefficients
        WHERE rn = 1
        ORDER BY 
            CASE "文字種類"
                WHEN 'ひらがな' THEN 1
                WHEN 'カタカナ' THEN 2
                WHEN '漢字（簡単）' THEN 3
                WHEN '漢字（普通）' THEN 4
                WHEN '漢字（複雑）' THEN 5
                WHEN '英数字（大文字）' THEN 6
                WHEN '英数字（小文字）' THEN 7
                WHEN '記号' THEN 8
                ELSE 99
            END
    ''', (tenant_id,))
    
    coefficients = cur.fetchall()
    cur.close()
    conn.close()
    
    result = [
        {
            'char_type': row[0],
            'coefficient': float(row[1]),
            'description': row[2]
        }
        for row in coefficients
    ]
    
    return jsonify({'success': True, 'coefficients': result})
