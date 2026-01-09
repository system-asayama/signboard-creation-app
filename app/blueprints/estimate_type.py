from flask import Blueprint, render_template, request, redirect, url_for, session
from app.utils.db import get_db, _sql
from app.utils.decorators import require_roles, require_app_enabled

bp = Blueprint('estimate_type', __name__, url_prefix='/signboard/estimate')

@bp.route('/select-type')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def select_type():
    """見積タイプ選択画面（ステップ1）"""
    project_id = request.args.get('project_id')
    
    # project_idをセッションに保存
    if project_id:
        session['current_project_id'] = int(project_id)
    
    conn = get_db()
    cur = conn.cursor()
    
    # 見積タイプ一覧を取得
    sql = _sql(conn, '''
        SELECT id, name, code, description, display_order
        FROM "T_見積タイプ"
        ORDER BY display_order
    ''')
    cur.execute(sql)
    estimate_types = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('estimate_type_select.html', estimate_types=estimate_types, project_id=project_id)

@bp.route('/select-subtype/<int:type_id>')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def select_subtype(type_id):
    """見積サブタイプ選択画面（ステップ2）"""
    conn = get_db()
    cur = conn.cursor()
    
    # 選択された見積タイプを取得
    sql = _sql(conn, '''
        SELECT id, name, code, description
        FROM "T_見積タイプ"
        WHERE id = %s
    ''')
    cur.execute(sql, (type_id,))
    estimate_type = cur.fetchone()
    
    if not estimate_type:
        cur.close()
        conn.close()
        return redirect(url_for('estimate_type.select_type'))
    
    # サブタイプ一覧を取得
    sql = _sql(conn, '''
        SELECT id, name, code, description, display_order
        FROM "T_見積サブタイプ"
        WHERE estimate_type_id = %s
        ORDER BY display_order
    ''')
    cur.execute(sql, (type_id,))
    subtypes = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('estimate_subtype_select.html', 
                         estimate_type=estimate_type, 
                         subtypes=subtypes)

@bp.route('/start/<int:subtype_id>')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def start_estimate(subtype_id):
    """見積もり作成開始（サブタイプを選択後、見積もり作成画面へ）"""
    # セッションにサブタイプIDを保存
    session['current_subtype_id'] = subtype_id
    
    # サブタイプ情報を取得（estimate_type_idを取得するため）
    conn = get_db()
    cur = conn.cursor()
    sql = _sql(conn, 'SELECT estimate_type_id FROM "T_見積サブタイプ" WHERE id = %s')
    cur.execute(sql, (subtype_id,))
    row = cur.fetchone()
    if row:
        session['current_estimate_type_id'] = row[0]
    conn.close()
    
    # 見積もり作成画面にリダイレクト
    return redirect(url_for('signboard.estimate_new'))

@bp.route('/manage')
@require_app_enabled('signboard')
@require_roles('tenant_admin')
def manage():
    """見積タイプ・サブタイプ管理画面"""
    conn = get_db()
    cur = conn.cursor()
    
    # 見積タイプ一覧を取得
    sql = _sql(conn, '''
        SELECT id, name, code, description, display_order
        FROM "T_見積タイプ"
        ORDER BY display_order
    ''')
    cur.execute(sql)
    estimate_types = cur.fetchall()
    
    # 各見積タイプのサブタイプを取得
    types_with_subtypes = []
    for et in estimate_types:
        sql = _sql(conn, '''
            SELECT id, name, code, description, display_order
            FROM "T_見積サブタイプ"
            WHERE estimate_type_id = %s
            ORDER BY display_order
        ''')
        cur.execute(sql, (et[0],))
        subtypes = cur.fetchall()
        types_with_subtypes.append({
            'type': et,
            'subtypes': subtypes
        })
    
    cur.close()
    conn.close()
    
    return render_template('estimate_type_manage.html', types_with_subtypes=types_with_subtypes)
