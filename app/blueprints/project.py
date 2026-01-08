"""
プロジェクト（案件）管理機能のBlueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.decorators import require_roles, require_app_enabled
from app.utils.db import get_db, _sql
from datetime import datetime

bp = Blueprint('project', __name__, url_prefix='/signboard/projects')


def generate_project_number():
    """プロジェクト番号を生成（例: PRJ-20260108-0001）"""
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    
    conn = get_db()
    cur = conn.cursor()
    
    # 今日のプロジェクト番号の最大値を取得
    sql = _sql(conn, 'SELECT MAX("project_number") FROM "T_プロジェクト" WHERE "project_number" LIKE %s')
    cur.execute(sql, (f'PRJ-{date_str}-%',))
    row = cur.fetchone()
    conn.close()
    
    if row and row[0]:
        # 既存の番号から連番を抽出
        last_number = int(row[0].split('-')[-1])
        seq = last_number + 1
    else:
        seq = 1
    
    return f'PRJ-{date_str}-{seq:04d}'


@bp.route('/')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def index():
    """プロジェクト一覧"""
    tenant_id = session.get('tenant_id')
    role = session.get('role')
    
    conn = get_db()
    cur = conn.cursor()
    
    # プロジェクト一覧を取得
    sql = _sql(conn, '''
        SELECT 
            p."id",
            p."project_number",
            p."project_name",
            p."customer_name",
            p."status",
            p."total_amount",
            p."created_at",
            COUNT(e."id") as estimate_count
        FROM "T_プロジェクト" p
        LEFT JOIN "T_看板見積もり" e ON p."id" = e."project_id"
        WHERE p."tenant_id" = %s
        GROUP BY p."id"
        ORDER BY p."created_at" DESC
    ''')
    cur.execute(sql, (tenant_id,))
    projects = cur.fetchall()
    conn.close()
    
    return render_template('project_list.html', projects=projects)


@bp.route('/new', methods=['GET', 'POST'])
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def new():
    """プロジェクト新規作成"""
    tenant_id = session.get('tenant_id')
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        customer_name = request.form.get('customer_name')
        customer_contact = request.form.get('customer_contact')
        site_address = request.form.get('site_address')
        notes = request.form.get('notes')
        
        if not project_name:
            flash('プロジェクト名を入力してください', 'error')
            return redirect(url_for('project.new'))
        
        # プロジェクト番号を生成
        project_number = generate_project_number()
        
        # プロジェクトを登録
        conn = get_db()
        cur = conn.cursor()
        
        sql = _sql(conn, '''
            INSERT INTO "T_プロジェクト" (
                "tenant_id", "project_number", "project_name", "customer_name",
                "customer_contact", "site_address", "notes", "status", "created_by"
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING "id"
        ''')
        cur.execute(sql, (
            tenant_id, project_number, project_name, customer_name,
            customer_contact, site_address, notes, 'draft', user_id
        ))
        project_id = cur.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        flash('プロジェクトを作成しました', 'success')
        return redirect(url_for('project.detail', project_id=project_id))
    
    return render_template('project_new.html')


@bp.route('/<int:project_id>')
@require_app_enabled('signboard')
@require_roles('tenant_admin', 'admin')
def detail(project_id):
    """プロジェクト詳細"""
    tenant_id = session.get('tenant_id')
    
    conn = get_db()
    cur = conn.cursor()
    
    # プロジェクト情報を取得
    sql = _sql(conn, '''
        SELECT 
            "id", "project_number", "project_name", "customer_name",
            "customer_contact", "site_address", "notes", "status",
            "total_amount", "created_at", "updated_at"
        FROM "T_プロジェクト"
        WHERE "id" = %s AND "tenant_id" = %s
    ''')
    cur.execute(sql, (project_id, tenant_id))
    project = cur.fetchone()
    
    if not project:
        conn.close()
        flash('プロジェクトが見つかりません', 'error')
        return redirect(url_for('project.index'))
    
    # プロジェクト内の見積もり一覧を取得
    sql = _sql(conn, '''
        SELECT 
            e."id",
            e."estimate_number",
            et."name" as type_name,
            est."name" as subtype_name,
            e."total_amount",
            e."created_at"
        FROM "T_看板見積もり" e
        LEFT JOIN "T_見積タイプ" et ON e."estimate_type_id" = et."id"
        LEFT JOIN "T_見積サブタイプ" est ON e."estimate_subtype_id" = est."id"
        WHERE e."project_id" = %s
        ORDER BY e."created_at" DESC
    ''')
    cur.execute(sql, (project_id,))
    estimates = cur.fetchall()
    
    conn.close()
    
    return render_template('project_detail.html', project=project, estimates=estimates)
