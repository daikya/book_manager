# BookRepository設計

Version : 0.1
Last Updated : 2026-07-21
Status : Draft

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおける `BookRepository` の設計を定義するものです。

`BookRepository` は、SQLiteの `book_items` テーブルに対するデータ操作を担当します。

主な責務は、次のとおりです。

* 書籍情報の登録。
* IDによる取得。
* 一覧取得。
* 書籍名による部分一致検索。
* ISBNによる検索。
* 雑誌コードによる検索。
* 書籍情報の更新。
* 書籍情報の削除。
* SQLiteの行から `BookItem` への変換。

---

## 2. 配置場所

実装ファイルは、次の場所へ配置します。

```text
src/book_manager/repositories/book_repository.py
```

パッケージ構成は、次のとおりです。

```text
src/
└── book_manager/
    └── repositories/
        ├── __init__.py
        └── book_repository.py
```

テストファイルは、次の場所へ配置します。

```text
tests/repositories/test_book_repository.py
```

---

## 3. クラス名

正式なクラス名は、次のとおりです。

```python
BookRepository
```

`book_items` テーブルに対する永続化処理を集約するクラスとします。

---

## 4. 基本方針

初期Versionでは、次の方針を採用します。

* ORMは使用しない。
* SQLはRepository内に記述する。
* RepositoryはSQLiteへ直接アクセスする。
* Repositoryは入力値の妥当性検証を行わない。
* Repositoryは日時を生成しない。
* RepositoryはGUI処理を行わない。
* Repositoryは外部APIを呼び出さない。
* Repositoryはデータベース接続をメソッドごとに作成する。
* 各メソッド内で接続を確実に閉じる。
* SQLパラメーターにはプレースホルダーを使用する。
* `sqlite3.Row` から `BookItem` への変換処理をRepositoryへ集約する。
* 存在しないIDの取得結果は `None` とする。
* 更新・削除の成否は `bool` で返す。
* 検索結果は `list[BookItem]` で返す。

---

## 5. コンストラクター

`BookRepository` は、データベースファイルのパスを受け取ります。

```python
class BookRepository:
    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        ...
```

保持する属性は、次のとおりです。

```python
self._database_path = Path(database_path)
```

データベース接続自体は、コンストラクターでは作成しません。

理由は、次のとおりです。

* 接続の閉じ忘れを避けやすい。
* メソッド単位で接続期間を明確にできる。
* Repositoryインスタンスを長時間保持できる。
* テストで一時データベースを扱いやすい。
* GUIのライフサイクルと接続ライフサイクルを分離できる。

---

## 6. 公開メソッド一覧

`BookRepository` の公開メソッドは、次のとおりです。

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

---

## 7. `add`

### 7.1 目的

新しい書籍情報を `book_items` テーブルへ登録します。

```python
def add(self, book_item: BookItem) -> BookItem:
    ...
```

### 7.2 引数

```python
book_item: BookItem
```

登録前の `BookItem` を受け取ります。

Service層で、少なくとも次の項目が設定済みであることを前提とします。

```text
title
created_at
updated_at
```

Repositoryでは、これらの値が妥当かどうかを検証しません。

### 7.3 登録対象

登録対象のカラムは、次のとおりです。

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

`id` はSQLiteが自動採番するため、INSERT文には含めません。

### 7.4 戻り値

登録後の `BookItem` を返します。

返されるモデルには、SQLiteが採番した `id` が設定されます。

```python
registered_book = repository.add(book_item)

assert registered_book.id is not None
```

初期Versionでは、引数として受け取ったオブジェクトを直接変更せず、新しい `BookItem` を返します。

これにより、Repository呼び出し前後の状態を明確にします。

### 7.5 SQL

想定するSQLは、次のとおりです。

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

採番されたIDは、次から取得します。

```python
cursor.lastrowid
```

### 7.6 エラー

SQLiteの制約違反やI/Oエラーは、Repository内で独自例外へ変換せず、そのまま呼び出し元へ伝播させます。

初期Versionでは、次のような独自例外は導入しません。

```text
RepositoryError
BookInsertError
DatabaseOperationError
```

---

## 8. `get_by_id`

### 8.1 目的

