# book_manager ドキュメントガイド

## 1. 目的

本ドキュメントは、`book_manager`プロジェクトで管理している設計書、レビュー記録、ADR、開発方針およびロードマップの構成と役割を整理するためのガイドである。

`docs`ディレクトリ内の文書は補助資料ではなく、ソースコードと同様に管理する正式な成果物として扱う。

機能追加や仕様変更を行う場合は、必要に応じて関連文書を更新し、設計書と実装の整合性を維持する。

---

## 2. ルートREADMEとの役割分担

プロジェクトルートの、

```text
README.md
```

は、`book_manager`そのものの概要、利用方法、主要機能、セットアップ、テスト、プロジェクト構成などを説明する。

本ファイル、

```text
docs/documentation_guide.md
```

は、`docs`ディレクトリ内の開発ドキュメントについて、その構成、役割、閲覧方法および運用方針を説明する。

両者の役割を明確に分離し、取り違えを防ぐ。

---

## 3. 現在のドキュメント構成

現在の`docs`ディレクトリは次の構成となっている。

```text
docs/
├── backup_settings_design.md
├── backup_restore_design.md
├── csv_import_design.md
├── data_path_migration_design.md
├── documentation_guide.md
├── book_manager_roadmap.md
├── development_guidelines.md
├── external_book_metadata_design.md
├── favorite_design.md
├── rating_design.md
├── reading_history_design.md
├── reading_statistics_design.md
├── reading_status_design.md
├── reading_information_sort_design.md
├── search_filter_design.md
├── settings_and_window_layout_design.md
├── tag_category_design.md
├── windows_distribution_design.md
├── windows_installer_design.md
├── window_state_design.md
│
├── adr/
│   └── ADR-0001-sqlite-selection.md
│
├── architecture/
│   ├── project_structure.md
│   └── project_structure_review.md
│
├── database/
│   ├── database_design.md
│   ├── database_design_review.md
│   └── er_diagram.md
│
├── gui/
│   ├── gui_design.md
│   ├── gui_design_review.md
│   ├── treeview_header_sort_design.md
│   ├── multi_condition_search_design.md
│   ├── thumbnail_list_design.md
│   └── auto_clear_after_save_design.md
│
├── models/
│   ├── book_item_design.md
│   └── book_item_design_review.md
│
├── repositories/
│   ├── book_repository_design.md
│   └── book_repository_design_review.md
│
├── services/
│   ├── book_service_design.md
│   ├── book_service_design_review.md
│   ├── book_service_implementation_review.md
│   ├── backup_service_design.md
│   └── csv_export_service_design.md
│
└── validators/
    ├── validator_design.md
    └── validator_design_review.md
```

将来、新しい機能や設計領域が必要になった場合は、必要性を確認したうえで文書またはディレクトリを追加する。

将来必要になる可能性だけを理由として、未使用の文書やディレクトリを先に作成しない。

---

## 4. プロジェクト全体に関する文書

### `book_manager_roadmap.md`

各Versionのテーマ、完成条件、実装済み機能、今後の候補およびリリース記録を管理する。

主な役割は次のとおりである。

- Versionごとの開発テーマを定義する。
- 主要スコープを整理する。
- 実装状況をチェックリストで管理する。
- 将来Versionの候補を記録する。
- 正式リリースの記録を残す。

---

### `development_guidelines.md`

book_manager全体の開発方針および運用ルールを定義する。

主な内容は次のとおりである。

- 開発姿勢
- 設計してから実装する方針
- Design Freeze
- 設計変更手続き
- ADR運用
- Git運用
- コミットメッセージ規則
- 命名規則
- コーディング方針
- レビュー方針
- テスト方針

---

### `external_book_metadata_design.md`

外部書誌情報取得機能の設計を管理する。

主な対象は次のとおりである。

- Google Books API
- openBD
- ISBN変換
- 複数取得元からの情報統合
- 情報欠損時の補完
- Rate Limit
- Not Found
- Raw Data
- 取得元情報
- 外部サービス障害時の処理

### `data_path_migration_design.md`

Version 2.0で実装した利用者データ保存先の一元化と、Version 1.9以前の既存データ移行を定義する。

