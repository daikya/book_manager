# BookRepository設計レビュー

Version : 0.1
Last Updated : 2026-07-22
Status : Approved

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおける `BookRepository` 設計のレビュー結果と正式承認を記録するものです。

レビュー対象は、次の文書です。

```text
docs/repositories/book_repository_design.md
```

`BookRepository` は、SQLiteの `book_items` テーブルに対する登録、取得、検索、更新および削除を担当するクラスです。

本レビューでは、データベース設計、`BookItem` モデル設計、プロジェクト構成、責務分離、トランザクション管理およびテスト可能性との整合性を確認しました。

---

## 2. レビュー対象

| 文書                          | 対象Version | レビュー前の状態 |
| --------------------------- | --------: | -------- |
| `book_repository_design.md` |       0.1 | Draft    |

---

## 3. レビュー実施日

```text
2026-07-22
```

---

## 4. レビュー観点

本レビューでは、主に次の項目を確認しました。

* Repositoryの責務が明確か。
* `BookItem` モデルとの対応が適切か。
* SQLiteの `book_items` テーブルと整合しているか。
* 公開メソッドの構成が初期CRUDに十分か。
* 戻り値の型と意味が明確か。
* データベース接続の管理方法が適切か。
* トランザクションの境界が明確か。
* SQLインジェクションへの対策が取られているか。
* SQLite行からモデルへの変換方法が適切か。
* Service層との責務境界が明確か。
* GUI処理がRepositoryへ混入していないか。
* 入力検証がRepositoryへ混入していないか。
* 日時生成がRepositoryへ混入していないか。
* 重複データの扱いがデータベース設計と一致しているか。
* 存在しないデータの扱いが一貫しているか。
* テスト可能な構成になっているか。
* 初期Versionとして過剰設計になっていないか。

---

## 5. レビュー結果

レビュー結果は、次のとおりです。

```text
承認
```

`BookRepository` 設計は、初期Versionで必要となるSQLiteのCRUD処理を十分に定義しています。

重大な修正事項はありません。

次の事項を実装時の補足方針として追加し、Version 0.1をDesign Freezeとします。

* `add()` が返すモデルは、`dataclasses.replace()` を使用して生成する。
* `add()` は、引数として受け取った `BookItem` を変更しない。
* `update()` と `delete()` の戻り値は、SQL実行後の `cursor.rowcount` に基づいて判定する。
* 読み取り処理でも、接続は必ず `finally` で閉じる。
* Repositoryのテストでは、各テストで独立した一時データベースを使用する。

---

## 6. 承認事項

### 6.1 クラス名

クラス名を次の名称とする設計を承認します。

```python
BookRepository
```

`BookItem` の永続化処理を担当することが明確な名称です。

---

### 6.2 配置場所

実装ファイルを次の場所へ配置する設計を承認します。

```text
src/book_manager/repositories/book_repository.py
```

パッケージ構成は次のとおりです。

```text
src/
└── book_manager/
    └── repositories/
        ├── __init__.py
        └── book_repository.py
```

プロジェクト構成設計と一致しています。

---

### 6.3 データベースパスの受け取り

コンストラクターでデータベースパスを受け取る設計を承認します。

```python
def __init__(
    self,
    database_path: Path | str,
) -> None:
    self._database_path = Path(database_path)
```

`Path` と文字列の両方を受け取り、内部では `Path` に統一します。

これにより、実環境のデータベースとpytestの一時データベースを同じRepository実装で扱えます。

---

### 6.4 コンストラクターで接続しない方針

データベース接続をコンストラクターで作成しない設計を承認します。

接続は各公開メソッドの実行時に作成します。

この構成には次の利点があります。

* 接続期間をメソッド内へ限定できる。
* 接続の閉じ忘れを防ぎやすい。
* 長時間保持されるRepositoryでも接続が残らない。
* GUIのライフサイクルとSQLite接続を分離できる。
* テストごとに独立したデータベースを使用しやすい。

---

## 7. 公開メソッド

初期Versionでは、次の公開メソッドを実装する設計を承認します。

