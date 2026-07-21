# BookItemモデル設計

Version : 0.1
Last Updated : 2026-07-21
Status : Draft

---

## 1. 目的

この文書は、`book_manager` で使用する書籍データモデル `BookItem` の設計を定義するものです。

`BookItem` は、SQLiteの `book_items` テーブルに保存される1件の書籍情報を、Pythonコード内で扱うためのモデルです。

---

## 2. 基本方針

`BookItem` は、Python標準ライブラリの `dataclasses.dataclass` を使用して実装します。

初期Versionでは、次の方針を採用します。

* ORMは使用しない。
* SQLite固有の処理をモデルへ含めない。
* 入力検証をモデルへ含めない。
* 日時の生成をモデルへ含めない。
* GUI処理をモデルへ含めない。
* 登録用モデルと取得用モデルを分けない。
* SQLiteの1行と対応しやすい単純なデータ構造とする。
* 初期値を持たない必須項目を先頭に定義する。
* 任意項目には `None` を使用する。

---

## 3. 配置場所

実装ファイルは、次の場所へ配置します。

```text
src/book_manager/models/book_item.py
```

パッケージ構成は、次のとおりです。

```text
src/
└── book_manager/
    └── models/
        ├── __init__.py
        └── book_item.py
```

---

## 4. クラス名

正式なクラス名は、次のとおりです。

```python
BookItem
```

1件の書籍情報を表すため、単数形とします。

---

## 5. dataclassの採用

`BookItem` は、次の形式で定義します。

```python
@dataclass(slots=True)
class BookItem:
    ...
```

`dataclass` を採用する理由は、次のとおりです。

* データ保持を目的としたクラスを簡潔に定義できる。
* `__init__()` を自動生成できる。
* 比較処理を自動生成できる。
* テストで値を比較しやすい。
* 標準ライブラリだけで実装できる。

`slots=True` を採用する理由は、次のとおりです。

* 未定義属性の誤追加を防止できる。
* モデルの属性を明確に固定できる。
* 単純なデータモデルとしての意図が明確になる。

---

## 6. 属性一覧

| 属性名                  | Python型       | SQLiteカラム            | 必須 | 初期値    |
| -------------------- | ------------- | -------------------- | -- | ------ |
| `title`              | `str`         | `title`              | 必須 | なし     |
| `id`                 | `int \| None` | `id`                 | 任意 | `None` |
| `isbn`               | `str \| None` | `isbn`               | 任意 | `None` |
| `magazine_code`      | `str \| None` | `magazine_code`      | 任意 | `None` |
| `author`             | `str \| None` | `author`             | 任意 | `None` |
| `publisher`          | `str \| None` | `publisher`          | 任意 | `None` |
| `publication_format` | `str \| None` | `publication_format` | 任意 | `None` |
| `description`        | `str \| None` | `description`        | 任意 | `None` |
| `completion_month`   | `str \| None` | `completion_month`   | 任意 | `None` |
| `notes`              | `str \| None` | `notes`              | 任意 | `None` |
| `created_at`         | `str \| None` | `created_at`         | 任意 | `None` |
| `updated_at`         | `str \| None` | `updated_at`         | 任意 | `None` |

---

## 7. 属性定義

### 7.1 `title`

書籍名を保持します。

```python
title: str
```

書籍名は、アプリケーション上の必須項目です。

SQLiteでは、次の制約を設定しています。

```sql
title TEXT NOT NULL
```

空文字列を許可するかどうかは、Service層で検証します。

モデル自身は、空文字列の検証を行いません。

---

### 7.2 `id`

SQLiteの主キーを保持します。

```python
id: int | None = None
```

新規登録前は `None` です。

SQLiteへの登録後、またはSQLiteから取得した場合は整数値を保持します。

```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
```

モデル側で採番は行いません。

---

### 7.3 `isbn`

ISBNを保持します。

```python
isbn: str | None = None
```

ISBNは数値ではなく文字列として扱います。

理由は、次のとおりです。

* 先頭のゼロを保持する必要がある。
* ハイフンを含む入力を受け取る可能性がある。
* 算術計算を行わない。
* ISBN-10とISBN-13の両方を扱う可能性がある。

正規化および妥当性検証は、Service層または `validators.py` で行います。

---

### 7.4 `magazine_code`

雑誌コードを保持します。

```python
magazine_code: str | None = None
```

雑誌コードも、数値ではなく文字列として扱います。

理由は、次のとおりです。

* 先頭のゼロを保持する可能性がある。
* 算術計算を行わない。
* 桁数や表記形式を保持する必要がある。

正規化および妥当性検証は、モデルでは行いません。

---

### 7.5 `author`

著者名を保持します。

```python
author: str | None = None
```

初期Versionでは、著者名を1つの文字列として保持します。

