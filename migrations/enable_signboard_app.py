"""
看板見積もりアプリを全テナントに対して有効化するマイグレーションスクリプト
"""
import os
import sys
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import SessionLocal
from app.models_login import TTenant, TTenantAppSetting


def enable_signboard_app():
    """看板見積もりアプリを全テナントに対して有効化"""
    db = SessionLocal()
    
    try:
        # 全テナントを取得
        tenants = db.query(TTenant).filter(TTenant.有効 == 1).all()
        
        print(f"有効なテナント数: {len(tenants)}")
        
        for tenant in tenants:
            # 既に設定が存在するかチェック
            existing = db.query(TTenantAppSetting).filter(
                TTenantAppSetting.tenant_id == tenant.id,
                TTenantAppSetting.app_id == 'signboard'
            ).first()
            
            if existing:
                print(f"テナント「{tenant.名称}」: 既に設定済み")
                # 既存の設定を有効化
                existing.enabled = 1
            else:
                print(f"テナント「{tenant.名称}」: 新規設定を作成")
                # 新規設定を作成
                app_setting = TTenantAppSetting(
                    tenant_id=tenant.id,
                    app_id='signboard',
                    enabled=1
                )
                db.add(app_setting)
        
        db.commit()
        print("看板見積もりアプリの有効化が完了しました")
        
    except Exception as e:
        db.rollback()
        print(f"エラーが発生しました: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    enable_signboard_app()
