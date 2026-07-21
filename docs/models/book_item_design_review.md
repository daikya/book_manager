# BookItemモデル設計レビュー

Version : 0.1
Last Updated : 2026-07-21
Status : Approved

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおける `BookItem` モデル設計のレビュー結果と最終承認を記録するものです。

レビュー対象は、次の文書です。

```text
docs/models/book_item_design.md
```

`BookItem` は、SQLiteの `book_items` テーブルに保存される1件の書籍情報を、Pythonコード内で扱うためのデータモデルです。

本レビューでは、データベース設計、プロジェクト構成設計、責務分離および初期実装の単純性との整合性を確認しました。

---

## 2. レビュー対象

| 文書                    | 対象Version | 状態    |
| --------------------- | --------: | ----- |
| `book_item_design.md` |       0.1 | Draft |

---

## 3. レビュー実施日

```text
2026-07-21
```

---

## 4. レビュー観点

本レビューでは、主に次の点を確認しました。

* モデルの責務が明確か。
* SQLiteの `book_items` テーブルと整合しているか。
* Pythonの型定義が適切か。
* 必須項目と任意項目が適切か。
* dataclassの属性順序が正しいか。
* `slots=True` の採用が妥当か。
* 登録前と取得後の状態を同じモデルで扱えるか。
* SQLite固有処理がモデルへ混入していないか。
* 入力検証がモデルへ混入していないか。
* 日時生成の責務が適切に分離されているか。
* Repositoryとの責務境界が明確か。
* Serviceとの責務境界が明確か。
* GUIとの責務境界が明確か。
* 初期Versionとして過剰設計になっていないか。
* テスト可能な構成になっているか。
* 将来の拡張を妨げないか。

---

## 5. レビュー結果

レビュー結果は、次のとおりです。

```text
承認
```

`BookItem` モデル設計は、初期実装に必要な範囲を十分に定義しています。

重大な修正事項はありません。

---

## 6. 承認事項

### 6.1 クラス名

クラス名を、次の名称とする設計を承認します。

```python
BookItem
```

1件の書籍情報を表すモデルであることが明確です。

---

### 6.2 配置場所

実装ファイルを、次の場所へ配置する設計を承認します。

```text
src/book_manager/models/book_item.py
```

モデル層として独立しており、プロジェクト構成設計と一致しています。

---

### 6.3 dataclassの採用

Python標準ライブラリの `dataclass` を使用する設計を承認します。

```python
@dataclass(slots=True)
class BookItem:
    ...
```

`BookItem` はデータ保持を主目的とするため、dataclassとの相性がよい構成です。

次の利点があります。

* コンストラクターを簡潔に定義できる。
* 等価比較を自動生成できる。
* テストで値を比較しやすい。
* 標準ライブラリだけで実装できる。
* 属性一覧をコード上で明確にできる。

---

### 6.4 `slots=True` の採用

`slots=True` を使用する設計を承認します。

これにより、次の効果が期待できます。

* 未定義属性の誤追加を防止できる。
* モデルが保持する属性を明確に固定できる。
* 属性名の入力ミスを早期に検出できる。
* データモデルとしての意図が明確になる。

初期Versionでは、動的な属性追加を必要とする要件はありません。

---

### 6.5 必須属性

初期Versionでは、`title` を唯一の必須属性とする設計を承認します。

```python
title: str
```

SQLiteでも、書籍名には次の制約があります。

```sql
title TEXT NOT NULL
```

ただし、空文字列や空白だけの文字列を不正とする検証は、モデルではなくService層で行います。

---

### 6.6 任意属性

次の属性を、初期値 `None` の任意属性とする設計を承認します。

```text
id
isbn
magazine_code
author
publisher
publication_format
description
completion_month
notes
created_at
updated_at
```

新規登録前には未確定となる値があり、外部APIから取得できない項目もあるため、`None` を許可する構成は妥当です。

---

### 6.7 属性の定義順序

初期値を持たない `title` を先頭に定義し、その後へ初期値を持つ任意属性を配置する設計を承認します。

```python
@dataclass(slots=True)
class BookItem:
    title: str
    id: int | None = None
    ...
```

これはdataclassの仕様に適合しています。

SQLiteのカラム順と完全には一致しませんが、Repositoryでキーワード引数を使用して生成するため、問題はありません。

---

### 6.8 `id` の型

`id` を、次の型とする設計を承認します。

```python
id: int | None = None
```

新規登録前は `None` とし、SQLiteへの登録後またはSQLiteからの取得後は整数値を保持します。

モデル側では、IDの採番を行いません。

---

### 6.9 ISBNの型