複数著者も、1つの文字列として保存します。

著者マスタや著者との多対多関係は、将来の拡張対象とし、初期Versionでは導入しません。

---

### 7.6 `publisher`

出版社名を保持します。

```python
publisher: str | None = None
```

初期Versionでは、出版社マスタを作成せず、文字列として保持します。

表記ゆれの正規化は、必要性が確認された段階でService層へ追加します。

---

### 7.7 `publication_format`

出版形態を保持します。

```python
publication_format: str | None = None
```

想定する値の例は、次のとおりです。

```text
単行本
文庫
新書
雑誌
電子書籍
その他
```

初期Versionでは、列挙型や専用マスタを導入せず、文字列として保持します。

選択肢の制御はGUIまたはService層で行います。

---

### 7.8 `description`

内容紹介を保持します。

```python
description: str | None = None
```

openBDやGoogle Booksなどの外部取得元から取得した文章を保存する想定です。

内容紹介が取得できない場合は `None` とします。

空文字列を `None` へ正規化する処理は、Service層で行います。

---

### 7.9 `completion_month`

読了年月を保持します。

```python
completion_month: str | None = None
```

保存形式は、次の形式とします。

```text
YYYY-MM
```

例：

```text
2026-07
```

未読または読了年月が不明な場合は `None` とします。

形式の検証はService層で行います。

SQLiteの日付型は使用せず、文字列として保存します。

---

### 7.10 `notes`

利用者が入力する備考を保持します。

```python
notes: str | None = None
```

複数行の文章を保存できるものとします。

文字数制限は、初期Versionでは設けません。

---

### 7.11 `created_at`

レコード作成日時を保持します。

```python
created_at: str | None = None
```

保存形式は、次の形式とします。

```text
YYYY-MM-DD HH:MM:SS
```

例：

```text
2026-07-21 15:30:00
```

新規登録前は `None` です。

登録時にService層が日本標準時で生成します。

モデル自身は日時を生成しません。

---

### 7.12 `updated_at`

レコード更新日時を保持します。

```python
updated_at: str | None = None
```

保存形式は、`created_at` と同じです。

```text
YYYY-MM-DD HH:MM:SS
```

新規登録時は `created_at` と同じ日時を設定します。

更新時は、Service層が新しい日時を生成します。

モデル自身は日時を更新しません。

---

## 8. 属性の定義順序

Pythonのdataclassでは、初期値を持たない属性を、初期値を持つ属性より前に定義する必要があります。

そのため、必須項目の `title` を最初に定義します。

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

SQLiteのカラム順と完全には一致しませんが、Pythonのdataclass仕様を優先します。

Repositoryでは、属性名を明示してモデルを生成します。

---

## 9. 新規登録時の状態

新規登録前の `BookItem` は、次のような状態を想定します。

```python
book_item = BookItem(
    title="吾輩は猫である",
    isbn="9784101010014",
    author="夏目漱石",
    publisher="新潮社",
    publication_format="文庫",
)
```

この時点では、次の属性は `None` です。

```text
id
created_at
updated_at
```

Service層が日時を設定し、RepositoryがSQLiteへ登録します。

登録後のIDは、Repositoryの戻り値または更新済みモデルとして扱います。

戻り値の正式な形式は、Repository設計で確定します。

---

## 10. SQLite取得時の状態

SQLiteから取得した場合は、原則として次の属性が設定されます。

```text
id
title
created_at
updated_at
```

SQLiteでNULLを許可している項目は、値がない場合に `None` となります。

Repositoryは、`sqlite3.Row` から属性名を明示して `BookItem` を生成します。

想定例：

```python
BookItem(
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

---

## 11. モデルに含めない責務

`BookItem` には、次の処理を実装しません。

* SQLiteへの接続。
* SQLの実行。
* ISBNの検証。
* ISBNのチェックデジット計算。
* 雑誌コードの検証。
* 書籍名の必須チェック。
* 入力値の前後空白除去。
* 空文字列から `None` への変換。
* 著者名の正規化。
* 日時の生成。
* 日時の更新。
* 重複検索。
* 重複登録の判定。
* GUIダイアログの表示。
* 外部APIからの書籍情報取得。
* 書影の取得。
* バックアップ処理。

これらは、Service、Repository、GUIまたは将来の外部取得機能へ分離します。

---

## 12. モデルにメソッドを追加しない方針

初期Versionの `BookItem` は、データ保持だけを目的とします。

そのため、次のような独自メソッドは実装しません。

```text
save()
delete()
validate()
normalize()
fetch_metadata()
update_timestamp()
```

必要性が確認されるまでは、データと処理を分離します。

---

## 13. 型変換の責務

SQLiteから取得した値を `BookItem` へ変換する処理は、Repositoryが担当します。

`BookItem` からSQLパラメーターを生成する処理も、Repositoryが担当します。

モデル自身に、次のような変換メソッドは初期実装では追加しません。

```text
from_row()
to_dict()
to_tuple()
```

同じ変換処理が複数箇所へ重複するようになった場合に、導入を再検討します。

---

## 14. イミュータブル化

初期Versionでは、`frozen=True` を使用しません。

```python
@dataclass(slots=True)
class BookItem:
    ...
