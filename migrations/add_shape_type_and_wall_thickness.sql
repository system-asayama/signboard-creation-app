-- 材質テーブルに形状タイプと肉厚カラムを追加
ALTER TABLE "T_材質" ADD COLUMN IF NOT EXISTS "shape_type" VARCHAR(20) DEFAULT 'square' COMMENT '形状タイプ（square:角形, round_solid:丸形中実, round_pipe:丸形パイプ）';
ALTER TABLE "T_材質" ADD COLUMN IF NOT EXISTS "wall_thickness" NUMERIC(10, 2) COMMENT '肉厚（mm）※丸形パイプの場合のみ';

-- 看板見積もり明細テーブルに形状タイプと肉厚カラムを追加
ALTER TABLE "T_看板見積もり明細" ADD COLUMN IF NOT EXISTS "shape_type" VARCHAR(20) DEFAULT 'square' COMMENT '形状タイプ（square:角形, round_solid:丸形中実, round_pipe:丸形パイプ）';
ALTER TABLE "T_看板見積もり明細" ADD COLUMN IF NOT EXISTS "wall_thickness" NUMERIC(10, 2) COMMENT '肉厚（mm）※丸形パイプの場合のみ';
ALTER TABLE "T_看板見積もり明細" ADD COLUMN IF NOT EXISTS "depth" NUMERIC(10, 2) COMMENT '奥行き（mm）※角形の場合';
ALTER TABLE "T_看板見積もり明細" ADD COLUMN IF NOT EXISTS "diameter" NUMERIC(10, 2) COMMENT '直径（mm）※丸形の場合';
