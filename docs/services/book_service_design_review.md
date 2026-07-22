# BookService設計レビュー

Version : 0.1
Last Updated : 2026-07-22
Status : Approved

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおける `BookService` 設計のレビュー結果と正式承認を記録するものです。

レビュー対象は、次の文書です。

```text
docs/services/book_service_design.md
```

`BookService` は、GUIと `BookRepository` の間に位置し、書籍情報の正規化、検証、日時生成、モデル生成および処理順序の制御を担当します。

本レビューでは、次の設計との整合性を確認しました。

* `BookItem` モデル設計。
* `BookRepository` 設計。
* SQLiteデータベース設計。
* プロジェクト構成設計。
* Validatorとの責務境界。
* GUIとの責務境界。
* テスト可能性。
* 初期Versionとしての実装規模。

---

## 2. レビュー対象

| 文書                       | 対象Version | レビュー前の状態 |
| ------------------------ | --------: | -------- |
| `book_service_design.md` |       0.1 | Draft    |

---

## 3. レビュー実施日

```text
2026-07-22
```

---

## 4. レビュー観点

本レビューでは、主に次の項目を確認しました。

* Serviceの責務が明確か。
* GUIとRepositoryの責務が適切に分離されているか。
* ServiceがSQLやSQLite接続を担当していないか。
* 入力値の正規化方針が一貫しているか。
* Validatorとの役割分担が明確か。
* `BookItem` の生成責務が適切か。
* 登録時と更新時の処理順序が明確か。
* `created_at` と `updated_at` の扱いが適切か。
* Repositoryの公開メソッドと整合しているか。
* 重複候補確認と登録処理の分離が適切か。
* 更新メソッドの引数形式が適切か。
* 存在しないデータの扱いが一貫しているか。
* 例外方針が初期Versionとして妥当か。
* テスト時に現在日時を固定できるか。
* 初期Versionとして過剰設計になっていないか。

---

## 5. レビュー結果

レビュー結果は、次のとおりです。

```text
承認
```

`BookService` 設計は、GUIと永続化層の間に必要なアプリケーションロジックを適切に定義しています。

重大な修正事項はありません。

ただし、設計を明確にするため、次の事項を正式な補足方針として採用します。

* `BookService` は具象クラスである `BookRepository` を受け取る。
* 初期VersionではRepositoryの抽象基底クラスやProtocolを導入しない。
* `update_book()` は `BookItem` を受け取る方式を採用する。
* `add_book()` は個別の値をキーワード専用引数で受け取る。
* `find_duplicate_candidates()` と `add_book()` は分離する。
* `find_duplicate_candidates()` は候補の提示のみを担当し、登録可否を判断しない。
* `find_duplicate_candidates()` はISBNと雑誌コードの両方に一致した同一書籍をIDで重複排除する。
* 登録および更新では、重複を理由に自動拒否しない。
* 検索語が空の場合は全件取得とする。
* 登録時と更新時で共通する正規化処理は、非公開メソッドへ集約する。
* Validatorは、正規化後かつ `None` ではない値だけを検証する。
* 更新対象の存在確認は、正規化および検証より先に行う。
* 更新対象が存在しない場合は、入力値を検証せず `False` を返す。
* Serviceは入力として受け取った `BookItem` を変更しない。
* Service独自の例外階層は初期Versionでは導入しない。

以上を反映し、Version 0.1をDesign Freezeとします。

---

## 6. クラス名

クラス名を次の名称とする設計を承認します。

```python
BookService
```

書籍管理に関するアプリケーションロジックを担当することが明確な名称です。

---

## 7. 配置場所

実装ファイルを次の場所へ配置する設計を承認します。

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

プロジェクト構成設計との不整合はありません。

---

## 8. Serviceの責務

`BookService` が次の処理を担当する設計を承認します。

```text
入力値の正規化
必須項目の確認
Validatorの呼び出し
現在日時の生成
BookItemの生成
Repositoryの呼び出し
処理順序の制御
重複候補の統合
Repositoryの戻り値の受け渡し
```

Serviceは、個別のSQLやSQLite接続方法を知りません。

---

## 9. Serviceに含めない責務

次の処理を `BookService` に含めない設計を承認します。

```text
SQLite接続
SQL実行
トランザクション管理
sqlite3.Rowの変換
データベース初期化
スキーマVersion管理
Tkinterウィジェットの操作
メッセージボックスの表示
利用者への登録確認
外部API通信
書籍情報取得元の選択
バックアップ処理
```

---

## 10. 依存方向

正式な依存方向を、次のとおり承認します。

```text
GUI
↓
BookService
├── Validators
└── BookRepository
    ↓
    database.connection
        ↓
        SQLite
```

次の逆方向の依存は禁止します。

```text
BookRepository → BookService
BookService → GUI
Validator → BookService
BookItem → BookService
```

---

## 11. コンストラクター

次のコンストラクター設計を承認します。

```python
from collections.abc import Callable
from datetime import datetime


def __init__(
    self,
    repository: BookRepository,
    now_provider: Callable[[], datetime] = datetime.now,
) -> None:
    self._repository = repository
    self._now_provider = now_provider
```

---

