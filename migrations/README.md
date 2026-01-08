# データベースマイグレーション手順

## 形状タイプと肉厚フィールドの追加

### 実行コマンド

```bash
heroku pg:psql --app signboard-creation-app-39ccf7162e88 < migrations/add_shape_type_and_wall_thickness.sql
```

### または、Heroku Dashboardから実行

1. https://dashboard.heroku.com/apps/signboard-creation-app-39ccf7162e88/resources
2. Heroku Postgresをクリック
3. Settingsタブ → View Credentials
4. Dataclipsまたはpsqlで接続
5. `migrations/add_shape_type_and_wall_thickness.sql`の内容を実行

### マイグレーション内容

- `T_材質`テーブルに`shape_type`カラムを追加（デフォルト: 'square'）
- `T_材質`テーブルに`wall_thickness`カラムを追加（NULLable）

### 形状タイプの種類

- `square`: 角形
- `round_solid`: 丸形中実
- `round_pipe`: 丸形パイプ
