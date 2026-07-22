# Validator設計

Version : 0.1
Last Updated : 2026-07-22
Status : Draft

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおける入力値検証機能の設計を定義するものです。

初期Versionでは、次の3種類のValidatorを実装します。

* ISBN Validator。
* 雑誌コードValidator。
* 読了年月Validator。

Validatorは、正規化済みの文字列が所定の形式と条件を満たしているか確認します。

---

## 2. 対象範囲

初期Versionで検証する項目は、次のとおりです。

| 対象    | 検証内容                  |
| ----- | --------------------- |
| ISBN  | 文字種、桁数、チェックデジット       |
| 雑誌コード | 文字種、桁数                |
| 読了年月  | `YYYY-MM`形式、年月としての妥当性 |

書籍名の必須確認は、`BookService` の `_normalize_title()` が担当します。

---

## 3. 配置場所

実装ファイルは、次の場所へ配置します。

```text
src/
└── book_manager/
    └── validators/
        ├── __init__.py
        ├── isbn_validator.py
        ├── magazine_code_validator.py
        └── completion_month_validator.py
```

テストファイルは、次の場所へ配置します。

```text
tests/
└── validators/
    ├── test_isbn_validator.py
    ├── test_magazine_code_validator.py
    └── test_completion_month_validator.py
```

---

## 4. 基本方針

Validatorは、次の方針で実装します。

* クラスではなく関数として実装する。
* 状態を保持しない。
* データベースへ接続しない。
* Repositoryを呼び出さない。
* GUIを操作しない。
* 入力値を変更しない。
* 正規化を行わない。
* 有効な場合は何も返さない。
* 無効な場合は `ValueError` を送出する。
* エラーメッセージは日本語とする。
* 外部ライブラリは使用しない。
* Python標準ライブラリだけで実装する。

---

## 5. 依存関係

依存方向は、次のとおりです。

```text
GUI
↓
BookService
↓
Validators
```

Validatorは、`BookService` を知りません。

次の依存は禁止します。

```text
Validator → BookService
Validator → BookRepository
Validator → SQLite
Validator → Tkinter
```

---

## 6. 正規化との責務境界

Validatorは、正規化済みの文字列を受け取ります。

正規化は `BookService` が担当します。

例：

```text
入力値
978-4-10-101001-4
↓
BookServiceで正規化
9784101010014
↓
validate_isbn()
```

Validator内では、次の処理を行いません。

* 前後空白の除去。
* ハイフンの除去。
* 空文字列から `None` への変換。
* 全角文字から半角文字への変換。
* 大文字・小文字の自動変換。
* 不正な文字の除去。

---

## 7. 戻り値と例外

各Validatorの公開関数は、次の形式とします。

```python
def validate_xxx(value: str) -> None:
    ...
```

有効な場合は、明示的な値を返しません。

```python
validate_isbn("9784101010014")
```

戻り値：

```python
None
```

無効な場合は、`ValueError` を送出します。

```python
raise ValueError(
    "ISBNの形式が正しくありません。"
)
```

---

# ISBN Validator

## 8. 公開関数

ISBN Validatorの公開関数は、次のとおりです。

```python
def validate_isbn(
    isbn: str,
) -> None:
    ...
```

配置場所：

```text
src/book_manager/validators/isbn_validator.py
```

---

## 9. 対応するISBN

初期Versionでは、次の形式に対応します。

* ISBN-10。
* ISBN-13。

例：

```text
ISBN-10
4101010013

ISBN-13
9784101010014
```

ISBN-10の最終桁には、数字または大文字の `X` を許可します。

```text
080442957X
```

小文字の `x` は許可しません。

---

## 10. ISBNの入力条件

Validatorへ渡されるISBNは、すでに次の状態であることを前提とします。

```text
ハイフンなし
空白なし
前後空白なし
```

有効例：

```text
9784101010014
4101010013
080442957X
```

無効例：

```text
978-4-10-101001-4
978 410 101001 4
９７８４１０１０１００１４
978410101001A
080442957x
```

---

## 11. ISBNの検証順序

正式な検証順序は、次のとおりです。

```text
文字列長を確認する
↓
10桁ならISBN-10として検証する
↓
13桁ならISBN-13として検証する
↓
それ以外はValueError
```

---

