# BookService実装結果レビュー

Version : 0.1
Last Updated : 2026-07-22
Status : Approved

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおける `BookService` の実装結果をレビューし、設計書および設計レビュー文書との整合性を確認した結果を記録するものです。

レビュー対象は、次の実装です。

```text
src/book_manager/services/__init__.py
src/book_manager/services/book_service.py
tests/services/test_book_service.py
```

本レビューでは、次の項目を確認します。

* Design Freeze済み設計との整合性。
* `BookService` の責務。
* `BookRepository` との責務分担。
* Validatorとの責務分担。
* 入力値の正規化。
* 書籍登録処理。
* 書籍取得および検索処理。
* 重複候補確認処理。
* 書籍更新処理。
* 書籍削除処理。
* 日時生成。
* テスト内容。
* 既存テストへの影響。
* 次工程へ進める状態であるか。

---

## 2. レビュー対象文書

| 文書                              | Version | 状態            |
| ------------------------------- | ------: | ------------- |
| `book_service_design.md`        |     0.1 | Design Freeze |
| `book_service_design_review.md` |     0.1 | Approved      |
| `validator_design.md`           |     0.1 | Design Freeze |
| `validator_design_review.md`    |     0.1 | Approved      |

---

## 3. レビュー対象実装

| ファイル                       | 役割                    |
| -------------------------- | --------------------- |
| `services/__init__.py`     | Serviceパッケージ定義        |
| `services/book_service.py` | 書籍管理のアプリケーションロジック     |
| `test_book_service.py`     | BookServiceの統合的な単体テスト |

---

## 4. レビュー実施日

```text
2026-07-22
```

---

## 5. 実装結果

レビュー結果は、次のとおりです。

```text
承認
```

`BookService` は、Design Freeze済みの設計に沿って実装されています。

全テストが成功しており、既存のDatabase層、Model層、Repository層およびValidator層への回帰も確認されています。

重大な修正事項はありません。

Service層の初期Versionを完成と判断します。

---

## 6. テスト結果

実行したテストは、次の2段階です。

```text
Serviceテスト
全テスト
```

実行コマンド：

```powershell
python -m pytest tests\services -v
python -m pytest -v
```

結果：

```text
すべて成功
```

次の問題は発生していません。

* テスト失敗。
* テスト収集エラー。
* ImportError。
* SQLiteエラー。
* Validatorとの不整合。
* Repositoryとの不整合。
* 既存テストの回帰。
* 一時データベースの競合。

---

## 7. コミット結果

実装とテストは、開発指針どおり別コミットとして管理されています。

実装：

```text
feat: BookServiceを追加
```

テスト：

```text
test: BookServiceテストを追加
```

リモートリポジトリへの `push` も完了しています。

---

# アーキテクチャレビュー

## 8. レイヤー構成

実装後の依存関係は、次のとおりです。

```text
GUI
↓
BookService
↓
BookRepository
↓
SQLite
```

入力値検証では、次の依存関係になります。

```text
BookService
↓
Validators
```

`BookService` がGUIと永続化層の間に配置され、アプリケーションロジックを担当する構成になっています。

---

## 9. BookServiceの責務

実装された `BookService` は、次の責務を担当しています。

* GUIなどの呼び出し元から入力値を受け取る。
* 入力値を正規化する。
* Validatorを呼び出す。
* 現在日時を生成する。
* `BookItem` を生成する。
* Repositoryへ登録を依頼する。
* Repositoryからデータを取得する。
* 検索条件を正規化する。
* 重複候補を取得する。
* 更新前の既存データを取得する。
* `created_at` を保持する。
* `updated_at` を更新する。
* Repositoryへ更新または削除を依頼する。

設計書で定義した責務と一致しています。

---

## 10. BookServiceに含まれていない責務

次の処理が `BookService` に含まれていないことを確認しました。

* SQLの直接実行。
* SQLite接続管理。
* テーブル作成。
* 行データからモデルへの変換。
* Tkinterウィジェット操作。
* メッセージボックス表示。
* TreeViewの更新。
* 重複登録確認ダイアログの表示。
* 外部APIへのアクセス。
* 書籍情報のネット取得。
* ファイル入出力。
* ログ画面の操作。

