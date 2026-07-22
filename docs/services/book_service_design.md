# BookService設計

Version : 0.1
Last Updated : 2026-07-22
Status : Draft

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおける `BookService` の設計を定義するものです。

`BookService` は、GUIとRepositoryの間に位置し、書籍管理に関するアプリケーションロジックを担当します。

主な責務は、次のとおりです。

* GUIから受け取った入力値の正規化。
* 必須項目の確認。
* ISBNの正規化および検証。
* 雑誌コードの検証。
* 読了年月の検証。
* 重複候補の検索。
* 登録日時および更新日時の生成。
* `BookItem` の生成。
* `BookRepository` の呼び出し。
* Repositoryの戻り値をGUI向けに整理する。
* 更新対象および削除対象の存在確認。

---

## 2. 配置場所

実装ファイルは、次の場所へ配置します。

```text
src/book_manager/services/book_service.py
```

パッケージ構成は、次のとおりです。

```text
src/
└── book_manager/
    └── services/
        ├── __init__.py
        └── book_service.py
```

テストファイルは、次の場所へ配置します。

```text
tests/services/test_book_service.py
```

---

## 3. クラス名

正式なクラス名は、次のとおりです。

```python
BookService
```

書籍情報に関するアプリケーションロジックを集約するクラスとします。

---

## 4. 基本方針

初期Versionでは、次の方針を採用します。

* GUIはRepositoryを直接呼び出さない。
* GUIはSQLiteへ直接アクセスしない。
* `BookService` が `BookRepository` を呼び出す。
* ServiceはSQLを記述しない。
* ServiceはSQLiteへ直接接続しない。
* ServiceはGUIウィジェットを操作しない。
* Serviceはメッセージボックスを表示しない。
* Serviceは入力値を正規化する。
* Serviceは入力値を検証する。
* Serviceは日時を生成する。
* Serviceは重複候補を確認する。
* Serviceは外部APIを直接呼び出さない。
* Serviceは処理結果を戻り値または例外でGUIへ伝える。
* 初期Versionでは依存性注入フレームワークを使用しない。
* Repositoryはコンストラクターで受け取る。
* 現在日時を取得する関数もコンストラクターで差し替え可能にする。

---

## 5. 依存関係

正式な依存方向は、次のとおりです。

```text
GUI
↓
BookService
↓
BookRepository
↓
SQLite
```

Validatorを導入した後は、次の構成とします。

```text
GUI
↓
BookService
├── Validators
└── BookRepository
    ↓
    SQLite
```

ServiceからGUIを呼び出してはいけません。

RepositoryからServiceを呼び出してはいけません。

---

## 6. コンストラクター

`BookService` は、`BookRepository` を受け取ります。

また、テスト時に現在日時を固定できるように、日時取得関数を受け取れる構成とします。

```python
from collections.abc import Callable
from datetime import datetime


class BookService:
    def __init__(
        self,
        repository: BookRepository,
        now_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        ...
```

保持する属性は、次のとおりです。

```python
self._repository = repository
self._now_provider = now_provider
```

---

## 7. Repositoryを受け取る理由

Service内でRepositoryを直接生成しません。

次のような実装は行いません。

```python
class BookService:
    def __init__(self) -> None:
        self._repository = BookRepository(
            "book_manager.db"
        )
```

Repositoryを外部から受け取ることで、次の利点があります。

* Serviceとデータベースパスを分離できる。
* テスト用Repositoryを渡せる。
* 一時データベースを使用できる。
* Repositoryの差し替えが容易になる。
* Serviceの責務をアプリケーションロジックへ限定できる。

---

## 8. 日時取得関数を受け取る理由

Serviceは、登録日時および更新日時を生成します。

しかし、Service内で直接 `datetime.now()` を呼び出すと、テスト結果が実行時刻に依存します。

そのため、現在日時を返す関数をコンストラクターで受け取ります。

通常実行時：

```python
service = BookService(repository)
```

テスト時：

