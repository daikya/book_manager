# book_manager

Python・Tkinter・SQLiteで開発する個人向け蔵書管理デスクトップアプリです。

## 方針
- Windows / macOS対応
- SQLiteへ書誌情報・Rawデータ・変更履歴を保存
- 表紙画像は外部キャッシュへ保存
- 複数の書誌情報取得元を統合
- 著者名などの表記揺れを正規化
- 設計書とコードをGitHubで管理

## 現在の段階
Version 1.0に向けた基礎設計中です。試作版DBの移行は行いません。

## 設計書
- [プロジェクト概要](docs/01_project_overview.md)
- [データベース設計](docs/02_database_design.md)
- [API設計](docs/03_api_design.md)
- [GUI設計](docs/04_gui_design.md)
- [アーキテクチャ](docs/05_architecture.md)
- [GitHub運用](docs/06_github_workflow.md)
- [ロードマップ](docs/07_roadmap.md)