## 12. Repositoryの注入

`BookService` が `BookRepository` を外部から受け取る設計を承認します。

通常実行時は、アプリケーションの起動処理でRepositoryを生成します。

```python
repository = BookRepository(database_path)
service = BookService(repository)
```

Service内でデータベースパスを取得したり、Repositoryを生成したりしません。

この構成により、次の責務を分離できます。

```text
データベースパスの決定
→ アプリケーション起動処理

Repositoryの生成
→ アプリケーション起動処理

書籍管理処理
→ BookService
```

---

## 13. 抽象化方針

初期Versionでは、次を導入しない設計を承認します。

```text
Repositoryの抽象基底クラス
RepositoryのProtocol
Serviceの抽象基底クラス
ServiceのProtocol
依存性注入フレームワーク
```

現在のRepositoryは `BookRepository` の1実装だけであり、差し替えの具体的な必要性が確認されていません。

テストでは実際の `BookRepository` と一時SQLiteデータベースを使用します。

必要性が確認される前に抽象化を導入しない方針は、初期Versionとして妥当です。

---

## 14. 現在日時の注入

現在日時を取得する関数を外部から受け取れる設計を承認します。

```python
now_provider: Callable[[], datetime] = datetime.now
```

通常実行時は、既定値として `datetime.now` を使用します。

```python
service = BookService(repository)
```

テスト時は、固定日時を返す関数を渡します。

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

これにより、日時に依存するテストを再現可能にできます。

---

## 15. 日時形式

SQLiteへ保存する日時を次の形式とする設計を承認します。

```text
YYYY-MM-DD HH:MM:SS
```

日時生成は、次の非公開メソッドへ集約します。

```python
def _current_timestamp(self) -> str:
    return self._now_provider().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
```

次の情報は保存しません。

```text
マイクロ秒
タイムゾーン情報
曜日
ロケール依存表記
```

初期のローカルデスクトップアプリとして、既存のデータベース設計と整合しています。

---

## 16. 公開メソッド

初期Versionでは、次の公開メソッドを実装する設計を承認します。

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
```

登録、取得、検索、重複候補確認、更新および削除を網羅しており、初期Versionとして適切です。

---

## 17. `add_book()` の引数形式

登録時に個別の値をキーワード専用引数で受け取る設計を承認します。

```python
def add_book(
    self,
    *,
    title: str,
    isbn: str | None = None,
    ...
) -> BookItem:
    ...
```

GUIは未保存の `BookItem` を生成しません。

正式な呼び出し形式は、次のとおりです。

```python
registered = service.add_book(
    title="吾輩は猫である",
    isbn="978-4-10-101001-4",
    author="夏目漱石",
)
```

この方式には、次の利点があります。

* GUIがモデル生成責務を持たない。
* Serviceが正規化後の値だけでモデルを生成できる。
* 日時の設定をServiceへ集約できる。
* 位置引数の取り違えを防げる。
* 登録用入力値と保存済みモデルを区別できる。

---

## 18. `update_book()` の引数形式

更新時は `BookItem` を受け取る設計を承認します。

```python
def update_book(
    self,
    book_item: BookItem,
) -> bool:
    ...
```

登録時と異なる方式ですが、初期Versionでは次の理由から妥当です。

* GUIは選択中の保存済み書籍を `BookItem` として保持できる。
* 更新対象IDをモデルと一緒に扱える。
* 全項目を個別引数として再定義する重複を避けられる。
* Repositoryの `update()` と自然に対応する。
* 更新前後のモデル比較をテストしやすい。

Serviceは受け取ったモデルを直接変更せず、正規化済みの新しい `BookItem` を生成します。

---

## 19. 登録と更新の引数形式が異なる理由

登録時は、まだ保存済みモデルが存在しません。

そのため、GUIから個別の入力値を受け取り、Serviceが次を設定します。

```text
id
created_at
updated_at
```

更新時は、対象IDを持つ保存済みモデルが存在します。

そのため、`BookItem` を受け取り、Serviceが次を再構成します。

```text
正規化済みの各属性
既存のcreated_at
新しいupdated_at
```

登録と更新で異なる引数形式を採用することは、それぞれのユースケースに対応した設計として問題ありません。

---

## 20. 正規化方針

Serviceが入力値を正規化する設計を承認します。

初期Versionで行う正規化は、次のとおりです。

```text
titleの前後空白を除去する
任意文字列の前後空白を除去する
空の任意文字列をNoneへ変換する
ISBNの前後空白を除去する
ISBN内の半角ハイフンを除去する
ISBN内の半角空白を除去する
```

Validatorは正規化後の値を受け取ります。

---

## 21. 書籍名の正規化

次の非公開メソッドを使用する設計を承認します。

```python
@staticmethod
def _normalize_title(
    title: str,
) -> str:
    normalized = title.strip()

    if normalized == "":
        raise ValueError(
            "書籍名を入力してください。"
        )

    return normalized
```

書籍名の必須確認と前後空白除去は密接に関連する単純な処理であるため、初期VersionではService内に置きます。

初期Versionでは、次の検証を行いません。

```text
最大文字数
最小文字数
禁止文字
文字種制限
同名書籍の拒否
```

---

## 22. 任意文字列の正規化

次の非公開メソッドを使用する設計を承認します。

```python
@staticmethod
def _normalize_optional_text(
    value: str | None,
) -> str | None:
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