IDを指定して、1件の書籍情報を取得します。

```python
def get_by_id(self, book_id: int) -> BookItem | None:
    ...
```

### 8.2 SQL

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

### 8.3 戻り値

該当する書籍が存在する場合は、`BookItem` を返します。

存在しない場合は、`None` を返します。

```python
book_item = repository.get_by_id(999)

assert book_item is None
```

存在しないことを例外とは扱いません。

---

## 9. `get_all`

### 9.1 目的

登録済みの書籍情報をすべて取得します。

```python
def get_all(self) -> list[BookItem]:
    ...
```

### 9.2 並び順

初期Versionでは、IDの降順で返します。

```sql
ORDER BY id DESC
```

新しく登録した書籍が先頭に表示される構成です。

### 9.3 戻り値

書籍が存在する場合は、`BookItem` のリストを返します。

登録済みの書籍がない場合は、空のリストを返します。

```python
[]
```

`None` は返しません。

---

## 10. `search_by_title`

### 10.1 目的

書籍名の部分一致検索を行います。

```python
def search_by_title(
    self,
    keyword: str,
) -> list[BookItem]:
    ...
```

### 10.2 SQL

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
WHERE title LIKE ?
ORDER BY id DESC
```

検索値は、次の形式で渡します。

```python
f"%{keyword}%"
```

SQL文字列へ直接埋め込まず、プレースホルダーを使用します。

### 10.3 空文字列

Repository単体では、空文字列を拒否しません。

空文字列が渡された場合、検索条件は次のようになります。

```text
%%
```

結果として、すべての書籍が返る可能性があります。

空文字列を許可するかどうかは、Service層で判断します。

### 10.4 大文字・小文字

SQLiteの標準的な `LIKE` の挙動を使用します。

日本語の検索を主対象とするため、初期Versionでは独自の照合順序や全文検索を導入しません。

### 10.5 戻り値

該当する書籍を `list[BookItem]` で返します。

該当しない場合は、空のリストを返します。

---

## 11. `find_by_isbn`

### 11.1 目的

ISBNが一致する書籍を検索します。

```python
def find_by_isbn(
    self,
    isbn: str,
) -> list[BookItem]:
    ...
```

### 11.2 SQL

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
WHERE isbn = ?
ORDER BY id DESC
```

### 11.3 戻り値

検索結果は、`list[BookItem]` で返します。

ISBNに一意制約を設けていないため、複数件返る可能性があります。

初期Versionでは、重複登録をデータベース制約で禁止しません。

重複候補の判断は、Service層が行います。

### 11.4 `None` の扱い

公開メソッドの引数は `str` とします。

`None` を検索する用途は、初期Versionでは設けません。

---

## 12. `find_by_magazine_code`

### 12.1 目的

雑誌コードが一致する書籍を検索します。

```python
def find_by_magazine_code(
    self,
    magazine_code: str,
) -> list[BookItem]:
    ...
```

### 12.2 SQL

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
WHERE magazine_code = ?
ORDER BY id DESC
```

### 12.3 戻り値

検索結果は、`list[BookItem]` で返します。

雑誌コードにも一意制約を設けていないため、複数件返る可能性があります。

---

## 13. `update`

### 13.1 目的

既存の書籍情報を更新します。

```python
def update(
    self,
    book_item: BookItem,
) -> bool:
    ...
```

### 13.2 前提条件

`book_item.id` が設定されていることを前提とします。

ただし、Repositoryでは、`id` が `None` の場合にSQLiteへ処理を委ねず、`ValueError` を送出します。

```python
if book_item.id is None:
    raise ValueError(
        "更新対象のBookItemにはidが必要です。"
    )
```

この確認は業務上の入力検証ではなく、Repositoryの呼び出し条件を守るための防御的処理です。

### 13.3 更新対象

更新するカラムは、次のとおりです。

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

`id` はレコード識別子であり、`created_at` は作成日時のためです。

### 13.4 SQL

```sql
UPDATE book_items
SET
    isbn = ?,
    magazine_code = ?,
    title = ?,
    author = ?,
    publisher = ?,
    publication_format = ?,
    description = ?,
    completion_month = ?,
    notes = ?,
    updated_at = ?
