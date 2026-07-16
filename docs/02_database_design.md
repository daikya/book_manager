# 02 データベース設計

## 設計方針
- SQLite
- 外部キー有効化
- WALモード
- Raw JSONは内容変更時のみ追加保存
- 変更履歴は項目単位
- 表紙画像本体は外部保存
- マイグレーション履歴を保持

## 主要テーブル
| テーブル | 役割 |
|---|---|
| books | 書誌情報 |
| book_copies | 所有情報 |
| authors | 著者マスタ |
| author_aliases | 著者の別名 |
| book_authors | 書籍・著者・役割 |
| publishers | 出版社 |
| series | シリーズ・レーベル |
| categories | 分類 |
| book_categories | 書籍と分類 |
| tags | タグ |
| book_tags | 書籍とタグ |
| data_sources | 取得元 |
| field_sources | 項目ごとの採用元 |
| raw_api_responses | Rawデータ |
| change_history | 変更履歴 |
| schema_migrations | DBバージョン |

## 著者名の正規化
例:
- 取得値: `松本,清張,1909-1992`
- 表示名: `松本 清張`
- 正規化名: `松本清張`

名前だけ一致した場合は自動統合せず、候補として確認する。

## 次の作業
各テーブルのカラム、制約、外部キー、インデックスを確定する。