`ApplicationPaths`、`BOOK_MANAGER_HOME`、SQLite Backup APIによる複製、上書き防止、再実行、バックアップ・表紙画像の移行および起動時通知を管理する。

### `windows_distribution_design.md`

Version 2.0のWindows実行ファイル作成を定義する。

PyInstallerの`onedir`構成、静的資源、専用アイコン、Version情報、ファイルログ、ビルドスクリプト、検証用ZIP、チェックサムおよび実環境確認を管理する。

### `windows_installer_design.md`

Version 2.0のWindowsインストーラーを定義する。

Inno Setup、利用者単位の導入、固定`AppId`、ショートカット、上書き更新、アンインストール後の利用者データ保持、再インストールおよびPython未導入環境での検証を管理する。

---

### `reading_status_design.md`

Version 1.3で追加した読書ステータス管理機能を定義する。

### `reading_history_design.md`

Version 1.8で追加した読書履歴管理機能を定義する。

一つの書籍に対する複数履歴、日付・メモの検証、データベース構造、Repository・Service・GUI連携、既存読書情報からの独立性およびバックアップ・復元方針を管理する。

### `reading_statistics_design.md`

Version 1.9で追加した読書記録の集計・可視化機能を定義する。

全体集計、年別・月別集計、集計結果Model、Repository・Service・GUIの責務、Canvas棒グラフ、空状態およびテスト方針を管理する。

### `reading_information_sort_design.md`

Version 1.6で追加した読書状態・お気に入り・評価による並べ替え機能を定義する。

### `tag_category_design.md`

Version 1.7で追加したタグ・カテゴリ機能を定義する。

一つの書籍への複数タグ設定、タグ名の検証、データベース構造、Repository・Service・GUI・CSV連携、タグ管理および旧形式CSVとの互換性を管理する。

### `favorite_design.md`

Version 1.3で追加したお気に入り機能を定義する。

### `rating_design.md`

Version 1.3で追加した評価機能を定義する。

### `csv_import_design.md`

Version 1.4で追加したCSVインポート機能を定義する。

### `backup_restore_design.md`

Version 1.4で追加したバックアップからの復元機能を定義する。

### `search_filter_design.md`

Version 1.5で追加した読書情報による検索・絞り込み、検索GUIおよび起動時ウィンドウ表示の改善を定義する。

### `settings_and_window_layout_design.md`

Version 2.1で追加したアプリケーション設定画面とサブウィンドウ配置を定義する。

Google Books APIキーの利用者環境への保存、設定状態表示、利用者データ関連パス、Version表示、フォルダーを開く操作、起動中クライアントへの反映および親画面を基準とする中央配置を管理する。

### `backup_settings_design.md`

Version 2.2で追加したバックアップ状態表示、手動作成、間隔・世代数の保存、同時刻の上書き防止および検証後の世代整理を定義する。ソース版の全1267件の自動テスト、Windows配布版のビルドとチェックサム、検証用データでの設定反映・世代整理・復元、2.1.0から2.2.0への上書き更新、アンインストール・再インストール後のDBと設定ファイルの保持を確認した。

### `window_state_design.md`

Version 2.3で追加したメインウィンドウの通常位置・サイズ・最大化状態の保存と復元、複数モニター作業領域、画面内補正、状態ファイルの検証・原子的保存、および設定画面からの初期化を定義する。

全1362件の自動テストとWindowsソース版・配布版で、通常表示・最大化の保存と復元、画面外座標と壊れたJSONからの安全な起動、初期化後の再作成防止と次回起動後の保存再開を確認した。Version 2.2.0からの上書き更新、アンインストールおよび再インストール後も、DB・バックアップ設定・ウィンドウ状態・バックアップの保持を確認した。

---

## 5. ADR

### `adr/ADR-0001-sqlite-selection.md`

SQLiteをbook_managerのローカルデータベースとして採用した設計判断を記録する。

ADRでは、採用した案だけではなく、比較した選択肢、採用理由、利点、欠点および影響を残す。

今後も、プロジェクト全体へ長期的な影響を与える重要な判断が発生した場合にADRを追加する。

軽微なレイアウト変更、誤字修正、単純な不具合修正などでは、原則としてADRを作成しない。

---

## 6. Architecture

`architecture`ディレクトリでは、アプリケーション全体の構造を管理する。

### `project_structure.md`

