# プロジェクト構成設計書

Version : 0.2
Last Updated : 2026-07-21
Status : Design Freeze

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおけるディレクトリ構成、Pythonモジュール構成、各ファイルの責務および依存関係の基本方針を定義するものです。

この設計書は、次の実装における正式な基準として使用します。

* Pythonプロジェクト設定。
* パス管理。
* SQLite接続。
* SQLite初期化。
* Repository。
* Service。
* GUI。
* 自動テスト。

Version 0.2は、プロジェクト構成設計レビューの指摘事項を反映したDesign Freeze版です。

---

## 2. 基本方針

プロジェクト構成では、次の方針を採用します。

* `src` レイアウトを使用する。
* アプリケーションコードは `src/book_manager` 配下へ配置する。
* GUI、Service、Repository、Databaseを分離する。
* GUIへSQLを記述しない。
* ServiceへSQLite接続処理を記述しない。
* Repositoryへ画面表示処理を記述しない。
* データベースパスを引数で注入できる構成にする。
* ファイルごとの責務を小さく保つ。
* 循環参照を避ける。
* テストコードは `tests` 配下へ配置する。
* 実データとソースコードを分離する。
* 初期段階から過剰に細分化しない。
* 必要性が確認される前に空の将来用ファイルを作成しない。
* 将来の変更に対応できる最低限の分離を行う。

---

## 3. 対象環境

初期実装では、次の環境を基準とします。

```text
Python 3.12以上
```

`pyproject.toml` では、次のように指定します。

```toml
requires-python = ">=3.12"
```

Python 3.11以前への互換性対応は、Version 0.1の対象外とします。

---

## 4. Version管理

アプリケーションVersionの初期値は、次のとおりです。

```text
0.1.0
```

SQLiteスキーマVersionは、次のとおりです。

```text
1
```

両者は別に管理します。

```text
アプリケーションVersion : 0.1.0
SQLite user_version      : 1
```

アプリケーションVersionは `pyproject.toml` で管理します。

SQLiteスキーマVersionは、`database/schema.py` で管理し、SQLiteの `PRAGMA user_version` へ設定します。

---

## 5. プロジェクト全体構成

初期実装から将来のGUI実装までを含む全体構成は、次のとおりです。

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
│   │   ├── project_structure.md
│   │   └── project_structure_review.md
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
│           ├── book_dialog.py
│           └── main_window.py
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

この構成は、アプリケーション全体が完成した時点での想定構成です。

すべてのファイルを一度に作成しません。

実装段階ごとに必要なファイルだけを追加します。

---

## 6. 初期実装時の構成

最初の実装では、次のファイルだけを作成します。

```text
book_manager/
├── src/
│   └── book_manager/
│       ├── __init__.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── paths.py
│       └── database/
│           ├── __init__.py
│           ├── connection.py
│           ├── initializer.py
│           └── schema.py
├── tests/
│   └── database/
│       ├── test_connection.py
│       └── test_initializer.py
└── pyproject.toml
```

`tests/conftest.py` は、複数のテストファイルで共有するfixtureが必要になった時点で作成します。

空の `conftest.py` は作成しません。

`app.py` と `__main__.py` は、GUI実装開始時に作成します。

---

## 7. `src` レイアウト

Pythonのアプリケーションコードは、次の場所へ配置します。

```text
src/book_manager/
```

プロジェクト直下へ、アプリケーション用Pythonファイルを直接配置しません。

`src` レイアウトを使用する理由は、次のとおりです。

* ソースコードとプロジェクト設定を分離できる。
* 開発中の意図しないインポートを防ぎやすい。
* テスト時に正しいパッケージを参照しやすい。
* 将来パッケージ化しやすい。
* プロジェクト構造が明確になる。

---

## 8. パッケージ構成

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

各層の役割は、次のとおりです。

| パッケージ          | 役割                        |
| -------------- | ------------------------- |
| `config`       | パスや固定設定を管理する。             |
| `database`     | SQLite接続、初期化、スキーマ定義を管理する。 |
| `models`       | アプリケーション内で扱うデータ構造を定義する。   |
| `repositories` | SQLiteへのCRUDと検索を担当する。     |
| `services`     | 入力検証、正規化、業務処理を担当する。       |
| `ui`           | Tkinter画面と利用者操作を担当する。     |

