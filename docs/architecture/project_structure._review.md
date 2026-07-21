# プロジェクト構成設計レビュー

Version : 0.2
Last Updated : 2026-07-21
Status : Approved

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおけるプロジェクト構成設計のレビュー結果、修正内容および最終承認を記録するものです。

レビュー対象は、次の文書です。

```text
docs/architecture/project_structure.md
```

Version 0.1に対する初回レビューでは、複数の修正条件を付けて条件付き承認としました。

その後、指摘事項がVersion 0.2へ反映されたことを確認したため、プロジェクト構成設計を正式承認し、初期実装におけるDesign Freeze版とします。

---

## 2. レビュー対象

### 初回レビュー対象

| 文書                     | 対象Version | 状態    |
| ---------------------- | --------: | ----- |
| `project_structure.md` |       0.1 | Draft |

### 最終確認対象

| 文書                     | 対象Version | 状態            |
| ---------------------- | --------: | ------------- |
| `project_structure.md` |       0.2 | Design Freeze |

---

## 3. レビュー実施日

初回レビュー日

```text
2026-07-21
```

最終確認日

```text
2026-07-21
```

---

## 4. レビュー観点

本レビューでは、主に次の点を確認しました。

* `src` レイアウトが適切か。
* ディレクトリ構成が理解しやすいか。
* 各パッケージの責務が明確か。
* 依存方向が適切か。
* GUI、Service、Repository、Databaseが分離されているか。
* SQLite固有処理が適切な場所に配置されているか。
* パス管理が一元化されているか。
* SQL定義が重複しない構成になっているか。
* 初期化処理を安全に実装できるか。
* データベースパスをテストへ注入できるか。
* SQLite接続の生成と終了の責務が明確か。
* スキーマVersionの扱いが明確か。
* 初期化処理のトランザクション境界が明確か。
* Repositoryの接続管理方式が明確か。
* ServiceとGUIの責務分担が適切か。
* テスト構成が実装構成と対応しているか。
* 本番データベースとテストデータベースを分離できるか。
* 初期実装として過剰に細分化されていないか。
* 将来の拡張を妨げないか。
* 実装順序が適切か。
* Gitのコミット単位が適切か。
* データベース設計書と矛盾していないか。
* PythonとアプリケーションのVersionが明確か。

---

## 5. 初回レビュー結果

Version 0.1に対する初回レビュー結果は、次のとおりでした。

```text
条件付き承認
```

基本的なプロジェクト構成と責務分離は妥当でしたが、Design Freeze前に次の事項を確定する必要がありました。

* `PROJECT_ROOT` の意味。
* SQLite接続関数名。
* 初期化関数の引数。
* データディレクトリ作成の責務。
* SQLite接続を閉じる責務。
* `sqlite3.Row` の設定場所。
* `PRAGMA user_version` の判定方法。
* スキーマ初期化のトランザクション。
* スキーマSQLの保持形式。
* モデルの日時型。
* 新規登録用モデルと取得済みモデルの扱い。
* Repositoryの接続管理方式。
* Serviceの結果表現。
* `validators.py` の責務。
* GUIダイアログの初期構成。
* `app.py` と `__main__.py` の作成時期。
* `tests/conftest.py` の作成時期。
* テスト用データベース形式。
* 独自例外の導入時期。
* Pythonの必要Version。
* アプリケーションVersion。

---

## 6. 指摘事項への対応結果

### 6.1 `PROJECT_ROOT` の意味

#### 指摘内容

開発時のリポジトリルートと、配布版の利用者データ保存先が混同される可能性がありました。

#### 対応内容

Version 0.1の開発中は、`PROJECT_ROOT` をGitリポジトリのルートディレクトリとして扱う方針が明記されました。

パス計算は、次のファイルへ集約します。

```text
src/book_manager/config/paths.py
```

`Path.cwd()` は、データベースパスの基準として使用しません。

配布版では、リポジトリまたはアプリケーション本体の配置場所と、利用者データ保存先を分離できる構成とします。

#### 判定

```text
対応完了
```

---

### 6.2 SQLite接続関数名

#### 指摘内容

`create_connection()` と `get_connection()` の2案が記載されていました。

#### 対応内容

正式な関数名を、次の名称へ統一しました。

```python
create_connection()
```

新しいSQLite接続を生成して返す関数であるため、`create` が処理内容を明確に表します。

#### 判定

```text
対応完了
```

---

### 6.3 SQLite接続関数の引数

#### 指摘内容

本番用データベースとテスト用データベースを切り替える方法を明確にする必要がありました。

#### 対応内容