ただし、雑誌コードおよび読了年月は、この正規化後にValidatorへ渡します。

---

## 23. ISBNの正規化

次の非公開メソッドを使用する設計を承認します。

```python
@staticmethod
def _normalize_isbn(
    isbn: str | None,
) -> str | None:
    if isbn is None:
        return None

    normalized = isbn.strip()
    normalized = normalized.replace("-", "")
    normalized = normalized.replace(" ", "")

    if normalized == "":
        return None

    return normalized
```

初期Versionで自動除去する文字は、次の2種類に限定します。

```text
半角ハイフン
半角空白
```

次の文字の自動変換や除去は、初期Versionでは行いません。

```text
全角数字
全角空白
全角ハイフン
長音記号
ダッシュ
タブ
改行
```

不明確な文字を広く変換しないことで、意図しない値の受け入れを防ぎます。

---

## 24. 正規化と検証の順序

正式な処理順序を、次のとおり承認します。

```text
入力値を受け取る
↓
正規化する
↓
正規化後にNoneか確認する
↓
NoneでなければValidatorを呼び出す
↓
正規化済みの値をBookItemへ設定する
```

Validatorへ正規化前の値を渡してはいけません。

例えば、次のISBNはServiceで正規化してから検証します。

```text
978-4-10-101001-4
↓
9784101010014
↓
validate_isbn()
```

---

## 25. Validatorとの責務境界

Validatorは、入力形式および値の妥当性確認を担当します。

Serviceは、Validatorを呼び出す順序と条件を管理します。

正式な役割分担は、次のとおりです。

| 処理              | Service | Validator |
| --------------- | ------: | --------: |
| 前後空白除去          |      担当 |     担当しない |
| 空文字列からNoneへの変換  |      担当 |     担当しない |
| ISBNの半角ハイフン除去   |      担当 |     担当しない |
| ISBNの桁数確認       |   担当しない |        担当 |
| ISBNの文字種確認      |   担当しない |        担当 |
| ISBNのチェックデジット確認 |   担当しない |        担当 |
| 雑誌コードの形式確認      |   担当しない |        担当 |
| 読了年月の形式確認       |   担当しない |        担当 |
| Validatorを呼ぶか判断 |      担当 |     担当しない |
| エラーメッセージの表示     |   担当しない |     担当しない |

---

## 26. Validatorの配置

Validatorを次の場所へ配置する設計を承認します。

```text
src/
└── book_manager/
    └── validators/
        ├── __init__.py
        ├── isbn_validator.py
        ├── magazine_code_validator.py
        └── completion_month_validator.py
```

初期Versionで想定する公開関数は、次のとおりです。

```python
validate_isbn(isbn: str) -> None

validate_magazine_code(
    magazine_code: str,
) -> None

validate_completion_month(
    completion_month: str,
) -> None
```

有効な場合は何も返さず、無効な場合は `ValueError` を送出します。

---

## 27. Validatorを先に実装する方針

`BookService` はValidatorへ依存します。

そのため、次の実装順序を承認します。

```text
Validator設計
↓
Validator設計レビュー
↓
Validator実装
↓
Validatorテスト
↓
BookService実装
↓
BookServiceテスト
```

依存先を先に完成させることで、Service実装時に未完成の仮処理を置かずに済みます。

---

## 28. `add_book()` の処理順序

正式な処理順序を次のとおり承認します。

```text
titleを正規化する
↓
ISBNを正規化する
↓
雑誌コードを正規化する
↓
authorを正規化する
↓
publisherを正規化する
↓
publication_formatを正規化する
↓
descriptionを正規化する
↓
completion_monthを正規化する
↓
notesを正規化する
↓
ISBNがあれば検証する
↓
雑誌コードがあれば検証する
↓
読了年月があれば検証する
↓
現在日時を1回取得する
↓
BookItemを生成する
↓
Repositoryへ登録する
↓
登録後のBookItemを返す
```

設計書に記載された「重複候補を検索する」は、`add_book()` の正式処理には含めません。

重複候補検索は `find_duplicate_candidates()` へ分離します。

---

## 29. 登録日時と更新日時

登録時は、現在日時を1回だけ取得します。

```python
current_timestamp = self._current_timestamp()
```

生成する `BookItem` には、同じ値を設定します。

```python
created_at=current_timestamp
updated_at=current_timestamp
```

`_current_timestamp()` を2回呼び出してはいけません。

処理の境界で秒が変化すると、登録直後にもかかわらず `created_at` と `updated_at` が異なる可能性があるためです。

---

## 30. 登録時のモデル生成

登録時にServiceが生成するモデルは、次の形式とします。

```python
book_item = BookItem(
    title=normalized_title,
    isbn=normalized_isbn,
    magazine_code=normalized_magazine_code,
    author=normalized_author,
    publisher=normalized_publisher,
    publication_format=normalized_publication_format,
    description=normalized_description,
    completion_month=normalized_completion_month,
    notes=normalized_notes,
    created_at=current_timestamp,
    updated_at=current_timestamp,
)
```

