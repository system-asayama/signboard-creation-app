#!/usr/bin/env python3
"""
看板見積もり機能のテーブル追加とマイグレーション
"""
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base, engine
from app.models_signboard import Material, SignboardEstimate


def migrate():
    """看板見積もり関連テーブルを作成"""
    print("看板見積もり関連テーブルを作成中...")
    
    try:
        # テーブル作成
        Base.metadata.create_all(bind=engine)
        print("✅ テーブル作成完了")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False
    
    return True


if __name__ == '__main__':
    migrate()