ISBNを、次の型とする設計を承認します。

```python
isbn: str | None = None
```

ISBNは、次の理由から文字列で扱うのが適切です。

* ISBN-10とISBN-13の両方を扱う可能性がある。
* ハイフン付き入力を受け取る可能性がある。
* 先頭のゼロを保持する必要がある。
* 算術計算の対象ではない。
* ISBN-10には末尾が `X` となる場合がある。

正規化と妥当性検証は、Service層または `validators.py` が担当します。

---

### 6.10 雑誌コードの型

雑誌コードを、次の型とする設計を承認します。

```python
magazine_code: str | None = None
```

雑誌コードも識別情報であり、算術計算の対象ではないため、文字列として扱う構成が適切です。

---

### 6.11 著者名

著者名を、初期Versionでは1つの文字列として保持する設計を承認します。

```python
author: str | None = None
```

複数著者、監修者、翻訳者などの詳細な構造化は、初期CRUDの範囲を超えます。

著者マスタや多対多関係は、必要性が明確になった段階で再設計します。

---

### 6.12 出版社名

出版社名を文字列として保持する設計を承認します。

```python
publisher: str | None = None
```

初期Versionでは、出版社マスタを作成しません。

表記ゆれの問題は認識されていますが、モデル設計の段階で複雑な正規化構造を導入する必要はありません。

---

### 6.13 出版形態

出版形態を文字列として保持する設計を承認します。

```python
publication_format: str | None = None
```

初期Versionでは、列挙型やマスターテーブルを導入しません。

想定値は次のとおりです。

```text
単行本
文庫
新書
雑誌
電子書籍
その他
```

利用可能な選択肢は、GUIまたはService層で制御します。

---

### 6.14 内容紹介

内容紹介を任意の文字列として保持する設計を承認します。

```python
description: str | None = None
```

外部APIや出版社によって取得可否や文章量が異なるため、`None` を許可する構成が適切です。

---

### 6.15 読了年月

読了年月を文字列として保持する設計を承認します。

```python
completion_month: str | None = None
```

保存形式は、次の形式とします。

```text
YYYY-MM
```

日まで必要としない情報であり、SQLiteに専用の日付型がないため、形式を統一した文字列として扱う構成は妥当です。

形式の検証はService層が担当します。

---

### 6.16 備考

備考を任意の文字列として保持する設計を承認します。

```python
notes: str | None = None
```

複数行の文章を保存できる構成とし、初期Versionではモデル側に文字数制限を設けません。

---

### 6.17 作成日時と更新日時

`created_at` と `updated_at` を、文字列として保持する設計を承認します。

```python
created_at: str | None = None
updated_at: str | None = None
```

保存形式は、次の形式とします。

```text
YYYY-MM-DD HH:MM:SS
```

新規登録前は `None` を許可し、登録時にService層が日本標準時で生成します。

モデル自身は日時を生成または更新しません。

---

### 6.18 登録用モデルと取得用モデル

初期Versionでは、登録用モデルと取得済みモデルを分けない設計を承認します。

1つの `BookItem` で、次の両方を扱います。

```text
新規登録前の書籍情報
SQLiteから取得した書籍情報
```

新規登録前には、次の属性が `None` となります。

```text
id
created_at
updated_at
```

初期CRUDとしては、モデルを分割するよりも単純で理解しやすい構成です。

---

### 6.19 モデルを可変とする設計

初期Versionでは、`frozen=True` を使用しない設計を承認します。

```python
@dataclass(slots=True)
class BookItem:
    ...
```

GUIでの編集や登録後のID反映などを考えると、属性を変更可能としておくことには合理性があります。

ただし、ServiceやRepositoryで不必要に入力モデルを書き換えないよう注意します。

---

### 6.20 標準の等価比較

dataclassが自動生成する標準の等価比較を使用する設計を承認します。

すべての属性が同じ場合に、2つの `BookItem` を等しいと判定します。

IDだけを比較する独自の `__eq__()` は実装しません。

モデルテストやRepositoryテストでも、dataclassの標準比較を利用できます。

---

### 6.21 独自メソッドを追加しない方針

初期Versionでは、`BookItem` に独自メソッドを追加しない設計を承認します。

次のような処理は実装しません。

```text
save()
delete()
validate()
normalize()
fetch_metadata()
update_timestamp()
```

これらをモデルへ追加すると、モデルがRepository、Service、外部APIなどの責務を持つことになります。

初期Versionでは、データと処理を明確に分離します。

---

### 6.22 SQLite変換処理

SQLiteの行から `BookItem` を生成する処理を、Repositoryの責務とする設計を承認します。