```python
fixed_now = datetime(
    2026,
    7,
    22,
    10,
    30,
    0,
)

service = BookService(
    repository,
    now_provider=lambda: fixed_now,
)
```

これにより、日時を含む処理を安定してテストできます。

---

## 9. 公開メソッド一覧

初期Versionでは、次の公開メソッドを実装します。

```python
def add_book(
    self,
    *,
    title: str,
    isbn: str | None = None,
    magazine_code: str | None = None,
    author: str | None = None,
    publisher: str | None = None,
    publication_format: str | None = None,
    description: str | None = None,
    completion_month: str | None = None,
    notes: str | None = None,
) -> BookItem:
    ...

def get_book(
    self,
    book_id: int,
) -> BookItem | None:
    ...

def get_all_books(
    self,
) -> list[BookItem]:
    ...

def search_books_by_title(
    self,
    keyword: str,
) -> list[BookItem]:
    ...

def find_books_by_isbn(
    self,
    isbn: str,
) -> list[BookItem]:
    ...

def find_books_by_magazine_code(
    self,
    magazine_code: str,
) -> list[BookItem]:
    ...

def update_book(
    self,
    book_item: BookItem,
) -> bool:
    ...

def delete_book(
    self,
    book_id: int,
) -> bool:
    ...
```

---

## 10. 登録入力の形式

初期Versionでは、登録時に未保存の `BookItem` をGUIから受け取りません。

GUIから個別の値を受け取り、Service内で `BookItem` を生成します。

```python
service.add_book(
    title=title,
    isbn=isbn,
    author=author,
)
```

理由は、次のとおりです。

* GUIがモデル生成の責務を持たずに済む。
* 正規化前の値をモデルへ入れずに済む。
* 必須項目の検証を一か所へ集約できる。
* 日時生成をServiceへ集約できる。
* GUIとModelの結合を弱められる。

---

## 11. キーワード専用引数

`add_book()` の入力値は、すべてキーワード専用引数とします。

```python
def add_book(
    self,
    *,
    title: str,
    isbn: str | None = None,
    ...
) -> BookItem:
```

次のような位置引数での呼び出しは許可しません。

```python
service.add_book(
    "吾輩は猫である",
    "9784101010014",
    None,
    "夏目漱石",
)
```

正式な呼び出しは、次の形式です。

```python
service.add_book(
    title="吾輩は猫である",
    isbn="9784101010014",
    author="夏目漱石",
)
```

書籍項目は数が多いため、キーワード引数を使用した方が安全で読みやすくなります。

---

## 12. 入力値の正規化

Serviceは、GUIから受け取った文字列を正規化します。

初期Versionで行う正規化は、次のとおりです。

* 文字列の前後空白を除去する。
* 空文字列を `None` へ変換する。
* `title` の前後空白を除去する。
* ISBNからハイフンと空白を除去する。
* 雑誌コードの前後空白を除去する。
* `completion_month` の前後空白を除去する。

---

## 13. 任意文字列の正規化

任意項目に対して、次の非公開メソッドを使用します。

```python
@staticmethod
def _normalize_optional_text(
    value: str | None,
) -> str | None:
    ...
```

想定実装は、次のとおりです。

```python
if value is None:
    return None

normalized = value.strip()

if normalized == "":
    return None

return normalized
```

対象項目は、次のとおりです。

```text
magazine_code
author
publisher
publication_format
description
completion_month
notes
```

ISBNは専用の正規化処理を使用します。

---

## 14. 書籍名の正規化

書籍名は必須項目です。

次の非公開メソッドを使用します。

```python
@staticmethod
def _normalize_title(
    title: str,
) -> str:
    ...
```

想定処理は、次のとおりです。

```python
normalized = title.strip()

if normalized == "":
    raise ValueError(
        "書籍名を入力してください。"
    )

return normalized
```

初期Versionでは、書籍名の最大文字数検証は行いません。

---

## 15. ISBNの正規化

ISBNは、次の非公開メソッドで正規化します。

