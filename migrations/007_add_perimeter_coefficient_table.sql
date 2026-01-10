-- 007_add_perimeter_coefficient_table.sql
-- 文字周長係数マスタテーブルを作成

-- 文字周長係数テーブル
CREATE TABLE IF NOT EXISTS "T_文字周長係数" (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE COMMENT '文字種類名（例: ひらがな、カタカナ、漢字（簡単）等）',
  coefficient DECIMAL(4, 2) NOT NULL COMMENT '周長係数（例: 6.0, 8.5等）',
  display_order INT NOT NULL DEFAULT 0 COMMENT '表示順序',
  is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '有効フラグ',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 初期データ投入
INSERT INTO "T_文字周長係数" (name, coefficient, display_order) VALUES
  ('ひらがな', 6.0, 1),
  ('カタカナ', 5.5, 2),
  ('漢字（簡単）', 7.0, 3),
  ('漢字（普通）', 8.5, 4),
  ('漢字（複雑）', 10.0, 5),
  ('英数字（大文字）', 5.0, 6),
  ('英数字（小文字）', 4.5, 7),
  ('記号', 4.0, 8);

-- インデックス作成
CREATE INDEX idx_perimeter_coefficient_display_order ON "T_文字周長係数" (display_order);
CREATE INDEX idx_perimeter_coefficient_is_active ON "T_文字周長係数" (is_active);