```python
def add(self, book_item: BookItem) -> BookItem:
    ...

def get_by_id(self, book_id: int) -> BookItem | None:
    ...

def get_all(self) -> list[BookItem]:
    ...

def search_by_title(self, keyword: str) -> list[BookItem]:
    ...

def find_by_isbn(self, isbn: str) -> list[BookItem]:
    ...

def find_by_magazine_code(
    self,
    magazine_code: str,
) -> list[BookItem]:
    ...

def update(self, book_item: BookItem) -> bool:
    ...

def delete(self, book_id: int) -> bool:
    ...
```

登録、単一取得、一覧取得、検索、更新および削除を網羅しており、初期CRUDとして適切です。

---

## 8. `add()` のレビュー

### 8.1 役割

`add()` が、新しい `BookItem` をSQLiteへ登録する設計を承認します。

```python
def add(
    self,
    book_item: BookItem,
) -> BookItem:
    ...
```

---

### 8.2 登録対象

次のカラムを登録対象とする設計を承認します。

```text
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

`id` はSQLiteが自動採番するため、INSERT対象には含めません。

---

### 8.3 戻り値

SQLiteが採番したIDを設定した、新しい `BookItem` を返す設計を承認します。

```python
registered_book = repository.add(book_item)
```

登録後は、次の状態となります。

```python
registered_book.id is not None
```

---

### 8.4 入力モデルを変更しない方針

`add()` は、引数として受け取った `BookItem` を直接変更しない設計を承認します。

登録前のモデルは、次の状態を保持します。

```python
book_item.id is None
```

登録後のIDを持つモデルは、別のインスタンスとして返します。

実装時には、Python標準ライブラリの `dataclasses.replace()` を使用します。

```python
from dataclasses import replace

