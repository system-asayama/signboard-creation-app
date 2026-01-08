-- マイグレーション: 形状タイプと肉厚を追加
-- 作成日: 2026-01-08

-- 材質テーブルに形状タイプカラムを追加
ALTER TABLE "T_材質" ADD COLUMN IF NOT EXISTS "shape_type" VARCHAR(20) DEFAULT 'square';

-- 材質テーブルに肉厚カラムを追加
ALTER TABLE "T_材質" ADD COLUMN IF NOT EXISTS "wall_thickness" DECIMAL(10,2) NULL;

-- コメント
COMMENT ON COLUMN "T_材質"."shape_type" IS '形状タイプ (square: 角形, round_solid: 丸形中実, round_pipe: 丸形パイプ)';
COMMENT ON COLUMN "T_材質"."wall_thickness" IS '肉厚（mm）- 丸形パイプの場合のみ使用';