```python
@staticmethod
def _normalize_isbn(
    isbn: str | None,
) -> str | None:
    ...
```

正規化処理は、次のとおりです。

* `None` はそのまま `None` とする。
* 前後空白を除去する。
* 半角ハイフンを除去する。
* 全角ハイフン類は初期Versionでは自動変換しない。
* 文字列内の半角空白を除去する。
* 正規化後に空文字列となった場合は `None` とする。

例：

```text
入力   : 978-4-10-101001-4
正規化 : 9784101010014
```

```text
入力   : 978 410 101001 4
正規化 : 9784101010014
```

---

## 16. ISBNの検証

初期Versionでは、ISBNの検証をServiceからValidatorへ委譲する設計とします。

想定するValidatorは、次のとおりです。

```python
validate_isbn(isbn: str) -> None
```

有効な場合は何も返しません。

無効な場合は `ValueError` を送出します。

```python
validate_isbn("9784101010014")
```

ISBNが `None` の場合は、Validatorを呼び出しません。

検証対象は、次のとおりです。

* ISBN-10。
* ISBN-13。
* 数字とISBN-10末尾の `X`。
* 桁数。
* チェックデジット。

---

## 17. 雑誌コードの検証

雑誌コードが入力されている場合は、Validatorへ検証を委譲します。

想定する関数は、次のとおりです。

```python
validate_magazine_code(
    magazine_code: str,
) -> None:
```

初期Versionでは、雑誌コードの正式な入力仕様をValidator設計時に確定します。

Serviceは、正規化後の値が `None` でない場合のみValidatorを呼び出します。

---

## 18. 読了年月の検証

`completion_month` が入力されている場合は、次の形式であることを検証します。

```text
YYYY-MM
```

想定するValidatorは、次のとおりです。

```python
validate_completion_month(
    completion_month: str,
) -> None:
```

有効例：

```text
2026-07
```

無効例：

```text
2026/07
202607
2026-7
2026-13
```

---

## 19. 日時の文字列形式

SQLiteへ保存する日時は、次の形式とします。

```text
YYYY-MM-DD HH:MM:SS
```

Service内で、次の非公開メソッドを使用します。

```python
def _current_timestamp(self) -> str:
    ...
```

想定実装は、次のとおりです。

```python
return self._now_provider().strftime(
    "%Y-%m-%d %H:%M:%S"
)
```

マイクロ秒は保存しません。

---

## 20. `add_book()`

### 20.1 目的

GUIから受け取った値を正規化および検証し、新しい書籍情報を登録します。

```python
def add_book(
    self,
    *,
    title: str,
    isbn: str | None = None,
    magazine_code: str | None = None,
    author: str | None = None,
    publisher: str | None = None,
    publication_format: str | None = None,
    description: str | None = None,
    completion_month: str | None = None,
    notes: str | None = None,
) -> BookItem:
    ...
```

---

### 20.2 処理順序

正式な処理順序は、次のとおりです。

```text
titleを正規化する
↓
任意項目を正規化する
↓
ISBNを正規化する
↓
ISBNを検証する
↓
雑誌コードを検証する
↓
読了年月を検証する
↓
重複候補を検索する
↓
現在日時を生成する
↓
BookItemを生成する
↓
Repositoryへ登録する
↓
登録後のBookItemを返す
```

---

### 20.3 重複候補の扱い

ISBNまたは雑誌コードが既存データと一致する場合があります。

ただし、初期Versionでは、Serviceが自動的に登録を拒否しません。

Repository設計では、重複登録を許可しています。

重複確認をGUIで行うためには、登録前確認と実際の登録を分ける必要があります。

そのため、初期Versionの `add_book()` では、重複確認を内部で行わず、そのまま登録する方針も検討対象となります。

正式な初期設計では、次の2段階方式を採用します。

```text
GUI
↓
find_duplicate_candidates()
↓
利用者へ確認
↓
add_book()
```

したがって、`add_book()` 自体は、重複を理由に登録を拒否しません。

---

