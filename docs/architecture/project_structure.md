# プロジェクト構成設計書

Version : 0.1
Last Updated : 2026-07-21
Status : Draft

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおけるディレクトリ構成、Pythonモジュール構成、各ファイルの責務および依存関係の基本方針を定義するものです。

この設計書は、SQLite初期化処理、Repository、Service、GUIおよびテストの実装開始前に、プロジェクト構成を統一するために使用します。

実装ファイルを追加する場合は、本書で定義した責務と配置方針に従います。

---

## 2. 基本方針

プロジェクト構成では、次の方針を採用します。

* `src` レイアウトを使用する。
* アプリケーションコードは `src/book_manager` 配下へ配置する。
* GUI、Service、Repository、データベース処理を分離する。
* GUIへSQLを記述しない。
* ServiceへSQLite接続処理を記述しない。
* Repositoryへ画面表示処理を記述しない。
* ファイルごとの責務を小さく保つ。
* 循環参照を避ける。
* テストコードは `tests` 配下へ配置する。
* 実データとソースコードを分離する。
* 初期段階から過剰に細分化しない。
* 将来の変更に対応できる最低限の分離を行う。

---

## 3. プロジェクト全体構成

初期実装時の構成は、次のとおりとします。

```text
book_manager/
├── backups/
│   └── .gitkeep
├── cache/
│   └── .gitkeep
├── data/
│   └── .gitkeep
├── docs/
│   ├── adr/
│   │   └── ADR-0001-sqlite-selection.md
│   ├── architecture/
│   │   └── project_structure.md
│   ├── database/
│   │   ├── database_design.md
│   │   ├── database_design_review.md
│   │   └── er_diagram.md
│   ├── development_guidelines.md
│   └── README.md
├── src/
│   └── book_manager/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── paths.py
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py
│       │   ├── initializer.py
│       │   └── schema.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── book_item.py
│       ├── repositories/
│       │   ├── __init__.py
│       │   └── book_repository.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── book_service.py
│       │   └── validators.py
│       └── ui/
│           ├── __init__.py
│           ├── main_window.py
│           └── dialogs.py
├── tests/
│   ├── conftest.py
│   ├── database/
│   │   ├── test_connection.py
│   │   └── test_initializer.py
│   ├── repositories/
│   │   └── test_book_repository.py
│   └── services/
│       ├── test_book_service.py
│       └── test_validators.py
├── .gitignore
├── pyproject.toml
└── README.md
```

この構成は初期案です。

実装の必要性が確認されるまで、すべてのファイルを一度に作成する必要はありません。

---

## 4. `src` レイアウト

Pythonのアプリケーションコードは、次の場所へ配置します。

```text
src/book_manager/
```

プロジェクト直下へ、アプリケーション用のPythonファイルを直接配置しません。

`src` レイアウトを使用する理由は、次のとおりです。

* ソースコードと設定ファイルを分離できる。
* 開発中の意図しないインポートを防ぎやすい。
* テスト時にインストールされたパッケージを確認しやすい。
* 将来パッケージ化しやすい。
* プロジェクト構造が明確になる。

---

## 5. パッケージ構成

`book_manager` パッケージは、次の層に分けます。

```text
book_manager
├── config
├── database
├── models
├── repositories
├── services
└── ui
```

各層の主な役割は、次のとおりです。

| パッケージ          | 役割                          |
| -------------- | --------------------------- |
| `config`       | パスやアプリケーション設定を管理する。         |
| `database`     | SQLite接続、初期化、スキーマ定義を管理する。   |
| `models`       | アプリケーション内で扱うデータ構造を定義する。     |
| `repositories` | SQLiteへのCRUDと検索を担当する。       |
| `services`     | 入力検証、正規化、業務処理を担当する。         |
| `ui`           | Tkinter画面、ダイアログ、利用者操作を担当する。 |

---

## 6. 依存関係

基本的な依存方向は、次のとおりです。

```text
ui
↓
services
↓
repositories
↓
database
```

モデルは、各層から参照できます。

```text
config
models
↑
各層から参照可能
```

次の依存は禁止します。

* `database` から `repositories` を参照する。
* `repositories` から `services` を参照する。
* `services` から `ui` を参照する。
* `models` から `ui` を参照する。
* RepositoryからTkinterを参照する。
* GUIからSQLを直接実行する。

