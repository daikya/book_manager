# 05 アーキテクチャ

```text
src/book_manager/
├── main.py
├── app.py
├── config.py
├── database/
├── models/
├── services/
├── providers/
├── ui/
└── utils/
```

## 責務
- UI: 表示と入力
- Provider: 外部情報取得
- Service: 統合・正規化・履歴
- Repository: SQLite操作
- Model: データ構造
