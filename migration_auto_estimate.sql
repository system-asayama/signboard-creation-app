-- 自動見積もりテーブル
CREATE TABLE IF NOT EXISTS "T_自動見積もり" (
    "ID" SERIAL PRIMARY KEY,
    "顧客名" VARCHAR(255) NOT NULL,
    "ステータス" VARCHAR(50) NOT NULL DEFAULT '解析中',
    "AI解析結果JSON" TEXT,
    "テナントID" INTEGER NOT NULL,
    "作成日時" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "更新日時" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 設計図ファイルテーブル
CREATE TABLE IF NOT EXISTS "T_設計図ファイル" (
    "ID" SERIAL PRIMARY KEY,
    "自動見積もりID" INTEGER NOT NULL REFERENCES "T_自動見積もり"("ID") ON DELETE CASCADE,
    "ファイル名" VARCHAR(255) NOT NULL,
    "ファイルパス" VARCHAR(500) NOT NULL,
    "ファイルタイプ" VARCHAR(50) NOT NULL,
    "アップロード日時" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS "idx_auto_estimate_tenant_id" ON "T_自動見積もり"("テナントID");
CREATE INDEX IF NOT EXISTS "idx_blueprint_file_auto_estimate_id" ON "T_設計図ファイル"("自動見積もりID");

-- 自動見積もり明細テーブル（AI解析結果を一時保存）
CREATE TABLE IF NOT EXISTS "T_自動見積もり明細" (
    "ID" SERIAL PRIMARY KEY,
    "自動見積もりID" INTEGER NOT NULL REFERENCES "T_自動見積もり"("ID") ON DELETE CASCADE,
    "材質名" VARCHAR(100),
    "幅" NUMERIC(10, 2),
    "高さ" NUMERIC(10, 2),
    "数量" INTEGER DEFAULT 1,
    "備考" TEXT,
    "作成日時" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS "idx_auto_estimate_item_auto_estimate_id" ON "T_自動見積もり明細"("自動見積もりID");
