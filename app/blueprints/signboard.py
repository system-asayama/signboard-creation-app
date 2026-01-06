"""
看板見積もり機能のBlueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.utils.decorators import require_roles
from app.utils.db import get_db, _sql
from datetime import datetime
import math

bp = Blueprint('signboard', __name__, url_prefix='/signboard')


def generate_estimate_number():
    """見積もり番号を生成（例: EST-20260106-0001）"""
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    
    conn = get_db()
    cur = conn.cursor()
    
    # 今日の見積もり番号の最大値を取得
    sql = _sql(conn, 'SELECT MAX("estimate_number") FROM "T_看板見積もり" WHERE "estimate_number" LIKE %s')
    cur.execute(sql, (f'EST-{date_str}-%',))
    row = cur.fetchone()
    conn.close()
    
    if row and row[0]:
        # 既存の番号から連番を抽出
        last_number = int(row[0].split('-')[-1])
        seq = last_number + 1
    else:
        seq = 1
    
    return f'EST-{date_str}-{seq:04d}'


def calculate_price(material_id, width_mm, height_mm, quantity):
    """
    価格を計算する
    
    Args:
        material_id: 材質ID
        width_mm: 幅（mm）
        height_mm: 高さ（mm）
        quantity: 数量
    
    Returns:
        dict: 計算結果
    """
    conn = get_db()
    cur = conn.cursor()
    
    # 材質情報を取得
    sql = _sql(conn, 
        'SELECT "name", "price_type", "unit_price_area", "unit_price_weight", '
        '"specific_gravity", "thickness" FROM "T_材質" WHERE "id" = %s'
    )
    cur.execute(sql, (material_id,))
    material = cur.fetchone()
    
    if not material:
        conn.close()
        raise ValueError("材質が見つかりません")
    
    name, price_type, unit_price_area, unit_price_weight, specific_gravity, thickness = material
    
    # 面積を計算（㎡）
    area_m2 = (width_mm / 1000) * (height_mm / 1000)
    
    # 重量を計算（kg）
    weight_kg = None
    unit_price = 0
    
    if price_type == 'area':
        # 面積単価の場合
        unit_price = unit_price_area or 0
        base_price = area_m2 * unit_price
    elif price_type == 'weight':
        # 重量単価の場合
        if specific_gravity and thickness:
            weight_kg = area_m2 * specific_gravity * thickness
            unit_price = unit_price_weight or 0
            base_price = weight_kg * unit_price
        else:
            conn.close()
            raise ValueError("重量単価の材質には比重と板厚が必要です")
    else:
        conn.close()
        raise ValueError("不明な単価タイプです")
    
    # ボリュームディスカウントを適用
    discount_rate = 0.0
    discounted_unit_price = unit_price
    
    sql = _sql(conn, 
        'SELECT "discount_type", "discount_rate", "discount_price" '
        'FROM "T_材質ボリュームディスカウント" '
        'WHERE "material_id" = %s AND "min_quantity" <= %s '
        'AND ("max_quantity" IS NULL OR "max_quantity" >= %s) '
        'ORDER BY "min_quantity" DESC LIMIT 1'
    )
    cur.execute(sql, (material_id, quantity, quantity))
    discount = cur.fetchone()
    conn.close()
    
    if discount:
        discount_type, disc_rate, disc_price = discount
        if discount_type == 'rate' and disc_rate:
            discount_rate = disc_rate
            discounted_unit_price = unit_price * (1 - discount_rate / 100)
        elif discount_type == 'price' and disc_price:
            discounted_unit_price = disc_price
            discount_rate = ((unit_price - disc_price) / unit_price) * 100 if unit_price > 0 else 0
    
    # 割引後の価格を計算
    if price_type == 'area':
        discounted_base_price = area_m2 * discounted_unit_price
    else:
        discounted_base_price = weight_kg * discounted_unit_price
    
    # 小計（数量を掛ける）
    subtotal = discounted_base_price * quantity
    
    # 消費税
    tax_rate = 0.10
    tax_amount = math.floor(subtotal * tax_rate)
    
    # 合計
    total_amount = subtotal + tax_amount
    
    return {
        'area': area_m2,
        'weight': weight_kg,
        'price_type': price_type,
        'unit_price': unit_price,
        'discount_rate': discount_rate,
        'discounted_unit_price': discounted_unit_price,
        'subtotal': subtotal,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'total_amount': total_amount
    }


@bp.route('/')
@require_roles(['tenant_admin', 'admin'])
def index():
    """見積もり一覧"""
    tenant_id = session.get('tenant_id')
    role = session.get('role')
    
    conn = get_db()
    cur = conn.cursor()
    
    # 見積もり一覧を取得
    if role == 'tenant_admin':
        sql = _sql(conn, 
            'SELECT e."id", e."estimate_number", e."customer_name", e."width", e."height", '
            'e."quantity", e."total_amount", e."status", e."created_at", m."name" as material_name '
            'FROM "T_看板見積もり" e '
            'LEFT JOIN "T_材質" m ON e."material_id" = m."id" '
            'WHERE e."tenant_id" = %s '
            'ORDER BY e."created_at" DESC'
        )
        cur.execute(sql, (tenant_id,))
    else:
        # 店舗管理者は自分の店舗の見積もりのみ
        store_id = session.get('store_id')
        sql = _sql(conn, 
            'SELECT e."id", e."estimate_number", e."customer_name", e."width", e."height", '
            'e."quantity", e."total_amount", e."status", e."created_at", m."name" as material_name '
            'FROM "T_看板見積もり" e '
            'LEFT JOIN "T_材質" m ON e."material_id" = m."id" '
            'WHERE e."tenant_id" = %s AND e."store_id" = %s '
            'ORDER BY e."created_at" DESC'
        )
        cur.execute(sql, (tenant_id, store_id))
    
    estimates = cur.fetchall()
    conn.close()
    
    return render_template('signboard_estimates.html', estimates=estimates)


@bp.route('/materials')
@require_roles(['tenant_admin'])
def materials():
    """材質マスタ一覧"""
    tenant_id = session.get('tenant_id')
    
    conn = get_db()
    cur = conn.cursor()
    
    sql = _sql(conn, 
        'SELECT "id", "name", "price_type", "unit_price_area", "unit_price_weight", '
        '"specific_gravity", "thickness", "active" '
        'FROM "T_材質" WHERE "tenant_id" = %s ORDER BY "created_at" DESC'
    )
    cur.execute(sql, (tenant_id,))
    materials = cur.fetchall()
    conn.close()
    
    return render_template('signboard_materials.html', materials=materials)


@bp.route('/materials/new', methods=['GET', 'POST'])
@require_roles(['tenant_admin'])
def material_new():
    """材質マスタ新規登録"""
    if request.method == 'POST':
        tenant_id = session.get('tenant_id')
        name = request.form.get('name')
        price_type = request.form.get('price_type')
        unit_price_area = request.form.get('unit_price_area')
        unit_price_weight = request.form.get('unit_price_weight')
        specific_gravity = request.form.get('specific_gravity')
        thickness = request.form.get('thickness')
        description = request.form.get('description')
        
        conn = get_db()
        cur = conn.cursor()
        
        sql = _sql(conn, 
            'INSERT INTO "T_材質" ("tenant_id", "name", "price_type", "unit_price_area", '
            '"unit_price_weight", "specific_gravity", "thickness", "description") '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'
        )
        cur.execute(sql, (
            tenant_id, name, price_type,
            float(unit_price_area) if unit_price_area else None,
            float(unit_price_weight) if unit_price_weight else None,
            float(specific_gravity) if specific_gravity else None,
            float(thickness) if thickness else None,
            description
        ))
        conn.commit()
        conn.close()
        
        flash('材質を登録しました', 'success')
        return redirect(url_for('signboard.materials'))
    
    return render_template('signboard_material_new.html')


@bp.route('/materials/<int:material_id>/edit', methods=['GET', 'POST'])
@require_roles(['tenant_admin'])
def material_edit(material_id):
    """材質マスタ編集"""
    tenant_id = session.get('tenant_id')
    conn = get_db()
    cur = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        price_type = request.form.get('price_type')
        unit_price_area = request.form.get('unit_price_area')
        unit_price_weight = request.form.get('unit_price_weight')
        specific_gravity = request.form.get('specific_gravity')
        thickness = request.form.get('thickness')
        description = request.form.get('description')
        
        sql = _sql(conn, 
            'UPDATE "T_材質" SET "name" = %s, "price_type" = %s, "unit_price_area" = %s, '
            '"unit_price_weight" = %s, "specific_gravity" = %s, "thickness" = %s, '
            '"description" = %s, "updated_at" = CURRENT_TIMESTAMP '
            'WHERE "id" = %s AND "tenant_id" = %s'
        )
        cur.execute(sql, (
            name, price_type,
            float(unit_price_area) if unit_price_area else None,
            float(unit_price_weight) if unit_price_weight else None,
            float(specific_gravity) if specific_gravity else None,
            float(thickness) if thickness else None,
            description, material_id, tenant_id
        ))
        conn.commit()
        conn.close()
        
        flash('材質を更新しました', 'success')
        return redirect(url_for('signboard.materials'))
    
    # 材質情報を取得
    sql = _sql(conn, 
        'SELECT "id", "name", "price_type", "unit_price_area", "unit_price_weight", '
        '"specific_gravity", "thickness", "description" '
        'FROM "T_材質" WHERE "id" = %s AND "tenant_id" = %s'
    )
    cur.execute(sql, (material_id, tenant_id))
    material = cur.fetchone()
    conn.close()
    
    if not material:
        flash('材質が見つかりません', 'error')
        return redirect(url_for('signboard.materials'))
    
    return render_template('signboard_material_edit.html', material=material)


@bp.route('/new', methods=['GET', 'POST'])
@require_roles(['tenant_admin', 'admin'])
def estimate_new():
    """見積もり新規作成"""
    tenant_id = session.get('tenant_id')
    role = session.get('role')
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        width = float(request.form.get('width'))
        height = float(request.form.get('height'))
        material_id = int(request.form.get('material_id'))
        quantity = int(request.form.get('quantity', 1))
        notes = request.form.get('notes')
        
        # 価格を計算
        try:
            calc = calculate_price(material_id, width, height, quantity)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('signboard.estimate_new'))
        
        # 見積もり番号を生成
        estimate_number = generate_estimate_number()
        
        conn = get_db()
        cur = conn.cursor()
        
        sql = _sql(conn, 
            'INSERT INTO "T_看板見積もり" '
            '("tenant_id", "store_id", "created_by", "created_by_role", "estimate_number", '
            '"customer_name", "width", "height", "material_id", "quantity", "area", "weight", '
            '"price_type", "unit_price", "discount_rate", "discounted_unit_price", "subtotal", '
            '"tax_rate", "tax_amount", "total_amount", "notes") '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
        )
        cur.execute(sql, (
            tenant_id,
            session.get('store_id') if role == 'admin' else None,
            user_id, role, estimate_number, customer_name,
            width, height, material_id, quantity,
            calc['area'], calc['weight'], calc['price_type'],
            calc['unit_price'], calc['discount_rate'], calc['discounted_unit_price'],
            calc['subtotal'], calc['tax_rate'], calc['tax_amount'], calc['total_amount'],
            notes
        ))
        conn.commit()
        conn.close()
        
        flash('見積もりを作成しました', 'success')
        return redirect(url_for('signboard.index'))
    
    # 材質一覧を取得
    conn = get_db()
    cur = conn.cursor()
    sql = _sql(conn, 
        'SELECT "id", "name", "price_type" FROM "T_材質" '
        'WHERE "tenant_id" = %s AND "active" = 1 ORDER BY "name"'
    )
    cur.execute(sql, (tenant_id,))
    materials = cur.fetchall()
    conn.close()
    
    return render_template('signboard_estimate_new.html', materials=materials)


@bp.route('/<int:estimate_id>')
@require_roles(['tenant_admin', 'admin'])
def estimate_detail(estimate_id):
    """見積もり詳細"""
    tenant_id = session.get('tenant_id')
    role = session.get('role')
    
    conn = get_db()
    cur = conn.cursor()
    
    if role == 'tenant_admin':
        sql = _sql(conn, 
            'SELECT e."id", e."estimate_number", e."customer_name", e."width", e."height", '
            'e."quantity", e."area", e."weight", e."price_type", e."unit_price", '
            'e."discount_rate", e."discounted_unit_price", e."subtotal", e."tax_rate", '
            'e."tax_amount", e."total_amount", e."notes", e."status", e."created_at", '
            'm."name" as material_name '
            'FROM "T_看板見積もり" e '
            'LEFT JOIN "T_材質" m ON e."material_id" = m."id" '
            'WHERE e."id" = %s AND e."tenant_id" = %s'
        )
        cur.execute(sql, (estimate_id, tenant_id))
    else:
        store_id = session.get('store_id')
        sql = _sql(conn, 
            'SELECT e."id", e."estimate_number", e."customer_name", e."width", e."height", '
            'e."quantity", e."area", e."weight", e."price_type", e."unit_price", '
            'e."discount_rate", e."discounted_unit_price", e."subtotal", e."tax_rate", '
            'e."tax_amount", e."total_amount", e."notes", e."status", e."created_at", '
            'm."name" as material_name '
            'FROM "T_看板見積もり" e '
            'LEFT JOIN "T_材質" m ON e."material_id" = m."id" '
            'WHERE e."id" = %s AND e."tenant_id" = %s AND e."store_id" = %s'
        )
        cur.execute(sql, (estimate_id, tenant_id, store_id))
    
    estimate = cur.fetchone()
    conn.close()
    
    if not estimate:
        flash('見積もりが見つかりません', 'error')
        return redirect(url_for('signboard.index'))
    
    return render_template('signboard_estimate_detail.html', estimate=estimate)


@bp.route('/api/calculate', methods=['POST'])
@require_roles(['tenant_admin', 'admin'])
def api_calculate():
    """見積もり金額をAPIで計算"""
    data = request.get_json()
    
    try:
        material_id = int(data.get('material_id'))
        width = float(data.get('width'))
        height = float(data.get('height'))
        quantity = int(data.get('quantity', 1))
        
        calc = calculate_price(material_id, width, height, quantity)
        
        return jsonify({
            'success': True,
            'data': {
                'area': round(calc['area'], 4),
                'weight': round(calc['weight'], 2) if calc['weight'] else None,
                'unit_price': int(calc['unit_price']),
                'discount_rate': round(calc['discount_rate'], 2),
                'discounted_unit_price': int(calc['discounted_unit_price']),
                'subtotal': int(calc['subtotal']),
                'tax_amount': int(calc['tax_amount']),
                'total_amount': int(calc['total_amount'])
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