---

## 9. 依存関係

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

`models` と `config` は、必要な層から参照できます。

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
* GUIからSQLite接続を直接生成する。

---

## 10. `PROJECT_ROOT` の定義

Version 0.1の開発中は、`PROJECT_ROOT` をGitリポジトリのルートディレクトリとして扱います。

想定する構成は、次のとおりです。

```text
book_manager/
├── data/
├── src/
└── pyproject.toml
```

`config/paths.py` から、リポジトリルートを計算します。

概念上は、次のような関係になります。

```python
Path(__file__).resolve().parents[3]
```

ただし、`parents[3]` のようなパス計算を複数のファイルへ記述しません。

パス計算は `config/paths.py` へ集約します。

配布版では、アプリケーション本体の配置場所と利用者データの保存場所を分離する可能性があります。

その場合は、`PROJECT_ROOT` とユーザーデータ基準ディレクトリを別の定数として管理します。

---

## 11. エントリーポイント

### 11.1 `__main__.py`

`python -m book_manager` で起動するためのエントリーポイントです。

主な責務は、次のとおりです。

* `app.main()` を呼び出す。
* Pythonモジュールとしての起動入口を提供する。

`__main__.py` へ、GUI構築やデータベース処理を直接記述しません。

想定コードは、次のとおりです。

```python
from book_manager.app import main

if __name__ == "__main__":
    main()
```

このファイルは、GUI実装開始時に作成します。

---

### 11.2 `app.py`

アプリケーション全体の起動を管理します。

主な責務は、次のとおりです。

* 本番用データベースパスを取得する。
* データベース初期化を実行する。
* Repositoryを生成する。
* Serviceを生成する。
* メインウィンドウを生成する。
* Tkinterのメインループを開始する。
* 起動失敗時の最上位エラー処理を行う。

`app.py` は、各層を組み立てるComposition Rootとして使用します。

このファイルは、GUI実装開始時に作成します。

---

## 12. `config` パッケージ

### 12.1 目的

`config` パッケージは、アプリケーション全体で使用するパスや固定設定を管理します。

初期実装では、パス管理を担当します。

---

### 12.2 `config/paths.py`

次のパスを一元管理します。

```text
PROJECT_ROOT
DATA_DIR
DATABASE_PATH
BACKUP_DIR
CACHE_DIR
```

将来書影機能を実装する場合は、次を追加します。

```text
COVER_CACHE_DIR
```

開発中のデータベースパスは、次の場所を指します。

```text
data/book_manager.db
```

現在の作業ディレクトリに依存するパス生成は行いません。

`Path.cwd()` をデータベースパスの基準として使用しません。

`paths.py` はパスの定義だけを担当します。

ディレクトリの作成は、実際にそのディレクトリを必要とする処理が担当します。

---

## 13. `database` パッケージ

### 13.1 目的

`database` パッケージは、SQLite固有の接続、スキーマおよび初期化処理を管理します。

---

### 13.2 `database/schema.py`

正式なSQL定義とスキーマVersionを管理します。

主な定義は、次のとおりです。

```text
SCHEMA_VERSION
CREATE_BOOK_ITEMS_TABLE
CREATE_BOOK_ITEMS_TITLE_INDEX
CREATE_BOOK_ITEMS_ISBN_INDEX
CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX
SCHEMA_STATEMENTS
```

初期スキーマVersionは、次の値です。

```python
SCHEMA_VERSION = 1
```

想定する構成は、次のとおりです。

```python
SCHEMA_VERSION = 1

CREATE_BOOK_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS book_items (
    id INTEGER PRIMARY KEY,
    isbn TEXT,
    magazine_code TEXT,
    title TEXT NOT NULL,
    author TEXT,
    publisher TEXT,
    publication_format TEXT,
    description TEXT,
    completion_month TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

CREATE_BOOK_ITEMS_TITLE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_book_items_title
ON book_items(title);
"""

CREATE_BOOK_ITEMS_ISBN_INDEX = """
CREATE INDEX IF NOT EXISTS idx_book_items_isbn
ON book_items(isbn);
"""

CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_book_items_magazine_code
ON book_items(magazine_code);
"""

SCHEMA_STATEMENTS = (
    CREATE_BOOK_ITEMS_TABLE,
    CREATE_BOOK_ITEMS_TITLE_INDEX,
    CREATE_BOOK_ITEMS_ISBN_INDEX,
    CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX,
)
```