## 12. ISBN-10の文字種

ISBN-10では、次の条件を満たす必要があります。

* 先頭9文字は数字。
* 最終文字は数字または大文字の `X`。

判定例：

```python
isbn[:9].isdigit()
```

最終文字：

```python
isbn[-1].isdigit() or isbn[-1] == "X"
```

---

## 13. ISBN-10のチェックデジット

ISBN-10は、各桁へ10から1までの重みを掛けた合計が、11で割り切れることを確認します。

計算対象：

```text
1桁目 × 10
2桁目 × 9
3桁目 × 8
4桁目 × 7
5桁目 × 6
6桁目 × 5
7桁目 × 4
8桁目 × 3
9桁目 × 2
10桁目 × 1
```

最終文字が `X` の場合は、数値10として扱います。

判定条件：

```python
weighted_sum % 11 == 0
```

想定実装：

```python
digits = [
    int(character)
    for character in isbn[:9]
]

check_digit = (
    10
    if isbn[-1] == "X"
    else int(isbn[-1])
)

weighted_sum = sum(
    digit * weight
    for digit, weight in zip(
        [*digits, check_digit],
        range(10, 0, -1),
        strict=True,
    )
)

if weighted_sum % 11 != 0:
    raise ValueError(
        "ISBNのチェックデジットが正しくありません。"
    )
```

---

## 14. ISBN-13の文字種

ISBN-13は、13文字すべてが数字である必要があります。

```python
isbn.isdigit()
```

ただし、`str.isdigit()` は全角数字などもTrueになるため、初期VersionではASCII数字だけを許可します。

正式な判定は、次の形式とします。

```python
isbn.isascii() and isbn.isdigit()
```

または次でも構いません。

```python
all(
    "0" <= character <= "9"
    for character in isbn
)
```

初期実装では、意図が明確な後者を推奨します。

---

## 15. ISBN-13のチェックデジット

ISBN-13では、先頭12桁に対して1と3の重みを交互に掛けます。

計算方法：

```text
1桁目 × 1
2桁目 × 3
3桁目 × 1
4桁目 × 3
...
12桁目 × 3
```

先頭12桁の加重合計を求め、次の式でチェックデジットを算出します。

```python
expected_check_digit = (
    10 - weighted_sum % 10
) % 10
```

13桁目と一致すれば有効です。

想定実装：

```python
digits = [
    int(character)
    for character in isbn
]

weighted_sum = sum(
    digit * (1 if index % 2 == 0 else 3)
    for index, digit in enumerate(
        digits[:12]
    )
)

expected_check_digit = (
    10 - weighted_sum % 10
) % 10

if digits[-1] != expected_check_digit:
    raise ValueError(
        "ISBNのチェックデジットが正しくありません。"
    )
```

---

## 16. ISBNのエラーメッセージ

ISBN Validatorでは、次のメッセージを使用します。

桁数が不正な場合：

```text
ISBNは10桁または13桁で入力してください。
```

文字種が不正な場合：

```text
ISBNの形式が正しくありません。
```

チェックデジットが不正な場合：

```text
ISBNのチェックデジットが正しくありません。
```

初期Versionでは、ISBN-10とISBN-13で異なるメッセージへ細分化しません。

---

## 17. ISBN Validatorの非公開関数

実装の可読性を保つため、次の非公開関数へ分割します。

```python
def _validate_isbn10(
    isbn: str,
) -> None:
    ...

def _validate_isbn13(
    isbn: str,
) -> None:
    ...
```

公開関数は、桁数に応じて処理を振り分けます。

```python
def validate_isbn(
    isbn: str,
) -> None:
    if len(isbn) == 10:
        _validate_isbn10(isbn)
        return

    if len(isbn) == 13:
        _validate_isbn13(isbn)
        return

    raise ValueError(
        "ISBNは10桁または13桁で入力してください。"
    )
```

---

# 雑誌コードValidator

## 18. 公開関数

雑誌コードValidatorの公開関数は、次のとおりです。

```python
def validate_magazine_code(
    magazine_code: str,
) -> None:
    ...
```

配置場所：

```text
src/book_manager/validators/magazine_code_validator.py
```

---

## 19. 雑誌コードの基本方針

初期Versionでは、一般的な雑誌コードを次の形式として扱います。

