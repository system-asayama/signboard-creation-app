-- 004_add_estimate_type_system.sql
-- 見積タイプとサブタイプのテーブルを作成

-- 見積タイプテーブル（ステップ1: 最初の選択）
CREATE TABLE IF NOT EXISTS "T_見積タイプ" (
    "id" SERIAL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "code" VARCHAR(50) NOT NULL UNIQUE,
    "description" TEXT,
    "display_order" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 見積サブタイプテーブル（ステップ2: 見積タイプ配下の選択）
CREATE TABLE IF NOT EXISTS "T_見積サブタイプ" (
    "id" SERIAL PRIMARY KEY,
    "estimate_type_id" INTEGER NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "code" VARCHAR(50) NOT NULL,
    "description" TEXT,
    "display_order" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("estimate_type_id") REFERENCES "T_見積タイプ"("id") ON DELETE CASCADE,
    UNIQUE ("estimate_type_id", "code")
);

-- 大分類にサブタイプIDを追加
ALTER TABLE "T_大分類" ADD COLUMN IF NOT EXISTS "subtype_id" INTEGER;
ALTER TABLE "T_大分類" ADD CONSTRAINT "fk_category_subtype" 
    FOREIGN KEY ("subtype_id") REFERENCES "T_見積サブタイプ"("id") ON DELETE SET NULL;

-- 見積タイプのデフォルトデータを登録
INSERT INTO "T_見積タイプ" ("name", "code", "description", "display_order") VALUES
('看板・表示設備', 'signage_equipment', 'モノそのもの', 1),
('施工・工事', 'construction', '取り付け・作業', 2),
('電気・配線', 'electrical', '光る・動くための設備', 3),
('デザイン・制作', 'design', '人の作業・知的役務', 4),
('運搬・諸経費', 'transport', '物流・雑費', 5),
('保守・サービス', 'maintenance', '導入後の対応', 6),
('申請・法令対応', 'permit', '行政・法規制', 7)
ON CONFLICT (code) DO NOTHING;

-- 見積サブタイプのデフォルトデータを登録

-- ①看板・表示設備 配下
INSERT INTO "T_見積サブタイプ" ("estimate_type_id", "name", "code", "description", "display_order") VALUES
(1, '固定表示看板', 'fixed_sign', '固定式の看板', 1),
(1, '内照式看板', 'illuminated_sign', '内部照明付き看板', 2),
(1, '電光掲示板', 'led_display', 'LED電光掲示板', 3),
(1, 'デジタルサイネージ', 'digital_signage', 'デジタルディスプレイ看板', 4),
(1, 'スタンド看板', 'stand_sign', '移動可能なスタンド看板', 5),
(1, 'のぼり・横断幕', 'banner_flag', 'のぼり旗・横断幕', 6)
ON CONFLICT (estimate_type_id, code) DO NOTHING;

-- ②施工・工事 配下
INSERT INTO "T_見積サブタイプ" ("estimate_type_id", "name", "code", "description", "display_order") VALUES
(2, '設置工事費', 'installation', '看板設置工事', 1),
(2, '撤去工事費', 'removal', '既存看板撤去工事', 2),
(2, '基礎工事費', 'foundation', '基礎工事', 3),
(2, '高所作業費', 'high_altitude', '高所作業費用', 4),
(2, '夜間作業費', 'night_work', '夜間作業費用', 5)
ON CONFLICT (estimate_type_id, code) DO NOTHING;

-- ③電気・配線 配下
INSERT INTO "T_見積サブタイプ" ("estimate_type_id", "name", "code", "description", "display_order") VALUES
(3, '電源工事', 'power_work', '電源引き込み工事', 1),
(3, '配線工事', 'wiring', '配線工事', 2),
(3, '分電盤工事', 'distribution_board', '分電盤設置工事', 3),
(3, 'タイマー設置', 'timer', 'タイマー設置', 4),
(3, '電源切替工事', 'power_switch', '電源切替工事', 5)
ON CONFLICT (estimate_type_id, code) DO NOTHING;

-- ④デザイン・制作 配下
INSERT INTO "T_見積サブタイプ" ("estimate_type_id", "name", "code", "description", "display_order") VALUES
(4, 'デザイン制作費', 'design_creation', 'デザイン制作', 1),
(4, 'データ作成費', 'data_creation', 'データ作成', 2),
(4, 'レイアウト調整費', 'layout_adjustment', 'レイアウト調整', 3),
(4, '修正対応費', 'revision', '修正対応', 4)
ON CONFLICT (estimate_type_id, code) DO NOTHING;

-- ⑤運搬・諸経費 配下
INSERT INTO "T_見積サブタイプ" ("estimate_type_id", "name", "code", "description", "display_order") VALUES
(5, '運搬費', 'transport_fee', '運搬費用', 1),
(5, '搬入費', 'delivery', '搬入費用', 2),
(5, '駐車場代', 'parking', '駐車場代', 3),
(5, '廃材処分費', 'disposal', '廃材処分費', 4)
ON CONFLICT (estimate_type_id, code) DO NOTHING;

-- ⑥保守・サービス 配下
INSERT INTO "T_見積サブタイプ" ("estimate_type_id", "name", "code", "description", "display_order") VALUES
(6, '点検費', 'inspection', '定期点検費用', 1),
(6, 'LED交換', 'led_replacement', 'LED交換費用', 2),
(6, '清掃', 'cleaning', '清掃費用', 3),
(6, '保守契約（月額）', 'maintenance_contract', '月額保守契約', 4)
ON CONFLICT (estimate_type_id, code) DO NOTHING;

-- ⑦申請・法令対応 配下
INSERT INTO "T_見積サブタイプ" ("estimate_type_id", "name", "code", "description", "display_order") VALUES
(7, '屋外広告物申請費', 'outdoor_ad_permit', '屋外広告物申請費用', 1),
(7, '図面作成費', 'drawing_creation', '図面作成費用', 2),
(7, '行政手数料（実費）', 'admin_fee', '行政手数料（実費）', 3),
(7, '立会い費用', 'attendance_fee', '立会い費用', 4)
ON CONFLICT (estimate_type_id, code) DO NOTHING;

-- 既存の大分類を「固定表示看板」に紐付け
UPDATE "T_大分類" SET "subtype_id" = (SELECT id FROM "T_見積サブタイプ" WHERE code = 'fixed_sign' LIMIT 1)
WHERE "subtype_id" IS NULL;