CREATE TABLE文やCREATE INDEX文を、複数のモジュールへ重複して記述しません。

SQL定義は `schema.py` が保持し、SQLの実行は `initializer.py` が担当します。

---

### 13.3 `database/connection.py`

SQLite接続を生成します。

正式な関数名は、次のとおりです。

```python
create_connection()
```

想定シグネチャは、次のとおりです。

```python
def create_connection(
    database_path: Path | str,
) -> sqlite3.Connection:
    ...
```

主な責務は、次のとおりです。

* データベースパスを受け取る。
* `Path` または文字列をSQLiteへ渡せる形にする。
* `sqlite3.connect()` を実行する。
* `sqlite3.Row` を設定する。
* 接続オブジェクトを呼び出し元へ返す。

`sqlite3.Row` は、`create_connection()` 内で設定します。

```python
connection.row_factory = sqlite3.Row
```

Version 0.1では外部キーを使用しません。

将来外部キーを使用する場合は、このモジュールで次を有効化します。

```sql
PRAGMA foreign_keys = ON;
```

`create_connection()` は、接続を生成して返すだけです。

接続を閉じる責務は、接続を取得した呼び出し元が持ちます。

---

### 13.4 `database/initializer.py`

データベース初期化を担当します。

正式な関数名は、次のとおりです。

```python
initialize_database()
```

想定シグネチャは、次のとおりです。

```python
def initialize_database(
    database_path: Path | str,
) -> None:
    ...
```

主な責務は、次のとおりです。

* データベースパスを受け取る。
* データベースパスを `Path` へ変換する。
* 親ディレクトリを作成する。
* SQLiteへ接続する。
* 現在の `PRAGMA user_version` を取得する。
* スキーマVersionを判定する。
* `book_items` テーブルを作成する。
* 3つのインデックスを作成する。
* `PRAGMA user_version = 1` を設定する。
* トランザクションを管理する。
* 接続を確実に閉じる。

親ディレクトリは、次のように作成します。

```python
database_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
```

開発環境の `data` ディレクトリだけに依存しません。

テストでは、任意の一時ディレクトリを指定できます。

---

## 14. スキーマVersionの判定

初期化処理では、現在の `PRAGMA user_version` を取得します。

Version 0.1では、次のように扱います。

### 14.1 `user_version = 0`

未初期化のデータベースとして扱います。

次の処理を行います。

```text
テーブルを作成する
↓
インデックスを作成する
↓
user_versionを1に設定する
```

---

### 14.2 `user_version = 1`

現行スキーマとして扱います。

`IF NOT EXISTS` を使用して、テーブルとインデックスの存在を確認します。

既存データを削除しません。

---

### 14.3 `user_version > 1`

このアプリケーションが対応していない新しいスキーマとして、エラーにします。

古いアプリケーションから新しいスキーマを誤って操作しないためです。

---

### 14.4 想定外のVersion

負数などの想定外の値を検出した場合も、初期化を続行しません。

Version 0.1の最初の実装では独自例外を作成せず、適切な標準例外を使用します。

独自例外が必要になった場合は、別途設計します。

---

## 15. 初期化処理のトランザクション

次の処理を、1つのトランザクションとして実行します。

```text
CREATE TABLE
↓
CREATE INDEX
↓
PRAGMA user_version = 1
↓
COMMIT
```

途中で例外が発生した場合は、ロールバックします。

`user_version` は、テーブルとインデックスの作成が成功した場合だけ更新します。

接続処理の想定構成は、次のとおりです。

```python
connection = create_connection(database_path)

try:
    with connection:
        ...
finally:
    connection.close()
```

Version 0.1では、独自の接続コンテキストマネージャーを作成しません。

---

## 16. `models` パッケージ

### 16.1 目的

`models` パッケージは、アプリケーション内で受け渡すデータ構造を定義します。

---