```text
5桁または7桁の半角数字
```

5桁形式の例：

```text
12345
```

7桁形式の例：

```text
1234507
```

プロジェクト内の既存テストデータでは、7桁形式を使用しています。

---

## 20. 5桁と7桁を許可する理由

雑誌コードは、管理や入力元によって5桁部分だけを扱う場合と、号情報を含む7桁で扱う場合があります。

初期Versionでは、柔軟性を持たせるため、次の両方を許可します。

```text
基本コードのみ：5桁
号情報を含むコード：7桁
```

将来、実際の運用で7桁だけに限定できることが確認された場合は、設計変更を検討します。

---

## 21. 雑誌コードの文字種

すべてASCII数字である必要があります。

正式な判定は、次の形式とします。

```python
all(
    "0" <= character <= "9"
    for character in magazine_code
)
```

次の文字は許可しません。

* 全角数字。
* ハイフン。
* 空白。
* 英字。
* 記号。
* 改行。
* タブ。

---

## 22. 雑誌コードの検証順序

正式な検証順序は、次のとおりです。

```text
桁数を確認する
↓
文字種を確認する
↓
正常なら終了する
```

---

## 23. 雑誌コードのチェックデジット

初期Versionでは、雑誌コードのチェックデジット検証を行いません。

理由は、次のとおりです。

* プロジェクト内で扱う雑誌コードの仕様がまだ完全に確定していない。
* 5桁と7桁の入力を許可する。
* 実際の取得元ごとに表記方法が異なる可能性がある。
* 不確実な計算規則を実装すると、正しいデータを拒否する恐れがある。

将来、正式な運用仕様が確定した場合に追加します。

---

## 24. 雑誌コードのエラーメッセージ

桁数が不正な場合：

```text
雑誌コードは5桁または7桁で入力してください。
```

数字以外が含まれる場合：

```text
雑誌コードは半角数字で入力してください。
```

---

## 25. 雑誌コードValidatorの想定実装

```python
def validate_magazine_code(
    magazine_code: str,
) -> None:
    if len(magazine_code) not in (5, 7):
        raise ValueError(
            "雑誌コードは5桁または7桁で入力してください。"
        )

    if not all(
        "0" <= character <= "9"
        for character in magazine_code
    ):
        raise ValueError(
            "雑誌コードは半角数字で入力してください。"
        )
```

---

# 読了年月Validator

## 26. 公開関数

読了年月Validatorの公開関数は、次のとおりです。

```python
def validate_completion_month(
    completion_month: str,
) -> None:
    ...
```

配置場所：

```text
src/book_manager/validators/completion_month_validator.py
```

---

## 27. 読了年月の正式形式

読了年月は、次の形式とします。

```text
YYYY-MM
```

有効例：

```text
2026-07
1999-12
0001-01
```

無効例：

```text
2026/07
202607
2026-7
26-07
2026-00
2026-13
```

---

## 28. 読了年月の形式条件

文字列は、必ず7文字である必要があります。

```text
位置0〜3：年
位置4：半角ハイフン
位置5〜6：月
```

形式：

```text
NNNN-NN
```

年と月はASCII数字だけを許可します。

---

## 29. 年の範囲

初期Versionでは、年を次の範囲とします。

```text
0001〜9999
```

`0000` は許可しません。

理由は、一般的な暦として年0を使用しないためです。

将来、年月未詳などの特殊値が必要になった場合は、別の入力仕様を検討します。

---

## 30. 月の範囲

月は次の範囲とします。

```text
01〜12
```

次の値は無効です。

```text
00
13
99
```

---

## 31. 読了年月の検証方法

標準ライブラリの `datetime.strptime()` を使用する方法もありますが、初期Versionでは文字列構造を明示的に検証します。

理由は、次のとおりです。

* 必須形式が明確である。
* `YYYY-MM` 以外を確実に拒否できる。
* エラーメッセージを制御しやすい。
* 日を補完する必要がない。
* 処理内容が読みやすい。

---

## 32. 読了年月の検証順序

正式な検証順序は、次のとおりです。

```text
文字数が7文字か確認する
↓
5文字目が半角ハイフンか確認する
↓
年部分が4桁のASCII数字か確認する
↓
月部分が2桁のASCII数字か確認する
↓
年が0001〜9999か確認する
↓
月が01〜12か確認する
```

