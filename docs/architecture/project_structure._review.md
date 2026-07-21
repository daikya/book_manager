# プロジェクト構成設計レビュー

Version : 0.1
Last Updated : 2026-07-21
Status : Conditional Approval

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおけるプロジェクト構成設計のレビュー結果を記録するものです。

レビュー対象は、次の文書です。

```text
docs/architecture/project_structure.md
```

本レビューでは、SQLite初期化処理、Repository、Service、GUIおよびテストの実装を開始できる構成になっているかを確認します。

レビュー結果を反映した `project_structure.md` Version 0.2を、初期実装におけるDesign Freeze版とする予定です。

---

## 2. レビュー対象

| 文書                     | 対象Version | 状態    |
| ---------------------- | --------: | ----- |
| `project_structure.md` |       0.1 | Draft |

---

## 3. レビュー実施日

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
* テスト構成が実装構成と対応しているか。
* 本番データベースとテストデータベースを分離できるか。
* 初期実装として過剰に細分化されていないか。
* 将来の拡張を妨げないか。
* 実装順序が適切か。
* Gitのコミット単位が適切か。
* データベース設計書と矛盾していないか。

---

## 5. 総合評価

レビュー結果は、次のとおりです。

```text
条件付き承認
```

Version 0.1の構成案は、初期実装を開始するための基本構成として妥当です。

特に、次の点は適切です。

* `src` レイアウトを採用している。
* アプリケーションコードを `src/book_manager` に集約している。
* GUI、Service、Repository、Databaseを分離している。
* 基本的な依存方向が定義されている。
* SQLite固有処理を `database` パッケージへ分離している。
* データベースパスを `config/paths.py` で一元管理する方針である。
* SQLとスキーマVersionを `database/schema.py` に集約している。
* SQLite接続処理と初期化処理を分離している。
* RepositoryへSQLを集約している。
* 入力検証と正規化をServiceへ配置している。
* GUIがRepositoryを直接呼び出さない構成である。
* pytestを使用する方針である。
* 本番用データベースをテストで使用しない方針である。
* 初期実装範囲がデータベース初期化に限定されている。
* 将来機能を先回りして実装しない方針である。

ただし、Design Freeze前に、いくつかの構成と責務を明確にする必要があります。

---

## 6. 承認済み事項

以下の構成は、そのまま採用します。

### 6.1 `src` レイアウト

アプリケーションコードは、次の場所へ配置します。

```text
src/book_manager/
```

プロジェクト直下へ、アプリケーション用Pythonファイルを直接配置しません。

`src` レイアウトを採用することで、ソースコードとプロジェクト設定を分離し、意図しないインポートを防ぎやすくします。

---

### 6.2 パッケージ名

アプリケーションのPythonパッケージ名は、次のとおりとします。

```text
book_manager
```

プロジェクト名とPythonパッケージ名を一致させます。

---

### 6.3 基本パッケージ構成

次のパッケージ構成を採用します。

```text
book_manager/
├── config/
├── database/
├── models/
├── repositories/
├── services/
└── ui/
```

各パッケージの基本責務は、次のとおりです。

| パッケージ          | 責務                      |
| -------------- | ----------------------- |
| `config`       | パスや固定設定を管理する。           |
| `database`     | SQLite接続、スキーマ、初期化を管理する。 |
| `models`       | アプリケーション内のデータ構造を定義する。   |
| `repositories` | SQLiteへのCRUDと検索を担当する。   |
| `services`     | 検証、正規化、業務処理を担当する。       |
| `ui`           | Tkinter画面と利用者操作を担当する。   |

---

### 6.4 基本的な依存方向

基本的な依存方向は、次のとおりとします。

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

逆方向の依存は避けます。

---

### 6.5 `__main__.py` と `app.py`

`__main__.py` と `app.py` は分離します。

`__main__.py` は、次の処理だけを担当します。

* `app.main()` の呼び出し。
* Pythonモジュールとしての起動入口。

`app.py` は、次の処理を担当します。