`id` は明示せず、既定値の `None` とします。

その後、Repositoryの `add()` を呼び出します。

```python
return self._repository.add(book_item)
```

---

## 31. 重複候補確認と登録の分離

重複候補確認と登録処理を分離する設計を承認します。

正式なGUI処理は、次のとおりです。

```text
入力欄からISBNと雑誌コードを取得する
↓
find_duplicate_candidates()を呼び出す
↓
候補がなければ登録へ進む
↓
候補があれば利用者へ表示する
↓
利用者が登録継続を選択する
↓
add_book()を呼び出す
```

Serviceは利用者への確認を行いません。

`add_book()` は重複候補の有無にかかわらず、正規化と検証に成功すれば登録します。

---

## 32. `find_duplicate_candidates()`

次の公開メソッドを設ける設計を承認します。

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

## 33. 重複候補検索の処理順序

正式な処理順序を、次のとおり承認します。

```text
ISBNを正規化する
↓
雑誌コードを正規化する
↓
ISBNがあれば検証する
↓
雑誌コードがあれば検証する
↓
ISBNがあればRepositoryで検索する
↓
雑誌コードがあればRepositoryで検索する
↓
結果を統合する
↓
同じIDを重複排除する
↓
ID降順で返す
```

ISBNと雑誌コードの両方が `None` の場合は、空のリストを返します。

---

## 34. 重複候補の統合

ISBN検索と雑誌コード検索の両方に同じ書籍が含まれる可能性があります。

同じIDを持つ書籍は1件へまとめます。

実装方針は、次のとおりです。

```python
books_by_id: dict[int, BookItem] = {}

for candidate in candidates:
    if candidate.id is not None:
        books_by_id[candidate.id] = candidate
```

その後、ID降順で返します。

```python
return sorted(
    books_by_id.values(),
    key=lambda book_item: book_item.id or 0,
    reverse=True,
)
```

---

## 35. IDが `None` の候補

Repositoryから取得した `BookItem` は、正常であれば必ずIDを持ちます。

ただし、Serviceでは防御的に `id is None` の候補を重複候補一覧へ含めません。

```python
if candidate.id is None:
    continue
```

異常な候補に対して新しいIDを生成したり、オブジェクト自体をキーとして扱ったりしません。

---

## 36. 重複候補の意味

`find_duplicate_candidates()` の戻り値は、重複が確定したデータではありません。

あくまで利用者が確認するための候補です。

例えば、同じISBNで複数冊を所有している場合や、同じ雑誌コードで複数レコードを管理する場合があります。

そのため、次の処理はServiceで行いません。

```text
自動登録拒否
既存データへの上書き
自動マージ
自動削除
重複フラグの保存
```

---

## 37. `get_book()`

IDによる単一取得をRepositoryへ委譲する設計を承認します。

```python
def get_book(
    self,
    book_id: int,
) -> BookItem | None:
    return self._repository.get_by_id(book_id)
```

存在しない場合は `None` を返します。

初期Versionでは、次の検証を追加しません。

```text
book_idが正数か
book_idが整数か
book_idが上限を超えていないか
```

型ヒントに従った呼び出しを前提とし、存在確認はRepositoryに委譲します。

---

## 38. `get_all_books()`

一覧取得をRepositoryへ委譲する設計を承認します。

```python
def get_all_books(
    self,
) -> list[BookItem]:
    return self._repository.get_all()
```

RepositoryがID降順で返すため、Serviceで再度並べ替えません。

---

## 39. `search_books_by_title()`

書籍名検索の設計を承認します。

```python
def search_books_by_title(
    self,
    keyword: str,
) -> list[BookItem]:
    ...
```

正式な処理順序は、次のとおりです。

```text
検索語の前後空白を除去する
↓
空文字列か確認する
↓
空なら全件取得する
↓
空でなければRepositoryで部分一致検索する
```

---

## 40. 空の検索語

空の検索語では全件取得とする設計を承認します。

```python
normalized_keyword = keyword.strip()

if normalized_keyword == "":
    return self._repository.get_all()
```

GUIの検索欄を消去した際に、通常一覧へ戻す処理として利用できます。

空文字列をRepositoryの `LIKE "%%"` に渡さず、明示的に `get_all()` を呼び出します。

---

## 41. `find_books_by_isbn()`

ISBNの完全一致検索をService経由で行う設計を承認します。

正式な処理順序は、次のとおりです。

```text
ISBNを正規化する
↓
正規化後にNoneなら空のリストを返す
↓
ISBNを検証する
↓
Repositoryで検索する
```

想定実装は、次のとおりです。

```python
normalized_isbn = self._normalize_isbn(isbn)

if normalized_isbn is None:
    return []

validate_isbn(normalized_isbn)

return self._repository.find_by_isbn(
    normalized_isbn
)
```

---

## 42. `find_books_by_magazine_code()`

雑誌コードの完全一致検索をService経由で行う設計を承認します。

正式な処理順序は、次のとおりです。

```text
雑誌コードを正規化する
↓
正規化後にNoneなら空のリストを返す
↓
雑誌コードを検証する
↓
Repositoryで検索する
```

