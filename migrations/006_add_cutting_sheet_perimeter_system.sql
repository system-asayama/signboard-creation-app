-- マイグレーション: カッティングシート文字周長計算システム
-- 作成日: 2026-01-09
-- 説明: 文字周長係数マスタ、見積もり明細への文字周長関連フィールド追加

-- 1. 文字周長係数マスタテーブル
CREATE TABLE IF NOT EXISTS "T_文字周長係数" (
    "ID" SERIAL PRIMARY KEY,
    "文字種類" VARCHAR(50) NOT NULL,
    "係数" DECIMAL(5,2) NOT NULL,
    "説明" TEXT,
    "テナントID" INTEGER REFERENCES "M_テナント"("ID") ON DELETE CASCADE,
    "作成日時" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "更新日時" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文字周長係数マスタにインデックスを追加
CREATE INDEX IF NOT EXISTS "idx_文字周長係数_テナントID" ON "T_文字周長係数"("テナントID");

-- 初期データ投入（全テナント共通のデフォルト値）
-- 既存データがある場合はスキップ
INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID")
SELECT 'ひらがな', 6.0, '丸みが多い文字（例：あいうえお）', NULL
WHERE NOT EXISTS (SELECT 1 FROM "T_文字周長係数" WHERE "文字種類" = 'ひらがな' AND "テナントID" IS NULL);

INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID")
SELECT 'カタカナ', 5.5, '直線が多い文字（例：アイウエオ）', NULL
WHERE NOT EXISTS (SELECT 1 FROM "T_文字周長係数" WHERE "文字種類" = 'カタカナ' AND "テナントID" IS NULL);

INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID")
SELECT '漢字（簡単）', 7.0, '画数が少ない漢字（例：口、日、中、上、下）', NULL
WHERE NOT EXISTS (SELECT 1 FROM "T_文字周長係数" WHERE "文字種類" = '漢字（簡単）' AND "テナントID" IS NULL);

INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID")
SELECT '漢字（普通）', 8.5, '一般的な漢字（例：営、業、店、時、間）', NULL
WHERE NOT EXISTS (SELECT 1 FROM "T_文字周長係数" WHERE "文字種類" = '漢字（普通）' AND "テナントID" IS NULL);

INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID")
SELECT '漢字（複雑）', 10.0, '画数が多い漢字（例：薔、鬱、麗、響、議）', NULL
WHERE NOT EXISTS (SELECT 1 FROM "T_文字周長係数" WHERE "文字種類" = '漢字（複雑）' AND "テナントID" IS NULL);

INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID")
SELECT '英数字（大文字）', 5.0, 'A-Z, 0-9', NULL
WHERE NOT EXISTS (SELECT 1 FROM "T_文字周長係数" WHERE "文字種類" = '英数字（大文字）' AND "テナントID" IS NULL);

INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID")
SELECT '英数字（小文字）', 4.5, 'a-z', NULL
WHERE NOT EXISTS (SELECT 1 FROM "T_文字周長係数" WHERE "文字種類" = '英数字（小文字）' AND "テナントID" IS NULL);

INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID")
SELECT '記号', 4.0, '記号・特殊文字', NULL
WHERE NOT EXISTS (SELECT 1 FROM "T_文字周長係数" WHERE "文字種類" = '記号' AND "テナントID" IS NULL);

-- 2. 見積もり明細テーブルに文字周長関連フィールドを追加
DO $$
BEGIN
    -- 文字加工モード
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '文字加工モード') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "文字加工モード" VARCHAR(20);
    END IF;
    
    -- 文字内容
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '文字内容') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "文字内容" TEXT;
    END IF;
    
    -- 文字数
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '文字数') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "文字数" INTEGER;
    END IF;
    
    -- 全体縦サイズ
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '全体縦サイズ') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "全体縦サイズ" DECIMAL(10,2);
    END IF;
    
    -- 全体横サイズ
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '全体横サイズ') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "全体横サイズ" DECIMAL(10,2);
    END IF;
    
    -- 文字種類
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '文字種類') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "文字種類" VARCHAR(50);
    END IF;
    
    -- 推定周長
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '推定周長') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "推定周長" DECIMAL(10,2);
    END IF;
    
    -- 実測周長
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '実測周長') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "実測周長" DECIMAL(10,2);
    END IF;
    
    -- 周長単価
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '周長単価') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "周長単価" DECIMAL(10,2);
    END IF;
    
    -- 加工賃
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_看板見積もり明細' AND column_name = '加工賃') THEN
        ALTER TABLE "T_看板見積もり明細" ADD COLUMN "加工賃" DECIMAL(10,2);
    END IF;
END $$;

-- 3. 文字明細テーブル（1文字ずつモード用）
CREATE TABLE IF NOT EXISTS "T_文字明細" (
    "ID" SERIAL PRIMARY KEY,
    "見積もり明細ID" INTEGER NOT NULL REFERENCES "T_看板見積もり明細"("ID") ON DELETE CASCADE,
    "文字" VARCHAR(10) NOT NULL,
    "縦サイズ" DECIMAL(10,2) NOT NULL,
    "横サイズ" DECIMAL(10,2) NOT NULL,
    "文字種類" VARCHAR(50) NOT NULL,
    "係数" DECIMAL(5,2) NOT NULL,
    "推定周長" DECIMAL(10,2) NOT NULL,
    "並び順" INTEGER DEFAULT 0,
    "作成日時" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文字明細にインデックスを追加
CREATE INDEX IF NOT EXISTS "idx_文字明細_見積もり明細ID" ON "T_文字明細"("見積もり明細ID");

-- 4. 材質マスタに文字加工対応フラグを追加
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'T_材質' AND column_name = '文字加工対応') THEN
        ALTER TABLE "T_材質" ADD COLUMN "文字加工対応" BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- カッティングシート材質を文字加工対応に設定（既存データがあれば）
UPDATE "T_材質"
SET "文字加工対応" = TRUE
WHERE "材質名" LIKE '%カッティング%' OR "材質名" LIKE '%シート%';

-- コメント追加
COMMENT ON TABLE "T_文字周長係数" IS 'カッティングシート文字周長計算用の係数マスタ';
COMMENT ON TABLE "T_文字明細" IS 'カッティングシート文字の1文字ずつの明細（individualモード用）';
