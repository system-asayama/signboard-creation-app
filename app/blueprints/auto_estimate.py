from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from app.utils.decorators import require_roles, require_app_enabled
import os
from datetime import datetime
import json
import base64

auto_estimate_bp = Blueprint('auto_estimate', __name__, url_prefix='/auto_estimate')

# アップロードフォルダの設定
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'blueprints')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# フォルダが存在しない場合は作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auto_estimate_bp.route('/')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def index():
    """自動見積もり一覧"""
    from app.utils.db import get_db_connection
    
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('ログインが必要です', 'error')
        return redirect(url_for('select_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT "ID", "顧客名", "ステータス", "作成日時"
        FROM "T_自動見積もり"
        WHERE "テナントID" = %s
        ORDER BY "作成日時" DESC
    ''', (tenant_id,))
    
    auto_estimates = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('auto_estimate_list.html', auto_estimates=auto_estimates)

@auto_estimate_bp.route('/new', methods=['GET', 'POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def new():
    """自動見積もり新規作成"""
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('ログインが必要です', 'error')
        return redirect(url_for('select_login'))
    
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        
        if not customer_name:
            flash('顧客名を入力してください', 'error')
            return redirect(url_for('auto_estimate.new'))
        
        # ファイルチェック
        if 'blueprint_files' not in request.files:
            flash('ファイルが選択されていません', 'error')
            return redirect(url_for('auto_estimate.new'))
        
        files = request.files.getlist('blueprint_files')
        
        if not files or files[0].filename == '':
            flash('ファイルが選択されていません', 'error')
            return redirect(url_for('auto_estimate.new'))
        
        from app.utils.db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # 自動見積もりレコードを作成
            cur.execute('''
                INSERT INTO "T_自動見積もり" ("顧客名", "ステータス", "テナントID")
                VALUES (%s, %s, %s)
                RETURNING "ID"
            ''', (customer_name, '解析中', tenant_id))
            
            auto_estimate_id = cur.fetchone()[0]
            
            # ファイルを保存
            uploaded_files = []
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{auto_estimate_id}_{timestamp}_{filename}"
                    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                    file.save(filepath)
                    
                    # データベースに保存
                    cur.execute('''
                        INSERT INTO "T_設計図ファイル" ("自動見積もりID", "ファイル名", "ファイルパス", "ファイルタイプ")
                        VALUES (%s, %s, %s, %s)
                    ''', (auto_estimate_id, filename, filepath, filename.rsplit('.', 1)[1].lower()))
                    
                    uploaded_files.append(filepath)
            
            conn.commit()
            
            # AI解析にリダイレクト
            return redirect(url_for('auto_estimate.analyze', auto_estimate_id=auto_estimate_id))
            
        except Exception as e:
            conn.rollback()
            flash(f'エラーが発生しました: {str(e)}', 'error')
            return redirect(url_for('auto_estimate.new'))
        finally:
            cur.close()
            conn.close()
    
    return render_template('auto_estimate_new.html')

@auto_estimate_bp.route('/analyze/<int:auto_estimate_id>')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def analyze(auto_estimate_id):
    """AI解析実行"""
    from app.utils.db import get_db_connection
    
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('ログインが必要です', 'error')
        return redirect(url_for('select_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 自動見積もり情報を取得
    cur.execute('''
        SELECT "ID", "顧客名", "ステータス"
        FROM "T_自動見積もり"
        WHERE "ID" = %s AND "テナントID" = %s
    ''', (auto_estimate_id, tenant_id))
    
    auto_estimate = cur.fetchone()
    
    if not auto_estimate:
        flash('自動見積もりが見つかりません', 'error')
        return redirect(url_for('auto_estimate.index'))
    
    # 設計図ファイルを取得
    cur.execute('''
        SELECT "ID", "ファイル名", "ファイルパス", "ファイルタイプ"
        FROM "T_設計図ファイル"
        WHERE "自動見積もりID" = %s
    ''', (auto_estimate_id,))
    
    blueprint_files = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('auto_estimate_analyze.html', 
                         auto_estimate=auto_estimate,
                         blueprint_files=blueprint_files)

@auto_estimate_bp.route('/api/analyze/<int:auto_estimate_id>', methods=['POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def api_analyze(auto_estimate_id):
    """AI解析API"""
    from app.utils.db import get_db_connection
    
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        return jsonify({'error': 'ログインが必要です'}), 401
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 設計図ファイルを取得
        cur.execute('''
            SELECT "ファイルパス", "ファイルタイプ"
            FROM "T_設計図ファイル"
            WHERE "自動見積もりID" = %s
        ''', (auto_estimate_id,))
        
        blueprint_files = cur.fetchall()
        
        if not blueprint_files:
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        # OpenAIクライアントを取得（階層的にAPIキーを検索）
        from app.utils.api_key import get_openai_client
        client = get_openai_client(tenant_id=tenant_id, app_name='signboard')
        
        if not client:
            return jsonify({'error': 'OpenAI APIキーが設定されていません。テナント情報またはテナントアプリ設定から設定してください。'}), 400
        
        all_items = []
        
        for filepath, filetype in blueprint_files:
            # 画像をBase64エンコード
            with open(filepath, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # GPT-4 Visionで解析
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """この設計図から看板の情報を抽出してください。
                                
以下の情報をJSON形式で返してください：
{
  "items": [
    {
      "material": "材質名（アルミ、鉄骨、アクリルなど）",
      "width": 幅（mm、数値のみ）,
      "height": 高さ（mm、数値のみ）,
      "quantity": 数量（数値のみ）,
      "notes": "備考（あれば）"
    }
  ]
}

- 複数の看板がある場合は、itemsに複数のオブジェクトを含めてください
- 数値は単位を除いた数字のみを返してください
- 材質が不明な場合は"不明"としてください
- 寸法が読み取れない場合は0としてください"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{filetype};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            # レスポンスをパース
            result_text = response.choices[0].message.content
            
            # JSONを抽出（```json ... ```の場合に対応）
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            result_json = json.loads(result_text)
            all_items.extend(result_json.get('items', []))
        
        # データベースに保存
        for item in all_items:
            cur.execute('''
                INSERT INTO "T_自動見積もり明細" 
                ("自動見積もりID", "材質名", "幅", "高さ", "数量", "備考")
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                auto_estimate_id,
                item.get('material', '不明'),
                item.get('width', 0),
                item.get('height', 0),
                item.get('quantity', 1),
                item.get('notes', '')
            ))
        
        # ステータスを更新
        cur.execute('''
            UPDATE "T_自動見積もり"
            SET "ステータス" = '確認待ち', "AI解析結果JSON" = %s, "更新日時" = CURRENT_TIMESTAMP
            WHERE "ID" = %s
        ''', (json.dumps(all_items, ensure_ascii=False), auto_estimate_id))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'items': all_items
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@auto_estimate_bp.route('/confirm/<int:auto_estimate_id>', methods=['GET', 'POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def confirm(auto_estimate_id):
    """AI解析結果の確認・編集"""
    from app.utils.db import get_db_connection
    
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('ログインが必要です', 'error')
        return redirect(url_for('select_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        # 編集された明細を保存
        try:
            # 既存の明細を削除
            cur.execute('''
                DELETE FROM "T_自動見積もり明細"
                WHERE "自動見積もりID" = %s
            ''', (auto_estimate_id,))
            
            # 新しい明細を保存
            items = request.form.getlist('items')
            for item_json in items:
                item = json.loads(item_json)
                cur.execute('''
                    INSERT INTO "T_自動見積もり明細" 
                    ("自動見積もりID", "材質名", "幅", "高さ", "数量", "備考")
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (
                    auto_estimate_id,
                    item.get('material', '不明'),
                    item.get('width', 0),
                    item.get('height', 0),
                    item.get('quantity', 1),
                    item.get('notes', '')
                ))
            
            conn.commit()
            flash('明細を更新しました', 'success')
            return redirect(url_for('auto_estimate.confirm', auto_estimate_id=auto_estimate_id))
            
        except Exception as e:
            conn.rollback()
            flash(f'エラーが発生しました: {str(e)}', 'error')
    
    # 自動見積もり情報を取得
    cur.execute('''
        SELECT "ID", "顧客名", "ステータス"
        FROM "T_自動見積もり"
        WHERE "ID" = %s AND "テナントID" = %s
    ''', (auto_estimate_id, tenant_id))
    
    auto_estimate = cur.fetchone()
    
    if not auto_estimate:
        flash('自動見積もりが見つかりません', 'error')
        return redirect(url_for('auto_estimate.index'))
    
    # 明細を取得
    cur.execute('''
        SELECT "ID", "材質名", "幅", "高さ", "数量", "備考"
        FROM "T_自動見積もり明細"
        WHERE "自動見積もりID" = %s
    ''', (auto_estimate_id,))
    
    items = cur.fetchall()
    
    # 材質マスタを取得
    cur.execute('''
        SELECT "id", "name", "price_type", "unit_price_area", "unit_price_weight"
        FROM "T_材質"
        WHERE "tenant_id" = %s AND "active" = 1
        ORDER BY "id"
    ''', (tenant_id,))
    
    materials = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('auto_estimate_confirm.html', 
                         auto_estimate=auto_estimate,
                         items=items,
                         materials=materials)

@auto_estimate_bp.route('/create_estimate/<int:auto_estimate_id>', methods=['POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def create_estimate(auto_estimate_id):
    """自動見積もりから手動見積もりを作成"""
    from app.utils.db import get_db_connection
    
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('ログインが必要です', 'error')
        return redirect(url_for('select_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 自動見積もり情報を取得
        cur.execute('''
            SELECT "顧客名"
            FROM "T_自動見積もり"
            WHERE "ID" = %s AND "テナントID" = %s
        ''', (auto_estimate_id, tenant_id))
        
        auto_estimate = cur.fetchone()
        
        if not auto_estimate:
            flash('自動見積もりが見つかりません', 'error')
            return redirect(url_for('auto_estimate.index'))
        
        customer_name = auto_estimate[0]
        
        # 明細を取得
        cur.execute('''
            SELECT "材質名", "幅", "高さ", "数量", "備考"
            FROM "T_自動見積もり明細"
            WHERE "自動見積もりID" = %s
        ''', (auto_estimate_id,))
        
        items = cur.fetchall()
        
        if not items:
            flash('明細が見つかりません', 'error')
            return redirect(url_for('auto_estimate.confirm', auto_estimate_id=auto_estimate_id))
        
        # 見積もり番号を生成
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        
        cur.execute('''
            SELECT COUNT(*) FROM "T_看板見積もり"
            WHERE "見積もり番号" LIKE %s
        ''', (f'EST-{today}-%',))
        
        count = cur.fetchone()[0]
        estimate_number = f'EST-{today}-{count + 1:04d}'
        
        # 見積もりヘッダーを作成
        cur.execute('''
            INSERT INTO "T_看板見積もり" 
            ("見積もり番号", "顧客名", "テナントID", "material_id")
            VALUES (%s, %s, %s, %s)
            RETURNING "id"
        ''', (estimate_number, customer_name, tenant_id, None))
        
        estimate_id = cur.fetchone()[0]
        
        # 明細を作成
        for item in items:
            material_name, width, height, quantity, notes = item
            
            # 材質名から材質IDを取得
            cur.execute('''
                SELECT "id", "単価タイプ", "単価", "比重"
                FROM "T_材質"
                WHERE "材質名" = %s AND "テナントID" = %s
                LIMIT 1
            ''', (material_name, tenant_id))
            
            material = cur.fetchone()
            
            if not material:
                # 材質が見つからない場合はデフォルトの材質を使用
                cur.execute('''
                    SELECT "id", "単価タイプ", "単価", "比重"
                    FROM "T_材質"
                    WHERE "テナントID" = %s
                    ORDER BY "id"
                    LIMIT 1
                ''', (tenant_id,))
                
                material = cur.fetchone()
            
            if material:
                material_id, price_type, unit_price, density = material
                
                # 面積計算（mm² → ㎡）
                area = (width * height) / 1000000
                
                # 重量計算（㎡ × 比重）
                weight = area * (density or 0)
                
                # 小計計算
                if price_type == '面積単価':
                    subtotal = area * unit_price * quantity
                else:  # 重量単価
                    subtotal = weight * unit_price * quantity
                
                # 明細を挿入
                cur.execute('''
                    INSERT INTO "T_看板見積もり明細"
                    ("見積もりID", "材質ID", "幅", "高さ", "数量", "面積", "重量", 
                     "単価タイプ", "単価", "割引率", "割引後単価", "小計")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    estimate_id, material_id, width, height, quantity,
                    area, weight, price_type, unit_price, 0, unit_price, subtotal
                ))
        
        # 自動見積もりのステータスを更新
        cur.execute('''
            UPDATE "T_自動見積もり"
            SET "ステータス" = '完了', "更新日時" = CURRENT_TIMESTAMP
            WHERE "ID" = %s
        ''', (auto_estimate_id,))
        
        conn.commit()
        
        flash(f'見積もり {estimate_number} を作成しました', 'success')
        return redirect(url_for('signboard.detail', estimate_id=estimate_id))
        
    except Exception as e:
        conn.rollback()
        flash(f'エラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('auto_estimate.confirm', auto_estimate_id=auto_estimate_id))
    finally:
        cur.close()
        conn.close()