責務の過剰な集中は発生していません。

---

## 11. Repositoryとの責務分担

`BookService` は、Repositoryの公開メソッドだけを使用しています。

使用される主なRepository APIは、次のとおりです。

```python
add()
get_by_id()
get_all()
search_by_title()
find_by_isbn()
find_by_magazine_code()
update()
delete()
```

`BookService` 内にはSQLが存在せず、データベース接続も行っていません。

Repositoryとの責務分担は適切です。

---

## 12. Validatorとの責務分担

`BookService` は、正規化後の値をValidatorへ渡しています。

使用するValidatorは、次のとおりです。

```python
validate_isbn()
validate_magazine_code()
validate_completion_month()
```

Validatorが担当する処理：

```text
形式確認
文字種確認
桁数確認
範囲確認
チェックデジット確認
```

`BookService` が担当する処理：

```text
strip
空文字列からNoneへの変換
ISBNのハイフン除去
ISBNの半角空白除去
Validatorの呼び出し制御
```

正規化と検証が分離されています。

---

# 依存性注入レビュー

## 13. Repositoryの注入

コンストラクタで `BookRepository` を受け取る設計が実装されています。

```python
def __init__(
    self,
    repository: BookRepository,
    now_provider: Callable[[], datetime] = datetime.now,
) -> None:
```

これにより、`BookService` 自身がRepositoryを生成する必要がありません。

次の利点があります。

* データベースパスをServiceが知らなくてよい。
* テスト用Repositoryを注入できる。
* Repository生成処理と業務ロジックを分離できる。
* 将来のRepository差し替えが容易になる。

---

## 14. `now_provider` の注入

現在日時を返す関数を注入できる設計が実装されています。

通常実行時：

```python
BookService(repository)
```

テスト時：

```python
BookService(
    repository,
    now_provider=lambda: FIXED_NOW,
)
```

テストで固定日時を使用できるため、次の項目を確実に確認できます。

* 登録時の `created_at`。
* 登録時の `updated_at`。
* 更新時の `updated_at`。
* 更新時の `created_at` 保持。

日時生成のテスト可能性は十分です。

---

# 正規化レビュー

## 15. 書籍名の正規化

書籍名は、次の処理を行います。

```text
前後空白を除去
↓
空文字列か確認
↓
空の場合はValueError
```

有効例：

```text
"  吾輩は猫である  "
↓
"吾輩は猫である"
```

無効例：

```text
"   "
```

エラーメッセージ：

```text
書籍名を入力してください。
```

書籍名の必須条件がService層で保証されています。

---

## 16. 任意文字列の正規化

任意入力項目には、共通の正規化処理が使用されています。

対象：

* 雑誌コード。
* 著者名。
* 出版社名。
* 出版形態。
* 内容紹介。
* 読了年月。
* 備考。

処理：

```text
NoneならNone
↓
前後空白を除去
↓
空文字列ならNone
↓
それ以外は正規化後の文字列
```

入力値の扱いが統一されています。

---

## 17. ISBNの正規化

ISBNでは、次の処理が実装されています。

```text
NoneならNone
↓
前後空白を除去
↓
半角ハイフンを除去
↓
半角空白を除去
↓
空文字列ならNone
```

例：

```text
" 978-4-10-101001-4 "
↓
"9784101010014"
```

正規化後にISBN Validatorが呼び出されます。

---

## 18. ISBN正規化の範囲

初期Versionでは、次の処理を行っていません。

* 全角数字から半角数字への変換。
* 全角ハイフンの除去。
* 小文字 `x` から大文字 `X` への変換。
* その他の記号除去。
* 不正文字の自動修正。

これはDesign Freeze済みの方針と一致しています。

---

# 登録処理レビュー

## 19. `add_book()`

登録処理は、次の順序で実装されています。

```text
入力値を受け取る
↓
書籍名を正規化する
↓
任意項目を正規化する
↓
ISBNを正規化する
↓
Validatorを呼び出す
↓
現在日時を1回生成する
↓
BookItemを生成する
↓
Repository.add()を呼び出す
↓
登録後のBookItemを返す
```

登録前に正規化と検証が完了するため、不正なデータはRepositoryへ渡されません。

---

