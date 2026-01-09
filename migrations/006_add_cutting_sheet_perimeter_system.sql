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
INSERT INTO "T_文字周長係数" ("文字種類", "係数", "説明", "テナントID") VALUES
('ひらがな', 6.0, '丸みが多い文字（例：あいうえお）', NULL),
('カタカナ', 5.5, '直線が多い文字（例：アイウエオ）', NULL),
('漢字（簡単）', 7.0, '画数が少ない漢字（例：口、日、中、上、下）', NULL),
('漢字（普通）', 8.5, '一般的な漢字（例：営、業、店、時、間）', NULL),
('漢字（複雑）', 10.0, '画数が多い漢字（例：薔、鬱、麗、響、議）', NULL),
('英数字（大文字）', 5.0, 'A-Z, 0-9', NULL),
('英数字（小文字）', 4.5, 'a-z', NULL),
('記号', 4.0, '記号・特殊文字', NULL);

-- 2. 見積もり明細テーブルに文字周長関連フィールドを追加
ALTER TABLE "T_看板見積もり明細"
ADD COLUMN IF NOT EXISTS "文字加工モード" VARCHAR(20),  -- 'overall'（全体サイズ）または 'individual'（1文字ずつ）
ADD COLUMN IF NOT EXISTS "文字内容" TEXT,  -- 「営業中」など
ADD COLUMN IF NOT EXISTS "文字数" INTEGER,  -- 3
ADD COLUMN IF NOT EXISTS "全体縦サイズ" DECIMAL(10,2),  -- 100.00 (mm)
ADD COLUMN IF NOT EXISTS "全体横サイズ" DECIMAL(10,2),  -- 300.00 (mm)
ADD COLUMN IF NOT EXISTS "文字種類" VARCHAR(50),  -- 漢字（普通）
ADD COLUMN IF NOT EXISTS "推定周長" DECIMAL(10,2),  -- 2550.00 (mm)
ADD COLUMN IF NOT EXISTS "実測周長" DECIMAL(10,2),  -- ユーザーが入力した実測値（オプション）
ADD COLUMN IF NOT EXISTS "周長単価" DECIMAL(10,2),  -- 5.00 (円/mm)
ADD COLUMN IF NOT EXISTS "加工賃" DECIMAL(10,2);  -- 12750.00 (円)

-- 3. 文字明細テーブル（1文字ずつモード用）
CREATE TABLE IF NOT EXISTS "T_文字明細" (
    "ID" SERIAL PRIMARY KEY,
    "見積もり明細ID" INTEGER NOT NULL REFERENCES "T_看板見積もり明細"("ID") ON DELETE CASCADE,
    "文字" VARCHAR(10) NOT NULL,  -- 「営」
    "縦サイズ" DECIMAL(10,2) NOT NULL,  -- 100.00 (mm)
    "横サイズ" DECIMAL(10,2) NOT NULL,  -- 100.00 (mm)
    "文字種類" VARCHAR(50) NOT NULL,  -- 漢字（普通）
    "係数" DECIMAL(5,2) NOT NULL,  -- 8.5
    "推定周長" DECIMAL(10,2) NOT NULL,  -- 850.00 (mm)
    "並び順" INTEGER DEFAULT 0,
    "作成日時" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文字明細にインデックスを追加
CREATE INDEX IF NOT EXISTS "idx_文字明細_見積もり明細ID" ON "T_文字明細"("見積もり明細ID");

-- 4. 材質マスタに文字加工対応フラグを追加
ALTER TABLE "T_材質"
ADD COLUMN IF NOT EXISTS "文字加工対応" BOOLEAN DEFAULT FALSE;

-- カッティングシート材質を文字加工対応に設定（既存データがあれば）
UPDATE "T_材質"
SET "文字加工対応" = TRUE
WHERE "材質名" LIKE '%カッティング%' OR "材質名" LIKE '%シート%';

-- コメント追加
COMMENT ON TABLE "T_文字周長係数" IS 'カッティングシート文字周長計算用の係数マスタ';
COMMENT ON TABLE "T_文字明細" IS 'カッティングシート文字の1文字ずつの明細（individualモード用）';
COMMENT ON COLUMN "T_看板見積もり明細"."文字加工モード" IS 'overall: 全体サイズで計算, individual: 1文字ずつ計算';
COMMENT ON COLUMN "T_看板見積もり明細"."推定周長" IS '係数テーブルから計算された推定周長（mm）';
COMMENT ON COLUMN "T_看板見積もり明細"."実測周長" IS 'ユーザーが入力した実測周長（mm）。入力があれば推定周長より優先';
COMMENT ON COLUMN "T_材質"."文字加工対応" IS 'カッティングシート等、文字周長計算が必要な材質かどうか';
