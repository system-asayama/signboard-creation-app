-- 005_add_project_system.sql
-- プロジェクト（案件）システムの追加

-- プロジェクトテーブル（案件）
CREATE TABLE IF NOT EXISTS "T_プロジェクト" (
    "id" SERIAL PRIMARY KEY,
    "tenant_id" INTEGER NOT NULL,
    "project_number" VARCHAR(50) NOT NULL UNIQUE,
    "project_name" VARCHAR(200) NOT NULL,
    "customer_name" VARCHAR(200),
    "customer_contact" TEXT,
    "site_address" TEXT,
    "notes" TEXT,
    "status" VARCHAR(50) DEFAULT 'draft',
    "total_amount" INTEGER DEFAULT 0,
    "created_by" INTEGER,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("tenant_id") REFERENCES "T_テナント"("id") ON DELETE CASCADE
);

-- プロジェクト番号のインデックス
CREATE INDEX IF NOT EXISTS "idx_project_number" ON "T_プロジェクト"("project_number");
CREATE INDEX IF NOT EXISTS "idx_project_tenant" ON "T_プロジェクト"("tenant_id");

-- 既存の見積もりテーブルにproject_idを追加
ALTER TABLE "T_看板見積もり" ADD COLUMN IF NOT EXISTS "project_id" INTEGER;

-- 外部キー制約を追加（既に存在する場合はスキップ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_estimate_project'
    ) THEN
        ALTER TABLE "T_看板見積もり" ADD CONSTRAINT "fk_estimate_project" 
            FOREIGN KEY ("project_id") REFERENCES "T_プロジェクト"("id") ON DELETE CASCADE;
    END IF;
END $$;

-- 見積もりテーブルにestimate_type_idを追加（どの見積タイプか）
ALTER TABLE "T_看板見積もり" ADD COLUMN IF NOT EXISTS "estimate_type_id" INTEGER;

-- 外部キー制約を追加（既に存在する場合はスキップ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_estimate_type'
    ) THEN
        ALTER TABLE "T_看板見積もり" ADD CONSTRAINT "fk_estimate_type" 
            FOREIGN KEY ("estimate_type_id") REFERENCES "T_見積タイプ"("id") ON DELETE SET NULL;
    END IF;
END $$;

-- 見積もりテーブルにestimate_subtype_idを追加（どのサブタイプか）
ALTER TABLE "T_看板見積もり" ADD COLUMN IF NOT EXISTS "estimate_subtype_id" INTEGER;

-- 外部キー制約を追加（既に存在する場合はスキップ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_estimate_subtype'
    ) THEN
        ALTER TABLE "T_看板見積もり" ADD CONSTRAINT "fk_estimate_subtype" 
            FOREIGN KEY ("estimate_subtype_id") REFERENCES "T_見積サブタイプ"("id") ON DELETE SET NULL;
    END IF;
END $$;

-- 既存の見積もりを自動的にプロジェクトに変換
-- 各見積もりに対して1つのプロジェクトを作成
INSERT INTO "T_プロジェクト" (
    "tenant_id",
    "project_number",
    "project_name",
    "customer_name",
    "notes",
    "status",
    "total_amount",
    "created_by",
    "created_at",
    "updated_at"
)
SELECT 
    "tenant_id",
    "estimate_number" || '-PRJ',
    "customer_name" || '様 案件',
    "customer_name",
    "notes",
    'completed',
    "total_amount",
    "created_by",
    "created_at",
    "updated_at"
FROM "T_看板見積もり"
WHERE "project_id" IS NULL
ON CONFLICT DO NOTHING;

-- 既存の見積もりをプロジェクトに紐付け
UPDATE "T_看板見積もり" e
SET "project_id" = p."id"
FROM "T_プロジェクト" p
WHERE e."project_id" IS NULL 
  AND p."project_number" = e."estimate_number" || '-PRJ';

-- 既存の見積もりに見積タイプを設定（デフォルトで「看板・表示設備」の「固定表示看板」）
UPDATE "T_看板見積もり"
SET 
    "estimate_type_id" = (SELECT id FROM "T_見積タイプ" WHERE code = 'signage_equipment' LIMIT 1),
    "estimate_subtype_id" = (SELECT id FROM "T_見積サブタイプ" WHERE code = 'fixed_sign' LIMIT 1)
WHERE "estimate_type_id" IS NULL;

-- 大分類をデフォルトで「固定表示看板」サブタイプに紐付け
UPDATE "T_大分類"
SET "subtype_id" = (SELECT id FROM "T_見積サブタイプ" WHERE code = 'fixed_sign' LIMIT 1)
WHERE "subtype_id" IS NULL;