`create_connection()` は、データベースパスを引数として受け取ります。

正式な想定シグネチャは、次のとおりです。

```python
def create_connection(
    database_path: Path | str,
) -> sqlite3.Connection:
    ...
```

本番コードでは `DATABASE_PATH` を渡し、テストでは一時データベースパスを渡します。

#### 判定

```text
対応完了
```

---

### 6.4 初期化関数の引数

#### 指摘内容

`initialize_database()` が、グローバルな本番用パスへ直接依存する可能性がありました。

#### 対応内容

`initialize_database()` も、データベースパスを引数として受け取ります。

正式な想定シグネチャは、次のとおりです。

```python
def initialize_database(
    database_path: Path | str,
) -> None:
    ...
```

これにより、本番用データベースとテスト用データベースを切り替えられます。

#### 判定

```text
対応完了
```

---

### 6.5 データディレクトリ作成の責務

#### 指摘内容

初期化処理が開発環境の `data` ディレクトリだけに依存しない構成が必要でした。

#### 対応内容

`initializer.py` が、渡されたデータベースパスの親ディレクトリを作成する方針となりました。

```python
database_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
```

`paths.py` はパスを定義し、`initializer.py` は実際に必要な親ディレクトリを作成します。

#### 判定

```text
対応完了
```

---

### 6.6 SQLite接続を閉じる責務

#### 指摘内容

接続を生成した後、どの処理が接続を閉じるかを明確にする必要がありました。

#### 対応内容

`create_connection()` は、接続を生成して返すだけとします。

接続を取得した呼び出し元が、接続を閉じる責務を持ちます。

初期化処理では、次の構成を基本とします。

```python
connection = create_connection(database_path)

try:
    with connection:
        ...
finally:
    connection.close()
```

Version 0.1では、独自の接続コンテキストマネージャーは作成しません。

#### 判定

```text
対応完了
```

---

### 6.7 `sqlite3.Row` の設定場所

#### 指摘内容

すべてのRepositoryで同じ行取得方式を使用できるよう、設定場所を統一する必要がありました。

#### 対応内容

`database/connection.py` の `create_connection()` 内で設定します。

```python
connection.row_factory = sqlite3.Row
```

#### 判定

```text
対応完了
```

---

### 6.8 `PRAGMA user_version` の判定

#### 指摘内容

`user_version` が0、1またはそれ以外の場合の扱いが未確定でした。

#### 対応内容

Version 0.1では、次のように扱います。

```text
user_version = 0
    未初期化として扱う。

user_version = 1
    現行スキーマとして扱う。

user_version > 1
    このアプリケーションが対応していない新しいスキーマとしてエラーにする。

想定外の値
    初期化を続行せずエラーにする。
```

古いアプリケーションから、より新しいスキーマを誤って操作することを防ぎます。

#### 判定

```text
対応完了
```

---

### 6.9 スキーマ初期化のトランザクション

#### 指摘内容

テーブル、インデックスおよびスキーマVersionの更新を、どの単位で確定するかが未確定でした。

#### 対応内容

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

途中で例外が発生した場合はロールバックします。

`user_version` は、テーブルとインデックス作成が成功した場合だけ設定します。

#### 判定

```text
対応完了
```

---

### 6.10 スキーマSQLの保持形式

#### 指摘内容

SQLの定義と実行順序が複数箇所へ分散する可能性がありました。

#### 対応内容

`database/schema.py` で、個別SQL定数と実行順序を表すタプルを定義します。

```python
SCHEMA_VERSION = 1

CREATE_BOOK_ITEMS_TABLE = """..."""
CREATE_BOOK_ITEMS_TITLE_INDEX = """..."""
CREATE_BOOK_ITEMS_ISBN_INDEX = """..."""
CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX = """..."""

SCHEMA_STATEMENTS = (
    CREATE_BOOK_ITEMS_TABLE,
    CREATE_BOOK_ITEMS_TITLE_INDEX,
    CREATE_BOOK_ITEMS_ISBN_INDEX,
    CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX,
)
```

SQL定義は `schema.py` が保持し、実行は `initializer.py` が担当します。

#### 判定

```text
対応完了
```

---

### 6.11 モデルの日時型

#### 指摘内容

`BookItem` モデルで、日時を文字列または `datetime` のどちらとして扱うかが未確定でした。

#### 対応内容

Version 0.1では、`created_at` と `updated_at` を文字列として扱います。

```python
created_at: str | None
updated_at: str | None
```

データベース保存形式と直接対応させ、初期実装を単純にします。

日時生成はServiceへ集約します。

#### 判定

```text
対応完了
```