* データベース初期化。
* RepositoryとServiceの生成。
* GUIの生成。
* Tkinterメインループの開始。
* 起動時の最上位エラー処理。

---

### 6.6 パス管理

パス管理は、次のファイルへ集約します。

```text
src/book_manager/config/paths.py
```

少なくとも、次のパスを管理します。

```text
PROJECT_ROOT
DATA_DIR
DATABASE_PATH
BACKUP_DIR
CACHE_DIR
```

現在の作業ディレクトリを基準にしません。

`Path.cwd()` をデータベースパスの決定に使用しません。

---

### 6.7 SQLite関連モジュール

SQLite関連処理は、次のように分離します。

```text
database/
├── connection.py
├── initializer.py
└── schema.py
```

それぞれの責務は、次のとおりです。

| ファイル             | 責務                             |
| ---------------- | ------------------------------ |
| `connection.py`  | SQLite接続を生成する。                 |
| `initializer.py` | テーブル、インデックス、スキーマVersionを初期化する。 |
| `schema.py`      | SQL定義とスキーマVersionを保持する。        |

---

### 6.8 SQLの配置

CREATE TABLE文とCREATE INDEX文は、`database/schema.py` へ集約します。

Repositoryで使用するCRUD用SQLは、原則としてRepository内へ配置します。

初期段階では、すべてのSQLを1つの巨大なSQLファイルへ集約しません。

---

### 6.9 モデル

書籍モデルには、Pythonの `dataclass` を使用します。

配置先は、次のとおりです。

```text
src/book_manager/models/book_item.py
```

モデルは、データの受け渡しに集中します。

次のものを保持しません。

* SQLite接続。
* SQL。
* Tkinterウィジェット。
* ダイアログ。
* Repository。
* Service。

---

### 6.10 Repository

Repositoryは、クラスとして実装します。

配置先は、次のとおりです。

```text
src/book_manager/repositories/book_repository.py
```

Repositoryは、次の責務を持ちます。

* SQL実行。
* プレースホルダーへの値の設定。
* SQLite行とモデルの変換。
* CRUD。
* 検索。
* 登録IDの取得。
* 更新件数と削除件数の返却。
* SQLite例外の上位層への通知。

---

### 6.11 Service

Serviceも、クラスとして実装します。

配置先は、次のとおりです。

```text
src/book_manager/services/book_service.py
```

Serviceは、次の責務を持ちます。

* 入力値の検証。
* 入力値の正規化。
* ISBNの検証。
* 重複確認。
* JST日時の生成。
* Repositoryの呼び出し。
* GUIが判断できる処理結果の返却。

ServiceからTkinterダイアログを表示しません。

---

### 6.12 テストフレームワーク

テストにはpytestを使用します。

テストコードは、次の場所へ配置します。

```text
tests/
```

初期段階では、次のテストを優先します。

* データベース接続。
* データベース初期化。
* Repository。
* Service。
* Validators。

GUIの自動テストは、初期実装の必須範囲には含めません。

---

### 6.13 `pyproject.toml`

プロジェクト設定は、`pyproject.toml` へ集約します。

初期段階では、次の設定だけを含めます。

* プロジェクト名。
* プロジェクトVersion。
* 必要なPython Version。
* `src` レイアウトのパッケージ設定。
* pytest設定。

コード整形や静的解析の設定は、実際にツールを導入するときに追加します。

---

### 6.14 初期実装範囲

最初の実装単位は、データベース接続と初期化に限定します。

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

Repository、Service、モデル、GUIは、データベース初期化が完成した後に追加します。

---

## 7. 条件付き承認の条件

Design Freeze前に、次の事項を反映または確定する必要があります。

### 7.1 `PROJECT_ROOT` の意味

#### 現状

`config/paths.py` で `PROJECT_ROOT` を定義する方針ですが、開発時のプロジェクトルートと、配布版のアプリケーションデータ保存先が混同される可能性があります。

#### 採用方針

Version 0.1の開発中は、`PROJECT_ROOT` をリポジトリのルートディレクトリとして扱います。

想定する関係は、次のとおりです。