WHERE id = ?
```

### 13.5 戻り値

更新対象が存在し、1件以上更新された場合は `True` を返します。

該当するIDが存在しない場合は `False` を返します。

判定には、次を使用します。

```python
cursor.rowcount
```

### 13.6 更新後モデル

初期Versionでは、更新後のモデルを戻り値として返しません。

Service層が必要に応じて `get_by_id()` を呼び出します。

---

## 14. `delete`

### 14.1 目的

IDを指定して書籍情報を削除します。

```python
def delete(
    self,
    book_id: int,
) -> bool:
    ...
```

### 14.2 SQL

```sql
DELETE FROM book_items
WHERE id = ?
```

### 14.3 戻り値

削除対象が存在した場合は `True` を返します。

対象が存在しない場合は `False` を返します。

削除対象が存在しないことを例外とは扱いません。

---

## 15. 行変換メソッド

SQLiteの行を `BookItem` へ変換する処理を、非公開メソッドとして実装します。

```python
@staticmethod
def _row_to_book_item(
    row: sqlite3.Row,
) -> BookItem:
    ...
```

想定実装は、次のとおりです。

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

キーワード引数を使用し、SQLiteのカラム順とdataclassの属性順への依存を避けます。

---

## 16. 接続管理

各公開メソッドは、原則として次の構造で接続を管理します。

```python
connection = create_connection(
    self._database_path,
)

try:
    ...
finally:
    connection.close()
```

登録、更新、削除では、トランザクションを次の形式で扱います。

```python
with connection:
    cursor = connection.execute(...)
```

`with connection:` は、正常終了時にコミットし、例外発生時にロールバックします。

接続自体は自動で閉じられないため、`finally` で明示的に閉じます。

---

## 17. SELECT文の列指定

SELECT文では、`SELECT *` を使用しません。

次のように、取得対象のカラムを明示します。

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
```

理由は、次のとおりです。

* 取得する値が明確になる。
* テーブル変更の影響を把握しやすい。
* カラム順への暗黙的依存を避けられる。
* コードレビューしやすい。
* 将来の不要カラム取得を防ぎやすい。

---

## 18. 共通SELECT文

同じ列一覧を複数メソッドで使用するため、モジュール定数として共通化します。

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

使用例：

```python
query = f"""
    SELECT
        {BOOK_ITEM_COLUMNS}
    FROM book_items
    WHERE id = ?
"""
```

この文字列は開発者が管理する固定値であり、利用者入力を含まないため、SQLインジェクションの原因にはなりません。

ただし、検索値やIDは必ずプレースホルダーで渡します。

---

## 19. SQLの配置方針

初期Versionでは、SQLを別ファイルへ分離しません。

次のような構成は採用しません。

```text
sql/
├── insert_book.sql
├── select_books.sql
└── update_book.sql
```

SQLは `book_repository.py` 内に記述します。

理由は、次のとおりです。

* 小規模なCRUDである。
* PythonコードとSQLの対応を追いやすい。
* 別ファイル化による移動負担を避けられる。
* 初期Versionとして単純である。

SQLが大規模化した場合に、再検討します。

---

## 20. Repositoryに含めない責務

`BookRepository` には、次の処理を含めません。

* 書籍名の必須検証。
* ISBNの形式検証。
* ISBNのハイフン除去。
* ISBNのチェックデジット検証。
* 雑誌コードの形式検証。
* 読了年月の形式検証。
* 空文字列から `None` への変換。
* 前後空白の除去。
* 著者名の正規化。
* 日時の生成。
* 重複登録を許可するかどうかの判断。
* 利用者への確認ダイアログ。
* エラーメッセージの画面表示。
* openBDの呼び出し。
* Google Books APIの呼び出し。
* バックアップ処理。
* データベース初期化。
* スキーマVersionの更新。

---

## 21. Service層との責務境界

Service層は、Repositoryを呼び出す前に次の処理を行います。

```text
入力値の前後空白を除去する
空文字列をNoneへ変換する
titleを検証する
ISBNを正規化する
ISBNを検証する
雑誌コードを検証する
completion_monthを検証する
重複候補を検索する
created_atを生成する
updated_atを生成する
```