## 21. `find_duplicate_candidates()`

登録前に重複候補を確認するため、次の公開メソッドを追加します。

```python
def find_duplicate_candidates(
    self,
    *,
    isbn: str | None = None,
    magazine_code: str | None = None,
) -> list[BookItem]:
    ...
```

---

### 21.1 処理方針

ISBNと雑誌コードを正規化および検証した後、Repositoryを検索します。

```text
ISBNがある
→ find_by_isbn()

雑誌コードがある
→ find_by_magazine_code()
```

両方が入力されている場合は、両方の検索結果を統合します。

同じ書籍が両方の結果に含まれる場合は、1件へまとめます。

---

### 21.2 重複排除

同じ `id` を持つ `BookItem` は、1件だけ返します。

戻り値はID降順とします。

想定処理は、次のとおりです。

```python
books_by_id: dict[int, BookItem] = {}

for book_item in candidates:
    if book_item.id is not None:
        books_by_id[book_item.id] = book_item

return sorted(
    books_by_id.values(),
    key=lambda item: item.id or 0,
    reverse=True,
)
```

---

### 21.3 識別情報がない場合

ISBNと雑誌コードの両方が `None` または空文字列の場合は、空のリストを返します。

```python
[]
```

例外にはしません。

---

## 22. `get_book()`

### 22.1 目的

IDを指定して、1件の書籍情報を取得します。

```python
def get_book(
    self,
    book_id: int,
) -> BookItem | None:
    ...
```

処理はRepositoryへ委譲します。

```python
return self._repository.get_by_id(
    book_id
)
```

存在しない場合は `None` を返します。

Service独自の例外へ変換しません。

---

## 23. `get_all_books()`

登録済みの書籍をすべて取得します。

```python
def get_all_books(
    self,
) -> list[BookItem]:
    ...
```

処理はRepositoryへ委譲します。

```python
return self._repository.get_all()
```

データが存在しない場合は空のリストを返します。

---

## 24. `search_books_by_title()`

### 24.1 目的

書籍名による部分一致検索を行います。

```python
def search_books_by_title(
    self,
    keyword: str,
) -> list[BookItem]:
    ...
```

---

### 24.2 検索語の正規化

検索語の前後空白を除去します。

```python
normalized_keyword = keyword.strip()
```

---

### 24.3 空の検索語

検索語が空文字列の場合は、すべての書籍を返します。

```python
if normalized_keyword == "":
    return self._repository.get_all()
```

これにより、GUIの検索欄を空にして検索した場合、一覧を再表示できます。

---

### 24.4 検索処理

検索語が空でない場合は、Repositoryへ委譲します。

```python
return self._repository.search_by_title(
    normalized_keyword
)
```

---

## 25. `find_books_by_isbn()`

ISBNによる完全一致検索を行います。

```python
def find_books_by_isbn(
    self,
    isbn: str,
) -> list[BookItem]:
    ...
```

正式な処理順序は、次のとおりです。

```text
ISBNを正規化する
↓
空である場合は空のリストを返す
↓
ISBNを検証する
↓
Repositoryで検索する
```

正規化後に `None` となった場合は、空のリストを返します。

---

## 26. `find_books_by_magazine_code()`

雑誌コードによる完全一致検索を行います。

```python
def find_books_by_magazine_code(
    self,
    magazine_code: str,
) -> list[BookItem]:
    ...
```

正式な処理順序は、次のとおりです。

```text
雑誌コードを正規化する
↓
空である場合は空のリストを返す
↓
雑誌コードを検証する
↓
Repositoryで検索する
```

---

## 27. `update_book()`

### 27.1 目的

既存の書籍情報を正規化および検証し、更新します。

```python
def update_book(
    self,
    book_item: BookItem,
) -> bool:
    ...
```

---

### 27.2 ID必須条件

`book_item.id` が `None` の場合は、`ValueError` を送出します。

```python
if book_item.id is None:
    raise ValueError(
        "更新対象のBookItemにはidが必要です。"
    )
```