## 20. 登録日時

登録時には、同じ日時を次の2項目へ設定しています。

```text
created_at
updated_at
```

日時生成は1回だけです。

```python
current_timestamp = self._current_timestamp()
```

そのため、登録直後の2項目は確実に一致します。

---

## 21. 登録時のモデル生成

`BookService` が正規化済み・検証済みの値から `BookItem` を生成しています。

Repositoryは、完成したモデルの保存だけを担当します。

次の処理がRepositoryへ漏れていません。

* 入力値の正規化。
* Validator呼び出し。
* 日時生成。
* 必須項目確認。

---

## 22. 登録失敗時の保存防止

不正な入力値で `ValueError` が発生した場合、Repositoryの登録処理は呼び出されません。

テストでは、例外発生後に次を確認しています。

```python
assert service.get_all_books() == []
```

次の不正値について、保存されないことが確認されています。

* 不正なISBN。
* 不正な雑誌コード。
* 不正な読了年月。

---

# 取得・検索処理レビュー

## 23. `get_book()`

`get_book()` は、Repositoryの `get_by_id()` を呼び出します。

対象が存在する場合：

```text
BookItemを返す
```

対象が存在しない場合：

```text
Noneを返す
```

Service層で不要な変換を行っていません。

---

## 24. `get_all_books()`

`get_all_books()` は、Repositoryの `get_all()` を呼び出します。

Repositoryで定義されたID降順が維持されています。

データがない場合は、空リストを返します。

---

## 25. `search_books_by_title()`

検索キーワードでは、前後空白を除去します。

通常のキーワード：

```text
Repository.search_by_title()
```

空のキーワード：

```text
Repository.get_all()
```

空文字による意図の不明な部分一致検索を避け、全件表示として扱う設計になっています。

---

## 26. `find_books_by_isbn()`

ISBN検索では、次の処理を行います。

```text
ISBNを正規化する
↓
空なら空リストを返す
↓
ISBN Validatorで検証する
↓
Repository.find_by_isbn()を呼び出す
```

ハイフン付きISBNで検索しても、保存済みの正規化値と一致します。

---

## 27. `find_books_by_magazine_code()`

雑誌コード検索では、次の処理を行います。

```text
前後空白を除去する
↓
空なら空リストを返す
↓
雑誌コードValidatorで検証する
↓
Repository.find_by_magazine_code()を呼び出す
```

不正な検索値は、Repositoryへ渡されません。

---

# 重複候補確認レビュー

## 28. `find_duplicate_candidates()`

重複候補確認は、登録処理から独立した公開メソッドとして実装されています。

正式な利用順序は、次のとおりです。

```text
GUIが入力値を受け取る
↓
find_duplicate_candidates()を呼び出す
↓
候補があればGUIで確認する
↓
利用者が登録を承認する
↓
add_book()を呼び出す
```

Serviceが確認ダイアログを表示しないため、GUIとの責務分担が維持されています。

---

## 29. 重複候補の検索条件

次の2項目を検索条件として使用します。

```text
ISBN
雑誌コード
```

両方が指定された場合は、それぞれの検索結果を統合します。

---

## 30. 重複候補の正規化と検証

ISBNおよび雑誌コードは、登録時と同じ規則で正規化・検証されます。

このため、登録時と重複確認時で判定条件が異なる問題は発生しません。

---

## 31. 重複候補の重複排除

同じ書籍がISBNと雑誌コードの両方で一致した場合、候補リストに同じ書籍を2件含めません。

IDをキーとする辞書で重複を排除しています。

```python
candidates_by_id: dict[int, BookItem]
```

---

## 32. IDがない候補

Repositoryから取得した保存済みデータには通常IDがあります。

ただし、防御的な処理として、IDが `None` の候補は結果から除外しています。

```python
if candidate.id is None:
    continue
```

初期Versionとして妥当です。

---

## 33. 重複候補の並び順

重複排除後の候補は、ID降順で返されます。

```text
新しく登録された候補
↓
古く登録された候補
```

GUIで候補を表示する際も、最近のデータを先に確認できます。

---

## 34. 重複登録の許可

`find_duplicate_candidates()` は、候補を返すだけです。

`add_book()` 自体は、重複を理由に登録を拒否しません。