雑誌コードの正規化には `_normalize_optional_text()` を使用します。

---

## 43. `update_book()`

既存書籍を更新する設計を承認します。

```python
def update_book(
    self,
    book_item: BookItem,
) -> bool:
    ...
```

---

## 44. 更新処理の正式な順序

正式な処理順序を、次のとおり承認します。

```text
book_item.idがNoneか確認する
↓
対象IDをRepositoryで取得する
↓
存在しなければFalseを返す
↓
titleを正規化する
↓
その他の項目を正規化する
↓
ISBNを検証する
↓
雑誌コードを検証する
↓
読了年月を検証する
↓
現在日時を生成する
↓
新しいBookItemを生成する
↓
Repositoryへ更新を依頼する
↓
boolを返す
```

---

## 45. 更新対象の存在確認を先に行う理由

更新対象が存在しない場合は、入力値の正規化および検証を行わず `False` を返します。

```python
existing = self._repository.get_by_id(
    book_item.id
)

if existing is None:
    return False
```

この順序には、次の利点があります。

* 存在しないデータに対する不要な検証を避けられる。
* Repositoryの更新結果と意味を統一できる。
* 存在しないIDに無効な入力値が含まれていても、対象不存在を優先できる。
* GUIが対象削除済みなどの状況を明確に判断できる。

---

## 46. 更新時のID必須条件

`book_item.id` が `None` の場合は、`ValueError` を送出します。

```python
if book_item.id is None:
    raise ValueError(
        "更新対象のBookItemにはidが必要です。"
    )
```

これは入力内容の妥当性ではなく、Serviceメソッドの呼び出し条件に対する防御処理です。

Repositoryにも同じ確認がありますが、Serviceでも早期に確認します。

---

## 47. 更新時の `created_at`

更新時は、入力モデルの `created_at` を使用しません。

既存データから取得した値を、新しいモデルへ設定します。

```python
created_at=existing.created_at
```

これにより、GUI側で誤った作成日時が設定されても、既存の作成日時を保持できます。

Repositoryは `created_at` をUPDATE対象としていませんが、Serviceが生成するモデルにも正しい値を保持させます。

---

## 48. 更新時の `updated_at`

更新時は、入力モデルの `updated_at` を使用しません。

Serviceが新しい現在日時を生成します。

```python
updated_at=self._current_timestamp()
```

これにより、GUIや呼び出し側が更新日時を決定することを防ぎます。

---

## 49. 更新時の入力モデル

Serviceは、引数として受け取った `BookItem` を変更しません。

次のような代入は禁止します。

```python
book_item.title = normalized_title
book_item.updated_at = current_timestamp
```

正式には、新しいモデルを生成します。

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

---

## 50. 更新時の重複確認

`update_book()` 内では、重複を理由に更新を拒否しません。

初期Versionでは、更新前の重複候補確認も自動実行しません。

必要な場合、GUIが更新前に `find_duplicate_candidates()` を呼び出します。

ただし、現在の設計では更新対象自身が候補に含まれる可能性があります。

初期Versionでは、GUIが対象IDと候補IDを比較して判断します。

将来、必要性が確認された場合は、次の機能追加を検討します。

```python
exclude_book_id: int | None = None
```

---

## 51. 更新の戻り値

Repositoryの `update()` が返す `bool` を、そのまま返します。

```python
return self._repository.update(
    normalized_book_item
)
```

意味は、次のとおりです。

```text
True  : 更新対象が存在し、UPDATEが作用した
False : 更新対象が存在しなかった
```

Serviceで独自の結果オブジェクトへ変換しません。

---

## 52. `delete_book()`

削除処理をRepositoryへ委譲する設計を承認します。

```python
def delete_book(
    self,
    book_id: int,
) -> bool:
    return self._repository.delete(book_id)
```

削除前の存在確認は行いません。

RepositoryがDELETEの処理結果を `bool` で返すため、事前SELECTは不要です。

利用者への削除確認はGUIが担当します。

---

## 53. 例外方針

初期Versionでは、Service独自の例外クラスを導入しない設計を承認します。

入力値が無効な場合は、`ValueError` を使用します。

```python
raise ValueError(
    "書籍名を入力してください。"
)
```

Validatorも `ValueError` を送出します。

SQLite関連の例外は、Repositoryからそのまま伝播します。

```text
sqlite3.IntegrityError
sqlite3.OperationalError
sqlite3.DatabaseError
```

---

## 54. GUIでの例外処理

GUIは、Service呼び出し時に例外を捕捉します。

想定構造は、次のとおりです。

```python
try:
    registered = service.add_book(...)
except ValueError as error:
    messagebox.showwarning(
        "入力エラー",
        str(error),
    )
except sqlite3.DatabaseError:
    messagebox.showerror(
        "データベースエラー",
        "書籍情報を保存できませんでした。",
    )
```

Serviceはメッセージボックスを表示しません。

---

## 55. エラーメッセージ

ValidatorおよびServiceが送出する `ValueError` には、GUIでそのまま表示可能な日本語メッセージを設定します。

ただし、Serviceは次の情報をメッセージへ含めません。

