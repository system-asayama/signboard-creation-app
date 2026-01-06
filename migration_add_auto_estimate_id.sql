-- T_看板見積もりテーブルに自動見積もりIDカラムを追加
ALTER TABLE "T_看板見積もり" ADD COLUMN IF NOT EXISTS "自動見積もりID" INTEGER;

-- 外部キー制約を追加（オプション）
-- ALTER TABLE "T_看板見積もり" ADD CONSTRAINT fk_auto_estimate 
-- FOREIGN KEY ("自動見積もりID") REFERENCES "T_自動見積もり"("id");