Repositoryにも同じ防御処理がありますが、Serviceでも早い段階で確認します。

---

### 27.3 存在確認

更新前に、対象IDが存在するか確認します。

```python
existing = self._repository.get_by_id(
    book_item.id
)
```

存在しない場合は、`False` を返します。

```python
if existing is None:
    return False
```

---

### 27.4 正規化と検証

更新対象の値にも、登録時と同じ正規化および検証を行います。

対象は、次のとおりです。

* title。
* isbn。
* magazine_code。
* author。
* publisher。
* publication_format。
* description。
* completion_month。
* notes。

---

### 27.5 `created_at` の扱い

更新時には、引数の `book_item.created_at` を信用しません。

Repositoryが `created_at` を更新しない設計であるため、SQLite上の値は保持されます。

ただし、Serviceが生成する更新用モデルにも、既存データの `created_at` を設定します。

```python
created_at=existing.created_at
```

---

### 27.6 `updated_at` の扱い

更新時には、必ず現在日時を新しく生成します。

```python
updated_at=self._current_timestamp()
```

GUIから渡された `updated_at` は使用しません。

---

### 27.7 更新用モデル

Service内で正規化済みの新しい `BookItem` を生成します。

```python
normalized_book_item = BookItem(
    id=book_item.id,
    title=normalized_title,
    isbn=normalized_isbn,
    magazine_code=normalized_magazine_code,
    author=normalized_author,
    publisher=normalized_publisher,
    publication_format=normalized_publication_format,
    description=normalized_description,
    completion_month=normalized_completion_month,
    notes=normalized_notes,
    created_at=existing.created_at,
    updated_at=current_timestamp,
)
```

元の `book_item` は変更しません。

---

### 27.8 戻り値

Repositoryの `update()` の戻り値を、そのまま返します。

```python
return self._repository.update(
    normalized_book_item
)
```

更新成功時は `True`、対象が存在しない場合は `False` です。

---

## 28. 更新時の重複候補

初期Versionでは、`update_book()` 内で重複を理由に更新を拒否しません。

GUIが必要に応じて、更新前に `find_duplicate_candidates()` を呼び出します。

ただし、更新対象自身が重複候補へ含まれる可能性があります。

将来、更新専用の重複確認が必要になった場合は、次の引数追加を検討します。

```python
exclude_book_id: int | None = None
```

初期Versionでは導入しません。

---

## 29. `delete_book()`

### 29.1 目的

IDを指定して書籍情報を削除します。

```python
def delete_book(
    self,
    book_id: int,
) -> bool:
    ...
```

---

### 29.2 存在確認

初期Versionでは、削除前の存在確認をServiceでは行いません。

Repositoryの `delete()` が、削除対象の有無を `bool` で返します。

```python
return self._repository.delete(
    book_id
)
```

不要なSELECTを避けるためです。

---

## 30. 非公開メソッド一覧

初期Versionでは、次の非公開メソッドを設けます。

```python
@staticmethod
def _normalize_title(
    title: str,
) -> str:
    ...

@staticmethod
def _normalize_optional_text(
    value: str | None,
) -> str | None:
    ...

@staticmethod
def _normalize_isbn(
    isbn: str | None,
) -> str | None:
    ...

def _current_timestamp(self) -> str:
    ...
```

Validator導入後は、検証処理をValidatorモジュールへ委譲します。

---

## 31. Validatorの配置候補

Validatorは、次の構成を想定します。

```text
src/
└── book_manager/
    └── validators/
        ├── __init__.py
        ├── isbn_validator.py
        ├── magazine_code_validator.py
        └── completion_month_validator.py
```

書籍名の必須確認は単純であるため、初期VersionではService内の `_normalize_title()` で行います。

将来、文字数制限や禁止文字などが増えた場合は、`title_validator.py` へ分離します。

---

## 32. 例外方針

初期Versionでは、Service独自の例外階層を導入しません。

入力値が無効な場合は、`ValueError` を送出します。

例：