Repositoryは、Serviceから受け取った値をSQLiteへ保存します。

依存方向は、次のとおりです。

```text
GUI
↓
BookService
↓
BookRepository
↓
SQLite
```

RepositoryからServiceやGUIを呼び出してはいけません。

---

## 22. 重複データの扱い

初期Versionでは、ISBNおよび雑誌コードへ一意制約を設定していません。

したがって、Repositoryは同じISBNや雑誌コードを持つ書籍を複数登録できます。

重複の可能性がある場合は、Service層が次の検索メソッドを使用します。

```python
find_by_isbn()
find_by_magazine_code()
```

Service層が重複候補をGUIへ返し、最終的な登録可否を利用者に確認します。

Repositoryは、重複を理由に登録を拒否しません。

---

## 23. 並び順

初期Versionでは、取得結果の既定の並び順を、次のとおりとします。

```sql
ORDER BY id DESC
```

対象メソッドは、次のとおりです。

```text
get_all
search_by_title
find_by_isbn
find_by_magazine_code
```

初期Versionでは、書籍名順、著者順、出版社順、読了年月順などの切り替えはRepositoryへ実装しません。

並び替え要件が確定した段階で、専用メソッドまたは引数の追加を検討します。

---

## 24. ページング

初期Versionでは、ページングを実装しません。

次のSQL句は使用しません。

```sql
LIMIT
OFFSET
```

すべての該当データを取得します。

書籍数が増え、GUI表示や検索性能に問題が発生した段階でページングを検討します。

---

## 25. 検索対象

初期Versionで実装する検索は、次の3種類です。

```text
書籍名の部分一致
ISBNの完全一致
雑誌コードの完全一致
```

次の検索は、初期Versionでは実装しません。

* 著者名検索。
* 出版社検索。
* 内容紹介検索。
* 備考検索。
* 読了年月検索。
* 複数項目を組み合わせた検索。
* 全文検索。
* あいまい検索。
* 正規表現検索。

必要性が確認された段階で追加します。

---

## 26. 例外方針

SQLiteから発生する例外は、原則としてそのまま伝播させます。

例：

```text
sqlite3.OperationalError
sqlite3.IntegrityError
sqlite3.DatabaseError
```

Repository独自の例外階層は、初期Versionでは導入しません。

ただし、`update()` に `id=None` のモデルが渡された場合は、呼び出し方法の誤りとして `ValueError` を送出します。

将来、GUIへ表示するエラー分類が必要になった場合は、Service層で例外を捕捉して整理します。

---

## 27. 型定義

実装時に使用する主な型は、次のとおりです。

```python
from pathlib import Path
import sqlite3

from book_manager.models.book_item import BookItem
```

コンストラクター：

```python
def __init__(
    self,
    database_path: Path | str,
) -> None:
```

単一取得：

```python
def get_by_id(
    self,
    book_id: int,
) -> BookItem | None:
```

複数取得：

```python
def get_all(
    self,
) -> list[BookItem]:
```

更新・削除：

```python
def update(
    self,
    book_item: BookItem,
) -> bool:
```

```python
def delete(
    self,
    book_id: int,
) -> bool:
```

---

## 28. 実装予定コード構成