### 16.2 `models/book_item.py`

書籍情報を表すモデルを定義します。

Version 0.1では、Pythonの `dataclass` を使用します。

新規登録用モデルと取得済みモデルは分けません。

想定構成は、次のとおりです。

```python
from dataclasses import dataclass


@dataclass(slots=True)
class BookItem:
    title: str
    id: int | None = None
    isbn: str | None = None
    magazine_code: str | None = None
    author: str | None = None
    publisher: str | None = None
    publication_format: str | None = None
    description: str | None = None
    completion_month: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
```

`created_at` と `updated_at` は、Version 0.1では文字列として扱います。

保存形式は、データベース設計書に従います。

```text
YYYY-MM-DD HH:MM:SS
```

モデルは、次のものを保持しません。

* SQLite接続。
* SQL。
* Tkinterウィジェット。
* Repository。
* Service。
* ダイアログ。

---

## 17. `repositories` パッケージ

### 17.1 目的

Repositoryは、SQLiteへのデータアクセスを担当します。

SQLは、原則としてRepositoryへ集約します。

---

### 17.2 `repositories/book_repository.py`

`book_items` テーブルに対するCRUDと検索を担当します。

Repositoryはクラスとして実装します。

想定構成は、次のとおりです。

```python
class BookRepository:
    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        self._database_path = Path(database_path)
```

Repositoryは、長時間使用するSQLite接続を保持しません。

各メソッドは、必要なタイミングで接続を生成し、処理後に閉じます。

理由は、次のとおりです。

