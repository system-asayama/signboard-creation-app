"""
大分類・中分類管理機能のBlueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.utils.decorators import require_roles, require_app_enabled
from app.utils.db import get_db, _sql

bp = Blueprint('category', __name__, url_prefix='/signboard/categories')


@bp.route('/')
@require_app_enabled('signboard')
@require_roles(['tenant_admin', 'store_admin'])
def index():
    """大分類・中分類一覧"""
    conn = get_db()
    cur = conn.cursor()
    
    # 大分類と中分類を取得
    sql = _sql(conn, '''
        SELECT 
            c."id" as category_id,
            c."code" as category_code,
            c."name" as category_name,
            c."description" as category_description,
            c."display_order" as category_order,
            s."id" as subcategory_id,
            s."code" as subcategory_code,
            s."name" as subcategory_name,
            s."description" as subcategory_description,
            s."display_order" as subcategory_order
        FROM "T_大分類" c
        LEFT JOIN "T_中分類" s ON c."id" = s."category_id"
        WHERE c."active" = TRUE
        ORDER BY c."display_order", s."display_order"
    ''')
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    
    # 大分類ごとにグループ化
    categories = {}
    for row in rows:
        cat_id = row[0]
        if cat_id not in categories:
            categories[cat_id] = {
                'id': row[0],
                'code': row[1],
                'name': row[2],
                'description': row[3],
                'display_order': row[4],
                'subcategories': []
            }
        
        if row[5]:  # 中分類が存在する場合
            categories[cat_id]['subcategories'].append({
                'id': row[5],
                'code': row[6],
                'name': row[7],
                'description': row[8],
                'display_order': row[9]
            })
    
    return render_template('category_index.html', categories=list(categories.values()))


@bp.route('/categories/new')
@require_app_enabled('signboard')
@require_roles(['tenant_admin'])
def category_new():
    """大分類新規登録画面"""
    return render_template('category_new.html')


@bp.route('/categories/create', methods=['POST'])
@require_app_enabled('signboard')
@require_roles(['tenant_admin'])
def category_create():
    """大分類新規登録処理"""
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    display_order = request.form.get('display_order', 0, type=int)
    
    if not code or not name:
        flash('コードと名前は必須です', 'error')
        return redirect(url_for('category.category_new'))
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        sql = _sql(conn, '''
            INSERT INTO "T_大分類" ("code", "name", "description", "display_order")
            VALUES (%s, %s, %s, %s)
        ''')
        cur.execute(sql, (code, name, description, display_order))
        conn.commit()
        flash('大分類を登録しました', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'登録に失敗しました: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('category.index'))


@bp.route('/categories/<int:category_id>/edit')
@require_app_enabled('signboard')
@require_roles(['tenant_admin'])
def category_edit(category_id):
    """大分類編集画面"""
    conn = get_db()
    cur = conn.cursor()
    
    sql = _sql(conn, 'SELECT "id", "code", "name", "description", "display_order" FROM "T_大分類" WHERE "id" = %s')
    cur.execute(sql, (category_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        flash('大分類が見つかりません', 'error')
        return redirect(url_for('category.index'))
    
    category = {
        'id': row[0],
        'code': row[1],
        'name': row[2],
        'description': row[3],
        'display_order': row[4]
    }
    
    return render_template('category_edit.html', category=category)


@bp.route('/categories/<int:category_id>/update', methods=['POST'])
@require_app_enabled('signboard')
@require_roles(['tenant_admin'])
def category_update(category_id):
    """大分類更新処理"""
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    display_order = request.form.get('display_order', 0, type=int)
    
    if not code or not name:
        flash('コードと名前は必須です', 'error')
        return redirect(url_for('category.category_edit', category_id=category_id))
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        sql = _sql(conn, '''
            UPDATE "T_大分類" 
            SET "code" = %s, "name" = %s, "description" = %s, "display_order" = %s, "updated_at" = CURRENT_TIMESTAMP
            WHERE "id" = %s
        ''')
        cur.execute(sql, (code, name, description, display_order, category_id))
        conn.commit()
        flash('大分類を更新しました', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'更新に失敗しました: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('category.index'))


@bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@require_app_enabled('signboard')
@require_roles(['tenant_admin'])
def category_delete(category_id):
    """大分類削除処理"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        sql = _sql(conn, 'DELETE FROM "T_大分類" WHERE "id" = %s')
        cur.execute(sql, (category_id,))
        conn.commit()
        flash('大分類を削除しました', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'削除に失敗しました: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('category.index'))


@bp.route('/subcategories/new')
@require_app_enabled('signboard')
@require_roles(['tenant_admin', 'store_admin'])
def subcategory_new():
    """中分類新規登録画面"""
    conn = get_db()
    cur = conn.cursor()
    
    # 大分類一覧を取得
    sql = _sql(conn, 'SELECT "id", "name" FROM "T_大分類" WHERE "active" = TRUE ORDER BY "display_order"')
    cur.execute(sql)
    categories = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
    conn.close()
    
    return render_template('subcategory_new.html', categories=categories)


@bp.route('/subcategories/create', methods=['POST'])
@require_app_enabled('signboard')
@require_roles(['tenant_admin', 'store_admin'])
def subcategory_create():
    """中分類新規登録処理"""
    category_id = request.form.get('category_id', type=int)
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    display_order = request.form.get('display_order', 0, type=int)
    
    if not category_id or not code or not name:
        flash('大分類、コード、名前は必須です', 'error')
        return redirect(url_for('category.subcategory_new'))
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        sql = _sql(conn, '''
            INSERT INTO "T_中分類" ("category_id", "code", "name", "description", "display_order")
            VALUES (%s, %s, %s, %s, %s)
        ''')
        cur.execute(sql, (category_id, code, name, description, display_order))
        conn.commit()
        flash('中分類を登録しました', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'登録に失敗しました: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('category.index'))


@bp.route('/subcategories/<int:subcategory_id>/edit')
@require_app_enabled('signboard')
@require_roles(['tenant_admin', 'store_admin'])
def subcategory_edit(subcategory_id):
    """中分類編集画面"""
    conn = get_db()
    cur = conn.cursor()
    
    # 中分類情報を取得
    sql = _sql(conn, 'SELECT "id", "category_id", "code", "name", "description", "display_order" FROM "T_中分類" WHERE "id" = %s')
    cur.execute(sql, (subcategory_id,))
    row = cur.fetchone()
    
    if not row:
        conn.close()
        flash('中分類が見つかりません', 'error')
        return redirect(url_for('category.index'))
    
    subcategory = {
        'id': row[0],
        'category_id': row[1],
        'code': row[2],
        'name': row[3],
        'description': row[4],
        'display_order': row[5]
    }
    
    # 大分類一覧を取得
    sql = _sql(conn, 'SELECT "id", "name" FROM "T_大分類" WHERE "active" = TRUE ORDER BY "display_order"')
    cur.execute(sql)
    categories = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
    conn.close()
    
    return render_template('subcategory_edit.html', subcategory=subcategory, categories=categories)


@bp.route('/subcategories/<int:subcategory_id>/update', methods=['POST'])
@require_app_enabled('signboard')
@require_roles(['tenant_admin', 'store_admin'])
def subcategory_update(subcategory_id):
    """中分類更新処理"""
    category_id = request.form.get('category_id', type=int)
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    display_order = request.form.get('display_order', 0, type=int)
    
    if not category_id or not code or not name:
        flash('大分類、コード、名前は必須です', 'error')
        return redirect(url_for('category.subcategory_edit', subcategory_id=subcategory_id))
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        sql = _sql(conn, '''
            UPDATE "T_中分類" 
            SET "category_id" = %s, "code" = %s, "name" = %s, "description" = %s, "display_order" = %s, "updated_at" = CURRENT_TIMESTAMP
            WHERE "id" = %s
        ''')
        cur.execute(sql, (category_id, code, name, description, display_order, subcategory_id))
        conn.commit()
        flash('中分類を更新しました', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'更新に失敗しました: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('category.index'))


@bp.route('/subcategories/<int:subcategory_id>/delete', methods=['POST'])
@require_app_enabled('signboard')
@require_roles(['tenant_admin', 'store_admin'])
def subcategory_delete(subcategory_id):
    """中分類削除処理"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        sql = _sql(conn, 'DELETE FROM "T_中分類" WHERE "id" = %s')
        cur.execute(sql, (subcategory_id,))
        conn.commit()
        flash('中分類を削除しました', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'削除に失敗しました: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('category.index'))


@bp.route('/api/subcategories/<int:category_id>')
@require_app_enabled('signboard')
@require_roles(['tenant_admin', 'store_admin'])
def api_subcategories(category_id):
    """大分類IDに紐づく中分類を取得するAPI"""
    conn = get_db()
    cur = conn.cursor()
    
    sql = _sql(conn, '''
        SELECT "id", "code", "name" 
        FROM "T_中分類" 
        WHERE "category_id" = %s AND "active" = TRUE 
        ORDER BY "display_order"
    ''')
    cur.execute(sql, (category_id,))
    subcategories = [{'id': row[0], 'code': row[1], 'name': row[2]} for row in cur.fetchall()]
    conn.close()
    
    return jsonify(subcategories)