```python
raise ValueError(
    "書籍名を入力してください。"
)
```

```python
raise ValueError(
    "ISBNの形式が正しくありません。"
)
```

SQLiteから発生した例外は、Repositoryからそのまま伝播します。

例：

```text
sqlite3.IntegrityError
sqlite3.OperationalError
sqlite3.DatabaseError
```

GUI層が、これらの例外を捕捉して利用者向けのメッセージを表示します。

---

## 33. GUIとの責務境界

GUIは、次の処理を担当します。

* 入力欄の値を取得する。
* Serviceを呼び出す。
* `ValueError` を捕捉する。
* データベース例外を捕捉する。
* 利用者へメッセージを表示する。
* 重複候補を一覧表示する。
* 登録継続の確認を行う。
* 一覧画面を更新する。
* 選択中の書籍IDを管理する。

Serviceは、次の処理を行いません。

* Tkinterウィジェットの生成。
* EntryやTextから値を取得する。
* messageboxを表示する。
* Treeviewへ値を挿入する。
* ボタンの有効・無効を切り替える。
* ウィンドウを開閉する。

---

## 34. Repositoryとの責務境界

Serviceは、次を担当します。

```text
正規化
検証
日時生成
モデル生成
処理順序の制御
Repositoryの呼び出し
```

Repositoryは、次を担当します。

```text
SQLite接続
SQL実行
トランザクション
行変換
CRUD
```

ServiceにSQLを記述してはいけません。

Repositoryに業務上の入力検証を記述してはいけません。

---

## 35. 外部APIとの責務境界

初期Versionの `BookService` は、openBDやGoogle Books APIを直接呼び出しません。

将来、書籍情報取得機能は、別のServiceまたはClientへ分離します。

想定構成は、次のとおりです。

```text
GUI
↓
BookLookupService
├── OpenBDClient
└── GoogleBooksClient
```

取得した候補を利用者が確認した後、`BookService.add_book()` へ渡します。

これにより、ローカル書籍管理と外部API通信を分離します。

---

## 36. 実装予定コード構成

```python
"""Application service for book management."""

from collections.abc import Callable
from datetime import datetime

from book_manager.models.book_item import BookItem
from book_manager.repositories.book_repository import BookRepository
from book_manager.validators.completion_month_validator import (
    validate_completion_month,
)
from book_manager.validators.isbn_validator import validate_isbn
from book_manager.validators.magazine_code_validator import (
    validate_magazine_code,
)


class BookService:
    """書籍管理に関するアプリケーションロジックを担当する。"""

    def __init__(
        self,
        repository: BookRepository,
        now_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._repository = repository
        self._now_provider = now_provider

    def add_book(
        self,
        *,
        title: str,
        isbn: str | None = None,
        magazine_code: str | None = None,
        author: str | None = None,
        publisher: str | None = None,
        publication_format: str | None = None,
        description: str | None = None,
        completion_month: str | None = None,
        notes: str | None = None,
    ) -> BookItem:
        ...

    def find_duplicate_candidates(
        self,
        *,
        isbn: str | None = None,
        magazine_code: str | None = None,
    ) -> list[BookItem]:
        ...

    def get_book(
        self,
        book_id: int,
    ) -> BookItem | None:
        ...

    def get_all_books(
        self,
    ) -> list[BookItem]:
        ...

    def search_books_by_title(
        self,
        keyword: str,
    ) -> list[BookItem]:
        ...

    def find_books_by_isbn(
        self,
        isbn: str,
    ) -> list[BookItem]:
        ...

    def find_books_by_magazine_code(
        self,
        magazine_code: str,
    ) -> list[BookItem]:
        ...

    def update_book(
        self,
        book_item: BookItem,
    ) -> bool:
        ...

    def delete_book(
        self,
        book_id: int,
    ) -> bool:
        ...

    @staticmethod
    def _normalize_title(
        title: str,
    ) -> str:
        ...

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
    ) -> str | None:
        ...

    @staticmethod
    def _normalize_isbn(
        isbn: str | None,
    ) -> str | None:
        ...

    def _current_timestamp(self) -> str:
        ...
```