この方針により、同じISBNを持つ次のようなデータも、利用者の判断で登録できます。

* 複数冊所有している書籍。
* 出版形態を分けて管理する書籍。
* 備考や読了情報を分けて管理する書籍。
* 重複と理解した上で登録する書籍。

設計どおり、最終判断はGUIと利用者に委ねられています。

---

# 更新処理レビュー

## 35. `update_book()`

更新処理は、次の順序で実装されています。

```text
BookItemのidを確認する
↓
既存データをRepositoryから取得する
↓
存在しなければFalseを返す
↓
入力値を正規化する
↓
Validatorを呼び出す
↓
created_atを既存データから取得する
↓
updated_atを新しく生成する
↓
更新用BookItemを生成する
↓
Repository.update()を呼び出す
```

Design Freeze済みの更新順序と一致しています。

---

## 36. ID必須確認

更新対象の `BookItem.id` が `None` の場合は、次の例外を送出します。

```text
更新対象のBookItemにはidが必要です。
```

IDなしのモデルを誤って更新処理へ渡すことを防止しています。

---

## 37. 存在確認の順序

ID確認後、最初に既存データを取得しています。

対象が存在しない場合：

```text
Falseを返す
```

入力値の正規化や検証は実行しません。

この順序により、存在しないデータに対する不要な検証を避けています。

---

## 38. `created_at` の保持

更新時に呼び出し元から渡された `created_at` は信用しません。

既存データの値を使用します。

```python
created_at=existing.created_at
```

このため、書籍の登録日時が更新処理で上書きされません。

---

## 39. `updated_at` の更新

更新時には、`now_provider` から新しい日時を取得します。

```python
updated_at=self._current_timestamp()
```

登録日時と更新日時を明確に区別できます。

---

## 40. 入力モデルの非変更

更新処理では、渡された `BookItem` 自体を変更しません。

正規化済みの値から、新しい `BookItem` を生成してRepositoryへ渡しています。

次の値は呼び出し後も維持されます。

* 入力時の書籍名。
* 入力時のISBN。
* 入力時の `created_at`。
* 入力時の `updated_at`。

副作用を抑えた実装になっています。

---

## 41. 更新失敗時のデータ保持

書籍名や任意項目の検証で `ValueError` が発生した場合、Repositoryの更新処理は呼び出されません。

既存データが変更されないことをテストで確認しています。

---

# 削除処理レビュー

## 42. `delete_book()`

`delete_book()` は、Repositoryの `delete()` を呼び出します。

対象が存在する場合：

```text
True
```

対象が存在しない場合：

```text
False
```

削除確認ダイアログはGUIの責務であり、Serviceには含まれていません。

---

# 非公開メソッドレビュー

## 43. `_normalize_title()`

責務：

```text
前後空白の除去
必須確認
正規化後の書籍名を返す
```

登録と更新で共通利用されています。

---

## 44. `_normalize_optional_text()`

責務：

```text
任意文字列の前後空白除去
空文字列からNoneへの変換
```

複数項目の正規化規則を統一しています。

---

## 45. `_normalize_isbn()`

責務：

```text
前後空白の除去
ハイフンの除去
半角空白の除去
空文字列からNoneへの変換
```

ISBN固有の正規化が他の項目から分離されています。

---

## 46. `_current_timestamp()`

責務：

```text
now_providerを呼び出す
保存形式の文字列へ変換する
```

日時形式：

```text
YYYY-MM-DD HH:MM:SS
```

データベース設計と一致しています。

---

## 47. `_validate_optional_values()`

実装では、Validator呼び出しを共通化する非公開メソッドが追加されています。

対象：

```text
ISBN
雑誌コード
読了年月
```

このメソッドは公開APIを変更せず、登録処理と更新処理の重複を削減しています。

次の理由により、設計上問題ありません。

* Serviceの責務内に収まっている。
* Validatorの責務を侵害していない。
* 正規化処理を行っていない。
* Repositoryを呼び出していない。
* GUIへ依存していない。
* 外部から呼び出されない。
* 設計の振る舞いを変更していない。

実装上の内部整理として承認します。

---

# テストレビュー

## 48. テスト環境

