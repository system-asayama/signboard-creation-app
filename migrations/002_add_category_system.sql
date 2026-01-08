-- マイグレーション: 大分類システムを追加
-- 作成日: 2026-01-08

-- 大分類マスタテーブルを作成
CREATE TABLE IF NOT EXISTS "T_大分類" (
    "id" SERIAL PRIMARY KEY,
    "code" VARCHAR(20) NOT NULL UNIQUE,
    "name" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "display_order" INTEGER NOT NULL DEFAULT 0,
    "active" BOOLEAN NOT NULL DEFAULT TRUE,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 大分類の初期データを挿入
INSERT INTO "T_大分類" ("code", "name", "description", "display_order") VALUES
('panel', '板面（表示面）', '板面製作費', 1),
('body', '看板本体（表示体）', '看板本体製作費（箱、フレーム、内部照明）', 2),
('structure', '支柱・構造部材', '支柱・構造部材製作費（ポール含む）', 3),
('foundation', '基礎・施工', '基礎工事費', 4)
ON CONFLICT ("code") DO NOTHING;

-- 材質マスタに大分類IDカラムを追加
ALTER TABLE "T_材質" ADD COLUMN IF NOT EXISTS "category_id" INTEGER;

-- 外部キー制約を追加（既存の場合はスキップ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_material_category'
    ) THEN
        ALTER TABLE "T_材質" ADD CONSTRAINT "fk_material_category" 
            FOREIGN KEY ("category_id") REFERENCES "T_大分類"("id") ON DELETE SET NULL;
    END IF;
END $$;

-- 見積もり明細に大分類IDカラムを追加
ALTER TABLE "T_看板見積もり明細" ADD COLUMN IF NOT EXISTS "category_id" INTEGER;

-- 外部キー制約を追加（既存の場合はスキップ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_item_category'
    ) THEN
        ALTER TABLE "T_看板見積もり明細" ADD CONSTRAINT "fk_item_category" 
            FOREIGN KEY ("category_id") REFERENCES "T_大分類"("id") ON DELETE SET NULL;
    END IF;
END $$;

-- コメント
COMMENT ON TABLE "T_大分類" IS '見積もり明細の大分類マスタ';
COMMENT ON COLUMN "T_大分類"."code" IS '大分類コード（panel, body, structure, foundation）';
COMMENT ON COLUMN "T_大分類"."name" IS '大分類名';
COMMENT ON COLUMN "T_大分類"."description" IS '大分類の説明';
COMMENT ON COLUMN "T_大分類"."display_order" IS '表示順序';
COMMENT ON COLUMN "T_材質"."category_id" IS '大分類ID';
COMMENT ON COLUMN "T_看板見積もり明細"."category_id" IS '大分類ID';
