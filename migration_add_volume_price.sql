-- 材質テーブルに体積単価カラムを追加
ALTER TABLE "T_材質" ADD COLUMN IF NOT EXISTS "unit_price_volume" NUMERIC(10, 2) COMMENT '体積単価（円/㎥）';

-- 単価タイプのコメントを更新（情報提供のみ、実際のコメント更新はデータベースによって異なる）
-- price_type: area: 面積単価, weight: 重量単価, volume: 体積単価