```text
project_structure.md
book_manager/
├── data/
├── src/
└── pyproject.toml
```

`paths.py` から見た基準は、概念上次のようになります。

```python
Path(__file__).resolve().parents[3]
```

ただし、`parents[3]` のような数値だけを各所へ直接記述しません。

パス計算は `paths.py` 内へ限定します。

配布版では、OSごとのユーザーデータ保存先へ変更する可能性があるため、`PROJECT_ROOT` と利用者データ保存先を将来分離できる構成にします。

#### 判定

Version 0.2へ反映します。

---

### 7.2 接続関数名

#### 現状

`create_connection()` と `get_connection()` の2案が記載されています。

#### 採用方針

接続関数名は、次の名称へ統一します。

```python
create_connection()
```

この関数は、新しいSQLite接続を生成して返すため、`create` が動作を明確に表します。

#### 想定シグネチャ

```python
def create_connection(database_path: Path | str) -> sqlite3.Connection:
    ...
```

データベースパスを引数として受け取れる構成にします。

本番コードでは `DATABASE_PATH` を渡し、テストでは一時データベースパスを渡します。

#### 判定

Version 0.2へ反映します。

---

### 7.3 初期化関数の引数

#### 現状

`initialize_database()` の候補名はありますが、データベースパスを引数で受け取るかが明確ではありません。

#### 採用方針

初期化関数も、データベースパスを引数として受け取ります。

想定シグネチャは、次のとおりです。

```python
def initialize_database(database_path: Path | str) -> None:
    ...
```

これにより、本番用データベースとテスト用データベースを容易に切り替えられます。

関数内で常にグローバルな `DATABASE_PATH` を直接使用する構成にはしません。

`app.py` が本番用パスを渡します。

#### 判定

Version 0.2へ反映します。

---

### 7.4 データディレクトリ作成の責務

#### 現状

`initializer.py` が `data` ディレクトリを作成するとされていますが、テストでは任意のデータベースパスを使用します。

#### 採用方針

`initializer.py` は、渡されたデータベースパスの親ディレクトリを作成します。

```python
database_path.parent.mkdir(parents=True, exist_ok=True)
```

これにより、開発環境の `data` ディレクトリだけに依存しません。

`paths.py` はパスを定義し、`initializer.py` は必要な親ディレクトリを作成します。

#### 判定

Version 0.2へ反映します。

---

### 7.5 SQLite接続のクローズ責務

#### 現状

`connection.py` が接続を生成し、利用側が閉じる方針ですが、責務をさらに明確にする必要があります。

#### 採用方針

`create_connection()` は接続を生成して返します。

接続を取得した呼び出し元が、接続を閉じる責務を持ちます。

初期化処理では、次のように確実に閉じます。

```python
connection = create_connection(database_path)

try:
    ...
finally:
    connection.close()
```

または、接続管理用のコンテキストマネージャーを別途用意する場合は、必要性を確認した後に導入します。

Version 0.1の最初の実装では、独自の接続コンテキストマネージャーは作成しません。

#### 判定

Version 0.2へ反映します。

---

### 7.6 `sqlite3.Row` の設定場所

#### 現状

`sqlite3.Row` を使用する方針は明確ですが、設定場所を確定する必要があります。

#### 採用方針

`connection.py` の `create_connection()` 内で設定します。

```python
connection.row_factory = sqlite3.Row
```

すべてのRepositoryで同じ設定を使用できるようにします。

#### 判定

Version 0.2へ反映します。

---

### 7.7 `PRAGMA user_version` の確認方法

#### 現状

初期化時に `user_version` を確認するとされていますが、Versionが0または1以外の場合の扱いが明確ではありません。

#### 採用方針

Version 0.1の初期化処理では、次のように扱います。

```text
user_version = 0
    未初期化としてテーブルとインデックスを作成する。

user_version = 1
    現行スキーマとしてテーブルとインデックスの存在を確認する。

user_version > 1
    このアプリケーションが対応していない新しいスキーマとしてエラーにする。
```

Version 0.1では、過去Versionからのマイグレーション処理はありません。