---

## 37. テスト方針

Serviceテストでは、実際の `BookRepository` と一時SQLiteデータベースを使用します。

pytestの `tmp_path` を利用し、各テストで独立したデータベースを作成します。

日時は、固定した `now_provider` を渡します。

```python
fixed_now = datetime(
    2026,
    7,
    22,
    10,
    30,
    0,
)

service = BookService(
    repository,
    now_provider=lambda: fixed_now,
)
```

初期Versionでは、Repositoryのモックは使用しません。

---

## 38. テスト用fixture

想定するfixtureは、次のとおりです。

```python
@pytest.fixture
def service(
    tmp_path: Path,
) -> BookService:
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    repository = BookRepository(database_path)

    fixed_now = datetime(
        2026,
        7,
        22,
        10,
        30,
        0,
    )

    return BookService(
        repository,
        now_provider=lambda: fixed_now,
    )
```

---

## 39. 登録テスト

最低限、次のテストを実装します。

* 書籍を登録できる。
* 登録後にIDが設定される。
* 書籍名の前後空白が除去される。
* 任意項目の前後空白が除去される。
* 空文字列が `None` へ変換される。
* ISBNのハイフンが除去される。
* ISBNの半角空白が除去される。
* `created_at` が設定される。
* `updated_at` が設定される。
* `created_at` と `updated_at` が同じになる。
* 書籍名が空の場合に `ValueError` が発生する。
* 無効なISBNの場合に `ValueError` が発生する。
* 無効な雑誌コードの場合に `ValueError` が発生する。
* 無効な読了年月の場合に `ValueError` が発生する。

---

## 40. 取得テスト

最低限、次のテストを実装します。

* IDで書籍を取得できる。
* 存在しないIDでは `None` を返す。
* 全書籍を取得できる。
* データがない場合は空のリストを返す。
* Repositoryと同じID降順で取得できる。

---

## 41. 検索テスト

最低限、次のテストを実装します。

* 書籍名で部分一致検索できる。
* 検索語の前後空白が除去される。
* 空の検索語では全件取得する。
* ISBNを正規化して検索できる。
* 雑誌コードを正規化して検索できる。
* 該当しない場合は空のリストを返す。
* 無効なISBNでは `ValueError` が発生する。
* 無効な雑誌コードでは `ValueError` が発生する。

---

## 42. 重複候補テスト

最低限、次のテストを実装します。

* ISBN一致の候補を取得できる。
* 雑誌コード一致の候補を取得できる。
* ISBNと雑誌コードの両方で検索できる。
* 同じ書籍が両方に一致しても1件だけ返す。
* 候補をID降順で返す。
* 両方が空の場合は空のリストを返す。
* ISBNを正規化して検索できる。
* 無効なISBNでは `ValueError` が発生する。

---

## 43. 更新テスト

最低限、次のテストを実装します。

* 既存書籍を更新できる。
* 更新値が正規化される。
* ISBNが正規化される。
* `created_at` が保持される。
* `updated_at` が現在日時へ更新される。
* 入力モデルを直接変更しない。
* 存在しないIDでは `False` を返す。
* `id=None` では `ValueError` が発生する。
* 書籍名が空の場合に `ValueError` が発生する。
* 無効なISBNでは `ValueError` が発生する。
* 無効な読了年月では `ValueError` が発生する。

---

## 44. 削除テスト

最低限、次のテストを実装します。

* 既存書籍を削除できる。
* 削除後に取得できない。
* 存在しないIDでは `False` を返す。

---

## 45. 初期Versionで導入しないもの

次の機能は、初期Versionでは導入しません。

