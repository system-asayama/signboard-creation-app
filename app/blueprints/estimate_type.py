from flask import Blueprint, render_template, request, redirect, url_for, session
from app.utils.db import get_db_connection
from app.utils.auth import require_login, require_roles

bp = Blueprint('estimate_type', __name__, url_prefix='/signboard/estimate')

@bp.route('/select-type')
@require_login
@require_roles('tenant_admin', 'store_admin')
def select_type():
    """見積タイプ選択画面（ステップ1）"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 見積タイプ一覧を取得
    cur.execute('''
        SELECT id, name, code, description, display_order
        FROM "T_見積タイプ"
        ORDER BY display_order
    ''')
    estimate_types = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('estimate_type_select.html', estimate_types=estimate_types)

@bp.route('/select-subtype/<int:type_id>')
@require_login
@require_roles('tenant_admin', 'store_admin')
def select_subtype(type_id):
    """見積サブタイプ選択画面（ステップ2）"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 選択された見積タイプを取得
    cur.execute('''
        SELECT id, name, code, description
        FROM "T_見積タイプ"
        WHERE id = %s
    ''', (type_id,))
    estimate_type = cur.fetchone()
    
    if not estimate_type:
        cur.close()
        conn.close()
        return redirect(url_for('estimate_type.select_type'))
    
    # サブタイプ一覧を取得
    cur.execute('''
        SELECT id, name, code, description, display_order
        FROM "T_見積サブタイプ"
        WHERE estimate_type_id = %s
        ORDER BY display_order
    ''', (type_id,))
    subtypes = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('estimate_subtype_select.html', 
                         estimate_type=estimate_type, 
                         subtypes=subtypes)

@bp.route('/start/<int:subtype_id>')
@require_login
@require_roles('tenant_admin', 'store_admin')
def start_estimate(subtype_id):
    """見積もり作成開始（サブタイプを選択後、見積もり作成画面へ）"""
    # セッションにサブタイプIDを保存
    session['current_subtype_id'] = subtype_id
    
    # 見積もり作成画面にリダイレクト
    return redirect(url_for('signboard.new'))