プロジェクト構成、レイヤー構成、依存方向、ディレクトリ構造および主要モジュールの責務を定義する。

基本的な依存方向は次の考え方を採用する。

```text
GUI
↓
Service
↓
Repository
↓
SQLite
```

必要に応じて、Model、Validator、Metadata、外部サービスなどの責務を分離する。

### `project_structure_review.md`

`project_structure.md`に対する設計レビュー結果を記録する。

---

## 7. Database

`database`ディレクトリでは、SQLiteデータベースの設計を管理する。

### `database_design.md`

主な内容は次のとおりである。

- データベースファイル
- テーブル構成
- カラム定義
- データ型
- NULLの扱い
- 制約
- インデックス
- 日付・日時保存方針
- スキーマVersion
- マイグレーション
- CRUD方針

### `database_design_review.md`

データベース設計のレビュー結果を記録する。

### `er_diagram.md`

テーブル、カラム、主キー、インデックスおよびリレーションを図または構造として整理する。

---

## 8. GUI

`gui`ディレクトリでは、画面構成、GUI操作およびVersionごとのGUI改善機能を管理する。

### `gui_design.md`

book_manager GUI全体の基本設計を定義する。

### `gui_design_review.md`

GUI基本設計のレビュー結果を記録する。

### `treeview_header_sort_design.md`

Version 1.1で追加した、書籍一覧ヘッダークリックによるソート機能を定義する。

### `multi_condition_search_design.md`

Version 1.2で追加した複合条件検索を定義する。

### `thumbnail_list_design.md`

Version 1.2で追加した表紙サムネイル付き一覧を定義する。

### `auto_clear_after_save_design.md`

Version 1.2で追加した登録・更新成功後の入力フォーム自動クリアを定義する。

---

## 9. Models

`models`ディレクトリでは、ドメインモデルの設計を管理する。

### `book_item_design.md`

`BookItem`モデルの項目、責務およびデータ保持方針を定義する。

### `book_item_design_review.md`

`BookItem`設計のレビュー結果を記録する。

---

## 10. Repositories

`repositories`ディレクトリでは、データアクセス層の設計を管理する。

### `book_repository_design.md`

`BookRepository`のCRUD、検索、ソートおよびSQLiteアクセス方針を定義する。

### `book_repository_design_review.md`

Repository設計のレビュー結果を記録する。

---

## 11. Services

`services`ディレクトリでは、業務処理およびアプリケーションサービスの設計を管理する。

### `book_service_design.md`

`BookService`の責務、入力値正規化、Validatorとの連携、Repositoryとの境界などを定義する。

### `book_service_design_review.md`

BookService設計のレビュー結果を記録する。

### `book_service_implementation_review.md`

BookService実装後のレビュー結果を記録する。

### `backup_service_design.md`

Version 1.1で追加したSQLiteデータベース自動バックアップ機能を定義する。

### `csv_export_service_design.md`

Version 1.1で追加したCSVエクスポート機能を定義する。

---

## 12. Validators

`validators`ディレクトリでは、入力値検証の設計を管理する。

### `validator_design.md`

ISBN、雑誌コード、読了年月などの入力値検証方針を定義する。

### `validator_design_review.md`

Validator設計のレビュー結果を記録する。

---

## 13. 推奨する閲覧順序

プロジェクト全体を初めて確認する場合は、次の順番を推奨する。

1. ルートの`README.md`
2. `docs/documentation_guide.md`
3. `docs/book_manager_roadmap.md`
4. `docs/development_guidelines.md`
5. `docs/architecture/project_structure.md`
6. `docs/database/database_design.md`
7. `docs/database/er_diagram.md`
8. `docs/models/book_item_design.md`
9. `docs/repositories/book_repository_design.md`
10. `docs/services/book_service_design.md`
11. `docs/gui/gui_design.md`
12. 必要な機能別設計書
13. 関連するADR
14. 必要に応じて各レビュー文書

特定機能だけを確認する場合は、その機能の設計書と関連するService、Repository、GUI設計を併せて確認する。

---

## 14. ドキュメント作成の基本手順

新しい機能または設計変更を行う場合は、原則として次の順番で進める。

```text
要件整理
↓
設計
↓
設計レビュー
↓
実装
↓
自動テスト
↓
GUI・実機確認
↓
ドキュメント更新
↓
リリースレビュー
```