```python
"""Repository for book items."""

import sqlite3
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

## 29. テスト方針

Repositoryテストは、実際のSQLite一時データベースを使用します。

モックは使用しません。

各テストでは、pytestの `tmp_path` を使用して独立したデータベースを作成します。

テスト開始前に、次を呼び出します。

```python
initialize_database(database_path)
```

その後、Repositoryを生成します。

```python
repository = BookRepository(database_path)
```

---

## 30. テスト項目

最低限、次のテストを実装します。

### 30.1 コンストラクター

* `Path` を受け取れる。
* 文字列パスを受け取れる。

### 30.2 登録

* 書籍を登録できる。
* 登録後にIDが設定される。
* 登録内容が保持される。
* 任意項目が `None` でも登録できる。
* 引数のモデルを直接変更しない。

### 30.3 ID取得

* 存在するIDから取得できる。
* 取得結果が `BookItem` になる。
* 存在しないIDでは `None` を返す。

### 30.4 一覧取得

* 複数件を取得できる。
* IDの降順で返る。
* データがない場合に空のリストを返す。

### 30.5 書籍名検索

* 完全一致する書籍を取得できる。
* 部分一致する書籍を取得できる。
* 日本語を検索できる。
* 該当しない場合に空のリストを返す。
* 複数件を取得できる。

### 30.6 ISBN検索

* 完全一致する書籍を取得できる。
* 同じISBNの複数件を取得できる。
* 該当しない場合に空のリストを返す。

### 30.7 雑誌コード検索

* 完全一致する書籍を取得できる。
* 同じ雑誌コードの複数件を取得できる。
* 該当しない場合に空のリストを返す。

### 30.8 更新

* 既存書籍を更新できる。
* `created_at` が変更されない。
* `updated_at` が更新される。
* 存在しないIDでは `False` を返す。
* `id=None` では `ValueError` を送出する。

### 30.9 削除

* 既存書籍を削除できる。
* 削除後に取得できない。
* 存在しないIDでは `False` を返す。

---

## 31. テストデータ

テストで使用する書籍例は、次のとおりです。

```python
BookItem(
    title="吾輩は猫である",
    isbn="9784101010014",
    author="夏目漱石",
    publisher="新潮社",
    publication_format="文庫",
    description="猫の視点から人間社会を描いた作品。",
    completion_month="2026-07",
    notes="再読。",
    created_at="2026-07-21 10:00:00",
    updated_at="2026-07-21 10:00:00",
)
```

任意項目が少ないデータ例：

```python
BookItem(
    title="坊っちゃん",
    created_at="2026-07-21 11:00:00",
    updated_at="2026-07-21 11:00:00",
)
```

---

## 32. 初期Versionで導入しないもの

次の機能は、初期Versionでは導入しません。

* Repositoryインターフェース。
* 抽象基底クラス。
* Protocol。
* Unit of Work。
* ORM。
* 非同期データベース接続。
* 接続プール。
* ページング。
* 動的な並び替え。
* 複合検索条件。
* 全文検索。
* 論理削除。
* 更新履歴。
* 排他制御。
* 楽観的ロック。
* 独自例外階層。
* Repositoryによる入力値正規化。
* Repositoryによる日時生成。
* Repositoryによる重複拒否。

---

## 33. 将来の拡張候補

必要性が確認された場合に、次の拡張を検討します。

* 著者名検索。
* 出版社検索。
* 読了年月検索。
* 複数項目検索。
* 並び順指定。
* ページング。
* 全文検索。
* タグ検索。
* 論理削除。
* 更新履歴テーブル。
* Repositoryインターフェース。
* トランザクション境界の外部管理。
* 複数RepositoryをまとめたUnit of Work。
* SQLの外部ファイル化。
* 独自例外の導入。
* バッチ登録。
* バッチ削除。

---

## 34. Design Freeze条件

次の項目が承認された時点で、Version 0.1をDesign Freezeとします。

* クラス名を `BookRepository` とする。
* データベースパスをコンストラクターで受け取る。
* 接続はメソッド単位で作成して閉じる。
* `add()` は登録後の新しい `BookItem` を返す。
* `get_by_id()` は存在しない場合に `None` を返す。
* 複数取得メソッドは `list[BookItem]` を返す。
* 取得結果はID降順とする。
* 書籍名は部分一致検索とする。
* ISBNと雑誌コードは完全一致検索とする。
* ISBNと雑誌コードの重複を許可する。
* `update()` は成否を `bool` で返す。
* `update()` は `id=None` の場合に `ValueError` を送出する。
* `delete()` は成否を `bool` で返す。
* `created_at` は更新しない。
* SQLite行変換を非公開メソッドへ集約する。
* `SELECT *` を使用しない。
* SQLパラメーターにはプレースホルダーを使用する。
* 入力検証と日時生成をService層の責務とする。
* 初期Versionでは独自例外、ORM、ページングを導入しない。

---

## 35. 次の作業

この設計書のレビューとDesign Freeze後、次の順序で進めます。

```text
book_repository_design_review.mdを作成する
↓
BookRepository設計を正式承認する
↓
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
Service層の設計へ進む
```