* 接続管理をメソッド単位で完結できる。
* テスト用データベースを注入しやすい。
* GUIアプリで接続を長時間保持する複雑さを避けられる。
* Version 0.1の処理件数では性能上の問題が小さい。

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
find_duplicates_by_isbn
find_duplicates_by_magazine_code
```

更新時は、更新対象自身のIDを重複判定から除外できる構成にします。

Repositoryの責務は、次のとおりです。

* SQLを実行する。
* プレースホルダーへ値を渡す。
* SQLiteの行をモデルへ変換する。
* 登録IDを返す。
* 更新件数を返す。
* 削除件数を返す。
* SQLite例外を上位層へ通知する。
* 接続を確実に閉じる。

Repositoryでは、次の処理を行いません。

* ISBNの正規化。
* ISBNのチェックデジット検証。
* 読了年月の検証。
* GUIダイアログの表示。
* Tkinterウィジェットの操作。
* 利用者向けメッセージの生成。

---

## 18. `services` パッケージ

### 18.1 目的

Serviceは、入力値の検証、正規化およびアプリケーション上の処理手順を担当します。

GUIとRepositoryの間を調整します。

---

### 18.2 `services/validators.py`

入力値の正規化と検証を担当します。

Version 0.1では、正規化関数と検証関数を同じファイルに配置します。

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

このモジュールでは、次の処理を行いません。

* SQLiteへの接続。
* SQLの実行。
* Tkinterダイアログの表示。
* Repositoryの呼び出し。

ファイルが大きくなった場合は、次の分割を検討します。

```text
services/
├── isbn.py
├── normalizers.py
└── validators.py
```

初期段階では分割しません。

---

### 18.3 `services/book_service.py`

書籍管理に関する処理を担当します。

Serviceはクラスとして実装します。

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

---

## 19. ServiceとGUIの確認処理

不正ISBNまたは重複登録を検出した場合は、次の2段階で処理します。

```text
GUIが入力値をServiceへ渡して事前確認する
↓
Serviceが検証結果と重複候補を返す
↓
GUIが確認ダイアログを表示する
↓
利用者が続行を選択する
↓
GUIが許可フラグ付きで登録または更新を依頼する
```

ServiceがTkinterの `messagebox` を呼び出すことはありません。

初期段階では、複雑な結果クラスを先に作成しません。

実装時に結果項目が増えた場合は、専用の結果モデルを追加するか検討します。

---

## 20. `ui` パッケージ

### 20.1 目的

`ui` パッケージは、Tkinterを使用した画面表示と利用者操作を担当します。

---

### 20.2 初期GUI構成

GUI実装開始時の構成は、次のとおりです。

```text
ui/
├── __init__.py
├── book_dialog.py
└── main_window.py
```

初期構成では `dialogs.py` を作成しません。

---

### 20.3 `ui/main_window.py`

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

### 20.4 `ui/book_dialog.py`

書籍登録と編集の入力画面を担当します。

主な責務は、次のとおりです。

* 入力欄を表示する。
* 登録対象の値を収集する。
* 編集対象の既存値を表示する。
* Serviceへ事前確認を依頼する。
* 不正ISBNの警告を表示する。
* 重複候補の警告を表示する。
* 利用者の続行またはキャンセルを受け付ける。
* 保存結果を画面へ反映する。

単純な確認、警告、エラー、情報表示には、Tkinterの `messagebox` を使用します。

独自ダイアログが複数必要になった場合は、後から `dialogs` パッケージへの分割を検討します。

---

## 21. `tests` ディレクトリ

テストコードは、アプリケーション構成に対応させます。

```text
tests/
├── database/
├── repositories/
└── services/
```

GUIの自動テストは、初期実装の必須範囲には含めません。

まず、データベース、Repository、Serviceの自動テストを優先します。

---

## 22. テスト用データベース

初期化処理と接続処理のテストでは、pytestの `tmp_path` を使用します。

例

```python
database_path = tmp_path / "test_book_manager.db"
```

一時SQLiteファイルを使用する理由は、次のとおりです。

* 親ディレクトリ作成を確認できる。
* SQLiteファイル作成を確認できる。
* 本番と同じファイル型データベースでテストできる。
* 本番データベースを誤って変更しない。
* テストごとに独立した環境を作成できる。

初期化処理のテストでは、インメモリデータベースを使用しません。

Repositoryテストで必要性が確認された場合は、インメモリデータベースを検討します。

---

## 23. `tests/conftest.py`

複数のテストファイルで共有するfixtureが発生した場合に作成します。

想定するfixtureは、次のとおりです。

* 一時データベースパス。
* 初期化済みSQLiteデータベース。
* テスト用Repository。
* テスト用Service。
* サンプル書籍データ。

共有fixtureが存在しない段階では、空の `conftest.py` を作成しません。

---

## 24. データベース接続テスト

`tests/database/test_connection.py` では、次の内容を確認します。

* 指定したSQLiteファイルへ接続できる。
* `sqlite3.Row` が設定される。
* SQLを実行できる。
* 日本語を保存および取得できる。
* 呼び出し元で接続を閉じられる。
* 不正な保存先では適切な例外が発生する。

---

## 25. データベース初期化テスト

`tests/database/test_initializer.py` では、次の内容を確認します。

* 親ディレクトリがない状態から作成できる。
* データベースファイルを作成できる。
* `book_items` テーブルが作成される。
* 3つのインデックスが作成される。
* `PRAGMA user_version` が1になる。
* 複数回初期化してもエラーにならない。
* 既存データが削除されない。
* `user_version = 1` のデータベースを再初期化できる。
* `user_version > 1` を検出してエラーにできる。
* 初期化失敗時に不完全なVersion更新を行わない。
* 接続が確実に閉じられる。

---

## 26. Repositoryテスト

`tests/repositories/test_book_repository.py` では、次の内容を確認します。

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
* メソッド処理後に接続が残らない。

---

## 27. Serviceテスト

### 27.1 `test_validators.py`

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

### 27.2 `test_book_service.py`

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

## 28. 例外構成

データベース初期化の最初の実装では、独自例外を作成しません。

SQLiteやファイルシステムの例外を、無条件に握りつぶさず上位へ伝播させます。

次の条件が発生した場合に、独自例外を追加します。

* GUIへ技術的な例外を直接渡したくない。
* 複数の下位例外を同じ意味として扱いたい。
* 未対応スキーマVersionを明確に区別したい。
* 入力検証エラーを統一的に扱いたい。

候補となる例外は、次のとおりです。

```text
BookManagerError
DatabaseError
ValidationError
BookNotFoundError
UnsupportedSchemaVersionError
```

例外専用モジュールを作成する場合は、次の場所を使用します。

```text
src/book_manager/exceptions.py
```

必要性が発生する前には作成しません。

---

## 29. ログ

Version 0.1の初期実装では、複雑なログ設定を必須としません。

`print()` を複数のモジュールへ分散させることは避けます。

ログが必要になった場合は、Python標準ライブラリの `logging` を使用します。

ログ設定を追加する場合の候補は、次のとおりです。

```text
src/book_manager/config/logging_config.py
```

---

## 30. 設定ファイル

Version 0.1の初期実装では、外部設定ファイルを必須としません。

パスや固定値は、Pythonモジュールで管理します。

利用者が変更する設定が増えた場合は、次の形式を検討します。

* JSON。
* TOML。
* SQLite内の設定テーブル。

設定方式は、必要性が発生した段階で決定します。

---

## 31. `pyproject.toml`

Pythonプロジェクトの設定は、`pyproject.toml` へ集約します。

初期段階では、次の内容を含めます。

* ビルドシステム。
* プロジェクト名。
* アプリケーションVersion。
* Pythonの必要Version。
* `src` レイアウトのパッケージ設定。
* pytest設定。

基本値は、次のとおりです。

```text
プロジェクト名 : book-manager
Version        : 0.1.0
Python         : 3.12以上
```

コード整形や静的解析の設定は、実際にツールを導入するときに追加します。

---

## 32. `.gitignore`

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

必要な空ディレクトリは、`.gitkeep` で維持します。

`.vscode` の設定を共有する必要が生じた場合は、必要なファイルだけを個別に管理します。

---

## 33. 初期実装順序

実装は、次の順番で進めます。

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
test_connection.pyを作成する
↓
test_initializer.pyを作成する
↓
pytestを実行する
↓
実装レビューを行う
↓
コミットする
```