Serviceテストでは、次の構成を使用しています。

```text
pytest
tmp_path
SQLite実データベース
BookRepository実装
BookService実装
固定日時
```

Mockは使用していません。

Repositoryを含めた実際のデータフローを確認できる構成です。

---

## 49. 一時データベース

各テストでは、`tmp_path` 配下へ一時データベースを作成しています。

利点：

* 本番データベースを変更しない。
* テスト間でデータが混在しない。
* テスト終了後に一時データを破棄できる。
* SQLite固有の動作を確認できる。
* Repositoryとの結合状態を確認できる。

---

## 50. 固定日時

登録用日時と更新用日時を分けて使用しています。

登録日時：

```text
2026-07-22 10:30:00
```

更新日時：

```text
2026-07-23 11:45:30
```

これにより、次の項目を検証しています。

* 登録時の日時一致。
* 更新後の `created_at` 保持。
* 更新後の `updated_at` 変更。

---

## 51. 登録テスト

登録処理では、次を確認しています。

* IDが付与される。
* 書籍名が保存される。
* ISBNが保存される。
* 登録日時が設定される。
* 更新日時が設定される。
* 登録時の2つの日時が一致する。
* 書籍名が正規化される。
* 任意文字列が正規化される。
* 空の任意文字列が `None` になる。
* ISBNのハイフンと空白が除去される。
* 空の書籍名が拒否される。
* 不正なISBNが拒否される。
* 不正な雑誌コードが拒否される。
* 不正な読了年月が拒否される。
* 検証失敗時に保存されない。

---

## 52. 取得テスト

取得処理では、次を確認しています。

* IDで書籍を取得できる。
* 存在しないIDで `None` を返す。
* 全件取得できる。
* ID降順で返される。
* データがない場合に空リストを返す。

---

## 53. 書籍名検索テスト

書籍名検索では、次を確認しています。

* 部分一致検索ができる。
* キーワードの前後空白が除去される。
* 空のキーワードで全件取得する。
* 該当書籍だけが返される。

---

## 54. ISBN検索テスト

ISBN検索では、次を確認しています。

* ハイフン付きISBNを正規化できる。
* 前後空白を除去できる。
* 空のISBNで空リストを返す。
* 不正なISBNで `ValueError` を送出する。
* 正規化済みの保存値と一致する。

---

## 55. 雑誌コード検索テスト

雑誌コード検索では、次を確認しています。

* 前後空白を除去できる。
* 空の雑誌コードで空リストを返す。
* 正規化後の値でRepositoryを検索する。
* 保存済みデータを取得できる。

---

## 56. 重複候補テスト

重複候補確認では、次を確認しています。

* ISBNで候補を取得できる。
* 雑誌コードで候補を取得できる。
* ISBNが正規化される。
* 雑誌コードが正規化される。
* 同じIDが重複して返されない。
* ID降順で返される。
* 両方が空の場合に空リストを返す。

---

## 57. 更新テスト

更新処理では、次を確認しています。

* 既存書籍を更新できる。
* 更新値が正規化される。
* ISBNが正規化される。
* `created_at` が保持される。
* `updated_at` が変更される。
* 入力された不正な日時を使用しない。
* 入力モデル自体を変更しない。
* IDなしで `ValueError` を送出する。
* 対象なしで `False` を返す。
* 対象なしの場合は入力値を検証しない。
* 不正な書籍名で更新しない。
* 検証失敗後も既存データを保持する。

---

## 58. 削除テスト

削除処理では、次を確認しています。

* 存在する書籍を削除できる。
* 削除後に取得できない。
* 存在しないIDで `False` を返す。

---

## 59. テスト範囲の評価

初期VersionのService層として、次の主要経路がテストされています。

```text
登録
取得
全件取得
書籍名検索
ISBN検索
雑誌コード検索
重複候補確認
更新
削除
正規化
Validation
日時生成
対象なし
入力エラー
```

テスト範囲は十分です。

---

## 60. 非公開メソッドのテスト

非公開メソッドは、原則として直接テストしていません。

公開メソッドを通じて、次の処理を間接的に確認しています。

* 書籍名の正規化。
* 任意文字列の正規化。
* ISBNの正規化。
* 日時文字列の生成。
* Validator呼び出し。