---

## 33. 読了年月のエラーメッセージ

形式が不正な場合：

```text
読了年月はYYYY-MM形式で入力してください。
```

月が範囲外の場合：

```text
読了年月の月は01から12で入力してください。
```

年が `0000` の場合：

```text
読了年月の年は0001から9999で入力してください。
```

---

## 34. 読了年月Validatorの想定実装

```python
def validate_completion_month(
    completion_month: str,
) -> None:
    if (
        len(completion_month) != 7
        or completion_month[4] != "-"
    ):
        raise ValueError(
            "読了年月はYYYY-MM形式で入力してください。"
        )

    year_text = completion_month[:4]
    month_text = completion_month[5:]

    if not (
        all(
            "0" <= character <= "9"
            for character in year_text
        )
        and all(
            "0" <= character <= "9"
            for character in month_text
        )
    ):
        raise ValueError(
            "読了年月はYYYY-MM形式で入力してください。"
        )

    year = int(year_text)
    month = int(month_text)

    if year == 0:
        raise ValueError(
            "読了年月の年は0001から9999で入力してください。"
        )

    if not 1 <= month <= 12:
        raise ValueError(
            "読了年月の月は01から12で入力してください。"
        )
```

---

# 共通設計

## 35. `None` の扱い

Validatorの引数型は `str` とします。

```python
def validate_isbn(
    isbn: str,
) -> None:
```

`None` は受け取りません。

任意入力項目が `None` の場合は、`BookService` がValidatorを呼び出しません。

```python
if normalized_isbn is not None:
    validate_isbn(normalized_isbn)
```

---

## 36. 空文字列の扱い

Validatorは、原則として空文字列を有効とはしません。

ただし、空文字列は `BookService` により `None` へ変換されるため、通常はValidatorへ渡されません。

直接呼び出された場合は、各Validatorの桁数または形式検証により `ValueError` となります。

---

## 37. 入力値を返さない理由

Validatorは、正規化済みの入力値を受け取るため、入力値を返しません。

次の形式は採用しません。

```python
def validate_isbn(
    isbn: str,
) -> str:
    return isbn
```

検証と変換を分離し、役割を明確にするためです。

---

## 38. booleanを返さない理由

次の形式は採用しません。

```python
def is_valid_isbn(
    isbn: str,
) -> bool:
    ...
```

`bool` だけでは、無効理由をGUIへ伝えられないためです。

正式には、無効理由を `ValueError` のメッセージで伝えます。

```python
validate_isbn(isbn)
```

---

## 39. 独自例外を導入しない理由

初期Versionでは、次のような独自例外を導入しません。

```python
class ValidationError(Exception):
    ...
```

理由は、次のとおりです。

* Validatorが3種類だけである。
* GUIでは入力エラーをまとめて扱える。
* `ValueError` で十分に意味が伝わる。
* 例外階層を増やす必要性がまだない。
* `BookService` 設計と整合する。

---

## 40. エラーメッセージの方針

エラーメッセージは、GUIでそのまま表示可能な日本語とします。

良い例：

```text
ISBNは10桁または13桁で入力してください。
```

避ける例：

```text
Invalid input.
```

```text
ValueError at isbn_validator.py line 42.
```

```text
Check digit mismatch: expected 4 but got 5.
```

内部計算値や技術情報は表示しません。

---

## 41. テスト方針

Validatorテストは、データベースを使用しない純粋な単体テストとします。

各テストでは、対象関数へ文字列を渡し、次を確認します。

* 有効な値で例外が発生しない。
* 無効な値で `ValueError` が発生する。
* エラーメッセージが設計どおりである。
* 境界値が正しく判定される。
* 全角数字などを誤って受け入れない。

---

# ISBN Validatorテスト

## 42. ISBN-10の有効値

最低限、次をテストします。

```text
4101010013
080442957X
```

確認内容：

```python
validate_isbn(isbn)
```

例外が発生しないこと。

---

## 43. ISBN-13の有効値

最低限、次をテストします。

```text
9784101010014
9784163917733
```

例外が発生しないことを確認します。

---

## 44. ISBNの桁数テスト

次をテストします。

* 9桁。
* 11桁。
* 12桁。
* 14桁。
* 空文字列。