```

次のようにはしません。

```python
@dataclass(slots=True, frozen=True)
class BookItem:
    ...
```

理由は、GUIで編集中の値や、登録後に採番されたIDを扱う際に、属性変更が必要になる可能性があるためです。

ただし、実際の更新処理では、予期しない副作用を避けるため、新しいインスタンスを生成する方式も検討します。

---

## 15. 等価比較

dataclassが生成する標準の等価比較を使用します。

すべての属性が同じ場合に、2つの `BookItem` を等しいと判定します。

```python
book1 == book2
```

IDだけで同一性を判定する独自の `__eq__()` は実装しません。

---

## 16. 表示文字列

初期Versionでは、独自の `__str__()` や `__repr__()` は実装しません。

dataclassが生成する標準表現を使用します。

GUI上の表示形式は、GUI層が決定します。

---

## 17. テスト方針

モデルのテストは、次のファイルへ配置します。

```text
tests/models/test_book_item.py
```

少なくとも次の項目を確認します。

* 必須項目の `title` だけで生成できる。
* 任意項目の初期値が `None` になる。
* すべての属性を指定して生成できる。
* 属性へ値を代入できる。
* 未定義属性を追加できない。
* 同じ値を持つモデル同士が等しい。
* 異なる値を持つモデル同士が等しくない。

---

## 18. 想定テスト例

```python
from book_manager.models.book_item import BookItem


def test_book_item_can_be_created_with_title_only() -> None:
    book_item = BookItem(title="吾輩は猫である")

    assert book_item.title == "吾輩は猫である"
    assert book_item.id is None
    assert book_item.isbn is None
    assert book_item.created_at is None
    assert book_item.updated_at is None
```

```python
def test_book_item_accepts_all_fields() -> None:
    book_item = BookItem(
        id=1,
        isbn="9784101010014",
        magazine_code=None,
        title="吾輩は猫である",
        author="夏目漱石",
        publisher="新潮社",
        publication_format="文庫",
        description="猫の視点から人間社会を描いた作品。",
        completion_month="2026-07",
        notes="再読。",
        created_at="2026-07-21 15:00:00",
        updated_at="2026-07-21 15:00:00",
    )

    assert book_item.id == 1
    assert book_item.title == "吾輩は猫である"
    assert book_item.author == "夏目漱石"
```

---

## 19. 実装予定コード

Design Freeze後に、次の内容で実装します。

```python
"""Book item model."""

from dataclasses import dataclass


@dataclass(slots=True)
class BookItem:
    """書籍情報を表すデータモデル。"""

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

---

## 20. 将来の拡張候補

必要性が確認された場合に、次の拡張を検討します。

* 登録用DTOの分離。
* 更新用DTOの分離。
* 著者モデルの分離。
* 出版社モデルの分離。
* 出版形態の列挙型化。
* 読了状態の追加。
* 購入日や購入価格の追加。
* 評価項目の追加。
* タグ機能の追加。
* 書影パスの追加。
* 外部取得元情報の追加。
* Rawデータとの関連付け。
* `created_at` と `updated_at` の `datetime` 型化。

これらは、初期Versionでは実装しません。

---

## 21. Design Freeze条件

次の項目が承認された時点で、Version 0.1をDesign Freezeとします。

* クラス名を `BookItem` とする。
* `dataclass(slots=True)` を使用する。
* `title` を唯一の必須属性とする。
* `id` を `int | None` とする。
* ISBNと雑誌コードを文字列とする。
* 読了年月を `YYYY-MM` 形式の文字列とする。
* 日時を `YYYY-MM-DD HH:MM:SS` 形式の文字列とする。
* 日時生成をService層の責務とする。
* 入力検証をService層の責務とする。
* SQLite変換をRepository層の責務とする。
* 登録用モデルと取得用モデルを分けない。
* 初期Versionでは独自メソッドを追加しない。
* 初期Versionでは `frozen=True` を使用しない。

---

## 22. 次の作業

この設計書のレビューとDesign Freeze後、次の順序で進めます。

```text
book_item_design_review.mdを作成する
↓
BookItem設計を正式承認する
↓
src/book_manager/models/book_item.pyを作成する
↓
tests/models/test_book_item.pyを作成する
↓
pytestを実行する
↓
BookRepositoryの設計へ進む