```text
SQL文
データベースパス
スタックトレース
内部クラス名
利用者に不要な技術情報
```

---

## 56. 外部APIとの分離

`BookService` がopenBDやGoogle Books APIを呼び出さない設計を承認します。

将来の外部取得機能は、別のServiceまたはClientとして設計します。

想定構成は、次のとおりです。

```text
GUI
├── BookService
│   └── BookRepository
└── BookLookupService
    ├── OpenBDClient
    └── GoogleBooksClient
```

外部APIから取得した情報も、最終的には利用者が確認した後で `BookService.add_book()` に渡します。

---

## 57. テスト方針

Serviceテストでは、実際の `BookRepository` と一時SQLiteデータベースを使用する設計を承認します。

```text
tmp_path
↓
initialize_database()
↓
BookRepository
↓
BookService
```

RepositoryのMockは使用しません。

この方式により、次をまとめて確認できます。

* Serviceの正規化。
* Validatorの呼び出し。
* BookItemの生成。
* Repositoryとの連携。
* SQLiteへの保存結果。
* 日時の保存。
* 更新と削除の結果。
* 重複候補の統合。

---

## 58. Serviceテストの位置付け

Serviceテストは、純粋な単体テストではなく、Service、Validator、RepositoryおよびSQLiteを連携させた小規模な統合テストとして扱います。

Repository単体のSQL動作は、すでにRepositoryテストで確認済みです。

Serviceテストでは、主に次を確認します。

```text
入力値が正規化されるか
無効な入力値が拒否されるか
日時が正しく生成されるか
正しいBookItemがRepositoryへ渡るか
Repositoryの結果を適切に返すか
```

---

## 59. テスト用fixture

次のfixture設計を承認します。

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

必要に応じて、Repositoryも返すfixtureを別途設けられます。

```python
@pytest.fixture
def service_and_repository(
    tmp_path: Path,
) -> tuple[BookService, BookRepository]:
    ...
```

初期実装では、テストコードの可読性に応じて選択します。

---

## 60. 登録テスト

次のテスト項目を承認します。

* 書籍を登録できる。
* 登録後のモデルにIDが設定される。
* 書籍名の前後空白が除去される。
* 任意項目の前後空白が除去される。
* 空文字列が `None` へ変換される。
* ISBNの半角ハイフンが除去される。
* ISBNの半角空白が除去される。
* ISBNが正規化後に検証される。
* 雑誌コードが検証される。
* 読了年月が検証される。
* `created_at` が固定日時になる。
* `updated_at` が固定日時になる。
* `created_at` と `updated_at` が同じになる。
* 書籍名が空の場合に `ValueError` が発生する。
* ISBNが無効な場合に `ValueError` が発生する。
* 雑誌コードが無効な場合に `ValueError` が発生する。
* 読了年月が無効な場合に `ValueError` が発生する。
* 無効な入力値ではデータが登録されない。

---

## 61. 重複候補テスト

次のテスト項目を承認します。

* ISBN一致の候補を取得できる。
* 雑誌コード一致の候補を取得できる。
* ISBNと雑誌コードの両方を検索できる。
* 同じ書籍が両方に一致しても1件だけ返す。
* 候補をID降順で返す。
* ISBNだけが空の場合は雑誌コードだけを検索する。
* 雑誌コードだけが空の場合はISBNだけを検索する。
* 両方が空の場合は空のリストを返す。
* ISBNを正規化して検索できる。
* 雑誌コードの前後空白を除去して検索できる。
* 無効なISBNでは `ValueError` が発生する。
* 無効な雑誌コードでは `ValueError` が発生する。

---

## 62. 取得テスト

次のテスト項目を承認します。

* IDで書籍を取得できる。
* 存在しないIDでは `None` を返す。
* 全書籍を取得できる。
* データがない場合は空のリストを返す。
* ID降順で取得できる。

取得処理はRepositoryへの単純委譲であるため、過剰に細分化したテストは行いません。

---

## 63. 書籍名検索テスト

次のテスト項目を承認します。

* 書籍名を部分一致で検索できる。
* 検索語の前後空白が除去される。
* 日本語の検索語を使用できる。
* 該当しない場合は空のリストを返す。
* 空文字列では全件取得する。
* 空白だけの検索語では全件取得する。
* 全件取得時もID降順となる。

---

## 64. ISBN検索テスト

次のテスト項目を承認します。

* ISBNで完全一致検索できる。
* ISBNの半角ハイフンを除去して検索できる。
* ISBNの半角空白を除去して検索できる。
* 空文字列では空のリストを返す。
* 空白だけでは空のリストを返す。
* 該当しない場合は空のリストを返す。
* 無効なISBNでは `ValueError` が発生する。

---

## 65. 雑誌コード検索テスト

次のテスト項目を承認します。

* 雑誌コードで完全一致検索できる。
* 前後空白を除去して検索できる。
* 空文字列では空のリストを返す。
* 空白だけでは空のリストを返す。
* 該当しない場合は空のリストを返す。
* 無効な雑誌コードでは `ValueError` が発生する。

---

## 66. 更新テスト

次のテスト項目を承認します。