すべて次のエラーとなります。

```text
ISBNは10桁または13桁で入力してください。
```

---

## 45. ISBNの文字種テスト

次をテストします。

* ISBN-13に英字が含まれる。
* ISBN-10の先頭9文字に英字が含まれる。
* ISBN-10の最終文字が小文字の `x`。
* 全角数字。
* ハイフン付き。
* 空白付き。

期待するエラー：

```text
ISBNの形式が正しくありません。
```

ただし、ハイフン付きや空白付きの値が13文字以外になる場合は、桁数エラーとなる可能性があります。

テストでは、どの検証順序に該当するかを明示して確認します。

---

## 46. ISBNのチェックデジットテスト

次をテストします。

* ISBN-10の末尾を不正な数字に変更する。
* ISBN-13の末尾を不正な数字に変更する。
* ISBN-10の `X` を不正な数字へ変更する。

期待するエラー：

```text
ISBNのチェックデジットが正しくありません。
```

---

## 47. ISBNの境界テスト

次を確認します。

* ISBN-10の最終文字が `0`。
* ISBN-10の最終文字が `X`。
* ISBN-13のチェックデジットが `0`。
* すべて数字であるがチェックデジットが不正。
* 全角数字を含む10文字または13文字。

---

# 雑誌コードValidatorテスト

## 48. 雑誌コードの有効値

次をテストします。

```text
12345
00001
1234507
0000001
```

例外が発生しないことを確認します。

---

## 49. 雑誌コードの桁数テスト

次をテストします。

* 4桁。
* 6桁。
* 8桁。
* 空文字列。

期待するエラー：

```text
雑誌コードは5桁または7桁で入力してください。
```

---

## 50. 雑誌コードの文字種テスト

次をテストします。

* 英字を含む。
* ハイフンを含む。
* 半角空白を含む。
* 全角数字。
* 記号を含む。

期待するエラー：

```text
雑誌コードは半角数字で入力してください。
```

文字数が5桁または7桁になるように調整し、文字種検証へ到達するテストを作成します。

---

# 読了年月Validatorテスト

## 51. 読了年月の有効値

次をテストします。

```text
0001-01
1999-12
2026-07
9999-12
```

例外が発生しないことを確認します。

---

## 52. 読了年月の形式テスト

次をテストします。

```text
202607
2026/07
2026-7
26-07
2026--07
2026-007
```

期待するエラー：

```text
読了年月はYYYY-MM形式で入力してください。
```

---

## 53. 読了年月の文字種テスト

次をテストします。

* 年に英字を含む。
* 月に英字を含む。
* 全角数字。
* 全角ハイフン。
* 半角空白。
* 改行。
* タブ。

期待するエラー：

```text
読了年月はYYYY-MM形式で入力してください。
```

---

## 54. 読了年月の月範囲テスト

次をテストします。

```text
2026-00
2026-13
2026-99
```

期待するエラー：

```text
読了年月の月は01から12で入力してください。
```

---

## 55. 読了年月の年範囲テスト

次をテストします。

```text
0000-01
```

期待するエラー：

```text
読了年月の年は0001から9999で入力してください。
```

4桁制限があるため、10000年以上は形式エラーとして扱います。

---

## 56. parametrized testの使用

同じ期待結果を持つ複数の入力値には、`pytest.mark.parametrize` を使用します。

例：

```python
@pytest.mark.parametrize(
    "isbn",
    [
        "123456789",
        "12345678901",
        "123456789012",
        "12345678901234",
        "",
    ],
)
def test_validate_isbn_rejects_invalid_length(
    isbn: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="ISBNは10桁または13桁で入力してください。",
    ):
        validate_isbn(isbn)
```

---

## 57. テストで確認しないもの

初期Versionでは、次をテスト対象としません。

* Validatorの実行速度。
* 大量データ処理。
* スレッド安全性。
* 外部APIとの連携。
* データベース保存。
* GUI表示。
* ログ出力。
* 英語メッセージ。
* ロケール切り替え。

---

## 58. 実装予定コード構成

### `isbn_validator.py`