モデル自身には、初期Versionで次のメソッドを追加しません。

```text
from_row()
to_dict()
to_tuple()
```

変換処理が複数のRepositoryや処理へ重複した場合に、必要性を再検討します。

---

## 7. 責務分離の確認

### 7.1 Modelの責務

`BookItem` の責務は、書籍情報をPythonコード内で保持することです。

```text
書籍情報を属性として保持する
```

---

### 7.2 Repositoryの責務

Repositoryは、次の処理を担当します。

* SQLiteへの接続。
* SQLの実行。
* `sqlite3.Row` から `BookItem` への変換。
* `BookItem` からSQLパラメーターへの変換。
* 登録、取得、更新、削除。
* 検索。
* 採番されたIDの取得。

---

### 7.3 Serviceの責務

Serviceは、次の処理を担当します。

* 入力値の正規化。
* 書籍名の必須検証。
* ISBNの正規化と検証。
* 雑誌コードの検証。
* 読了年月の形式検証。
* 重複候補の確認。
* 日本標準時での日時生成。
* Repositoryの呼び出し。
* GUIへ返す結果の整理。

---

### 7.4 GUIの責務

GUIは、次の処理を担当します。

* 入力欄の表示。
* 利用者入力の取得。
* Serviceの呼び出し。
* 検証エラーの表示。
* 重複確認ダイアログの表示。
* 一覧への書籍情報の表示。

---

### 7.5 外部取得機能の責務

将来実装する外部取得機能は、次の処理を担当します。

* openBDの呼び出し。
* Google Books APIの呼び出し。
* ISBNや雑誌コードからの書籍情報取得。
* APIレスポンスの解析。
* 取得元固有データの保持。
* 取得情報から `BookItem` の入力候補を生成する処理。

---

## 8. データベース設計との整合性

`BookItem` の属性と、SQLiteの `book_items` テーブルとの整合性を確認しました。

| BookItem属性           | SQLiteカラム            | 整合性 |
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

## 9. プロジェクト構成設計との整合性

`project_structure.md` Version 0.2との整合性を確認しました。

| 確認項目                       | 結果 |
| -------------------------- | -- |
| モデルを `models` パッケージへ配置する   | 一致 |
| `BookItem` にdataclassを使用する | 一致 |
| 登録用モデルと取得用モデルを分けない         | 一致 |
| 日時属性を文字列とする                | 一致 |
| SQLite変換をRepositoryが担当する   | 一致 |
| 検証をServiceが担当する            | 一致 |
| GUI処理をモデルへ含めない             | 一致 |
| 過剰設計を避ける                   | 一致 |

重大な不整合はありません。

---

## 10. 実装予定コードの確認

設計書に記載された実装予定コードを確認しました。

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

Python 3.12以上を前提としており、型構文に問題はありません。

dataclassの属性順序にも問題はありません。

---

## 11. テスト方針の確認

モデルテストは、次の場所へ配置します。

```text
tests/models/test_book_item.py
```

次のテスト項目を承認します。

* `title` だけでモデルを生成できる。
* 任意属性の初期値が `None` になる。
* すべての属性を指定して生成できる。
* 定義済み属性を変更できる。
* 未定義属性を追加できない。
* 同じ属性値を持つモデル同士が等しい。
* 異なる属性値を持つモデル同士が等しくない。

---

## 12. 追加を推奨するテスト

設計書に記載されたテストに加えて、次のテストも実装時に推奨します。

### 12.1 `title` を省略できないこと

```python
def test_book_item_requires_title() -> None:
    with pytest.raises(TypeError):
        BookItem()
```

このテストは、`title` がコンストラクター上の必須引数であることを確認します。

型チェッカーでは検出できますが、モデル仕様をテストとして明示できます。

---

### 12.2 未定義属性を追加できないこと

```python
def test_book_item_rejects_undefined_attribute() -> None:
    book_item = BookItem(title="吾輩は猫である")

    with pytest.raises(AttributeError):
        book_item.unexpected = "value"
```

`slots=True` の効果を直接確認できます。

---

### 12.3 属性を変更できること

```python
def test_book_item_fields_can_be_updated() -> None:
    book_item = BookItem(title="旧書名")

    book_item.title = "新書名"

    assert book_item.title == "新書名"
```

`frozen=True` を使用しない設計を確認できます。

---

## 13. 注意事項

### 13.1 型ヒントは実行時検証ではない

次の型ヒントがあっても、Pythonは実行時に自動検証しません。

```python
title: str
```

そのため、次のようなコードも実行時にはモデルを生成できる可能性があります。

```python
BookItem(title=None)
```