---

### 6.12 新規登録用モデルと取得済みモデル

#### 指摘内容

新規登録時には、`id`、`created_at`、`updated_at` が未設定になるため、モデルを分けるか検討する必要がありました。

#### 対応内容

Version 0.1では、登録用モデルと取得済みモデルを分けません。

該当属性を省略可能とする `BookItem` dataclassを使用します。

```python
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

必要性が発生した場合に、登録用DTOなどへの分離を検討します。

#### 判定

```text
対応完了
```

---

### 6.13 Repositoryの接続管理方式

#### 指摘内容

RepositoryがSQLite接続を保持するか、データベースパスを保持するかが未確定でした。

#### 対応内容

Repositoryは、長時間使用するSQLite接続を保持しません。

Repositoryはデータベースパスを保持します。

```python
class BookRepository:
    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        self._database_path = Path(database_path)
```

各メソッドは、処理単位で接続を生成し、処理後に閉じます。

#### 判定

```text
対応完了
```

---

### 6.14 Serviceの結果表現

#### 指摘内容

不正ISBNや重複を検出した場合に、ServiceとGUIがどのように処理を分担するかが未確定でした。

#### 対応内容

次の2段階処理を採用します。

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

ServiceはTkinterのダイアログを直接表示しません。

Version 0.1では、複雑な結果クラスを先に作成しません。

#### 判定

```text
対応完了
```

---

### 6.15 `validators.py` の責務

#### 指摘内容

正規化と検証を同じファイルに配置するか、最初から分割するかを確認する必要がありました。

#### 対応内容

Version 0.1では、正規化関数と検証関数を `services/validators.py` にまとめます。

初期関数数が少なく、関連性が高いためです。

ファイルが大きくなった場合に、次の分割を検討します。

```text
services/
├── isbn.py
├── normalizers.py
└── validators.py
```

#### 判定

```text
対応完了
```

---

### 6.16 GUIダイアログの初期構成

#### 指摘内容

登録、編集、警告、確認などを、初期段階から `dialogs.py` へ集約する案は、責務が曖昧になる可能性がありました。

#### 対応内容

GUI実装開始時は、次の構成を採用します。

```text
ui/
├── __init__.py
├── book_dialog.py
└── main_window.py
```

単純な確認、警告、エラーおよび情報表示には、Tkinterの `messagebox` を使用します。

初期構成では `dialogs.py` を作成しません。

#### 判定

```text
対応完了
```

---

### 6.17 `app.py` と `__main__.py` の作成時期

#### 指摘内容

データベース初期化だけを実装する段階で、将来用の空ファイルを作成する必要があるかを確認しました。

#### 対応内容

`app.py` と `__main__.py` は、GUI実装開始時に作成します。

最終的な配置と責務は設計書で確定していますが、空の将来用ファイルは先に作成しません。

#### 判定

```text
対応完了
```

---

### 6.18 `tests/conftest.py` の作成時期

#### 指摘内容

初期テスト構成に、空の `conftest.py` を含める必要があるかを確認しました。

#### 対応内容

複数のテストファイルで共有するfixtureが発生した時点で作成します。

共有fixtureが存在しない段階では作成しません。

#### 判定

```text
対応完了
```

---

### 6.19 テスト用データベース形式

#### 指摘内容

一時ファイル型SQLiteとインメモリSQLiteのどちらを初期テストで使用するかが未確定でした。

#### 対応内容

接続処理と初期化処理のテストでは、pytestの `tmp_path` を使用した一時SQLiteファイルを使用します。

```python
database_path = tmp_path / "test_book_manager.db"
```

これにより、親ディレクトリとファイル作成も含めて確認できます。

インメモリデータベースは、必要性が確認されたRepositoryテストで検討します。

#### 判定

```text
対応完了
```

---

### 6.20 独自例外の導入時期

#### 指摘内容

独自例外の候補は定義されていましたが、初期実装で作成するかが未確定でした。

#### 対応内容

データベース初期化の最初の実装では、独自例外を作成しません。

SQLiteやファイルシステムの例外を無条件に握りつぶさず、上位へ伝播させます。

次の条件が発生した場合に導入を検討します。

* GUIへ技術的例外を直接渡したくない。
* 複数の下位例外を同じ意味として扱いたい。
* 未対応スキーマVersionを明確に区別したい。
* 入力検証エラーを統一的に扱いたい。

#### 判定

```text
対応完了
```

---

### 6.21 Pythonの必要Version

#### 指摘内容

開発環境はPython 3.12ですが、プロジェクトの最低Versionが未確定でした。

#### 対応内容

初期実装では、Python 3.12以上を使用します。

`pyproject.toml` には、次の内容を設定します。

```toml
requires-python = ">=3.12"
```

#### 判定

```text
対応完了
```

---

### 6.22 アプリケーションVersion

#### 指摘内容

`pyproject.toml` に記録する初期Versionが未確定でした。

#### 対応内容

初期アプリケーションVersionを、次の値とします。

```text
0.1.0
```

SQLiteスキーマVersionとは別に管理します。

```text
アプリケーションVersion : 0.1.0
SQLite user_version      : 1
```

#### 判定

```text
対応完了
```

---

## 7. 設計書との整合性

`project_structure.md` Version 0.2と、関連するDesign Freeze済み文書の整合性を確認しました。

対象文書は、次のとおりです。

```text
docs/development_guidelines.md
docs/database/database_design.md
docs/database/er_diagram.md
docs/database/database_design_review.md
docs/adr/ADR-0001-sqlite-selection.md
```

確認結果は、次のとおりです。

| 確認項目                        | 結果 |
| --------------------------- | -- |
| SQLiteの使用                   | 一致 |
| Python標準ライブラリ `sqlite3` の使用 | 一致 |
| 開発中のデータベース保存先               | 一致 |
| `PRAGMA user_version = 1`   | 一致 |
| SQL定義の一元管理                  | 一致 |
| SQLite接続処理の分離               | 一致 |
| SQLite初期化処理の分離              | 一致 |
| RepositoryへのCRUD用SQL集約      | 一致 |
| Serviceでの入力検証と正規化           | 一致 |
| GUIとRepositoryの分離           | 一致 |
| 日時をJSTで生成する方針               | 一致 |
| 本番DBとテストDBの分離               | 一致 |
| バックアップを初期CRUDから除外           | 一致 |
| 書影を初期CRUDから除外               | 一致 |
| 過剰設計を避ける方針                  | 一致 |
| Design Freeze後の変更手順         | 一致 |

重大な不整合はありません。

---

## 8. 正式な初期ファイル構成

Design Freeze後、最初に作成するファイルは次のとおりです。

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

次のファイルは、必要性が発生するまで作成しません。

```text
src/book_manager/__main__.py
src/book_manager/app.py
tests/conftest.py
src/book_manager/exceptions.py
```

---

## 9. 正式な将来構成

データベース初期化完了後、必要な段階で次の構成を追加します。

```text
src/book_manager/
├── __main__.py
├── app.py
├── models/
│   ├── __init__.py
│   └── book_item.py
├── repositories/
│   ├── __init__.py
│   └── book_repository.py
├── services/
│   ├── __init__.py
│   ├── book_service.py
│   └── validators.py
└── ui/
    ├── __init__.py
    ├── book_dialog.py
    └── main_window.py