* 既存書籍を更新できる。
* 書籍名が正規化される。
* 任意項目が正規化される。
* 空の任意項目が `None` になる。
* ISBNが正規化される。
* ISBNが検証される。
* 雑誌コードが検証される。
* 読了年月が検証される。
* `created_at` が保持される。
* 入力モデルの `created_at` を無視する。
* `updated_at` が固定日時へ更新される。
* 入力モデルの `updated_at` を無視する。
* 入力モデルを直接変更しない。
* 存在しないIDでは `False` を返す。
* 存在しないIDでは入力値の検証を行わない。
* `id=None` では `ValueError` が発生する。
* 書籍名が空の場合に `ValueError` が発生する。
* ISBNが無効な場合に `ValueError` が発生する。
* 雑誌コードが無効な場合に `ValueError` が発生する。
* 読了年月が無効な場合に `ValueError` が発生する。
* 無効な入力値では既存データが変更されない。

---

## 67. 削除テスト

次のテスト項目を承認します。

* 既存書籍を削除できる。
* 削除後に取得できない。
* 存在しないIDでは `False` を返す。
* 削除後の一覧に含まれない。

---

## 68. 非公開メソッドの直接テスト

初期Versionでは、原則として非公開メソッドを直接テストしません。

次のメソッドは、公開メソッドを通して確認します。

```text
_normalize_title()
_normalize_optional_text()
_normalize_isbn()
_current_timestamp()
```

非公開メソッドの実装詳細ではなく、利用者から見えるServiceの動作をテストします。

ただし、テストケースが不必要に複雑になる場合は、正規化処理を別モジュールへ分離する設計変更を検討します。

---

## 69. 実装時の注意事項

### 69.1 `datetime.now()` を直接呼ばない

次のような実装は禁止します。

```python
current_timestamp = datetime.now().strftime(
    "%Y-%m-%d %H:%M:%S"
)
```

正式には、注入された関数を使用します。

```python
current_timestamp = self._current_timestamp()
```

---

### 69.2 登録時に日時を2回取得しない

次の実装は禁止します。

```python
BookItem(
    ...
    created_at=self._current_timestamp(),
    updated_at=self._current_timestamp(),
)
```

正式には1回だけ取得します。

```python
current_timestamp = self._current_timestamp()

BookItem(
    ...
    created_at=current_timestamp,
    updated_at=current_timestamp,
)
```

---

### 69.3 正規化前にValidatorを呼ばない

次の処理順序は禁止します。

```python
validate_isbn(isbn)
normalized_isbn = self._normalize_isbn(isbn)
```

正式な順序は、次のとおりです。

```python
normalized_isbn = self._normalize_isbn(isbn)

if normalized_isbn is not None:
    validate_isbn(normalized_isbn)
```

---

### 69.4 `None` をValidatorへ渡さない

Validatorは文字列を受け取ります。

次の呼び出しは禁止します。

```python
validate_isbn(None)
```

Serviceが `None` の判定を担当します。

---

### 69.5 入力モデルを変更しない

`update_book()` は、引数として受け取ったモデルへ代入しません。

正規化済みの新しいモデルを生成します。

---

### 69.6 Repositoryの戻り値を不要に加工しない

取得、更新および削除では、特別な理由がない限りRepositoryの戻り値をそのまま返します。

次のような独自辞書への変換は行いません。

```python
return {
    "success": result,
}
```

初期Versionでは、`BookItem`、`list[BookItem]`、`bool` および `None` を使用します。

---

### 69.7 ServiceでSQLを書かない

次のような処理は禁止します。

```python
connection.execute(
    "SELECT ...",
)
```

検索条件が増えた場合も、Repositoryの公開メソッド追加として設計します。

---

### 69.8 ServiceでGUIを操作しない

次のような処理は禁止します。

```python
messagebox.showwarning(...)
treeview.insert(...)
entry.delete(...)
```

Serviceは処理結果または例外だけを返します。

---

## 70. 初期Versionで導入しないもの

次の機能は、初期Versionでは導入しません。

```text
Serviceの抽象基底クラス
ServiceのProtocol
RepositoryのProtocol
依存性注入フレームワーク
Service独自例外
ServiceResult型
Result型
ViewModel
DTO
Commandオブジェクト
検索条件オブジェクト
Unit of Work
非同期処理
バッチ登録
バッチ更新
バッチ削除
ページング
自由な並び順指定
複合条件検索
全文検索
自動重複拒否
自動マージ
更新時の重複候補除外
論理削除
Undo機能
更新履歴
外部API呼び出し
```

---

## 71. 将来の拡張条件

次の状況が発生した場合に、設計変更を検討します。

### Repositoryの抽象化

```text
SQLite以外の永続化方式を追加する
Repositoryのテスト用Fakeが必要になる
複数のRepository実装を切り替える
```

### Service独自例外

```text
GUIで例外種別ごとに処理を細分化する
ValueErrorだけでは原因を区別できない
外部API例外を統一して扱う
```

### DTOまたは入力モデル

```text
登録および更新の引数がさらに増える
複数GUIから同じ入力構造を使用する
入力データと保存モデルの差が大きくなる
```

### Unit of Work

