"""
看板見積もり機能のBlueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.utils.decorators import require_roles, require_app_enabled
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
        '"unit_price_volume", "specific_gravity", "thickness" FROM "T_材質" WHERE "id" = %s'
    )
    cur.execute(sql, (material_id,))
    material = cur.fetchone()
    
    if not material:
        conn.close()
        raise ValueError("材質が見つかりません")
    
    name, price_type, unit_price_area, unit_price_weight, unit_price_volume, specific_gravity, thickness = material
    
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
    elif price_type == 'volume':
        # 体積単価の場合
        if thickness:
            # 体積 = 面積（㎡） × 板厚（mm） / 1000 = ㎥
            volume_m3 = area_m2 * (thickness / 1000)
            unit_price = unit_price_volume or 0
            base_price = volume_m3 * unit_price
        else:
            conn.close()
            raise ValueError("体積単価の材質には板厚が必要です")
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
    elif price_type == 'weight':
        discounted_base_price = weight_kg * discounted_unit_price
    elif price_type == 'volume':
        volume_m3 = area_m2 * (thickness / 1000)
        discounted_base_price = volume_m3 * discounted_unit_price
    else:
        discounted_base_price = 0
    
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
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def index():
    """看板見積もりアプリのトップページ - メニュー選択画面"""
    return render_template('signboard_menu.html')

@bp.route('/master')
@require_app_enabled('signboard')
@require_roles('tenant_admin')
def master_menu():
    """マスター登録メニュー画面"""
    return render_template('signboard_master_menu.html')

@bp.route('/estimates')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def estimates():
    """見積もり一覧（旧版）"""
    tenant_id = session.get('tenant_id')
    role = session.get('role')
    
    conn = get_db()
    cur = conn.cursor()
    
    # 見積もり一覧を取得（明細テーブルから集計）
    if role == 'tenant_admin':
        sql = _sql(conn, 
            'SELECT e."id", e."estimate_number", e."customer_name", '
            'COALESCE(d."幅", e."width") as width, '
            'COALESCE(d."高さ", e."height") as height, '
            'COALESCE(d."数量", e."quantity") as quantity, '
            'e."total_amount", e."status", e."created_at", '
            'COALESCE(m."name", mat."name") as material_name '
            'FROM "T_看板見積もり" e '
            'LEFT JOIN "T_材質" mat ON e."material_id" = mat."id" '
            'LEFT JOIN ( '
            '    SELECT "見積もりID", '
            '    MAX("幅") as "幅", MAX("高さ") as "高さ", '
            '    SUM("数量") as "数量", '
            '    (SELECT "name" FROM "T_材質" WHERE "id" = MAX(d2."材質ID")) as name '
            '    FROM "T_看板見積もり明細" d2 '
            '    GROUP BY "見積もりID" '
            ') d ON e."id" = d."見積もりID" '
            'LEFT JOIN "T_材質" m ON m."name" = d."name" '
            'WHERE e."tenant_id" = %s '
            'ORDER BY e."created_at" DESC'
        )
        cur.execute(sql, (tenant_id,))
    else:
        # 店舗管理者は自分の店舗の見積もりのみ
        store_id = session.get('store_id')
        sql = _sql(conn, 
            'SELECT e."id", e."estimate_number", e."customer_name", '
            'COALESCE(d."幅", e."width") as width, '
            'COALESCE(d."高さ", e."height") as height, '
            'COALESCE(d."数量", e."quantity") as quantity, '
            'e."total_amount", e."status", e."created_at", '
            'COALESCE(m."name", mat."name") as material_name '
            'FROM "T_看板見積もり" e '
            'LEFT JOIN "T_材質" mat ON e."material_id" = mat."id" '
            'LEFT JOIN ( '
            '    SELECT "見積もりID", '
            '    MAX("幅") as "幅", MAX("高さ") as "高さ", '
            '    SUM("数量") as "数量", '
            '    (SELECT "name" FROM "T_材質" WHERE "id" = MAX(d2."材質ID")) as name '
            '    FROM "T_看板見積もり明細" d2 '
            '    GROUP BY "見積もりID" '
            ') d ON e."id" = d."見積もりID" '
            'LEFT JOIN "T_材質" m ON m."name" = d."name" '
            'WHERE e."tenant_id" = %s AND e."store_id" = %s '
            'ORDER BY e."created_at" DESC'
        )
        cur.execute(sql, (tenant_id, store_id))
    
    estimates = cur.fetchall()
    conn.close()
    
    return render_template('signboard_estimates.html', estimates=estimates)


@bp.route('/materials')
@require_app_enabled('signboard')
@require_roles('tenant_admin')
def materials():
    """材質マスタ一覧"""
    tenant_id = session.get('tenant_id')
    
    conn = get_db()
    cur = conn.cursor()
    
    sql = _sql(conn, 
        'SELECT "id", "name", "price_type", "unit_price_area", "unit_price_weight", '
        '"unit_price_volume", "specific_gravity", "thickness", "active", "shape_type", "wall_thickness" '
        'FROM "T_材質" WHERE "tenant_id" = %s ORDER BY "created_at" DESC'
    )
    cur.execute(sql, (tenant_id,))
    materials = cur.fetchall()
    conn.close()
    
    return render_template('signboard_materials.html', materials=materials)


@bp.route('/materials/new', methods=['GET', 'POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin')
def material_new():
    """材質マスタ新規登録"""
    if request.method == 'POST':
        tenant_id = session.get('tenant_id')
        name = request.form.get('name')
        price_type = request.form.get('price_type')
        unit_price_area = request.form.get('unit_price_area')
        unit_price_weight = request.form.get('unit_price_weight')
        unit_price_volume = request.form.get('unit_price_volume')
        specific_gravity = request.form.get('specific_gravity')
        thickness = request.form.get('thickness')
        shape_type = request.form.get('shape_type')
        wall_thickness = request.form.get('wall_thickness')
        category_id = request.form.get('category_id')
        subcategory_id = request.form.get('subcategory_id')
        description = request.form.get('description')
        
        conn = get_db()
        cur = conn.cursor()
        
        sql = _sql(conn, 
            'INSERT INTO "T_材質" ("tenant_id", "name", "price_type", "unit_price_area", '
            '"unit_price_weight", "unit_price_volume", "specific_gravity", "thickness", "shape_type", "wall_thickness", "category_id", "subcategory_id", "description", "active", "created_at", "updated_at") '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)'
        )
        cur.execute(sql, (
            tenant_id, name, price_type,
            float(unit_price_area) if unit_price_area else None,
            float(unit_price_weight) if unit_price_weight else None,
            float(unit_price_volume) if unit_price_volume else None,
            float(specific_gravity) if specific_gravity else None,
            float(thickness) if thickness else None,
            shape_type or 'square',
            float(wall_thickness) if wall_thickness else None,
            int(category_id) if category_id else None,
            int(subcategory_id) if subcategory_id else None,
            description,
            1  # active: 1=有効
        ))
        conn.commit()
        conn.close()
        
        flash('材質を登録しました', 'success')
        return redirect(url_for('signboard.materials'))
    
    # 大分類一覧を取得
    conn = get_db()
    cur = conn.cursor()
    sql = _sql(conn, 'SELECT "id", "name", "description" FROM "T_大分類" WHERE "active" = TRUE ORDER BY "display_order"')
    cur.execute(sql)
    categories = cur.fetchall()
    conn.close()
    
    return render_template('signboard_material_new.html', categories=categories)


@bp.route('/materials/<int:material_id>/edit', methods=['GET', 'POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin')
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
        unit_price_volume = request.form.get('unit_price_volume')
        specific_gravity = request.form.get('specific_gravity')
        thickness = request.form.get('thickness')
        shape_type = request.form.get('shape_type')
        wall_thickness = request.form.get('wall_thickness')
        category_id = request.form.get('category_id')
        subcategory_id = request.form.get('subcategory_id')
        description = request.form.get('description')
        
        sql = _sql(conn, 
            'UPDATE "T_材質" SET "name" = %s, "price_type" = %s, "unit_price_area" = %s, '
            '"unit_price_weight" = %s, "unit_price_volume" = %s, "specific_gravity" = %s, "thickness" = %s, '
            '"shape_type" = %s, "wall_thickness" = %s, "category_id" = %s, "subcategory_id" = %s, "description" = %s, "updated_at" = CURRENT_TIMESTAMP '
            'WHERE "id" = %s AND "tenant_id" = %s'
        )
        cur.execute(sql, (
            name, price_type,
            float(unit_price_area) if unit_price_area else None,
            float(unit_price_weight) if unit_price_weight else None,
            float(unit_price_volume) if unit_price_volume else None,
            float(specific_gravity) if specific_gravity else None,
            float(thickness) if thickness else None,
            shape_type or 'square',
            float(wall_thickness) if wall_thickness else None,
            int(category_id) if category_id else None,
            int(subcategory_id) if subcategory_id else None,
            description, material_id, tenant_id
        ))
        conn.commit()
        conn.close()
        
        flash('材質を更新しました', 'success')
        return redirect(url_for('signboard.materials'))
    
    # 材質情報を取得
    sql = _sql(conn, 
        'SELECT "id", "name", "price_type", "unit_price_area", "unit_price_weight", '
        '"unit_price_volume", "specific_gravity", "thickness", "description", "shape_type", "wall_thickness", "category_id", "subcategory_id" '
        'FROM "T_材質" WHERE "id" = %s AND "tenant_id" = %s'
    )
    cur.execute(sql, (material_id, tenant_id))
    material = cur.fetchone()
    
    # 大分類一覧を取得
    sql = _sql(conn, 'SELECT "id", "name", "description" FROM "T_大分類" WHERE "active" = TRUE ORDER BY "display_order"')
    cur.execute(sql)
    categories = cur.fetchall()
    
    # 中分類一覧を取得（現在の大分類に紐づくもの）
    subcategories = []
    if material and material[11]:  # category_idが存在する場合
        sql = _sql(conn, 'SELECT "id", "name" FROM "T_中分類" WHERE "category_id" = %s AND "active" = TRUE ORDER BY "display_order"')
        cur.execute(sql, (material[11],))
        subcategories = cur.fetchall()
    
    conn.close()
    
    if not material:
        flash('材質が見つかりません', 'error')
        return redirect(url_for('signboard.materials'))
    
    return render_template('signboard_material_edit.html', material=material, categories=categories, subcategories=subcategories)


@bp.route('/new', methods=['GET', 'POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def estimate_new():
    """見積もり新規作成"""
    tenant_id = session.get('tenant_id')
    role = session.get('role')
    user_id = session.get('user_id')
    
    # セッションからサブタイプIDを取得（見積タイプ選択フローから来た場合）
    subtype_id = session.get('current_subtype_id')
    
    # サブタイプIDがない場合は見積タイプ選択画面にリダイレクト
    if not subtype_id:
        return redirect(url_for('estimate_type.select_type'))
    
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        notes = request.form.get('notes')
        auto_estimate_id = request.form.get('auto_estimate_id') or None  # AI解析で生成された自動見積もりID（空文字列はNoneに変換）
        
        # 明細データを取得
        items_data = []
        total_subtotal = 0
        
        # フォームから明細データを抽出
        form_keys = list(request.form.keys())
        item_ids = set()
        for key in form_keys:
            if key.startswith('items[') and '][material_id]' in key:
                # items[1][material_id] から 1 を抽出
                item_id = key.split('[')[1].split(']')[0]
                item_ids.add(item_id)
        
        # 各明細の価格を計算
        for item_id in item_ids:
            try:
                material_id_str = request.form.get(f'items[{item_id}][material_id]')
                width_str = request.form.get(f'items[{item_id}][width]')
                height_str = request.form.get(f'items[{item_id}][height]')
                quantity_str = request.form.get(f'items[{item_id}][quantity]', '1')
                
                if not material_id_str or not width_str or not height_str:
                    flash(f'明細{item_id}の入力が不完全です', 'error')
                    return redirect(url_for('signboard.estimate_new'))
                
                material_id = int(material_id_str)
                width = float(width_str)
                height = float(height_str)
                quantity = int(quantity_str)
            except (ValueError, TypeError) as e:
                flash(f'明細{item_id}の入力値が不正です: {str(e)}', 'error')
                return redirect(url_for('signboard.estimate_new'))
            
            # 文字加工情報を取得
            text_processing_mode = request.form.get(f'items[{item_id}][text_processing_mode]')
            text_content = request.form.get(f'items[{item_id}][text_content]')
            text_width = request.form.get(f'items[{item_id}][text_width]')
            text_height = request.form.get(f'items[{item_id}][text_height]')
            character_type_id = request.form.get(f'items[{item_id}][character_type_id]')
            actual_perimeter = request.form.get(f'items[{item_id}][actual_perimeter]')
            perimeter_unit_price = request.form.get(f'items[{item_id}][perimeter_unit_price]')
            
            text_processing_data = None
            processing_cost = 0
            
            if text_processing_mode and text_content and text_height and character_type_id:
                try:
                    # 推定周長を計算
                    conn_temp = get_db()
                    cur_temp = conn_temp.cursor()
                    sql_coeff = _sql(conn_temp, 'SELECT "係数" FROM "T_文字周長係数" WHERE "ID" = %s')
                    cur_temp.execute(sql_coeff, (int(character_type_id),))
                    coeff_row = cur_temp.fetchone()
                    conn_temp.close()
                    
                    if coeff_row:
                        coefficient = float(coeff_row[0])
                        character_count = len(text_content)
                        estimated_perimeter = float(text_height) * character_count * coefficient
                        
                        # 実測周長があればそれを優先
                        final_perimeter = float(actual_perimeter) if actual_perimeter else estimated_perimeter
                        
                        # 加工賃を計算
                        if perimeter_unit_price:
                            processing_cost = int(final_perimeter * float(perimeter_unit_price))
                        
                        text_processing_data = {
                            'mode': text_processing_mode,
                            'content': text_content,
                            'width': float(text_width) if text_width else None,
                            'height': float(text_height),
                            'character_type_id': int(character_type_id),
                            'estimated_perimeter': estimated_perimeter,
                            'actual_perimeter': float(actual_perimeter) if actual_perimeter else None,
                            'perimeter_unit_price': float(perimeter_unit_price) if perimeter_unit_price else None,
                            'processing_cost': processing_cost
                        }
                except (ValueError, TypeError) as e:
                    flash(f'明細{item_id}の文字加工情報の処理エラー: {str(e)}', 'error')
                    return redirect(url_for('signboard.estimate_new'))
            
            try:
                calc = calculate_price(material_id, width, height, quantity)
                items_data.append({
                    'material_id': material_id,
                    'width': width,
                    'height': height,
                    'quantity': quantity,
                    'calc': calc,
                    'text_processing': text_processing_data,
                    'processing_cost': processing_cost
                })
                total_subtotal += calc['subtotal'] + processing_cost
            except ValueError as e:
                flash(f'明細{item_id}の計算エラー: {str(e)}', 'error')
                return redirect(url_for('signboard.estimate_new'))
        
        if not items_data:
            flash('明細が入力されていません', 'error')
            return redirect(url_for('signboard.estimate_new'))
        
        # 合計金額を計算
        tax_rate = 0.10
        tax_amount = int(total_subtotal * tax_rate)
        total_amount = total_subtotal + tax_amount
        
        # 見積もり番号を生成
        estimate_number = generate_estimate_number()
        
        conn = get_db()
        cur = conn.cursor()
        
        # セッションからproject_id, estimate_type_id, estimate_subtype_idを取得
        project_id = session.get('current_project_id')
        estimate_type_id = session.get('current_estimate_type_id')
        estimate_subtype_id = session.get('current_subtype_id')
        
        # 見積もりヘッダーを登録（明細情報は削除）
        sql = _sql(conn, 
            'INSERT INTO "T_看板見積もり" '
            '("tenant_id", "store_id", "created_by", "created_by_role", "estimate_number", '
            '"customer_name", "width", "height", "material_id", "quantity", "area", "weight", '
            '"price_type", "unit_price", "discount_rate", "discounted_unit_price", "subtotal", '
            '"tax_rate", "tax_amount", "total_amount", "notes", "status", "自動見積もりID", '
            '"project_id", "estimate_type_id", "estimate_subtype_id", "created_at", "updated_at") '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING "id"'
        )
        cur.execute(sql, (
            tenant_id,
            session.get('store_id') if role == 'admin' else None,
            user_id, role, estimate_number, customer_name,
            0, 0, None, 0,  # width, height, material_id, quantity（ダミー値）
            0, None, 'area',  # area, weight, price_type（ダミー値）
            0, 0, 0,  # unit_price, discount_rate, discounted_unit_price（ダミー値）
            total_subtotal, tax_rate, tax_amount, total_amount,
            notes, 'draft',
            int(auto_estimate_id) if auto_estimate_id else None,  # 自動見積もりID
            project_id, estimate_type_id, estimate_subtype_id  # プロジェクト情報
        ))
        estimate_id = cur.fetchone()[0]
        
        # 明細を登録
        for item in items_data:
            calc = item['calc']
            text_proc = item.get('text_processing')
            
            # 文字加工情報がある場合
            if text_proc:
                sql = _sql(conn,
                    'INSERT INTO "T_看板見積もり明細" '
                    '("見積もりID", "材質ID", "幅", "高さ", "数量", "面積", "重量", '
                    '"単価タイプ", "単価", "割引率", "割引後単価", "小計", '
                    '"文字加工モード", "文字内容", "文字幅", "文字高さ", "文字種類ID", '
                    '"推定周長", "実測周長", "周長単価", "加工賃", '
                    '"作成日時", "更新日時") '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)'
                )
                cur.execute(sql, (
                    estimate_id,
                    item['material_id'],
                    item['width'],
                    item['height'],
                    item['quantity'],
                    calc['area'],
                    calc['weight'],
                    calc['price_type'],
                    calc['unit_price'],
                    calc['discount_rate'],
                    calc['discounted_unit_price'],
                    calc['subtotal'] + item['processing_cost'],  # 加工賃を含む
                    text_proc['mode'],
                    text_proc['content'],
                    text_proc['width'],
                    text_proc['height'],
                    text_proc['character_type_id'],
                    text_proc['estimated_perimeter'],
                    text_proc['actual_perimeter'],
                    text_proc['perimeter_unit_price'],
                    text_proc['processing_cost']
                ))
            else:
                # 文字加工情報がない場合
                sql = _sql(conn,
                    'INSERT INTO "T_看板見積もり明細" '
                    '("見積もりID", "材質ID", "幅", "高さ", "数量", "面積", "重量", '
                    '"単価タイプ", "単価", "割引率", "割引後単価", "小計", "作成日時", "更新日時") '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)'
                )
                cur.execute(sql, (
                    estimate_id,
                    item['material_id'],
                    item['width'],
                    item['height'],
                    item['quantity'],
                    calc['area'],
                    calc['weight'],
                    calc['price_type'],
                    calc['unit_price'],
                    calc['discount_rate'],
                    calc['discounted_unit_price'],
                    calc['subtotal']
                ))
        
        # プロジェクトの合計金額を更新
        if project_id:
            sql = _sql(conn, '''
                UPDATE "T_プロジェクト"
                SET "total_amount" = (
                    SELECT COALESCE(SUM("total_amount"), 0)
                    FROM "T_看板見積もり"
                    WHERE "project_id" = %s
                ),
                "updated_at" = CURRENT_TIMESTAMP
                WHERE "id" = %s
            ''')
            cur.execute(sql, (project_id, project_id))
        
        conn.commit()
        conn.close()
        
        # セッションをクリア
        session.pop('current_project_id', None)
        session.pop('current_estimate_type_id', None)
        session.pop('current_subtype_id', None)
        
        flash('見積もりを作成しました', 'success')
        
        # プロジェクトがあればプロジェクト詳細にリダイレクト
        if project_id:
            return redirect(url_for('project.detail', project_id=project_id))
        else:
            return redirect(url_for('signboard.index'))
    
    # サブタイプ情報と材質一覧を取得
    conn = get_db()
    cur = conn.cursor()
    
    # サブタイプ情報を取得
    sql = _sql(conn, '''
        SELECT st."name", st."description", et."name"
        FROM "T_見積サブタイプ" st
        JOIN "T_見積タイプ" et ON st."estimate_type_id" = et."id"
        WHERE st."id" = %s
    ''')
    cur.execute(sql, (subtype_id,))
    subtype_info = cur.fetchone()
    
    # 材質一覧を取得（サブタイプに紐付く大分類の材質のみ）
    sql = _sql(conn, '''
        SELECT DISTINCT m."id", m."name", m."price_type", m."shape_type", m."wall_thickness", m."supports_text_processing"
        FROM "T_材質" m
        JOIN "T_中分類" sc ON m."subcategory_id" = sc."id"
        JOIN "T_大分類" c ON sc."category_id" = c."id"
        WHERE m."tenant_id" = %s AND m."active" = 1 AND c."subtype_id" = %s
        ORDER BY m."name"
    ''')
    cur.execute(sql, (tenant_id, subtype_id))
    materials = cur.fetchall()
    conn.close()
    
    return render_template('signboard_estimate_new.html', 
                         materials=materials, 
                         subtype_info=subtype_info)


@bp.route('/<int:estimate_id>')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
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
            'm."name" as material_name, e."自動見積もりID" '
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
            'm."name" as material_name, e."自動見積もりID" '
            'FROM "T_看板見積もり" e '
            'LEFT JOIN "T_材質" m ON e."material_id" = m."id" '
            'WHERE e."id" = %s AND e."tenant_id" = %s AND e."store_id" = %s'
        )
        cur.execute(sql, (estimate_id, tenant_id, store_id))
    
    estimate = cur.fetchone()
    
    if not estimate:
        conn.close()
        flash('見積もりが見つかりません', 'error')
        return redirect(url_for('signboard.index'))
    
    # 明細を取得
    sql = _sql(conn,
        'SELECT i."見積もりID", i."材質ID", i."幅", i."高さ", i."数量", i."面積", i."重量", '
        'i."単価タイプ", i."単価", i."割引率", i."割引後単価", i."小計", '
        'm."name" as material_name '
        'FROM "T_看板見積もり明細" i '
        'LEFT JOIN "T_材質" m ON i."材質ID" = m."id" '
        'WHERE i."見積もりID" = %s '
        'ORDER BY i."ID"'
    )
    cur.execute(sql, (estimate_id,))
    items = cur.fetchall()
    
    # 自動見積もりIDから画像ファイルを取得
    blueprint_images = []
    auto_estimate_id = estimate[20]  # 自動見積もりIDは21番目のカラム
    if auto_estimate_id:
        sql = _sql(conn,
            'SELECT "ID", "ファイル名", "ファイルパス" '
            'FROM "T_設計図ファイル" '
            'WHERE "自動見積もりID" = %s '
            'ORDER BY "ID"'
        )
        cur.execute(sql, (auto_estimate_id,))
        blueprint_images = cur.fetchall()
    
    conn.close()
    
    return render_template('signboard_estimate_detail.html', estimate=estimate, items=items, blueprint_images=blueprint_images)


@bp.route('/api/calculate', methods=['POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
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


@bp.route('/<int:estimate_id>/edit', methods=['GET', 'POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def estimate_edit(estimate_id):
    """見積もり編集"""
    tenant_id = session.get('tenant_id')
    role = session.get('role')
    user_id = session.get('user_id')
    
    conn = get_db()
    cur = conn.cursor()
    
    # 見積もりの権限チェック
    if role == 'tenant_admin':
        sql = _sql(conn, 
            'SELECT "id" FROM "T_看板見積もり" WHERE "id" = %s AND "tenant_id" = %s'
        )
        cur.execute(sql, (estimate_id, tenant_id))
    else:
        store_id = session.get('store_id')
        sql = _sql(conn, 
            'SELECT "id" FROM "T_看板見積もり" WHERE "id" = %s AND "tenant_id" = %s AND "store_id" = %s'
        )
        cur.execute(sql, (estimate_id, tenant_id, store_id))
    
    if not cur.fetchone():
        conn.close()
        flash('見積もりが見つかりません', 'error')
        return redirect(url_for('signboard.index'))
    
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        notes = request.form.get('notes')
        
        # 明細データを取得
        items_data = []
        total_subtotal = 0
        
        # フォームから明細データを抽出
        form_keys = list(request.form.keys())
        item_ids = set()
        for key in form_keys:
            if key.startswith('items[') and '][material_id]' in key:
                item_id = key.split('[')[1].split(']')[0]
                item_ids.add(item_id)
        
        # 各明細の価格を計算
        for item_id in item_ids:
            try:
                material_id_str = request.form.get(f'items[{item_id}][material_id]')
                width_str = request.form.get(f'items[{item_id}][width]')
                height_str = request.form.get(f'items[{item_id}][height]')
                quantity_str = request.form.get(f'items[{item_id}][quantity]', '1')
                
                if not material_id_str or not width_str or not height_str:
                    flash(f'明細{item_id}の入力が不完全です', 'error')
                    return redirect(url_for('signboard.estimate_new'))
                
                material_id = int(material_id_str)
                width = float(width_str)
                height = float(height_str)
                quantity = int(quantity_str)
            except (ValueError, TypeError) as e:
                flash(f'明細{item_id}の入力値が不正です: {str(e)}', 'error')
                return redirect(url_for('signboard.estimate_new'))
            
            try:
                calc = calculate_price(material_id, width, height, quantity)
                items_data.append({
                    'material_id': material_id,
                    'width': width,
                    'height': height,
                    'quantity': quantity,
                    'calc': calc
                })
                total_subtotal += calc['subtotal']
            except ValueError as e:
                conn.close()
                flash(f'明細{item_id}の計算エラー: {str(e)}', 'error')
                return redirect(url_for('signboard.estimate_edit', estimate_id=estimate_id))
        
        if not items_data:
            conn.close()
            flash('明細が入力されていません', 'error')
            return redirect(url_for('signboard.estimate_edit', estimate_id=estimate_id))
        
        # 合計金額を計算
        tax_rate = 0.10
        tax_amount = int(total_subtotal * tax_rate)
        total_amount = total_subtotal + tax_amount
        
        # 見積もりヘッダーを更新
        sql = _sql(conn, 
            'UPDATE "T_看板見積もり" SET '
            '"customer_name" = %s, "subtotal" = %s, "tax_rate" = %s, "tax_amount" = %s, '
            '"total_amount" = %s, "notes" = %s, "updated_at" = CURRENT_TIMESTAMP '
            'WHERE "id" = %s'
        )
        cur.execute(sql, (
            customer_name, total_subtotal, tax_rate, tax_amount, total_amount, notes, estimate_id
        ))
        
        # 既存の明細を削除
        sql = _sql(conn, 'DELETE FROM "T_看板見積もり明細" WHERE "見積もりID" = %s')
        cur.execute(sql, (estimate_id,))
        
        # 新しい明細を登録
        for item in items_data:
            calc = item['calc']
            sql = _sql(conn,
                'INSERT INTO "T_看板見積もり明細" '
                '("見積もりID", "材質ID", "幅", "高さ", "数量", "面積", "重量", '
                '"単価タイプ", "単価", "割引率", "割引後単価", "小計", "作成日時", "更新日時") '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)'
            )
            cur.execute(sql, (
                estimate_id,
                item['material_id'],
                item['width'],
                item['height'],
                item['quantity'],
                calc['area'],
                calc['weight'],
                calc['price_type'],
                calc['unit_price'],
                calc['discount_rate'],
                calc['discounted_unit_price'],
                calc['subtotal']
            ))
        
        conn.commit()
        conn.close()
        
        flash('見積もりを更新しました', 'success')
        return redirect(url_for('signboard.estimate_detail', estimate_id=estimate_id))
    
    # 見積もり情報を取得
    sql = _sql(conn, 
        'SELECT "id", "estimate_number", "customer_name", "notes" '
        'FROM "T_看板見積もり" WHERE "id" = %s'
    )
    cur.execute(sql, (estimate_id,))
    estimate = cur.fetchone()
    
    # 明細を取得
    sql = _sql(conn,
        'SELECT "id", "材質ID", "幅", "高さ", "数量" '
        'FROM "T_看板見積もり明細" WHERE "見積もりID" = %s ORDER BY "id"'
    )
    cur.execute(sql, (estimate_id,))
    items = cur.fetchall()
    
    # 材質一覧を取得
    sql = _sql(conn, 
        'SELECT "id", "name", "price_type", "shape_type", "wall_thickness" FROM "T_材質" '
        'WHERE "tenant_id" = %s AND "active" = 1 ORDER BY "name"'
    )
    cur.execute(sql, (tenant_id,))
    materials = cur.fetchall()
    
    conn.close()
    
    return render_template('signboard_estimate_edit.html', 
                         estimate=estimate, items=items, materials=materials)


@bp.route('/<int:estimate_id>/delete', methods=['POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def estimate_delete(estimate_id):
    """見積もり削除"""
    tenant_id = session.get('tenant_id')
    role = session.get('role')
    
    conn = get_db()
    cur = conn.cursor()
    
    # 見積もりの権限チェック
    if role == 'tenant_admin':
        sql = _sql(conn, 
            'SELECT "estimate_number" FROM "T_看板見積もり" WHERE "id" = %s AND "tenant_id" = %s'
        )
        cur.execute(sql, (estimate_id, tenant_id))
    else:
        store_id = session.get('store_id')
        sql = _sql(conn, 
            'SELECT "estimate_number" FROM "T_看板見積もり" WHERE "id" = %s AND "tenant_id" = %s AND "store_id" = %s'
        )
        cur.execute(sql, (estimate_id, tenant_id, store_id))
    
    row = cur.fetchone()
    if not row:
        conn.close()
        flash('見積もりが見つかりません', 'error')
        return redirect(url_for('signboard.index'))
    
    estimate_number = row[0]
    
    # 明細を削除
    sql = _sql(conn, 'DELETE FROM "T_看板見積もり明細" WHERE "見積もりID" = %s')
    cur.execute(sql, (estimate_id,))
    
    # 見積もりを削除
    sql = _sql(conn, 'DELETE FROM "T_看板見積もり" WHERE "id" = %s')
    cur.execute(sql, (estimate_id,))
    
    conn.commit()
    conn.close()
    
    flash(f'見積もり {estimate_number} を削除しました', 'success')
    return redirect(url_for('signboard.index'))