大きな機能については、一つの機能を完成させてから次の機能へ進む。

複数の大きな変更を同時に進行させない。

---

## 15. ドキュメント更新ルール

### 15.1 実装との整合性

設計書と実装は可能な限り一致させる。

実装中に設計変更が必要になった場合は、必要に応じて設計書も更新する。

機能完成時には、設計書の完成条件と実装結果を照合する。

---

### 15.2 Version

主要な設計文書では、必要に応じて文書Versionや対象アプリケーションVersionを明示する。

アプリケーションVersionと文書Versionは異なる概念として扱う。

SQLiteのスキーマVersionも、アプリケーションVersionとは別に管理する。

---

### 15.3 変更理由

仕様または設計を変更する場合は、可能な限り変更内容だけでなく変更理由も確認できるようにする。

長期的な影響を持つ重要な判断はADRへの記録を検討する。

---

### 15.4 関連文書

一つの設計書を変更した場合は、必要に応じて関連文書への影響を確認する。

例：

```text
GUI設計変更
↓
関連Serviceを確認
↓
関連Repositoryを確認
↓
テストを確認
↓
ロードマップを確認
```

---

## 16. Design Freeze

設計レビューを完了した文書は、実装基準としてDesign Freezeする。

Design Freezeは、設計を永久に変更できないことを意味しない。

変更が必要になった場合は、原則として次の流れで扱う。

```text
変更理由を確認
↓
影響範囲を確認
↓
設計書を更新
↓
必要に応じてADRを追加
↓
レビュー
↓
実装
↓
テスト
↓
設計書と実装を再確認
```

---

## 17. Git運用

ドキュメントもソースコードと同様にGitで管理する。

コミットは原則として一つの目的ごとに分ける。

コミットメッセージは次の形式を使用する。

```text
<英語のプレフィックス>: <日本語の説明>
```

例：

```text
docs: Version 1.2のロードマップを更新
docs: 複合条件検索の設計を追加
feat: 表紙サムネイル付き一覧を追加
fix: 検索条件クリア時の不具合を修正
```

詳細なGit運用およびコミットメッセージ規則は、

```text
docs/development_guidelines.md
```

を参照する。

---

## 18. 現在の状態

book_managerはVersion 2.2.0まで正式リリース済みである。

Version 1.7.0は、タグ・カテゴリ機能の実装、812件の自動テスト全件成功およびWindows実環境での主要操作確認を経て、2026-09-04に正式リリースした。

Version 1.0では基本的な書籍管理機能を完成させた。

Version 1.1では、データ保護と日常利用の改善として次の機能を追加した。

- 自動バックアップ
- CSVエクスポート
- 一覧ヘッダークリックによるソート

Version 1.2では、検索と一覧操作の改善として次の機能を追加した。

- 複合条件検索
- 表紙サムネイル付き一覧
- 登録・更新成功後の入力フォーム自動クリア

Version 1.3では、蔵書の状態管理と日常利用の改善として次の機能を追加した。

- 読書ステータス管理
- お気に入り機能
- 1〜5段階の評価機能

Version 1.4では、データの移行と復旧機能の強化として次の機能を追加した。

- CSVインポート
- バックアップからの復元

Version 1.5では、蔵書の絞り込みと検索機能の強化として次の機能を追加した。

- 読書状態による絞り込み
- お気に入り状態による絞り込み
- 未評価および指定評価以上による絞り込み
- 既存の書籍情報と読書情報を組み合わせたAND検索
- 検索GUIの改善
- 起動時ウィンドウ表示の改善

Version 1.6では、読書情報の並べ替え機能の強化として次の機能を追加した。

- 読書状態による並べ替え
- お気に入り状態による並べ替え
- 未評価を含む評価による並べ替え
- 読書情報3項目の一覧ヘッダークリックソート
- 検索・絞り込み条件を維持した並べ替え

Version 1.7では、蔵書の分類と整理機能の強化として次の機能を実装した。