---

## 34. 初期実装のコミット単位

### 34.1 Pythonプロジェクト設定

```text
chore: Pythonプロジェクト設定を追加
```

対象

```text
pyproject.toml
```

---

### 34.2 データベースパス管理

```text
feat: データベースパス管理を追加
```

対象

```text
src/book_manager/__init__.py
src/book_manager/config/__init__.py
src/book_manager/config/paths.py
```

---

### 34.3 SQLite初期化処理

```text
feat: SQLite初期化処理を追加
```

対象

```text
src/book_manager/database/__init__.py
src/book_manager/database/schema.py
src/book_manager/database/connection.py
src/book_manager/database/initializer.py
```

---

### 34.4 SQLite初期化テスト

```text
test: SQLite初期化テストを追加
```

対象

```text
tests/database/test_connection.py
tests/database/test_initializer.py
```

---

## 35. 過剰設計を避ける方針

初期実装では、次の機能を先に作りません。

* 抽象Repositoryクラス。
* Repositoryインターフェース。
* 依存性注入フレームワーク。
* ORM。
* 複雑なマイグレーション基盤。
* 独自接続コンテキストマネージャー。
* プラグイン構成。
* イベントバス。
* 非同期データベース処理。
* 複数データベース対応。
* Web API。
* 高度なログ基盤。
* 設定管理フレームワーク。
* 登録専用モデルと取得専用モデルの分割。
* 複雑なService結果クラス。
* 将来用の空ファイル。

実際の要件が発生した場合に追加します。

---

## 36. 将来の変更候補

将来、次の構成を追加する可能性があります。

```text
src/book_manager/
├── api/
├── exceptions.py
├── migrations/
├── importers/
├── exporters/
└── utils/
```

用途が明確になるまでは追加しません。

汎用処理を安易に `utils` へ集約せず、責務が明確なモジュールへ配置します。

---

## 37. 実装時の必須事項

初期実装では、次の事項を必須とします。

* Python 3.12以上を使用する。
* 型ヒントを付ける。
* `pathlib.Path` を使用する。
* データベースパスを引数で注入できるようにする。
* テストで本番データベースを使用しない。
* SQLへ利用者入力を直接連結しない。
* スキーマ初期化をトランザクションで行う。
* `user_version` をテーブルとインデックス作成後に設定する。
* 未対応の新しいスキーマVersionを検出する。
* 接続を確実に閉じる。
* `sqlite3.Row` を接続生成時に設定する。
* 初期化処理を複数回実行可能にする。
* 既存データを削除しない。
* SQLite例外を無条件に握りつぶさない。
* 不要な抽象化を追加しない。
* 空の将来用ファイルを作成しない。