---

## 7. エントリーポイント

### 7.1 `__main__.py`

`python -m book_manager` で起動するためのエントリーポイントです。

主な責務は、次のとおりです。

* `app.main()` を呼び出す。
* 起動処理をほかのモジュールへ委譲する。

`__main__.py` へ、GUI構築やデータベース処理を直接記述しません。

想定コードは、次のような最小構成です。

```python
from book_manager.app import main

if __name__ == "__main__":
    main()
```

---

### 7.2 `app.py`

アプリケーション全体の起動を管理します。

主な責務は、次のとおりです。

* データベース初期化を実行する。
* 必要なRepositoryとServiceを生成する。
* メインウィンドウを生成する。
* Tkinterのメインループを開始する。
* 起動失敗時の最上位エラー処理を行う。

`app.py` は、各層を組み立てる場所として使用します。

この役割をComposition Rootとします。

---

## 8. `config` パッケージ

### 8.1 目的

`config` パッケージは、アプリケーション全体で使用するパスや設定値を管理します。

初期実装では、主にパス管理を担当します。

---

### 8.2 `config/paths.py`

次のパスを一元管理します。

* プロジェクト基準ディレクトリ。
* `data` ディレクトリ。
* SQLiteデータベースファイル。
* `backups` ディレクトリ。
* `cache` ディレクトリ。
* 将来の書影キャッシュディレクトリ。

想定する定数は、次のとおりです。

```text
PROJECT_ROOT
DATA_DIR
DATABASE_PATH
BACKUP_DIR
CACHE_DIR
```

開発中のデータベースパスは、次の場所を指します。

```text
data/book_manager.db
```

現在の作業ディレクトリに依存するパス生成は行いません。

`Path.cwd()` をデータベースパスの基準として使用しません。

---

## 9. `database` パッケージ

### 9.1 目的

`database` パッケージは、SQLite固有の接続、スキーマおよび初期化処理を管理します。

---

### 9.2 `database/schema.py`

正式なSQL定義とスキーマVersionを管理します。

主な定義は、次のとおりです。

```text
SCHEMA_VERSION
CREATE_BOOK_ITEMS_TABLE
CREATE_BOOK_ITEMS_TITLE_INDEX
CREATE_BOOK_ITEMS_ISBN_INDEX
CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX
```

初期スキーマVersionは、次の値です。

```text
1
```

CREATE TABLE文やCREATE INDEX文を、複数のモジュールへ重複して記述しません。

---

### 9.3 `database/connection.py`

SQLite接続を生成します。

主な責務は、次のとおりです。

* データベースパスを受け取る。
* `sqlite3.connect()` を実行する。
* `sqlite3.Row` を設定する。
* 必要に応じて接続オプションを設定する。
* 接続オブジェクトを呼び出し元へ返す。

Version 0.1では外部キーを使用しません。

将来外部キーを使用する場合は、このモジュールで次を有効化します。

```sql
PRAGMA foreign_keys = ON;
```

接続生成関数の候補名は、次のとおりです。

```python
create_connection()
```

または

```python
get_connection()
```

命名は実装開始時に統一します。

---

### 9.4 `database/initializer.py`

データベース初期化を担当します。

主な責務は、次のとおりです。

* `data` ディレクトリの存在を確認する。
* 存在しない場合は作成する。
* SQLiteへ接続する。
* 現在の `PRAGMA user_version` を確認する。
* `book_items` テーブルを作成する。
* 3つのインデックスを作成する。
* `PRAGMA user_version = 1` を設定する。
* トランザクションを管理する。
* 接続を確実に閉じる。

初期化処理は、複数回実行しても既存データを削除しない構成とします。

関数名は、次を候補とします。

```python
initialize_database()
```

---

## 10. `models` パッケージ

### 10.1 目的

`models` パッケージは、アプリケーション内で受け渡すデータ構造を定義します。

---

### 10.2 `models/book_item.py`

書籍情報を表すモデルを定義します。

初期実装では、Pythonの `dataclass` を使用する方針です。

想定する属性は、次のとおりです。

```text
id
isbn
magazine_code
title
author
publisher
publication_format
description
completion_month
notes
created_at
updated_at
```

新規登録前は、次の属性が未設定になる場合があります。

```text
id
created_at
updated_at
```