- 一つの書籍への複数タグ設定
- 登録済みタグの再利用、名称変更、削除
- 書籍一覧へのタグ表示
- タグおよびタグ未設定による絞り込み
- 既存検索条件とタグ条件を組み合わせたAND検索
- CSVエクスポート・インポートへのタグ対応
- タグ列を持たない旧形式CSVとの互換性
- 既存データを維持したスキーマVersion 6への移行
- 812件の自動テスト全件成功
- Windows実環境での主要操作確認

Version 1.8では、読書記録と再読履歴の管理として次の機能を実装した。

- 一つの書籍への複数読書履歴の登録
- 読書開始日・読了日・読書メモの記録
- 読書履歴の一覧表示・変更・削除
- 現在の読書状態・読了年月から独立した履歴管理
- 書籍削除時の関連履歴の自動削除
- 既存データを維持したスキーマVersion 7への移行
- バックアップ・復元での読書履歴保持
- 911件の自動テスト全件成功
- Windows実環境での主要操作確認

Version 1.8.0は、読書履歴管理機能の実装、911件の自動テスト全件成功およびWindows実環境での主要操作確認を経て、2026-09-07に正式リリースした。

Version 1.9では、読書記録の集計と可視化として次の機能を実装した。

- 読書履歴総数・履歴のある書籍数・読了記録数・再読書籍数の集計
- 読了記録が存在する年の選択
- 1月から12月までの月別読了数表示
- TkinterのCanvasによる月別棒グラフ
- 読了記録がない場合の空状態表示
- スキーマVersion 7と既存CSV形式の維持
- 970件の自動テスト全件成功
- Windows実環境での主要な集計値とグラフ表示確認

Version 1.9.0は、読書記録集計・可視化機能の実装、970件の自動テスト全件成功およびWindows実環境での10項目の主要操作確認を経て、2026-09-08に正式リリースした。

Version 2.0は、Windows向け配布・導入の正式対応として実装と検証を完了した。

利用者データ保存先の`%LOCALAPPDATA%\book_manager`への一元化、Version 1.9以前の既存データ移行、ローテーション付きファイルログ、PyInstallerによる`onedir`ビルド、専用アイコン、Inno SetupによるWindowsインストーラーおよびSHA-256チェックサムの作成を完了した。

全1110件の自動テスト、Version 1.9.0から2.0.0への上書き更新、アンインストール後の利用者データ保持、再インストールおよびPython未導入の別Windows 11 Pro機での確認を経て、Version 2.0.0を2026-09-10に正式リリースした。

Version 2.1は、設定画面とウィンドウ操作性の改善について、ソース版の実装と検証を完了した。

Google Books APIキーの設定状態確認・登録・変更・削除、起動中クライアントへの即時反映、利用者データ関連パスとVersionの表示、フォルダーを開く操作、および設定画面と主要サブウィンドウの親画面中央表示を実装した。

関連するfocused pytestと全1194件の自動テストが成功し、Windowsソース版で設定画面の9項目と既存サブウィンドウ中央表示の6項目を確認した。

Version 2.1.0のWindows実行ファイル、検証用ZIPおよびWindowsインストーラーを作成し、Version 2.0.0からの上書き更新、アンインストール後の利用者データ・APIキー保持、および再インストール後の再利用を確認した。

Version 2.1.0は、設定画面とウィンドウ操作性の改善、全1194件の自動テスト成功、Windowsソース版・配布版での主要操作確認を経て、2026-09-11に正式リリースした。

Version 2.2.0は、バックアップの状態表示・手動作成・間隔と世代数の保存を追加した。全1267件の自動テスト、Windows配布版での設定・世代整理・復元の確認、2.1.0からの上書き更新、およびアンインストール・再インストール後の利用者データと設定の保持を経て、2026-09-14に正式リリースした。

Version 2.3は、メインウィンドウ状態の保存と安全な復元を実装した。全1362件の自動テストが成功し、Windowsソース版と配布版で通常表示・最大化・画面外座標・破損設定・初期化・保存再開を確認した。Windows実行ファイル・ZIP・インストーラーのVersionとSHA-256、Version 2.2.0からの上書き更新、アンインストール・再インストール後の利用者データ保持も確認した。

今後の開発内容は、

```text
docs/book_manager_roadmap.md
```

を基準として検討する。

---

**book_managerの開発ドキュメントは、設計・実装・テストの履歴を残し、将来の保守と機能追加を安全に進めるための正式な成果物として管理する。**