---

## 38. データベース設計との整合性

この構成は、次のDesign Freeze済み文書を前提とします。

```text
docs/database/database_design.md
docs/database/er_diagram.md
docs/database/database_design_review.md
```

整合している主な内容は、次のとおりです。

* SQLiteを使用する。
* Python標準ライブラリの `sqlite3` を使用する。
* 開発中のデータベース保存先を `data/book_manager.db` とする。
* SQLiteスキーマVersionを1とする。
* SQL定義を一元管理する。
* RepositoryへCRUD用SQLを配置する。
* Serviceで入力検証と正規化を行う。
* GUIとRepositoryを直接接続しない。
* 初期化処理を複数回実行可能にする。
* 本番データベースとテストデータベースを分離する。
* バックアップ機能を初期CRUDの必須範囲に含めない。
* 書影機能を初期CRUDの必須範囲に含めない。

---

## 39. 現時点の正式な設計判断

Version 0.2では、次の内容を正式に採用します。

* `src` レイアウトを使用する。
* Python 3.12以上を使用する。
* アプリケーションVersionを0.1.0とする。
* Pythonパッケージ名を `book_manager` とする。
* GUI、Service、Repository、Databaseを分離する。
* `__main__.py` と `app.py` を分離する。
* `app.py` をComposition Rootとする。
* `app.py` と `__main__.py` はGUI実装時に作成する。
* パス管理を `config/paths.py` へ集約する。
* `PROJECT_ROOT` は開発中のリポジトリルートを表す。
* `Path.cwd()` をデータベースパスの基準にしない。
* SQL定義を `database/schema.py` へ集約する。
* スキーマVersionを `SCHEMA_VERSION` で管理する。
* 初期スキーマVersionを1とする。
* SQLite接続関数名を `create_connection()` とする。
* `create_connection()` はデータベースパスを引数で受け取る。
* `sqlite3.Row` を接続生成時に設定する。
* 接続を閉じる責務は呼び出し元が持つ。
* 初期化関数名を `initialize_database()` とする。
* `initialize_database()` はデータベースパスを引数で受け取る。
* 初期化処理がデータベースパスの親ディレクトリを作成する。
* スキーマ初期化を1つのトランザクションで行う。
* `user_version = 0` を未初期化として扱う。
* `user_version = 1` を現行スキーマとして扱う。
* `user_version > 1` を未対応としてエラーにする。
* 書籍モデルに `dataclass` を使用する。
* 新規登録用と取得用のモデルを分けない。
* モデルの日時属性を文字列とする。
* Repositoryをクラスとして実装する。
* Repositoryはデータベースパスを保持する。
* Repositoryは処理単位で接続を生成して閉じる。
* Serviceをクラスとして実装する。
* 不正ISBNと重複確認はGUIとの2段階処理とする。
* 初期GUIでは `main_window.py` と `book_dialog.py` を使用する。
* 単純な確認や警告には `messagebox` を使用する。
* テストにはpytestを使用する。
* 初期テストでは `tmp_path` の一時SQLiteファイルを使用する。
* 共有fixtureが必要になるまで `conftest.py` を作成しない。
* 独自例外は必要になった段階で追加する。
* 不要な将来用ファイルを作成しない。

---

## 40. Design Freeze

この文書のVersion 0.2を、初期実装におけるプロジェクト構成のDesign Freeze版とします。

次の実装は、この設計を基準として行います。

* `pyproject.toml`。
* データベースパス管理。
* SQLite接続。
* SQLiteスキーマ定義。
* SQLite初期化。
* データベース接続テスト。
* データベース初期化テスト。
* 将来のモデル、Repository、Service、GUI。

Design Freeze後に構成を変更する場合は、開発ガイドラインに従い、変更理由、影響範囲、関連文書、実装およびテストを更新します。

---

## 41. 次の作業

Design Freeze後は、次の順番で進めます。

```text
project_structure_review.mdを正式承認へ更新する
↓
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
test_connection.pyを作成する
↓
test_initializer.pyを作成する
↓
pytestを実行する
↓
実装レビューを行う