実装詳細へ過度に依存しないテスト構成になっています。

---

# 設計との整合性

## 61. API整合性

| 公開メソッド                          | 実装結果 |
| ------------------------------- | ---- |
| `add_book()`                    | 一致   |
| `find_duplicate_candidates()`   | 一致   |
| `get_book()`                    | 一致   |
| `get_all_books()`               | 一致   |
| `search_books_by_title()`       | 一致   |
| `find_books_by_isbn()`          | 一致   |
| `find_books_by_magazine_code()` | 一致   |
| `update_book()`                 | 一致   |
| `delete_book()`                 | 一致   |

---

## 62. 正規化方針との整合性

| 項目               | 実装結果 |
| ---------------- | ---- |
| 前後空白を除去する        | 一致   |
| 空文字列を `None` にする | 一致   |
| ISBNのハイフンを除去する   | 一致   |
| ISBNの半角空白を除去する   | 一致   |
| 書籍名を必須とする        | 一致   |
| 全角数字を自動変換しない     | 一致   |
| 小文字 `x` を自動変換しない | 一致   |

---

## 63. Validator設計との整合性

| 項目                  | 実装結果 |
| ------------------- | ---- |
| 正規化後にValidatorを呼ぶ   | 一致   |
| `None` の項目は検証しない    | 一致   |
| Validatorは値を変更しない   | 一致   |
| 無効時は `ValueError`   | 一致   |
| 独自例外を使用しない          | 一致   |
| ISBN Validatorを使用する | 一致   |
| 雑誌コードValidatorを使用する | 一致   |
| 読了年月Validatorを使用する  | 一致   |

---

## 64. Repository設計との整合性

| 項目                        | 実装結果 |
| ------------------------- | ---- |
| RepositoryをDIする           | 一致   |
| ServiceにSQLを書かない          | 一致   |
| メソッド単位の接続管理はRepositoryが担当 | 一致   |
| RepositoryのCRUD APIを使用する  | 一致   |
| Repositoryから返されたモデルを利用する  | 一致   |
| 重複をDB制約で拒否しない             | 一致   |

---

## 65. Model設計との整合性

| 項目                    | 実装結果 |
| --------------------- | ---- |
| `BookItem` を使用する      | 一致   |
| モデル内でValidationしない    | 一致   |
| Serviceで正規化済みモデルを生成する | 一致   |
| 更新時に新しいモデルを生成する       | 一致   |
| `created_at` を保持する    | 一致   |
| `updated_at` を更新する    | 一致   |

---

## 66. Database設計との整合性

| 項目                 | 実装結果 |
| ------------------ | ---- |
| 日時をTEXT形式で保存する     | 一致   |
| 日時形式が統一されている       | 一致   |
| 任意項目に `None` を使用する | 一致   |
| ISBNを文字列として扱う      | 一致   |
| 雑誌コードを文字列として扱う     | 一致   |
| 読了年月を文字列として扱う      | 一致   |

---

# 実装品質レビュー

## 67. 可読性

処理は公開メソッドと非公開メソッドに適切に分割されています。

特に次の処理が分離されています。

```text
書籍名正規化
任意文字列正規化
ISBN正規化
日時生成
任意項目Validation
```

メソッド名から責務を判断しやすい構成です。

---

## 68. 型ヒント

公開メソッド、非公開メソッド、コンストラクタに型ヒントが設定されています。

例：

```python
Callable[[], datetime]
BookItem
BookItem | None
list[BookItem]
str | None
bool
```

Python 3.12以上を前提とするプロジェクト方針と一致しています。

---

## 69. Docstring

Serviceクラスと主要メソッドにDocstringが設定されています。

次の情報を確認できます。

* メソッドの目的。
* 引数。
* 戻り値。
* 発生する例外。

初期Versionとして十分です。

---

## 70. 副作用

入力として渡された `BookItem` を直接変更しない設計になっています。

永続化以外の予期しない副作用はありません。

---

## 71. 例外方針

入力値の問題には `ValueError` を使用しています。

対象が存在しない更新・削除には、例外ではなく `False` を返しています。

取得対象が存在しない場合は、`None` を返しています。

設計書で定義した戻り値と例外方針が維持されています。