```text
複数テーブルを一つの処理で更新する
複数Repositoryを同一トランザクションで扱う
著者マスタやタグ管理を同時更新する
```

---

## 72. 設計間の整合性

### 72.1 `BookItem` との整合性

| 確認項目                            | 結果 |
| ------------------------------- | -- |
| Serviceが正規化済みの `BookItem` を生成する | 一致 |
| モデル自身は入力検証を行わない                 | 一致 |
| モデル自身は日時を生成しない                  | 一致 |
| 登録前のIDは `None`                  | 一致 |
| 更新時はIDが必要                       | 一致 |
| 入力モデルを直接変更しない                   | 一致 |

---

### 72.2 `BookRepository` との整合性

| Serviceメソッド                     | Repositoryメソッド            | 整合性 |
| ------------------------------- | ------------------------- | --- |
| `add_book()`                    | `add()`                   | 一致  |
| `get_book()`                    | `get_by_id()`             | 一致  |
| `get_all_books()`               | `get_all()`               | 一致  |
| `search_books_by_title()`       | `search_by_title()`       | 一致  |
| `find_books_by_isbn()`          | `find_by_isbn()`          | 一致  |
| `find_books_by_magazine_code()` | `find_by_magazine_code()` | 一致  |
| `update_book()`                 | `update()`                | 一致  |
| `delete_book()`                 | `delete()`                | 一致  |
| `find_duplicate_candidates()`   | ISBN・雑誌コード検索の組み合わせ        | 一致  |

---

### 72.3 データベース設計との整合性

| 確認項目                        | 結果 |
| --------------------------- | -- |
| Serviceがデータベースへ直接接続しない      | 一致 |
| 日時を文字列として保存する               | 一致 |
| 日時形式が `YYYY-MM-DD HH:MM:SS` | 一致 |
| ISBN重複をServiceが自動拒否しない      | 一致 |
| 雑誌コード重複をServiceが自動拒否しない     | 一致 |
| 任意項目を `None` として保存できる       | 一致 |

---

### 72.4 プロジェクト構成との整合性

| 確認項目                          | 結果 |
| ----------------------------- | -- |
| Serviceを `services` に配置する     | 一致 |
| Validatorを `validators` に配置する | 一致 |
| GUIからServiceを呼び出す             | 一致 |
| ServiceからRepositoryを呼び出す      | 一致 |
| Serviceと外部API処理を分離する          | 一致 |
| 初期Versionで過剰な抽象化を避ける          | 一致 |

---

## 73. 正式な実装構成

Design Freeze後は、最終的に次のファイルを作成します。

```text
src/book_manager/services/__init__.py
src/book_manager/services/book_service.py
tests/services/test_book_service.py
```

ただし、先に次のValidator関連ファイルを作成します。

```text
src/book_manager/validators/__init__.py
src/book_manager/validators/isbn_validator.py
src/book_manager/validators/magazine_code_validator.py
src/book_manager/validators/completion_month_validator.py

tests/validators/test_isbn_validator.py
tests/validators/test_magazine_code_validator.py
tests/validators/test_completion_month_validator.py
```

---

## 74. 実装予定コード構成

正式な `BookService` のコード構成は、次のとおりです。

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

## 75. コミット単位

設計書とレビュー文書は、次のドキュメントコミットとして管理します。

```text
docs: BookService設計を正式承認
```

Validator実装は、設計文書とは分けてコミットします。

想定するコミット単位は、次のとおりです。

```text
docs: Validator設計を追加
docs: Validator設計を正式承認
feat: Validatorを追加
test: Validatorテストを追加
feat: BookServiceを追加
test: BookServiceテストを追加
```

---

## 76. Design Freeze判定

`BookService` 設計Version 0.1を、初期実装におけるDesign Freeze版として承認します。

```text
Approved
Design Freeze
```

正式な設計基準は、次のとおりです。

```text
book_service_design.md        : Version 0.1
book_service_design_review.md : Version 0.1
class                         : BookService
model                         : BookItem
repository                    : BookRepository
validation                    : 関数形式のValidator
datetime provider             : Callable[[], datetime]
timestamp format              : YYYY-MM-DD HH:MM:SS
application version           : 0.1.0
Python                        : 3.12以上
```

---

## 77. Design Freeze後の変更手順

公開メソッド、引数、戻り値、正規化方法、検証順序、日時生成または責務を変更する場合は、次の手順を行います。

```text
変更理由を整理する
↓
GUIへの影響を確認する
↓
BookItemへの影響を確認する
↓
BookRepositoryへの影響を確認する
↓
Validatorへの影響を確認する
↓
データベース設計への影響を確認する
↓
book_service_design.mdを更新する
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

## 78. 次の作業

Design Freeze後は、次の順序で進めます。

```text
Validator設計書を作成する
↓
Validator設計レビューを作成する
↓
Validator設計をDesign Freezeする
↓
ISBN Validatorを実装する
↓
雑誌コードValidatorを実装する
↓
読了年月Validatorを実装する
↓
各Validatorのテストを作成する
↓
全テストを実行する
↓
BookServiceを実装する
↓
BookServiceテストを作成する
↓
全テストを実行する
↓
GUI設計へ進む
```