`user_version` が負数になることは通常ありませんが、想定外の値はエラーとして扱います。

#### 判定

Version 0.2へ反映します。

---

### 7.8 スキーマ初期化のトランザクション

#### 現状

テーブルとインデックス作成後に `user_version` を設定する方針ですが、トランザクション境界を明確にする必要があります。

#### 採用方針

次の処理を1つのトランザクションとして実行します。

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

`user_version` は、テーブルとインデックスの作成が成功した場合だけ更新します。

#### 判定

Version 0.2へ反映します。

---

### 7.9 スキーマSQLの保持形式

#### 現状

SQLを個別定数として保持する案が記載されています。

#### 採用方針

個別のSQL定数に加え、初期化処理で順番に実行できるタプルを定義します。

例

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

SQLの実行順序を `initializer.py` に重複して記述しないようにします。

ただし、SQL定義と実行処理の責務は分離します。

#### 判定

Version 0.2へ反映します。

---

### 7.10 モデルの日時型

#### 現状

データベースでは日時をTEXTとして保存しますが、`BookItem` モデルで日時を `str` または `datetime` のどちらとして扱うかが未確定です。

#### 採用方針

Version 0.1では、モデルの `created_at` と `updated_at` は文字列として扱います。

```python
created_at: str | None
updated_at: str | None
```

理由は、次のとおりです。

* データベース保存形式と直接対応する。
* 初期実装を単純にできる。
* タイムゾーン変換を複数箇所へ分散させずに済む。
* 画面表示でそのまま利用できる。

日時生成はServiceへ集約します。

将来日時計算が必要になった場合は、`datetime` 型への変換を検討します。

#### 判定

Version 0.2へ反映します。

---

### 7.11 新規登録用モデルと取得済みモデル

#### 現状

新規登録時は `id`、`created_at`、`updated_at` が未設定になる可能性があります。

#### 採用方針

Version 0.1では、モデルを複数種類に分けません。

`BookItem` の該当属性を省略可能とします。

想定例

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

初期段階では、登録用DTOと取得用モデルを分けません。

必要性が発生した場合に分離します。

#### 判定

Version 0.2へ反映します。

---

### 7.12 Repositoryの接続管理方式

#### 現状

Repositoryをクラスとして実装する方針ですが、接続を保持するか、データベースパスを保持するかが未確定です。

#### 採用方針

Repositoryは、長時間使用するSQLite接続を保持しません。

Repositoryは、データベースパスを保持します。

想定構成は、次のとおりです。

```python
class BookRepository:
    def __init__(self, database_path: Path | str) -> None:
        self._database_path = Path(database_path)
```

各Repositoryメソッドは、必要なタイミングで接続を生成し、処理後に閉じます。

理由は、次のとおりです。

* GUIアプリで接続を長時間保持する複雑さを避けられる。
* テスト用データベースを注入しやすい。
* 接続の閉じ忘れをメソッド単位で管理できる。
* Version 0.1の処理件数では性能上の問題が小さい。

将来性能上の問題が確認された場合は、接続管理を見直します。

#### 判定

Version 0.2へ反映します。

---

### 7.13 Serviceの結果表現

#### 現状

不正ISBNや重複時に、GUIが判断できる結果を返す方針ですが、具体的な表現が未確定です。

#### 採用方針

初期段階では、不正ISBNと重複登録の確認処理を、一度に複雑な結果クラスへまとめません。

次のように処理を分けます。

```text
GUIが入力値をServiceへ渡して事前確認する
↓
Serviceが検証結果と重複候補を返す
↓
GUIが確認ダイアログを表示する
↓
利用者が続行した場合は、許可フラグ付きで登録を依頼する
```

専用結果クラスが必要になった場合は、実装前に責務を整理して追加します。

Version 0.1の構成設計では、具体的な結果クラス名までは固定しません。

#### 判定

責務だけをVersion 0.2へ反映します。

---

### 7.14 `validators.py` の責務

#### 現状

正規化関数と検証関数が同じファイルに配置されています。