```python
"""ISBN validation functions."""


def validate_isbn(
    isbn: str,
) -> None:
    """ISBN-10またはISBN-13を検証する。"""
    if len(isbn) == 10:
        _validate_isbn10(isbn)
        return

    if len(isbn) == 13:
        _validate_isbn13(isbn)
        return

    raise ValueError(
        "ISBNは10桁または13桁で入力してください。"
    )


def _validate_isbn10(
    isbn: str,
) -> None:
    ...


def _validate_isbn13(
    isbn: str,
) -> None:
    ...
```

### `magazine_code_validator.py`

```python
"""Magazine code validation functions."""


def validate_magazine_code(
    magazine_code: str,
) -> None:
    """雑誌コードを検証する。"""
    ...
```

### `completion_month_validator.py`

```python
"""Completion month validation functions."""


def validate_completion_month(
    completion_month: str,
) -> None:
    """読了年月を検証する。"""
    ...
```

---

## 59. 初期Versionで導入しないもの

次は、初期Versionでは導入しません。

* Validatorクラス。
* 共通基底クラス。
* Protocol。
* 独自例外クラス。
* ValidationResult型。
* エラーコード。
* 複数エラーの同時返却。
* 国際化。
* メッセージテンプレート。
* 正規表現の共通管理。
* ISBNの自動正規化。
* 全角数字の自動変換。
* 雑誌コードのチェックデジット。
* JANコード検証。
* ISSN検証。
* 出版年月検証。
* 書籍名文字数検証。
* 著者名検証。
* 出版社名検証。
* 禁止文字検証。

---

## 60. 将来の拡張候補

必要性が確認された場合に、次を検討します。

* `ValidationError` の導入。
* エラーコードの追加。
* 全角数字の正規化。
* ISBNプレフィックス検証。
* 雑誌コードの正式なチェックデジット検証。
* JANコードValidator。
* ISSN Validator。
* 出版年月Validator。
* 複数エラーの一括返却。
* GUI入力中のリアルタイム検証。
* 多言語メッセージ。
* 入力項目ごとの最大文字数検証。

---

## 61. Design Freeze条件

次の項目が承認された時点で、Version 0.1をDesign Freezeとします。

* Validatorは関数として実装する。
* Validatorは状態を持たない。
* Validatorは正規化を行わない。
* Validatorはデータベースへ接続しない。
* ValidatorはGUIを操作しない。
* 有効な場合は `None` を返す。
* 無効な場合は `ValueError` を送出する。
* ISBN-10とISBN-13へ対応する。
* ISBNのチェックデジットを検証する。
* ISBN-10末尾の大文字 `X` を許可する。
* 小文字 `x` は許可しない。
* ASCII数字だけを許可する。
* 雑誌コードは5桁または7桁とする。
* 雑誌コードはASCII数字だけを許可する。
* 雑誌コードのチェックデジットは初期Versionでは検証しない。
* 読了年月は `YYYY-MM` とする。
* 読了年月の年は `0001〜9999` とする。
* 読了年月の月は `01〜12` とする。
* エラーメッセージは日本語とする。
* 標準ライブラリだけで実装する。
* テストはデータベースを使わない単体テストとする。

---

## 62. 検討事項

Design Freeze前に、次を最終確認します。

### 62.1 雑誌コードの桁数

現在案：

```text
5桁または7桁
```

別案：

```text
7桁のみ
```

初期Versionでは、既存データや入力元の差を考慮し、5桁と7桁の両方を許可する案を推奨します。

---

### 62.2 読了年月の年 `0000`

現在案では無効とします。

```text
0000-01
```

将来、年月不明を表す必要がある場合は、特殊値ではなく `None` を使用する方針を推奨します。

---

### 62.3 ISBN小文字 `x`

現在案では無効とします。

```text
080442957x
```

Serviceは大文字変換を行わないため、利用者には大文字の `X` を入力してもらいます。

将来、入力利便性を優先する場合は、ServiceのISBN正規化で小文字 `x` を大文字 `X` へ変換する設計変更を検討します。

---

## 63. 次の作業

この設計書のレビューとDesign Freeze後、次の順序で進めます。

```text
validator_design_review.mdを作成する
↓
Validator設計を正式承認する
↓
ISBN Validatorを実装する
↓
雑誌コードValidatorを実装する
↓
読了年月Validatorを実装する
↓
Validatorテストを作成する
↓
全テストを実行する
↓
BookServiceを実装する
```
