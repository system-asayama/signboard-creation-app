-- app_nameをapp_idに戻す
ALTER TABLE "T_テナントアプリ設定"
RENAME COLUMN "app_name" TO "app_id";

ALTER TABLE "T_店舗アプリ設定"
RENAME COLUMN "app_name" TO "app_id";