* Serviceの抽象基底クラス。
* ServiceのProtocol。
* 依存性注入フレームワーク。
* Service独自の例外階層。
* 非同期処理。
* バッチ登録。
* バッチ更新。
* バッチ削除。
* トランザクションのService管理。
* 複数RepositoryをまたぐUnit of Work。
* GUI表示用のViewModel。
* ページング。
* 複数項目の自由検索。
* 全文検索。
* タグ管理。
* 著者マスタ管理。
* 出版社マスタ管理。
* 外部API呼び出し。
* 自動重複拒否。
* 自動マージ。
* 論理削除。
* 更新履歴。
* Undo機能。

---

## 46. 将来の拡張候補

必要性が確認された場合に、次の拡張を検討します。

* 更新専用の重複候補検索。
* 著者名検索。
* 出版社検索。
* 読了年月検索。
* 複数項目検索。
* タグ検索。
* 検索条件オブジェクト。
* ページング。
* 並び順指定。
* ServiceResult型。
* 独自ValidationError。
* DuplicateCandidate型。
* Unit of Work。
* バッチ操作。
* 論理削除。
* 更新履歴。
* 著者名正規化Service。
* 外部API取得結果との統合。

---

## 47. Design Freeze条件

次の項目が承認された時点で、Version 0.1をDesign Freezeとします。

* クラス名を `BookService` とする。
* Repositoryをコンストラクターで受け取る。
* 日時取得関数をコンストラクターで受け取れるようにする。
* Serviceが入力値の正規化を行う。
* Serviceが入力値の検証を行う。
* Serviceが日時を生成する。
* GUIはRepositoryを直接呼び出さない。
* ServiceはSQLを記述しない。
* ServiceはGUIを操作しない。
* 登録時は個別の値をキーワード引数で受け取る。
* Service内で `BookItem` を生成する。
* 空の任意文字列を `None` へ変換する。
* ISBNから半角ハイフンと半角空白を除去する。
* ISBN、雑誌コード、読了年月の検証をValidatorへ委譲する。
* 書籍名が空の場合は `ValueError` を送出する。
* 登録日時と更新日時をServiceが設定する。
* 更新時に既存の `created_at` を保持する。
* 更新時に新しい `updated_at` を生成する。
* 入力された `BookItem` を直接変更しない。
* 重複確認と登録処理を分離する。
* 重複候補検索はISBNと雑誌コードを対象とする。
* 登録および更新では重複を自動拒否しない。
* 空の書籍名検索では全件を返す。
* 初期VersionではService独自例外を導入しない。
* 初期Versionでは外部APIをServiceへ含めない。

---

## 48. 検討事項

Design Freeze前に、次の点を最終確認します。

### 48.1 更新メソッドの引数

現在案：

```python
def update_book(
    self,
    book_item: BookItem,
) -> bool:
```

別案として、登録と同じように個別の値を受け取る方法があります。

```python
def update_book(
    self,
    *,
    book_id: int,
    title: str,
    isbn: str | None = None,
    ...
) -> bool:
```

初期案では、GUIが選択中の `BookItem` を保持することを想定し、`BookItem` を受け取る方式とします。

---

### 48.2 空の検索語

現在案では、空の検索語を全件取得として扱います。

```python
search_books_by_title("")
```

結果：

```python
get_all_books()
```

GUIで検索欄を消したときに一覧へ戻しやすいため、この方針を推奨します。

---

### 48.3 重複候補確認

重複候補検索と登録を分離します。

これにより、GUIは次の順序で処理できます。

```text
入力値を取得する
↓
find_duplicate_candidates()を呼ぶ
↓
候補があれば確認ダイアログを表示する
↓
利用者が続行を選ぶ
↓
add_book()を呼ぶ
```

この方式を初期Versionの正式案とします。

---

## 49. 次の作業

この設計書のレビューとDesign Freeze後、次の順序で進めます。

```text
book_service_design_review.mdを作成する
↓
BookService設計を正式承認する
↓
Validator設計を作成する
↓
Validator設計をレビューする
↓
Validatorを実装する
↓
Validatorテストを作成する
↓
BookServiceを実装する
↓
BookServiceテストを作成する
↓
全テストを実行する
↓
GUI設計へ進む
```