モデルは、SQLite接続やTkinterウィジェットを保持しません。

モデルは、データの受け渡しに集中します。

---

## 11. `repositories` パッケージ

### 11.1 目的

Repositoryは、SQLiteへのデータアクセスを担当します。

SQLは、原則としてRepositoryへ集約します。

---

### 11.2 `repositories/book_repository.py`

`book_items` テーブルに対するCRUDと検索を担当します。

想定する主なメソッドは、次のとおりです。

```text
create
find_all
find_by_id
search_by_title
find_by_isbn
find_by_magazine_code
update
delete
```

必要に応じて、重複確認用のメソッドを追加します。

```text
exists_by_isbn
exists_by_magazine_code
find_duplicates_by_isbn
find_duplicates_by_magazine_code
```

更新時に更新対象自身を除外するため、IDを指定できる構成を検討します。

Repositoryの責務は、次のとおりです。

* SQLを実行する。
* プレースホルダーへ値を渡す。
* SQLiteの行をモデルへ変換する。
* 新規登録IDを返す。
* 更新件数を返す。
* 削除件数を返す。
* SQLite例外を上位層へ通知する。

Repositoryでは、次の処理を行いません。

* ISBNの正規化。
* ISBNのチェックデジット検証。
* GUIダイアログの表示。
* エラーメッセージの画面表示。
* Tkinterウィジェットの操作。

---

## 12. `services` パッケージ

### 12.1 目的

Serviceは、入力値の検証、正規化およびアプリケーション上の処理手順を担当します。

GUIとRepositoryの間を調整します。

---

### 12.2 `services/validators.py`

汎用的な検証と正規化を担当します。

想定する関数は、次のとおりです。

```text
normalize_optional_text
normalize_isbn
is_valid_isbn10
is_valid_isbn13
is_valid_isbn
validate_completion_month
validate_title
```

このモジュールでは、SQLiteへ接続しません。

Tkinterダイアログも表示しません。

検証結果は、戻り値または例外として呼び出し元へ返します。

---

### 12.3 `services/book_service.py`

書籍管理に関する処理を担当します。

主な責務は、次のとおりです。

* 登録値を正規化する。
* `title` を検証する。
* ISBNを正規化する。
* ISBNの妥当性を検証する。
* 不正ISBNの警告情報を作成する。
* ISBNと雑誌コードの重複を確認する。
* 読了年月を検証する。
* JST日時を生成する。
* Repositoryへ登録、更新、取得、削除を依頼する。
* Repositoryの結果をGUI向けに整理する。

Serviceは、確認ダイアログを直接表示しません。

不正ISBNや重複を検出した場合は、GUIが判断できる結果を返します。

---

## 13. `ui` パッケージ

### 13.1 目的

`ui` パッケージは、Tkinterを使用した画面表示と利用者操作を担当します。

---

### 13.2 `ui/main_window.py`

メイン画面を定義します。

主な責務は、次のとおりです。

* 書籍一覧を表示する。
* 検索入力を受け付ける。
* 登録画面を開く。
* 編集画面を開く。
* 削除確認を行う。
* Serviceを呼び出す。
* Serviceの結果を画面へ反映する。
* 利用者向けエラーを表示する。

メイン画面からRepositoryを直接呼び出しません。

---

### 13.3 `ui/dialogs.py`

ダイアログ関連処理をまとめます。

想定するダイアログは、次のとおりです。

* 書籍登録ダイアログ。
* 書籍編集ダイアログ。
* 削除確認ダイアログ。
* 不正ISBN警告ダイアログ。
* 重複登録警告ダイアログ。
* エラー表示。
* 情報表示。

初期実装でファイルが大きくなる場合は、後から次のように分割できます。

```text
ui/dialogs/
├── book_dialog.py
├── confirmation_dialog.py
└── error_dialog.py
```

初期段階では、必要になるまで細分化しません。

---

## 14. `tests` ディレクトリ

テストコードは、アプリケーションの構成に対応させます。

```text
tests/
├── database/
├── repositories/
└── services/
```

GUIテストは、初期段階では必須としません。

まず、データベース、Repository、Serviceの自動テストを優先します。

---

## 15. `tests/conftest.py`

pytestで共有するfixtureを定義します。

想定するfixtureは、次のとおりです。