```

空の将来用ファイルは、先行して作成しません。

---

## 10. 承認済み設計事項

Version 0.2では、次の設計事項を正式に承認します。

* `src` レイアウトを使用する。
* Python 3.12以上を使用する。
* アプリケーションVersionを0.1.0とする。
* Pythonパッケージ名を `book_manager` とする。
* GUI、Service、Repository、Databaseを分離する。
* 基本依存方向を `ui → services → repositories → database` とする。
* GUIへSQLを記述しない。
* ServiceへSQLite接続処理を記述しない。
* RepositoryへTkinter処理を記述しない。
* `__main__.py` と `app.py` を分離する。
* `app.py` をComposition Rootとする。
* `app.py` と `__main__.py` はGUI実装時に作成する。
* パス管理を `config/paths.py` へ集約する。
* `PROJECT_ROOT` を開発中のリポジトリルートとする。
* `Path.cwd()` をデータベースパスの基準にしない。
* SQLite接続処理を `database/connection.py` へ配置する。
* SQLite初期化処理を `database/initializer.py` へ配置する。
* SQLとスキーマVersionを `database/schema.py` へ集約する。
* SQLite接続関数名を `create_connection()` とする。
* `create_connection()` はデータベースパスを引数で受け取る。
* `sqlite3.Row` を接続生成時に設定する。
* 接続を閉じる責務は呼び出し元が持つ。
* 初期化関数名を `initialize_database()` とする。
* `initialize_database()` はデータベースパスを引数で受け取る。
* 初期化処理がデータベースパスの親ディレクトリを作成する。
* スキーマ初期化を1トランザクションで行う。
* `user_version = 0` を未初期化として扱う。
* `user_version = 1` を現行スキーマとして扱う。
* `user_version > 1` を未対応としてエラーにする。
* スキーマSQLの実行順序を `SCHEMA_STATEMENTS` で管理する。
* 書籍モデルに `dataclass` を使用する。
* 新規登録用モデルと取得用モデルを分けない。
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
* 不要な抽象化を追加しない。
* 空の将来用ファイルを作成しない。

---

## 11. 実装時の必須事項

初期実装では、次の事項を必須とします。

* Python 3.12以上を使用する。
* 型ヒントを付ける。
* `pathlib.Path` を使用する。
* データベースパスを引数で注入できるようにする。
* テストで本番用データベースを使用しない。
* SQLite接続生成時に `sqlite3.Row` を設定する。
* SQLite接続を確実に閉じる。
* SQLへ利用者入力を直接連結しない。
* スキーマ初期化をトランザクションで行う。
* テーブルとインデックスの作成後に `user_version` を設定する。
* 未対応の新しいスキーマVersionを検出する。
* 初期化処理を複数回実行可能にする。
* 既存データを削除しない。
* SQLite例外を無条件に握りつぶさない。
* 不要な抽象化を追加しない。
* 空の将来用ファイルを作成しない。

---

## 12. 初期実装のテスト項目

### 12.1 SQLite接続

`tests/database/test_connection.py` では、少なくとも次の内容を確認します。

* 指定したSQLiteファイルへ接続できる。
* `sqlite3.Row` が設定される。
* SQLを実行できる。
* 日本語を保存および取得できる。
* 呼び出し元で接続を閉じられる。
* 不正な保存先で適切な例外が発生する。

### 12.2 SQLite初期化

`tests/database/test_initializer.py` では、少なくとも次の内容を確認します。

* 親ディレクトリがない状態から作成できる。
* データベースファイルを作成できる。
* `book_items` テーブルが作成される。
* 3つのインデックスが作成される。
* `PRAGMA user_version` が1になる。
* 初期化処理を複数回実行してもエラーにならない。
* 既存データが削除されない。
* `user_version = 1` のデータベースを再初期化できる。
* `user_version > 1` を検出してエラーにできる。
* 初期化失敗時に不完全なVersion更新を行わない。
* 接続が確実に閉じられる。

---

## 13. 初期実装順序

正式な初期実装順序は、次のとおりです。

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

## 14. 正式なコミット単位

### 14.1 Pythonプロジェクト設定

```text
chore: Pythonプロジェクト設定を追加
```

対象

```text
pyproject.toml
```

### 14.2 データベースパス管理

```text
feat: データベースパス管理を追加
```

対象

```text
src/book_manager/__init__.py
src/book_manager/config/__init__.py
src/book_manager/config/paths.py
```

### 14.3 SQLite初期化処理

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

### 14.4 SQLite初期化テスト

```text
test: SQLite初期化テストを追加
```

対象

```text
tests/database/test_connection.py
tests/database/test_initializer.py
```

---

## 15. 過剰設計を避ける事項

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

## 16. 最終レビュー結果

Version 0.2に対する最終レビュー結果は、次のとおりです。

```text
承認
```

初回レビューで示した条件は、すべて `project_structure.md` Version 0.2へ反映されています。

初期実装を開始するために必要なプロジェクト構成、責務分離、依存方向、パス注入、SQLite接続、スキーマ初期化およびテスト方針は、十分に具体化されています。

---

## 17. Design Freeze判定

プロジェクト構成設計Version 0.2を、初期実装におけるDesign Freeze版として承認します。

```text
Approved
Design Freeze
```

次の文書を、初期実装の正式な構成基準とします。

```text
project_structure.md        : Version 0.2
project_structure_review.md : Version 0.2
application version         : 0.1.0
Python                      : 3.12以上
SQLite user_version         : 1
```

Design Freeze後に構成を変更する場合は、開発ガイドラインに従って次の手順を行います。

```text
変更理由を整理する
↓
影響範囲を確認する
↓
project_structure.mdを更新する
↓
必要に応じて関連する設計書やADRを更新する
↓
レビューする
↓
文書Versionを更新する
↓
実装を変更する
↓
テストを更新する
↓
既存機能への影響を確認する
```

---

## 18. 次の作業

Design Freeze後は、実装フェーズへ移行します。

次の順番で進めます。

```text
pyproject.tomlを作成する
↓
Pythonプロジェクト設定を確認する
↓
config/paths.pyを作成する
↓
database/schema.pyを作成する
↓
database/connection.pyを作成する
↓
database/initializer.pyを作成する
↓
SQLite接続テストを作成する
↓
SQLite初期化テストを作成する
↓
pytestを実行する
↓
初期実装レビューを行う