---

## 72. 過剰な抽象化

次の要素は導入されていません。

* Service基底クラス。
* Service用Protocol。
* UseCaseクラス。
* Commandオブジェクト。
* DTO。
* 独自例外階層。
* Result型。
* イベントバス。
* DIコンテナ。
* Unit of Work。
* 非同期処理。

初期Versionとして適切な実装規模です。

---

# 改善候補

## 73. 現時点で修正不要の項目

次の項目は将来の改善候補ですが、初期Versionでは修正不要です。

* RepositoryをProtocolで抽象化する。
* Service独自例外を導入する。
* Validationエラーへ項目名を付与する。
* 複数Validationエラーをまとめて返す。
* `BookItem` ではなく更新専用DTOを受け取る。
* ISBNの全角数字を正規化する。
* ISBN末尾の小文字 `x` を大文字へ変換する。
* 重複候補の判定条件を追加する。
* 出版社や書籍名による重複候補判定を追加する。
* 日時をタイムゾーン付きで扱う。
* ロギングを追加する。
* トランザクション境界をServiceで管理する。
* 非同期Repositoryへ対応する。

必要性が確認されるまで導入しません。

---

## 74. GUI実装時の注意事項

GUIは、`BookService` の公開メソッドだけを使用します。

GUIから次を直接呼び出しません。

```text
BookRepository
SQLite connection
Validators
BookItemの保存用日時生成
```

GUIの基本的な呼び出し経路は、次のとおりです。

登録：

```text
入力欄から値を取得
↓
find_duplicate_candidates()
↓
必要に応じて確認ダイアログ
↓
add_book()
↓
一覧を再表示
```

更新：

```text
選択中のBookItemを取得
↓
入力値を設定したBookItemを生成
↓
update_book()
↓
一覧を再表示
```

削除：

```text
選択中のIDを取得
↓
確認ダイアログ
↓
delete_book()
↓
一覧を再表示
```

---

## 75. GUIでの例外処理

GUIは、`BookService` から送出される `ValueError` を捕捉します。

例：

```python
try:
    service.add_book(...)
except ValueError as error:
    messagebox.showerror(
        "入力エラー",
        str(error),
    )
```

Serviceはメッセージボックスを表示しません。

---

## 76. GUIでの戻り値処理

更新処理：

```python
result = service.update_book(book_item)
```

結果が `False` の場合は、対象データがすでに削除されている可能性をGUIで通知します。

削除処理：

```python
result = service.delete_book(book_id)
```

結果が `False` の場合も、対象データが存在しないことをGUIで通知します。

---

# 完成判定

## 77. Service層完成条件

次の条件をすべて満たしています。

* 設計書が存在する。
* 設計レビュー文書が存在する。
* Design Freezeされている。
* `BookService` が実装されている。
* RepositoryがDIされている。
* `now_provider` がDIされている。
* 登録処理が実装されている。
* 取得処理が実装されている。
* 検索処理が実装されている。
* 重複候補確認が実装されている。
* 更新処理が実装されている。
* 削除処理が実装されている。
* 入力値の正規化が実装されている。
* Validatorと連携している。
* Serviceテストが実装されている。
* Serviceテストが成功している。
* 全テストが成功している。
* 実装とテストが別コミットになっている。
* リモートリポジトリへpushされている。

---

## 78. 正式判定

Service層の初期Versionを完成として承認します。

```text
Approved
Implementation Complete
```

正式な状態は、次のとおりです。

```text
BookService design          : Approved
BookService implementation  : Complete
BookService tests           : Passed
Regression tests            : Passed
Commit                      : Complete
Push                        : Complete
Service layer               : Complete
```

---

## 79. 次工程

次工程は、GUI層の設計です。

次の順序で進めます。

```text
GUI要件を整理する
↓
画面構成を設計する
↓
GUIとBookServiceの責務境界を定義する
↓
画面遷移と操作フローを定義する
↓
入力項目を定義する
↓
一覧表示項目を定義する
↓
登録・更新・削除フローを定義する
↓
重複確認フローを定義する
↓
エラー表示方針を定義する
↓
GUI設計書をレビューする
↓
Design Freeze
↓
GUIを実装する
```