* 一時ディレクトリ。
* テスト用データベースパス。
* 初期化済みSQLiteデータベース。
* テスト用Repository。
* テスト用Service。
* サンプル書籍データ。

本番用の `data/book_manager.db` を、テストで使用してはなりません。

---

## 16. データベーステスト

### 16.1 `test_connection.py`

次の内容を確認します。

* 指定したSQLiteファイルへ接続できる。
* `sqlite3.Row` が設定される。
* 日本語を保存および取得できる。
* 接続できない場合に例外が発生する。

---

### 16.2 `test_initializer.py`

次の内容を確認します。

* `data` ディレクトリ相当の場所を作成できる。
* データベースファイルを作成できる。
* `book_items` テーブルが作成される。
* 3つのインデックスが作成される。
* `PRAGMA user_version` が1になる。
* 複数回初期化してもエラーにならない。
* 既存データが削除されない。

---

## 17. Repositoryテスト

`test_book_repository.py` では、次の内容を確認します。

* 書籍を登録できる。
* 登録IDを取得できる。
* 全件取得できる。
* IDで取得できる。
* 書籍名を部分一致検索できる。
* ISBNで検索できる。
* 雑誌コードで検索できる。
* 書籍を更新できる。
* 書籍を削除できる。
* 存在しないIDの更新を検出できる。
* 存在しないIDの削除を検出できる。
* 同じISBNを複数登録できる。
* 同じ雑誌コードを複数登録できる。
* NULLを保存できる。

---

## 18. Serviceテスト

### 18.1 `test_validators.py`

次の内容を確認します。

* 任意項目の前後空白を除去できる。
* 空文字を `None` へ変換できる。
* ISBNのハイフンを除去できる。
* ISBNの半角空白を除去できる。
* ISBNの全角空白を除去できる。
* ISBN-10末尾の小文字 `x` を大文字 `X` に変換できる。
* 正しいISBN-10を判定できる。
* 不正なISBN-10を判定できる。
* 正しいISBN-13を判定できる。
* 不正なISBN-13を判定できる。
* 正しい読了年月を判定できる。
* 不正な読了年月を判定できる。
* 空の書籍名を拒否できる。

---

### 18.2 `test_book_service.py`

次の内容を確認します。

* 正常な書籍を登録できる。
* 登録前に値が正規化される。
* 不正ISBNを警告結果として返せる。
* 不正ISBNを許可して登録できる。
* ISBN重複を検出できる。
* 雑誌コード重複を検出できる。
* 重複を許可して登録できる。
* 更新時に対象自身を重複判定から除外できる。
* JST日時を生成できる。
* 更新時に `created_at` を維持できる。
* 更新時に `updated_at` を変更できる。

---

## 19. 例外構成

初期実装では、例外クラスを過剰に増やしません。

必要になった段階で、次のような独自例外を検討します。

```text
BookManagerError
DatabaseError
ValidationError
BookNotFoundError
UnsupportedSchemaVersionError
```

例外専用モジュールを作成する場合は、次の場所を候補とします。

```text
src/book_manager/exceptions.py
```

初期段階では、実際に必要になるまで作成しません。

---

## 20. ログ

Version 0.1の初期実装では、複雑なログ設定を必須としません。

ただし、`print()` を多数のモジュールへ分散させることは避けます。

ログが必要になった場合は、Python標準ライブラリの `logging` を使用します。

将来の候補構成は、次のとおりです。

```text
src/book_manager/config/logging_config.py
```

---

## 21. 設定ファイル

Version 0.1の初期実装では、外部設定ファイルを必須としません。

パスや固定値は、Pythonモジュールで管理します。

利用者が変更する設定が増えた場合は、次の形式を検討します。

* JSON。
* TOML。
* SQLite内の設定テーブル。

設定方式は、必要性が発生した段階でADRを作成して決定します。

---

## 22. `pyproject.toml`

Pythonプロジェクトの設定は、`pyproject.toml` へ集約する方針です。

想定する内容は、次のとおりです。

* プロジェクト名。
* Version。
* Pythonの必要Version。
* パッケージ設定。
* pytest設定。
* 将来のコード整形ツール設定。
* 将来の静的解析設定。

初期段階では、必要最小限の内容から開始します。

---

## 23. `.gitignore`

少なくとも、次をGit管理対象から除外します。

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/