初期Versionでは、モデルへ実行時型検証を追加しません。

不正な値をRepositoryへ渡さないように、Service層で検証します。

---

### 13.2 空文字列もモデル単体では許可される

次のモデルは、Python上では生成できます。

```python
BookItem(title="")
```

書籍名が空であることを不正とする判断は、Service層の責務です。

モデルへ `__post_init__()` を追加して検証することは、初期Versionでは行いません。

---

### 13.3 SQLiteの必須項目との差異

SQLiteでは、次のカラムが `NOT NULL` です。

```text
title
created_at
updated_at
```

一方、新規登録前のモデルでは、`created_at` と `updated_at` は `None` を許可します。

これは、登録前の入力モデルとしても同じクラスを使用するための意図的な差異です。

Repositoryへ登録を依頼する前に、Service層が日時を設定する必要があります。

---

### 13.4 モデルの直接保存は禁止する

GUIや外部取得機能から、未検証の `BookItem` を直接Repositoryへ渡す構成は避けます。

正式な依存方向は、次のとおりです。

```text
GUI
↓
Service
↓
Repository
↓
Database
```

Serviceを経由することで、入力検証、正規化、日時生成および重複確認を行います。

---

## 14. 初期Versionで導入しないもの

次の機能は、初期Versionでは導入しません。

* Pydantic。
* attrs。
* ORMモデル。
* `Enum` による出版形態。
* `datetime` 型の日時属性。
* `__post_init__()` による検証。
* 登録専用DTO。
* 更新専用DTO。
* SQLite行からのクラスメソッド。
* SQLパラメーター変換メソッド。
* IDだけを使用した独自等価比較。
* 独自の文字列表現。
* 自動保存メソッド。
* 著者のリスト型属性。
* 出版社オブジェクト。
* 外部APIレスポンスの保持。

必要性が確認された場合に、設計変更として検討します。

---

## 15. 正式な実装内容

Design Freeze後は、次のファイルを作成します。

```text
src/book_manager/models/__init__.py
src/book_manager/models/book_item.py
```

`book_item.py` の実装内容は、次のとおりです。

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

## 16. 正式なテスト内容

次のファイルを作成します。

```text
tests/models/test_book_item.py
```

最低限、次のテストを実装します。

```text
titleだけで生成できる
任意属性がNoneになる
すべての属性を指定できる
titleを省略できない
定義済み属性を変更できる
未定義属性を追加できない
同一内容のモデルが等しい
異なる内容のモデルが等しくない
```

---

## 17. 実装順序

正式な実装順序は、次のとおりです。

```text
modelsディレクトリを作成する
↓
models/__init__.pyを作成する
↓
models/book_item.pyを作成する
↓
tests/modelsディレクトリを作成する
↓
tests/models/test_book_item.pyを作成する
↓
モデルテストを実行する
↓
全テストを実行する
↓
実装レビューを行う
↓
コミットする
```

---

## 18. コミット単位

モデル実装とモデルテストは、責務が異なるため、次の2コミットに分けます。

### 18.1 モデル実装

```text
feat: BookItemモデルを追加
```

対象ファイル：

```text
src/book_manager/models/__init__.py
src/book_manager/models/book_item.py
```

### 18.2 モデルテスト

```text
test: BookItemモデルテストを追加
```

対象ファイル：

```text
tests/models/test_book_item.py
```

設計書とレビュー文書は、別のドキュメントコミットとして管理します。

---

## 19. Design Freeze判定

`BookItem` モデル設計Version 0.1を、初期実装におけるDesign Freeze版として承認します。

```text
Approved
Design Freeze
```

正式な設計基準は、次のとおりです。

```text
book_item_design.md        : Version 0.1
book_item_design_review.md : Version 0.1
class                      : BookItem
implementation             : dataclass(slots=True)
required field             : title
application version        : 0.1.0
Python                     : 3.12以上
```

Design Freeze後に属性、型または責務を変更する場合は、次の手順を行います。

```text
変更理由を整理する
↓
データベース設計への影響を確認する
↓
RepositoryとServiceへの影響を確認する
↓
book_item_design.mdを更新する
↓
必要に応じて関連設計書を更新する
↓
レビューする
↓
文書Versionを更新する
↓
実装とテストを変更する
```

---

## 20. 次の作業

Design Freeze後は、次の順序で実装します。

```text
src/book_manager/models/__init__.pyを作成する
↓
src/book_manager/models/book_item.pyを作成する
↓
tests/models/test_book_item.pyを作成する
↓
モデルテストを実行する
↓
全テストを実行する
↓
BookRepository設計へ進む
