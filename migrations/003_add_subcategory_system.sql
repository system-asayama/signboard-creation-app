-- マイグレーション: 中分類システムを追加
-- 作成日: 2026-01-08

-- 中分類マスタテーブルを作成
CREATE TABLE IF NOT EXISTS "T_中分類" (
    "id" SERIAL PRIMARY KEY,
    "category_id" INTEGER NOT NULL,
    "code" VARCHAR(50) NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "display_order" INTEGER NOT NULL DEFAULT 0,
    "active" BOOLEAN NOT NULL DEFAULT TRUE,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "fk_subcategory_category" FOREIGN KEY ("category_id") 
        REFERENCES "T_大分類"("id") ON DELETE CASCADE,
    CONSTRAINT "uq_subcategory_code" UNIQUE ("category_id", "code")
);

-- 板面（表示面）の中分類を挿入
INSERT INTO "T_中分類" ("category_id", "code", "name", "description", "display_order") VALUES
((SELECT "id" FROM "T_大分類" WHERE "code" = 'panel'), 'aluminum_composite', 'アルミ複合板', 'アルミ複合板を使用した表示面', 1),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'panel'), 'acrylic', 'アクリル板', 'アクリル板を使用した表示面', 2),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'panel'), 'stainless', 'ステンレス板', 'ステンレス板を使用した表示面', 3),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'panel'), 'sheet_print', 'シート・印刷', 'インクジェット出力、カッティングシート等', 4),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'panel'), 'illuminated', '電飾・内照式', '内照式の表示面', 5)
ON CONFLICT ("category_id", "code") DO NOTHING;

-- 看板本体（表示体）の中分類を挿入
INSERT INTO "T_中分類" ("category_id", "code", "name", "description", "display_order") VALUES
((SELECT "id" FROM "T_大分類" WHERE "code" = 'body'), 'box_letter', '箱文字', '立体的な箱文字看板', 1),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'body'), 'channel_letter', 'チャンネル文字', 'チャンネル文字看板', 2),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'body'), 'side_sign', '袖看板', '壁面から突き出た袖看板', 3),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'body'), 'pole_sign', '野立て看板', '独立した野立て看板', 4),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'body'), 'panel_sign', 'パネル看板', '平面パネル看板', 5)
ON CONFLICT ("category_id", "code") DO NOTHING;

-- 支柱・構造部材の中分類を挿入
INSERT INTO "T_中分類" ("category_id", "code", "name", "description", "display_order") VALUES
((SELECT "id" FROM "T_大分類" WHERE "code" = 'structure'), 'square_pipe', '角パイプ', '角形鋼管', 1),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'structure'), 'round_pipe', '丸パイプ', '丸形鋼管', 2),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'structure'), 'h_steel', 'H鋼', 'H形鋼', 3),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'structure'), 'angle', 'アングル', '山形鋼（アングル）', 4)
ON CONFLICT ("category_id", "code") DO NOTHING;

-- 基礎・施工の中分類を挿入
INSERT INTO "T_中分類" ("category_id", "code", "name", "description", "display_order") VALUES
((SELECT "id" FROM "T_大分類" WHERE "code" = 'foundation'), 'independent', '独立基礎', '独立基礎工事', 1),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'foundation'), 'continuous', '布基礎', '布基礎工事', 2),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'foundation'), 'anchor', 'アンカー固定', 'アンカーボルトによる固定', 3),
((SELECT "id" FROM "T_大分類" WHERE "code" = 'foundation'), 'construction', '施工費', '一般施工費', 4)
ON CONFLICT ("category_id", "code") DO NOTHING;

-- 材質マスタに中分類IDカラムを追加
ALTER TABLE "T_材質" ADD COLUMN IF NOT EXISTS "subcategory_id" INTEGER;

-- 外部キー制約を追加（既存の場合はスキップ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_material_subcategory'
    ) THEN
        ALTER TABLE "T_材質" ADD CONSTRAINT "fk_material_subcategory" 
            FOREIGN KEY ("subcategory_id") REFERENCES "T_中分類"("id") ON DELETE SET NULL;
    END IF;
END $$;

-- 見積もり明細に中分類IDカラムを追加
ALTER TABLE "T_看板見積もり明細" ADD COLUMN IF NOT EXISTS "subcategory_id" INTEGER;

-- 外部キー制約を追加（既存の場合はスキップ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_item_subcategory'
    ) THEN
        ALTER TABLE "T_看板見積もり明細" ADD CONSTRAINT "fk_item_subcategory" 
            FOREIGN KEY ("subcategory_id") REFERENCES "T_中分類"("id") ON DELETE SET NULL;
    END IF;
END $$;

-- インデックスを作成
CREATE INDEX IF NOT EXISTS "idx_subcategory_category_id" ON "T_中分類"("category_id");
CREATE INDEX IF NOT EXISTS "idx_material_subcategory_id" ON "T_材質"("subcategory_id");
CREATE INDEX IF NOT EXISTS "idx_estimate_item_subcategory_id" ON "T_看板見積もり明細"("subcategory_id");

-- コメント
COMMENT ON TABLE "T_中分類" IS '見積もり明細の中分類マスタ';
COMMENT ON COLUMN "T_中分類"."category_id" IS '大分類ID';
COMMENT ON COLUMN "T_中分類"."code" IS '中分類コード';
COMMENT ON COLUMN "T_中分類"."name" IS '中分類名';
COMMENT ON COLUMN "T_中分類"."description" IS '中分類の説明';
COMMENT ON COLUMN "T_中分類"."display_order" IS '表示順序';
COMMENT ON COLUMN "T_材質"."subcategory_id" IS '中分類ID';
COMMENT ON COLUMN "T_看板見積もり明細"."subcategory_id" IS '中分類ID';