data/*.db
data/*.db-shm
data/*.db-wal

backups/*.db
cache/covers/

.vscode/
.DS_Store
```

`.vscode` を共有する必要が生じた場合は、必要な設定だけを個別に管理する方針を検討します。

---

## 24. 初期実装で作成するファイル

最初の実装単位では、次のファイルだけを作成します。

```text
src/book_manager/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── paths.py
└── database/
    ├── __init__.py
    ├── connection.py
    ├── initializer.py
    └── schema.py
```

対応するテストは、次のとおりです。

```text
tests/
├── conftest.py
└── database/
    ├── test_connection.py
    └── test_initializer.py
```

Repository、Service、モデル、GUIは、データベース初期化処理が完成した後に追加します。

---

## 25. 初期実装順序

実装は、次の順番で進めます。

```text
config/paths.py
↓
database/schema.py
↓
database/connection.py
↓
database/initializer.py
↓
tests/conftest.py
↓
tests/database/test_connection.py
↓
tests/database/test_initializer.py
↓
テスト実行
↓
レビュー
↓
コミット
```

---

## 26. コミット単位

初期実装は、次のように分ける方針です。

### パス管理

```text
feat: データベースパス管理を追加
```

### スキーマと接続

```text
feat: SQLite接続とスキーマ定義を追加
```

### 初期化処理

```text
feat: データベース初期化処理を追加
```

### テスト

```text
test: データベース初期化テストを追加
```

実装状況により、スキーマ、接続、初期化を1コミットにまとめる場合でも、1つの目的として説明できる範囲に留めます。

---

## 27. 過剰設計を避ける方針

初期実装では、次の機能を先に作りません。

* 抽象Repositoryクラス。
* Repositoryインターフェース。
* 依存性注入フレームワーク。
* ORM。
* 複雑なマイグレーション基盤。
* プラグイン構成。
* イベントバス。
* 非同期データベース処理。
* 複数データベース対応。
* Web API。
* 高度なログ基盤。
* 設定管理フレームワーク。

実際の要件が発生した場合に追加します。

---

## 28. 将来の変更候補

将来、次の構成を追加する可能性があります。

```text
src/book_manager/
├── api/
├── exceptions.py
├── logging/
├── migrations/
├── importers/
├── exporters/
└── utils/
```

ただし、用途が明確になるまでは追加しません。

汎用処理を安易に `utils` へ集約せず、責務が明確なモジュールへ配置します。

---

## 29. Design Freeze前の確認事項

この構成を確定する前に、次の内容を確認します。

* `src` レイアウトを採用して問題ないか。
* `app.py` と `__main__.py` を分けるか。
* パス管理を `config/paths.py` へ配置してよいか。
* SQL定義を `database/schema.py` へ配置してよいか。
* 接続と初期化を別ファイルに分けてよいか。
* モデルに `dataclass` を使用してよいか。
* Repositoryをクラスとして実装するか。
* Serviceをクラスとして実装するか。
* GUIダイアログの初期分割範囲。
* pytestを使用するか。
* `pyproject.toml` を初期段階で作成するか。
* 独自例外をいつ追加するか。

---

## 30. 現時点の推奨判断

現時点では、次の方針を推奨します。

* `src` レイアウトを採用する。
* `__main__.py` と `app.py` を分ける。
* パス管理を `config/paths.py` へ集約する。
* SQLとスキーマVersionを `database/schema.py` へ集約する。
* SQLite接続と初期化処理を別ファイルに分ける。
* 書籍モデルには `dataclass` を使用する。
* Repositoryはクラスとして実装する。
* Serviceもクラスとして実装する。
* GUIは必要になるまで細分化しない。
* テストにはpytestを使用する。
* `pyproject.toml` を初期実装前に作成する。
* 独自例外は必要になった時点で追加する。
* 最初はデータベース初期化処理とテストだけを実装する。

---

## 31. 次の作業

この構成をレビューし、必要な修正を反映した後にVersion 0.2を作成します。

Version 0.2をDesign Freezeした後、次の順番で実装を開始します。

```text
pyproject.tomlを作成する
↓
config/paths.pyを作成する
↓
database/schema.pyを作成する
↓
database/connection.pyを作成する
↓
database/initializer.pyを作成する
↓
データベース初期化テストを作成する
↓
テストを実行する
↓
実装レビューを行う