#### 採用方針

Version 0.1では、`validators.py` へ正規化と検証をまとめます。

初期関数数が少なく、ISBN関連処理と入力検証の関係が近いためです。

ファイルが大きくなった場合は、次の分割を検討します。

```text
services/
├── isbn.py
├── normalizers.py
└── validators.py
```

初期段階では分割しません。

#### 判定

現行案を承認します。

---

### 7.15 `dialogs.py` の扱い

#### 現状

登録、編集、確認、警告などを1ファイルへ配置する案になっています。

#### 採用方針

GUI実装開始時には、まず次の2ファイルを使用します。

```text
ui/
├── main_window.py
└── book_dialog.py
```

単純な確認、警告、エラー表示は、Tkinterの `messagebox` を利用します。

そのため、初期構成では `dialogs.py` を作成しません。

独自ダイアログが複数必要になった場合に、`dialogs` パッケージへの分割を検討します。

#### 判定

Version 0.2で構成を修正します。

---

### 7.16 `app.py` とGUI未実装時の扱い

#### 現状

全体構成には `app.py` と `__main__.py` が含まれていますが、初期実装ではデータベース処理だけを作成します。

#### 採用方針

最初のデータベース初期化実装では、`app.py` と `__main__.py` をまだ作成しません。

GUI実装開始時に追加します。

ただし、最終的な配置と責務は、設計書上で確定しておきます。

空のファイルを将来用として先に作成しません。

#### 判定

Version 0.2へ反映します。

---

### 7.17 `conftest.py` の作成時期

#### 現状

初期テスト構成に `tests/conftest.py` が含まれています。

#### 採用方針

複数テストファイルで共有するfixtureが発生した時点で作成します。

最初から空の `conftest.py` は作成しません。

`test_connection.py` と `test_initializer.py` の両方で同じfixtureを使う場合は、その段階で追加します。

#### 判定

Version 0.2へ反映します。

---

### 7.18 テスト用データベース形式

#### 現状

一時ファイルとインメモリデータベースの両方が候補になっています。

#### 採用方針

初期化処理と接続処理のテストでは、pytestの `tmp_path` を使った一時SQLiteファイルを使用します。

例

```text
tmp_path / "test_book_manager.db"
```

理由は、次のとおりです。

* ディレクトリ作成をテストできる。
* SQLiteファイル作成を確認できる。
* 本番と同じファイル型データベースで確認できる。
* テスト終了後にpytestが一時領域を処理する。

インメモリデータベースは、必要性が確認されたRepository単体テストで検討します。

#### 判定

Version 0.2へ反映します。

---

### 7.19 独自例外の導入時期

#### 現状

独自例外の候補が示されていますが、作成時期は未確定です。

#### 採用方針

データベース初期化の最初の実装では、独自例外を作成しません。

まずSQLiteやファイルシステムの例外を適切に伝播させ、テストで挙動を確認します。

次の条件が発生した場合に独自例外を追加します。

* GUIへ技術的例外を直接渡したくない。
* 複数の下位例外を同じ意味として扱いたい。
* 未対応スキーマVersionを明確に区別したい。
* Serviceで入力検証エラーを統一的に扱いたい。

#### 判定

現行案を承認します。

---

### 7.20 Pythonの必要Version

#### 現状

ユーザーの開発環境はPython 3.12ですが、`pyproject.toml` に設定する最低Versionが未確定です。

#### 採用方針

初期実装では、次を指定します。

```toml
requires-python = ">=3.12"
```

Python 3.12を基準に実装し、古いPython Versionへの互換性対応は行いません。

#### 判定

Version 0.2へ反映します。

---

### 7.21 プロジェクトVersion

#### 現状

`pyproject.toml` に記録するアプリケーションVersionが未確定です。

#### 採用方針

初期実装開始時のVersionは、次のとおりとします。

```text
0.1.0
```

このVersionは、データベーススキーマVersionの `1` とは別に管理します。

```text
アプリケーションVersion : 0.1.0
SQLite user_version      : 1
```

#### 判定

Version 0.2へ反映します。