return replace(
    book_item,
    id=cursor.lastrowid,
)
```

この方法には次の利点があります。

* 全属性を手作業で再指定する必要がない。
* 将来属性が追加された場合の記載漏れを防ぎやすい。
* 入力オブジェクトを変更しない方針が明確になる。
* `BookItem` の現在の値をそのまま保持できる。

---

### 8.5 `lastrowid`

採番されたIDを次から取得する設計を承認します。

```python
cursor.lastrowid
```

SQLiteの自動採番IDを取得する方法として適切です。

実装では、`lastrowid` が `None` ではないことを前提とします。

`book_items.id` は `INTEGER PRIMARY KEY AUTOINCREMENT` であるため、正常なINSERT後には整数値が得られます。

---

### 8.6 SQL

次のINSERT文を使用する設計を承認します。

```sql
INSERT INTO book_items (
    isbn,
    magazine_code,
    title,
    author,
    publisher,
    publication_format,
    description,
    completion_month,
    notes,
    created_at,
    updated_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

すべての値をプレースホルダーで渡しており、適切です。

---

### 8.7 例外

SQLiteから発生した例外を、初期Versionでは独自例外へ変換せず、そのまま伝播させる設計を承認します。

想定される例外には次があります。

```text
sqlite3.IntegrityError
sqlite3.OperationalError
sqlite3.DatabaseError
```

初期Versionで独自例外階層を導入しない方針は、過剰設計を避ける観点から妥当です。

---

## 9. `get_by_id()` のレビュー

IDを指定して1件の書籍を取得する設計を承認します。

```python
def get_by_id(
    self,
    book_id: int,
) -> BookItem | None:
    ...
```

該当する書籍が存在する場合は `BookItem` を返します。

該当するIDが存在しない場合は `None` を返します。

存在しないデータを通常の検索結果として扱い、例外を送出しない設計は適切です。

SQLは次の形式とします。

```sql
SELECT
    id,
    isbn,
    magazine_code,
    title,
    author,
    publisher,
    publication_format,
    description,
    completion_month,
    notes,
    created_at,
    updated_at
FROM book_items
WHERE id = ?
```

主キー検索のため、取得には `fetchone()` を使用します。

---

## 10. `get_all()` のレビュー

登録済みのすべての書籍を取得する設計を承認します。

```python
def get_all(self) -> list[BookItem]:
    ...
```

データが存在しない場合は、`None` ではなく空のリストを返します。

```python
[]
```

呼び出し側が常にリストとして扱えるため、適切です。

---

### 10.1 並び順

初期Versionでは、IDの降順で取得する設計を承認します。

```sql
ORDER BY id DESC
```

新しく登録した書籍が先頭に表示されるため、初期GUIの一覧表示に適しています。

---

## 11. `search_by_title()` のレビュー

書籍名を部分一致で検索する設計を承認します。

```python
def search_by_title(
    self,
    keyword: str,
) -> list[BookItem]:
    ...
```

検索条件には、次の値を使用します。

```python
f"%{keyword}%"
```

SQLは次の形式とします。

```sql
WHERE title LIKE ?
ORDER BY id DESC
```

検索語をSQL文字列へ直接埋め込まず、プレースホルダーとして渡す構成を承認します。

---

### 11.1 空文字列

Repository単体では、空文字列を拒否しない設計を承認します。

空文字列が渡された場合は、実質的に全件検索となる可能性があります。

これを利用者操作として許可するかどうかは、Service層で判断します。

Repositoryが入力ルールを持たないことで、責務が明確に保たれます。

---

### 11.2 検索方式

初期Versionでは、SQLite標準の `LIKE` を使用します。

次の機能は導入しません。

```text
全文検索
正規表現検索
類似度検索
独自照合順序
```

日本語の書籍名を対象とした初期の部分一致検索として十分です。

---

## 12. `find_by_isbn()` のレビュー

ISBNの完全一致検索を行う設計を承認します。

```python
def find_by_isbn(
    self,
    isbn: str,
) -> list[BookItem]:
    ...
```

ISBNに一意制約を設定していないため、戻り値を単一の `BookItem` ではなく、リストとする設計は適切です。

```python
list[BookItem]
```

同じISBNを持つ複数の書籍が登録されている場合も、すべて取得します。

重複登録を許可するかどうかの判断は、Service層およびGUI層が担当します。

---

## 13. `find_by_magazine_code()` のレビュー

雑誌コードの完全一致検索を行う設計を承認します。

```python
def find_by_magazine_code(
    self,
    magazine_code: str,
) -> list[BookItem]:
    ...
```

雑誌コードにも一意制約を設けていないため、戻り値を `list[BookItem]` とする設計は妥当です。

---

## 14. `update()` のレビュー

### 14.1 役割

既存の書籍情報を更新する設計を承認します。

```python
def update(
    self,
    book_item: BookItem,
) -> bool:
    ...
```

---

### 14.2 ID必須条件

更新対象を識別するため、`book_item.id` が必要です。

`id` が `None` の場合に、次の `ValueError` を送出する設計を承認します。

```python
if book_item.id is None:
    raise ValueError(
        "更新対象のBookItemにはidが必要です。"
    )
```

これは書籍情報の妥当性検証ではなく、Repositoryメソッドの呼び出し条件を確認するための防御的処理です。

---

### 14.3 更新対象

次のカラムを更新する設計を承認します。

```text
isbn
magazine_code
title
author
publisher
publication_format
description
completion_month
notes
updated_at
```

次のカラムは更新しません。

```text
id
created_at
```

主キーと作成日時を変更しない設計は適切です。

---

### 14.4 戻り値

更新対象が存在した場合は `True`、存在しなかった場合は `False` を返します。

```python
return cursor.rowcount > 0
```

Service層はこの戻り値を使用して、更新対象が存在したかを判断できます。

---

### 14.5 値が同じ場合の注意

SQLiteの更新件数の扱いは、SQLおよびSQLiteの動作条件に依存します。

初期Versionでは、`cursor.rowcount` をRepositoryの更新成否判定に使用します。

ここでの `True` は、更新対象のSQL処理が1件以上に作用したことを表します。

「更新前と更新後の値が実質的に変化したかどうか」を判定する機能は、初期Versionでは設けません。

---

## 15. `delete()` のレビュー

IDを指定して書籍を削除する設計を承認します。

```python
def delete(
    self,
    book_id: int,
) -> bool:
    ...
```

削除対象が存在した場合は `True` を返します。

存在しない場合は `False` を返します。

```python
return cursor.rowcount > 0
```

存在しないIDの削除を例外としない設計は、`get_by_id()` や `update()` の結果方針とも整合しています。

---

## 16. SQLite行からの変換

SQLiteの `sqlite3.Row` を `BookItem` へ変換する処理を、非公開の静的メソッドへ集約する設計を承認します。

```python
@staticmethod
def _row_to_book_item(
    row: sqlite3.Row,
) -> BookItem:
    ...
```

想定実装は次のとおりです。

```python
return BookItem(
    id=row["id"],
    isbn=row["isbn"],
    magazine_code=row["magazine_code"],
    title=row["title"],
    author=row["author"],
    publisher=row["publisher"],
    publication_format=row["publication_format"],
    description=row["description"],
    completion_month=row["completion_month"],
    notes=row["notes"],
    created_at=row["created_at"],
    updated_at=row["updated_at"],
)
```

キーワード引数を使用することで、SQLiteのカラム順やdataclassの属性定義順への依存を避けられます。

---

## 17. `sqlite3.Row` の前提

`BookRepository` は、既存の接続生成関数を使用します。

```python
from book_manager.database.connection import create_connection
```

`create_connection()` では次が設定されています。

```python
connection.row_factory = sqlite3.Row
```

したがって、Repositoryは次の形式でカラム名を使用できます。

```python
row["title"]
```

データベース接続設計との整合性に問題はありません。

---

## 18. 接続管理

各公開メソッドで接続を作成し、必ず閉じる設計を承認します。

基本構造は次のとおりです。

```python
connection = create_connection(
    self._database_path,
)

try:
    ...
finally:
    connection.close()
```

SELECT処理、INSERT処理、UPDATE処理およびDELETE処理のすべてで、同じ接続管理方針を使用します。

---

## 19. トランザクション管理

登録、更新および削除では、次の形式を使用する設計を承認します。

```python
with connection:
    cursor = connection.execute(...)
```

正常終了時にはコミットされ、例外発生時にはロールバックされます。

ただし、`with connection:` は接続自体を閉じません。

そのため、外側の `finally` で `connection.close()` を実行する必要があります。

---

## 20. SELECT文の列指定

SELECT文で `SELECT *` を使用しない設計を承認します。

取得対象のカラムを明示することで、次の利点があります。

* Repositoryが必要とするカラムが明確になる。
* テーブル変更時の影響を確認しやすい。
* カラム順への依存を避けられる。
* 不要なカラム取得を防ぎやすい。
* コードレビューが容易になる。

---

## 21. 共通カラム定数

取得カラムの一覧を、モジュール定数として共通化する設計を承認します。

```python
BOOK_ITEM_COLUMNS = """
    id,
    isbn,
    magazine_code,
    title,
    author,
    publisher,
    publication_format,
    description,
    completion_month,
    notes,
    created_at,
    updated_at
"""
```

各SELECT文では、固定された開発者管理文字列として使用します。

```python
query = f"""
    SELECT
        {BOOK_ITEM_COLUMNS}
    FROM book_items
    WHERE id = ?
"""
```

`BOOK_ITEM_COLUMNS` に利用者入力は含まれないため、この使用方法はSQLインジェクションの原因にはなりません。

検索値やIDは、引き続きプレースホルダーで渡します。

---

## 22. SQLの配置

初期Versionでは、SQLを `book_repository.py` 内に記述する設計を承認します。

SQLファイルを別ディレクトリへ分離しません。

対象となるSQLが小規模なCRUDであり、PythonコードとSQLを同じ場所で確認できる方が理解しやすいためです。

将来SQLが大規模化した場合に、外部ファイル化を再検討します。

---

## 23. 並び順

次の複数取得メソッドで、ID降順を使用する設計を承認します。

```text
get_all
search_by_title
find_by_isbn
find_by_magazine_code
```

SQLは次の形式です。

```sql
ORDER BY id DESC
```

すべてのメソッドで並び順が統一されており、呼び出し側で扱いやすい構成です。

---

## 24. 重複データ

ISBNおよび雑誌コードの重複を、Repositoryでは拒否しない設計を承認します。

データベースにも一意制約は設定しません。

Repositoryは、次の検索メソッドによって重複候補を返します。

```python
find_by_isbn()
find_by_magazine_code()
```

重複候補が存在する場合の最終的な登録判断は、Service層とGUI層が担当します。

---

## 25. 責務分離

### 25.1 Repositoryの責務

`BookRepository` は、次の処理を担当します。

```text
SQLite接続の作成と終了
SQLの実行
トランザクション管理
BookItemの登録
BookItemの取得
BookItemの検索
BookItemの更新
BookItemの削除
sqlite3.RowからBookItemへの変換
自動採番されたIDの取得
```

---

### 25.2 Repositoryに含めない責務

次の処理をRepositoryへ含めない設計を承認します。

```text
titleの必須検証
前後空白の除去
空文字列からNoneへの変換
ISBNの正規化
ISBNの形式検証
ISBNのチェックデジット検証
雑誌コードの形式検証
読了年月の形式検証
著者名の正規化
日時の生成
重複登録を許可するかどうかの判断
利用者への確認
GUIダイアログの表示
外部APIの呼び出し
データベース初期化
スキーマVersion管理
バックアップ処理
```

---

### 25.3 Serviceの責務

Service層は、Repositoryを呼び出す前に次の処理を担当します。

```text
入力値の正規化
必須項目の検証
ISBNの検証
雑誌コードの検証
読了年月の検証
重複候補の確認
created_atの生成
updated_atの生成
Repositoryの戻り値の解釈
GUIへ返す結果の整理
```

---

### 25.4 依存方向

正式な依存方向は、次のとおりです。

```text
GUI
↓
BookService
↓
BookRepository
↓
database.connection
↓
SQLite
```

RepositoryからServiceまたはGUIを呼び出してはいけません。

---

## 26. データベース設計との整合性

`BookRepository` が扱うカラムと、`book_items` テーブルの整合性を確認しました。

| Repositoryで扱う属性      | SQLiteカラム            | 整合性 |
| -------------------- | -------------------- | --- |
| `id`                 | `id`                 | 一致  |
| `isbn`               | `isbn`               | 一致  |
| `magazine_code`      | `magazine_code`      | 一致  |
| `title`              | `title`              | 一致  |
| `author`             | `author`             | 一致  |
| `publisher`          | `publisher`          | 一致  |
| `publication_format` | `publication_format` | 一致  |
| `description`        | `description`        | 一致  |
| `completion_month`   | `completion_month`   | 一致  |
| `notes`              | `notes`              | 一致  |
| `created_at`         | `created_at`         | 一致  |
| `updated_at`         | `updated_at`         | 一致  |

重大な不整合はありません。

---

## 27. `BookItem` 設計との整合性

`BookItem` モデル設計との整合性を確認しました。

| 確認項目                         | 結果 |
| ---------------------------- | -- |
| Repositoryが `BookItem` を受け取る | 一致 |
| Repositoryが `BookItem` を返す   | 一致 |
| 新規登録前の `id` が `None`         | 一致 |
| 登録後の `id` が整数                | 一致 |
| SQLite変換をRepositoryが担当する     | 一致 |
| モデルに保存メソッドを持たせない             | 一致 |
| モデルに検証処理を持たせない               | 一致 |
| モデルに日時生成処理を持たせない             | 一致 |
| 登録用モデルと取得用モデルを分けない           | 一致 |

重大な不整合はありません。

---

## 28. プロジェクト構成との整合性

`project_structure.md` Version 0.2との整合性を確認しました。

| 確認項目                             | 結果 |
| -------------------------------- | -- |
| Repositoryを `repositories` へ配置する | 一致 |
| SQLをRepositoryへ集約する              | 一致 |
| ModelとRepositoryを分離する            | 一致 |
| ServiceからRepositoryを呼び出す         | 一致 |
| GUIからSQLiteへ直接アクセスしない            | 一致 |
| ORMを使用しない                        | 一致 |
| 初期Versionで過剰な抽象化をしない             | 一致 |

重大な不整合はありません。

---

## 29. テスト方針

Repositoryテストでは、モックではなく実際のSQLiteデータベースを使用する設計を承認します。

pytestの `tmp_path` を使用し、各テストで独立したデータベースを作成します。

基本構造は次のとおりです。

```python
def test_example(tmp_path: Path) -> None:
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    repository = BookRepository(database_path)
```

この方式により、次をまとめて確認できます。

* SQL構文。
* テーブル名。
* カラム名。
* プレースホルダー数。
* SQLiteの型変換。
* コミット処理。
* ロールバック処理。
* `sqlite3.Row` からの変換。
* 実際のCRUD動作。

---

## 30. 承認するテスト項目

### 30.1 コンストラクター

* `Path` を受け取れる。
* 文字列パスを受け取れる。

### 30.2 登録

* 書籍を登録できる。
* 登録後のモデルにIDが設定される。
* 登録した値を取得できる。
* 任意項目が `None` でも登録できる。
* 入力モデルのIDが変更されない。
* 登録結果が入力モデルとは別インスタンスになる。

### 30.3 ID取得

* 存在するIDから取得できる。
* 戻り値が `BookItem` になる。
* すべての属性が復元される。
* 存在しないIDでは `None` を返す。

### 30.4 一覧取得

* 複数件を取得できる。
* ID降順で返る。
* データが存在しない場合に空のリストを返す。

### 30.5 書籍名検索

* 完全一致する書籍を取得できる。
* 部分一致する書籍を取得できる。
* 日本語を検索できる。
* 複数件を取得できる。
* 該当しない場合に空のリストを返す。

### 30.6 ISBN検索

* 完全一致する書籍を取得できる。
* 同じISBNを持つ複数件を取得できる。
* ID降順で返る。
* 該当しない場合に空のリストを返す。

### 30.7 雑誌コード検索

* 完全一致する書籍を取得できる。
* 同じ雑誌コードを持つ複数件を取得できる。
* ID降順で返る。
* 該当しない場合に空のリストを返す。

### 30.8 更新

* 既存書籍を更新できる。
* 更新後の値を取得できる。
* `created_at` が変更されない。
* `updated_at` が更新される。
* 存在しないIDでは `False` を返す。
* `id=None` では `ValueError` を送出する。

### 30.9 削除

* 既存書籍を削除できる。
* 削除後は取得できない。
* 削除後の一覧に含まれない。
* 存在しないIDでは `False` を返す。

---

## 31. テスト用fixtureの推奨

Repositoryテストでは、テストコードの重複を抑えるため、pytest fixtureの使用を推奨します。

データベースパスとRepositoryを作成するfixtureの例は、次のとおりです。

```python
@pytest.fixture
def repository(
    tmp_path: Path,
) -> BookRepository:
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    return BookRepository(database_path)
```

登録用の `BookItem` を作成する補助関数も使用できます。

```python
def create_book_item(
    *,
    title: str = "吾輩は猫である",
    isbn: str | None = "9784101010014",
    created_at: str = "2026-07-22 10:00:00",
    updated_at: str = "2026-07-22 10:00:00",
) -> BookItem:
    return BookItem(
        title=title,
        isbn=isbn,
        created_at=created_at,
        updated_at=updated_at,
    )
```

補助関数はテスト専用とし、製品コードへ追加しません。

---

## 32. 実装時の注意事項

### 32.1 接続を必ず閉じる

SELECT処理を含むすべてのメソッドで、接続を `finally` で閉じます。

```python
connection = create_connection(
    self._database_path,
)

try:
    ...
finally:
    connection.close()
```

---

### 32.2 更新・削除ではトランザクションを使用する

INSERT、UPDATEおよびDELETEでは、次を使用します。

```python
with connection:
    cursor = connection.execute(...)
```

例外発生時に、中途半端な状態を残さないようにします。

---

### 32.3 利用者入力をSQLへ直接埋め込まない

次のようなSQL文字列生成は禁止します。

```python
query = f"""
    SELECT *
    FROM book_items
    WHERE title LIKE '%{keyword}%'
"""
```

正式な実装では、プレースホルダーを使用します。

```python
connection.execute(
    query,
    (f"%{keyword}%",),
)
```

---

### 32.4 カラム順に依存しない

`BookItem` の生成には、位置引数ではなくキーワード引数を使用します。

次のような生成は行いません。

```python
BookItem(*row)
```

正式には、カラム名を明示します。

```python
BookItem(
    id=row["id"],
    title=row["title"],
    ...
)
```

---

### 32.5 Repositoryで値を正規化しない

Repository内で次のような処理は行いません。

```python
title = book_item.title.strip()
isbn = book_item.isbn.replace("-", "")
```

正規化済みの値をRepositoryへ渡す責任は、Service層にあります。

---

### 32.6 Repositoryで日時を生成しない

Repository内で次のような処理は行いません。

```python
datetime.now()
```

`created_at` と `updated_at` は、Service層が設定した値を保存します。

---

## 33. 初期Versionで導入しないもの

次の機能は、初期Versionでは導入しません。

```text
Repositoryの抽象基底クラス
RepositoryのProtocol
Unit of Work
ORM
非同期SQLiteアクセス
接続プール
依存性注入フレームワーク
独自例外階層
ページング
動的な並び替え
複合条件検索
全文検索
論理削除
更新履歴
楽観的ロック
排他制御
バッチ登録
バッチ更新
バッチ削除
SQLの外部ファイル化
```

必要性が確認された段階で、設計変更として検討します。

---

## 34. 正式な実装構成

Design Freeze後は、次のファイルを作成します。

```text
src/book_manager/repositories/__init__.py
src/book_manager/repositories/book_repository.py
tests/repositories/test_book_repository.py
```

---

## 35. 実装予定コード構成

正式なコード構成は、次のとおりです。

```python
"""Repository for book items."""

import sqlite3
from dataclasses import replace
from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.models.book_item import BookItem


BOOK_ITEM_COLUMNS = """
    id,
    isbn,
    magazine_code,
    title,
    author,
    publisher,
    publication_format,
    description,
    completion_month,
    notes,
    created_at,
    updated_at
"""


class BookRepository:
    """book_itemsテーブルの永続化処理を担当する。"""

    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        self._database_path = Path(database_path)

    def add(
        self,
        book_item: BookItem,
    ) -> BookItem:
        ...

    def get_by_id(
        self,
        book_id: int,
    ) -> BookItem | None:
        ...

    def get_all(
        self,
    ) -> list[BookItem]:
        ...

    def search_by_title(
        self,
        keyword: str,
    ) -> list[BookItem]:
        ...

    def find_by_isbn(
        self,
        isbn: str,
    ) -> list[BookItem]:
        ...

    def find_by_magazine_code(
        self,
        magazine_code: str,
    ) -> list[BookItem]:
        ...

    def update(
        self,
        book_item: BookItem,
    ) -> bool:
        ...

    def delete(
        self,
        book_id: int,
    ) -> bool:
        ...

    @staticmethod
    def _row_to_book_item(
        row: sqlite3.Row,
    ) -> BookItem:
        ...
```

---

## 36. 実装順序

正式な実装順序は、次のとおりです。

```text
repositoriesディレクトリを作成する
↓
repositories/__init__.pyを作成する
↓
repositories/book_repository.pyを作成する
↓
BookRepositoryのCRUDを実装する
↓
tests/repositoriesディレクトリを作成する
↓
tests/repositories/test_book_repository.pyを作成する
↓
Repositoryテストを実行する
↓
データベース関連を含む全テストを実行する
↓
実装内容をレビューする
↓
コミットする
```

---

## 37. コミット単位

Repository実装とRepositoryテストは、次の2コミットに分けます。

### 37.1 Repository実装

```text
feat: BookRepositoryを追加
```

対象ファイル：

```text
src/book_manager/repositories/__init__.py
src/book_manager/repositories/book_repository.py
```

### 37.2 Repositoryテスト

```text
test: BookRepositoryテストを追加
```

対象ファイル：

```text
tests/repositories/test_book_repository.py
```

設計書とレビュー文書は、実装とは別のドキュメントコミットとして管理します。

---

## 38. Design Freeze判定

`BookRepository` 設計Version 0.1を、初期実装におけるDesign Freeze版として承認します。

```text
Approved
Design Freeze
```

正式な設計基準は、次のとおりです。

```text
book_repository_design.md        : Version 0.1
book_repository_design_review.md : Version 0.1
class                            : BookRepository
database                         : SQLite
model                            : BookItem
connection lifecycle             : メソッド単位
default order                    : id DESC
application version              : 0.1.0
Python                           : 3.12以上
```

Design Freeze後に公開メソッド、戻り値、SQL、検索方式または責務を変更する場合は、次の手順を行います。

```text
変更理由を整理する
↓
データベース設計への影響を確認する
↓
BookItemモデルへの影響を確認する
↓
Service層への影響を確認する
↓
book_repository_design.mdを更新する
↓
関連設計書を更新する
↓
レビューする
↓
文書Versionを更新する
↓
実装とテストを変更する
```

---

## 39. 次の作業

Design Freeze後は、次の順序で進めます。

```text
src/book_manager/repositories/__init__.pyを作成する
↓
src/book_manager/repositories/book_repository.pyを実装する
↓
tests/repositories/test_book_repository.pyを作成する
↓
Repositoryテストを実行する
↓
全テストを実行する
↓
BookServiceとvalidatorsの設計へ進む
```
