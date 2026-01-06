-- T_テナントアプリ設定テーブルにopenai_api_keyカラムを追加
ALTER TABLE "T_テナントアプリ設定"
ADD COLUMN IF NOT EXISTS "openai_api_key" VARCHAR(255);

-- T_店舗アプリ設定テーブルにopenai_api_keyカラムを追加
ALTER TABLE "T_店舗アプリ設定"
ADD COLUMN IF NOT EXISTS "openai_api_key" VARCHAR(255);

-- app_idをapp_nameに変更（既存データがある場合は注意）
ALTER TABLE "T_テナントアプリ設定"
RENAME COLUMN "app_id" TO "app_name";

ALTER TABLE "T_店舗アプリ設定"
RENAME COLUMN "app_id" TO "app_name";