---

## 8. 指摘事項一覧

| 番号 | 指摘事項                      | 重要度 | 対応                                   |
| -: | ------------------------- | --- | ------------------------------------ |
|  1 | `PROJECT_ROOT` の意味を明確にする。 | 中   | Version 0.2へ反映する。                    |
|  2 | 接続関数名を確定する。               | 軽微  | `create_connection()` に統一する。         |
|  3 | 初期化関数がデータベースパスを受け取る構成にする。 | 高   | Version 0.2へ反映する。                    |
|  4 | 任意パスの親ディレクトリを作成する。        | 中   | Version 0.2へ反映する。                    |
|  5 | 接続を閉じる責務を明確にする。           | 中   | 呼び出し元の責務とする。                         |
|  6 | `sqlite3.Row` の設定場所を確定する。 | 軽微  | `connection.py` で設定する。               |
|  7 | 未対応スキーマVersionの扱いを明確にする。  | 高   | 新しいVersionはエラーとする。                   |
|  8 | スキーマ初期化のトランザクション境界を明確にする。 | 高   | 1トランザクションで処理する。                      |
|  9 | SQL実行順序を定義する。             | 軽微  | `SCHEMA_STATEMENTS` を追加する。           |
| 10 | モデルの日時型を確定する。             | 中   | Version 0.1では文字列とする。                 |
| 11 | 登録用モデルを分離するか確定する。         | 中   | 初期段階では分離しない。                         |
| 12 | Repositoryの接続管理方式を確定する。   | 高   | DBパスを保持し、処理単位で接続する。                  |
| 13 | Serviceの確認結果の責務を整理する。     | 中   | GUIとの2段階処理とする。                       |
| 14 | GUIダイアログの初期構成を簡素化する。      | 中   | `book_dialog.py` と `messagebox` を使う。 |
| 15 | `app.py` の作成時期を明確にする。     | 軽微  | GUI実装時に作成する。                         |
| 16 | 空の `conftest.py` を作成しない。  | 軽微  | 共有fixture発生時に作成する。                   |
| 17 | テスト用DB形式を確定する。            | 中   | `tmp_path` の一時ファイルを使う。               |
| 18 | 独自例外の導入時期を明確にする。          | 軽微  | 必要になった時点で追加する。                       |
| 19 | 必要Python Versionを確定する。    | 中   | Python 3.12以上とする。                    |
| 20 | アプリケーションVersionを確定する。     | 軽微  | 0.1.0とする。                            |

---

## 9. データベース設計との整合性

`project_structure.md` Version 0.1と、Design Freeze済みのデータベース設計との整合性を確認しました。

| 確認項目                        | 結果 |
| --------------------------- | -- |
| SQLiteの使用                   | 一致 |
| Python標準ライブラリ `sqlite3` の使用 | 一致 |
| データベース保存先                   | 一致 |
| `PRAGMA user_version = 1`   | 一致 |
| スキーマ定義の一元管理                 | 一致 |
| SQLite接続の分離                 | 一致 |
| 初期化処理の分離                    | 一致 |
| RepositoryへのSQL集約           | 一致 |
| Serviceでの入力検証               | 一致 |
| GUIとRepositoryの分離           | 一致 |
| バックアップ機能を初期CRUDから除外         | 一致 |
| 書影機能を初期CRUDから除外             | 一致 |
| テスト用DBと本番DBの分離              | 一致 |

重大な矛盾はありません。

---

## 10. Version 0.2へ反映する変更

`project_structure.md` Version 0.2では、次の変更を反映します。

* Statusを `Design Freeze` へ変更する。
* `PROJECT_ROOT` の意味を明確にする。
* `create_connection()` を正式名称とする。
* `create_connection()` がデータベースパスを引数で受け取ることを明記する。
* `initialize_database()` がデータベースパスを引数で受け取ることを明記する。
* 初期化処理がデータベースパスの親ディレクトリを作成することを明記する。
* 接続を閉じる責務を呼び出し元へ置く。
* `sqlite3.Row` を `create_connection()` で設定する。
* `user_version` が0、1、1より大きい場合の扱いを定義する。
* スキーマ初期化を1トランザクションで行う。
* `SCHEMA_STATEMENTS` をスキーマ定義案へ追加する。
* `BookItem` の日時属性を文字列とする。
* 新規登録用と取得用のモデルを分離しない。
* Repositoryはデータベースパスを保持する。
* Repositoryは処理単位で接続を生成して閉じる。
* ServiceとGUIの確認処理を2段階に分ける。
* 初期GUI構成から `dialogs.py` を除外する。
* `ui/book_dialog.py` を採用する。
* 確認、警告、エラーは `messagebox` を基本とする。
* `app.py` と `__main__.py` はGUI実装開始時に作成する。
* 空の `conftest.py` は作成しない。
* 初期テストでは `tmp_path` の一時SQLiteファイルを使用する。
* Python 3.12以上を必要Versionとする。
* アプリケーションVersionを0.1.0とする。

---

## 11. Version 0.2の初期ファイル構成

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

共有fixtureが必要になった場合だけ、次のファイルを追加します。

```text
tests/conftest.py
```

---

## 12. 将来のアプリケーション構成

データベース初期化完了後は、必要な段階で次のファイルを追加します。

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

必要性が確認される前に、空ファイルだけを先行して作成しません。

---

## 13. 初期実装順序

Design Freeze後は、次の順番で実装します。

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

## 14. 実装時の必須事項

初期実装では、次の事項を必須とします。

* Python 3.12以上を使用する。
* 型ヒントを付ける。
* `pathlib.Path` を使用する。
* データベースパスを引数で注入できるようにする。
* テストで本番データベースを使用しない。
* SQLを文字列連結しない。
* スキーマ初期化をトランザクションで行う。
* `user_version` をテーブルとインデックス作成後に設定する。
* 未対応の新しいスキーマVersionを検出する。
* 接続を確実に閉じる。
* 初期化処理を複数回実行可能にする。
* 既存データを削除しない。
* SQLite例外を無条件に握りつぶさない。
* 不要な抽象化を追加しない。
* 空の将来用ファイルを作成しない。

---

## 15. 推奨する最初のコミット単位

### 15.1 プロジェクト設定

```text
chore: Pythonプロジェクト設定を追加
```

対象

```text
pyproject.toml
```

### 15.2 パス管理

```text
feat: データベースパス管理を追加
```

対象

```text
src/book_manager/__init__.py
src/book_manager/config/__init__.py
src/book_manager/config/paths.py
```

### 15.3 SQLite初期化

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

### 15.4 テスト

```text
test: SQLite初期化テストを追加
```

対象

```text
tests/database/test_connection.py
tests/database/test_initializer.py
```

---

## 16. 最終レビュー結果

現時点のレビュー結果は、次のとおりです。

```text
条件付き承認
```

基本構成は妥当であり、初期実装の方針として採用できます。

ただし、Version 0.2へ次の重要事項を反映する必要があります。

* データベースパスの注入。
* Repositoryの接続管理。
* 未対応スキーマVersionの扱い。
* スキーマ初期化のトランザクション。
* 初期GUI構成の簡素化。
* テスト用SQLiteファイルの方針。
* PythonとアプリケーションのVersion。

---

## 17. Design Freeze判定

現時点では、まだDesign Freezeしません。

`project_structure.md` をVersion 0.2へ更新し、本レビューの指摘事項が反映されたことを確認した後に、次の状態へ変更します。

```text
Approved
Design Freeze
```

Version 0.2を、初期実装における正式なプロジェクト構成基準とします。

---

## 18. 次の作業

次の順番で進めます。

```text
project_structure.mdをVersion 0.2へ更新する
↓
レビュー指摘事項の反映を確認する
↓
プロジェクト構成を正式承認する
↓
Design Freezeする
↓
pyproject.tomlを作成する
↓
データベースパス管理を実装する
↓
SQLite接続処理を実装する
↓
SQLite初期化処理を実装する
↓
初期化テストを作成する
