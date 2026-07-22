# Validator設計レビュー

Version : 0.1
Last Updated : 2026-07-22
Status : Approved

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおけるValidator設計のレビュー結果と正式承認を記録するものです。

レビュー対象は、次の文書です。

```text
docs/validators/validator_design.md
```

初期Versionでは、次の3種類のValidatorを対象とします。

* ISBN Validator。
* 雑誌コードValidator。
* 読了年月Validator。

本レビューでは、`BookService` との責務境界、検証仕様、例外方針、テスト可能性および初期Versionとしての実装規模を確認しました。

---

## 2. レビュー対象

| 文書                    | 対象Version | レビュー前の状態 |
| --------------------- | --------: | -------- |
| `validator_design.md` |       0.1 | Draft    |

---

## 3. レビュー実施日

```text
2026-07-22
```

---

## 4. レビュー観点

本レビューでは、主に次の項目を確認しました。

* Validatorの責務が明確か。
* `BookService` との責務分担が適切か。
* 正規化と検証が分離されているか。
* Validatorが状態を持たない設計になっているか。
* ISBN-10およびISBN-13の検証仕様が正しいか。
* ISBNのチェックデジット検証が妥当か。
* 雑誌コードの桁数仕様が初期Versionとして適切か。
* 読了年月の形式および範囲が明確か。
* ASCII数字だけを許可する方針が一貫しているか。
* 無効値の扱いが明確か。
* 例外メッセージがGUIで利用可能か。
* テスト項目が十分か。
* 過剰な抽象化が含まれていないか。

---

## 5. レビュー結果

レビュー結果は、次のとおりです。

```text
承認
```

Validator設計は、`BookService` から独立した入力値検証機能として、適切に責務が整理されています。

重大な修正事項はありません。

次の補足方針を正式に採用し、Version 0.1をDesign Freezeとします。

* Validatorは関数形式で実装する。
* Validatorは正規化を行わない。
* Validatorは正規化済みの文字列だけを受け取る。
* ISBN-10とISBN-13の両方を検証する。
* ISBN-10末尾の大文字 `X` を許可する。
* ISBN-10末尾の小文字 `x` は許可しない。
* ISBNはASCII数字だけを許可する。
* 雑誌コードは5桁または7桁のASCII数字とする。
* 雑誌コードのチェックデジット検証は行わない。
* 読了年月は `YYYY-MM` 形式とする。
* 読了年月の年は `0001〜9999` とする。
* 読了年月の月は `01〜12` とする。
* 有効な場合は `None` を返す。
* 無効な場合は `ValueError` を送出する。
* エラーメッセージはGUIでそのまま表示可能な日本語とする。
* Validator独自の例外クラスは導入しない。
* テストはデータベースを使用しない単体テストとする。

---

## 6. Validatorの責務

Validatorが担当する処理を、次のとおり承認します。

```text
入力文字列の形式確認
文字種の確認
桁数の確認
値の範囲確認
チェックデジットの確認
無効理由を示すValueErrorの送出
```

Validatorは、値が保存可能かどうかを判定します。

---

## 7. Validatorに含めない責務

次の処理をValidatorに含めない設計を承認します。

```text
前後空白の除去
空文字列からNoneへの変換
ハイフンの除去
全角文字から半角文字への変換
小文字から大文字への変換
入力値の自動修正
BookItemの生成
Repositoryの呼び出し
SQLiteへの接続
GUIメッセージの表示
重複確認
日時生成
```

これらは、`BookService` またはGUIが担当します。

---

## 8. 依存方向

正式な依存方向を、次のとおり承認します。

```text
GUI
↓
BookService
↓
Validators
```

Validatorは、次のモジュールへ依存しません。

```text
BookService
BookRepository
BookItem
SQLite
Tkinter
外部API
```

Validatorは、Python標準機能だけで完結します。

---

## 9. 関数形式

Validatorをクラスではなく関数として実装する設計を承認します。

公開関数は、次のとおりです。

```python
def validate_isbn(
    isbn: str,
) -> None:
    ...

def validate_magazine_code(
    magazine_code: str,
) -> None:
    ...

def validate_completion_month(
    completion_month: str,
) -> None:
    ...
```

Validatorは状態を保持せず、入力値だけを検証します。

---

## 10. クラスを使用しない理由

初期Versionでは、次のようなクラスは使用しません。

```python
class IsbnValidator:
    def validate(
        self,
        isbn: str,
    ) -> None:
        ...
```

理由は、次のとおりです。

* Validatorが状態を持たない。
* 設定値を保持しない。
* 依存オブジェクトを必要としない。
* 関数だけで役割を十分に表現できる。
* 呼び出し方が単純になる。
* テストが容易になる。

---

## 11. 正規化との責務境界

正規化を `BookService`、検証をValidatorが担当する設計を承認します。

正式な処理順序は、次のとおりです。

```text
GUIから入力値を受け取る
↓
BookServiceが正規化する
↓
正規化後にNoneか確認する
↓
NoneでなければValidatorを呼び出す
↓
検証済みの値をBookItemへ設定する
```

例：

```text
978-4-10-101001-4
↓
BookServiceで正規化
9784101010014
↓
validate_isbn()
```

---

## 12. Validatorで正規化しない理由

Validator内で正規化すると、次の問題が発生します。

* 検証前後で値が変化する。
* 呼び出し側が保存される値を把握しにくくなる。
* 検証と変換の責務が混在する。
* GUI、Service、Validatorで正規化処理が重複する。
* 誤った入力値が暗黙的に修正される可能性がある。
* テスト対象が複雑になる。

したがって、Validatorは入力値を変更しません。

---

## 13. 戻り値

有効な場合に `None` を返す設計を承認します。

```python
result = validate_isbn(
    "9784101010014"
)

assert result is None
```

Validatorは入力値を変換せず、検証結果の値も返しません。

---

## 14. `bool` を返さない理由

次の形式は採用しません。

```python
def is_valid_isbn(
    isbn: str,
) -> bool:
    ...
```

`bool` だけでは、無効理由をGUIへ伝えられません。

正式には、無効な場合に `ValueError` を送出します。

```python
validate_isbn(isbn)
```

呼び出し側は、例外メッセージを利用できます。

---

## 15. 例外方針

無効な入力値では、`ValueError` を送出する設計を承認します。

例：

```python
raise ValueError(
    "ISBNの形式が正しくありません。"
)
```

初期Versionでは、次の独自例外を導入しません。

```python
class ValidationError(Exception):
    ...
```

現在は入力検証エラーを1種類として扱えば十分であり、独自例外階層は不要です。

---

## 16. `None` の扱い

Validatorの引数型は `str` とします。

```python
def validate_isbn(
    isbn: str,
) -> None:
```

`None` は受け取りません。

任意項目が `None` の場合は、`BookService` がValidatorを呼び出しません。

```python
if normalized_isbn is not None:
    validate_isbn(normalized_isbn)
```

Validator内に、`None` を許可する処理は追加しません。

---

## 17. 空文字列の扱い

空文字列は有効とはしません。

ただし、通常は `BookService` が空文字列を `None` に変換するため、Validatorへ渡されません。

Validatorを直接呼び出した場合は、桁数または形式エラーになります。

```python
validate_isbn("")
```

結果：

```text
ValueError
```

---

# ISBN Validatorレビュー

## 18. 公開関数

次の公開関数を承認します。

```python
def validate_isbn(
    isbn: str,
) -> None:
    ...
```

配置場所は、次のとおりです。

```text
src/book_manager/validators/isbn_validator.py
```

---

## 19. 対応形式

初期Versionでは、次のISBN形式に対応する設計を承認します。

```text
ISBN-10
ISBN-13
```

有効例：

```text
4101010013
080442957X
9784101010014
9784163917733
```

---

## 20. 桁数による振り分け

桁数に応じて検証処理を振り分ける設計を承認します。

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

10桁および13桁以外の入力値は、内容にかかわらず桁数エラーとします。

---

## 21. ISBN-10の文字種

ISBN-10では、次の条件を採用します。

```text
先頭9文字：ASCII数字
最終文字：ASCII数字または大文字X
```

正式な判定例は、次のとおりです。

```python
first_nine_are_digits = all(
    "0" <= character <= "9"
    for character in isbn[:9]
)

last_is_valid = (
    "0" <= isbn[-1] <= "9"
    or isbn[-1] == "X"
)
```

`str.isdigit()` だけを使用しない方針を承認します。

---

## 22. ISBN-10末尾の `X`

ISBN-10の最終文字として、大文字の `X` を許可する設計を承認します。

```text
080442957X
```

`X` は数値10として扱います。

```python
check_digit = (
    10
    if isbn[-1] == "X"
    else int(isbn[-1])
)
```

---

## 23. 小文字 `x`

ISBN-10末尾の小文字 `x` は無効とする設計を承認します。

```text
080442957x
```

結果：

```text
ISBNの形式が正しくありません。
```

初期Versionでは、Serviceによる自動大文字変換も行いません。

利用者には、大文字の `X` を入力してもらいます。

---

## 24. ISBN-10のチェックデジット

ISBN-10のチェックデジット検証方法を承認します。

各桁へ10から1までの重みを掛けます。

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

加重合計が11で割り切れる場合に有効とします。

```python
weighted_sum % 11 == 0
```

---

## 25. ISBN-10の実装方針

次の実装方針を承認します。

```python
def _validate_isbn10(
    isbn: str,
) -> None:
    if not all(
        "0" <= character <= "9"
        for character in isbn[:9]
    ):
        raise ValueError(
            "ISBNの形式が正しくありません。"
        )

    if not (
        "0" <= isbn[-1] <= "9"
        or isbn[-1] == "X"
    ):
        raise ValueError(
            "ISBNの形式が正しくありません。"
        )

    digits = [
        int(character)
        for character in isbn[:9]
    ]

    check_digit = (
        10
        if isbn[-1] == "X"
        else int(isbn[-1])
    )

    values = [
        *digits,
        check_digit,
    ]

    weighted_sum = sum(
        value * weight
        for value, weight in zip(
            values,
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

## 26. ISBN-13の文字種

ISBN-13では、13文字すべてをASCII数字とする設計を承認します。

正式な判定は、次のとおりです。

```python
all(
    "0" <= character <= "9"
    for character in isbn
)
```

全角数字は無効です。

```text
９７８４１０１０１００１４
```

---

## 27. ISBN-13のチェックデジット

ISBN-13のチェックデジット検証方法を承認します。

先頭12桁へ、1と3の重みを交互に掛けます。

```python
weighted_sum = sum(
    digit * (
        1
        if index % 2 == 0
        else 3
    )
    for index, digit in enumerate(
        digits[:12]
    )
)
```

チェックデジットは、次の式で求めます。

```python
expected_check_digit = (
    10 - weighted_sum % 10
) % 10
```

13桁目と一致した場合に有効とします。

---

## 28. ISBN-13の実装方針

次の実装方針を承認します。

```python
def _validate_isbn13(
    isbn: str,
) -> None:
    if not all(
        "0" <= character <= "9"
        for character in isbn
    ):
        raise ValueError(
            "ISBNの形式が正しくありません。"
        )

    digits = [
        int(character)
        for character in isbn
    ]

    weighted_sum = sum(
        digit * (
            1
            if index % 2 == 0
            else 3
        )
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

## 29. ISBNプレフィックス

初期Versionでは、ISBN-13の先頭3桁が `978` または `979` であるかを検証しません。

検証対象は、次のとおりです。

```text
桁数
文字種
チェックデジット
```

理由は、初期VersionではISBNの数学的妥当性を検証することを優先し、プレフィックス管理まで対象を広げないためです。

将来、必要性が確認された場合に追加します。

---

## 30. ISBNエラーメッセージ

次のエラーメッセージを承認します。

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

ISBN-10とISBN-13でメッセージを分けません。

---

## 31. ISBN非公開関数

次の非公開関数への分割を承認します。

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

公開関数は桁数による振り分けだけを担当します。

---

# 雑誌コードValidatorレビュー

## 32. 公開関数

次の公開関数を承認します。

```python
def validate_magazine_code(
    magazine_code: str,
) -> None:
    ...
```

配置場所は、次のとおりです。

```text
src/book_manager/validators/magazine_code_validator.py
```

---

## 33. 雑誌コードの正式仕様

初期Versionでは、次の形式を有効とします。

```text
5桁または7桁のASCII数字
```

有効例：

```text
12345
00001
1234507
0000001
```

---

## 34. 5桁と7桁を許可する方針

雑誌コードを5桁または7桁とする設計を承認します。

理由は、次のとおりです。

* 入力元により5桁部分だけを取得する可能性がある。
* 既存のRepositoryテストでは7桁を使用している。
* 初期段階では入力形式を過度に限定しない方が安全である。
* 実運用データを確認した後に制限を強化できる。
* データベース設計では文字列として保存している。

現時点では、7桁だけに限定しません。

---

## 35. 雑誌コードの文字種

ASCII数字だけを許可する設計を承認します。

正式な判定は、次のとおりです。

```python
all(
    "0" <= character <= "9"
    for character in magazine_code
)
```

次の値は無効です。

```text
１２３４５
12A45
12-45
12 45
```

---

## 36. 雑誌コードの検証順序

正式な検証順序を、次のとおり承認します。

```text
桁数を確認する
↓
文字種を確認する
↓
正常なら終了する
```

桁数が5桁または7桁でない場合は、文字種にかかわらず桁数エラーとします。

---

## 37. 雑誌コードのチェックデジット

初期Versionでは、雑誌コードのチェックデジット検証を行わない設計を承認します。

理由は、次のとおりです。

* 5桁と7桁の両方を許可する。
* 入力元ごとの仕様差がまだ不明である。
* 正式な運用データを確認していない。
* 不確実な検証を実装すると正しい値を拒否する可能性がある。
* 初期Versionでは文字種と桁数で十分な防御になる。

---

## 38. 雑誌コードの実装方針

次の実装方針を承認します。

```python
def validate_magazine_code(
    magazine_code: str,
) -> None:
    if len(magazine_code) not in (
        5,
        7,
    ):
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

## 39. 雑誌コードのエラーメッセージ

次のメッセージを承認します。

桁数が不正な場合：

```text
雑誌コードは5桁または7桁で入力してください。
```

文字種が不正な場合：

```text
雑誌コードは半角数字で入力してください。
```

---

# 読了年月Validatorレビュー

## 40. 公開関数

次の公開関数を承認します。

```python
def validate_completion_month(
    completion_month: str,
) -> None:
    ...
```

配置場所は、次のとおりです。

```text
src/book_manager/validators/completion_month_validator.py
```

---

## 41. 読了年月の正式形式

読了年月を次の形式とする設計を承認します。

```text
YYYY-MM
```

文字列長は、必ず7文字とします。

```text
位置0〜3：年
位置4：半角ハイフン
位置5〜6：月
```

---

## 42. 有効値

次の値を有効とします。

```text
0001-01
1999-12
2026-07
9999-12
```

年および月は、ASCII数字だけを許可します。

---

## 43. 年の範囲

年を `0001〜9999` とする設計を承認します。

```text
0001
〜
9999
```

`0000` は無効とします。

```text
0000-01
```

理由は、通常の暦では年0を使用しないためです。

年月が不明な場合は、特殊な年月ではなく `None` を使用します。

---

## 44. 月の範囲

月を `01〜12` とする設計を承認します。

有効範囲：

```text
01
〜
12
```

無効例：

```text
00
13
99
```

---

## 45. `datetime.strptime()` を使用しない方針

初期Versionでは、`datetime.strptime()` を使用せず、文字列構造を明示的に検証する設計を承認します。

理由は、次のとおりです。

* `YYYY-MM` 形式を厳密に確認できる。
* 月だけを保存する仕様に適している。
* 年0の扱いを明示できる。
* エラーメッセージを制御しやすい。
* 実装内容が読みやすい。
* 日を補完する必要がない。

---

## 46. 読了年月の検証順序

正式な検証順序を、次のとおり承認します。

```text
文字数が7文字か確認する
↓
5文字目が半角ハイフンか確認する
↓
年部分が4桁のASCII数字か確認する
↓
月部分が2桁のASCII数字か確認する
↓
年が0000でないか確認する
↓
月が01〜12か確認する
```

---

## 47. 読了年月の実装方針

次の実装方針を承認します。

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

    if not all(
        "0" <= character <= "9"
        for character in year_text
    ):
        raise ValueError(
            "読了年月はYYYY-MM形式で入力してください。"
        )

    if not all(
        "0" <= character <= "9"
        for character in month_text
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

## 48. 読了年月のエラーメッセージ

次のメッセージを承認します。

形式が不正な場合：

```text
読了年月はYYYY-MM形式で入力してください。
```

年が `0000` の場合：

```text
読了年月の年は0001から9999で入力してください。
```

月が範囲外の場合：

```text
読了年月の月は01から12で入力してください。
```

---

# 共通テスト方針

## 49. テストの種類

Validatorテストは、データベースを使用しない純粋な単体テストとします。

```text
入力文字列
↓
Validator関数
↓
例外の有無を確認
```

次の機能は使用しません。

```text
SQLite
BookRepository
BookService
Tkinter
外部API
Mock
```

---

## 50. 有効値のテスト方法

有効な値では、例外が発生しないことを確認します。

例：

```python
def test_validate_isbn_accepts_valid_isbn13(
) -> None:
    validate_isbn(
        "9784101010014"
    )
```

戻り値を確認する場合は、次のように記述できます。

```python
result = validate_isbn(
    "9784101010014"
)

assert result is None
```

---

## 51. 無効値のテスト方法

無効な値では、`ValueError` とメッセージを確認します。

```python
with pytest.raises(
    ValueError,
    match="ISBNの形式が正しくありません。",
):
    validate_isbn(
        "978410101001A"
    )
```

エラーメッセージが設計から変更された場合も、テストで検出できます。

---

## 52. parametrized test

同じ期待結果を持つ複数入力には、`pytest.mark.parametrize` を使用する設計を承認します。

```python
@pytest.mark.parametrize(
    "isbn",
    [
        "",
        "123456789",
        "12345678901",
        "123456789012",
        "12345678901234",
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

テスト名と入力値の意味が分かりにくくなる場合は、個別テストへ分けます。

---

# ISBNテストレビュー

## 53. ISBN-10の有効値

最低限、次の値をテストします。

```text
4101010013
080442957X
```

確認内容：

* 数字だけのISBN-10を受け入れる。
* 末尾が大文字 `X` のISBN-10を受け入れる。
* 戻り値が `None` になる。

---

## 54. ISBN-13の有効値

最低限、次の値をテストします。

```text
9784101010014
9784163917733
```

確認内容：

* 13桁のASCII数字を受け入れる。
* チェックデジットが正しく判定される。
* 戻り値が `None` になる。

---

## 55. ISBN桁数テスト

次の値をテストします。

```text
空文字列
9桁
11桁
12桁
14桁
```

期待するメッセージ：

```text
ISBNは10桁または13桁で入力してください。
```

---

## 56. ISBN文字種テスト

次をテストします。

* ISBN-10の先頭9文字に英字を含む。
* ISBN-10末尾が小文字 `x`。
* ISBN-10末尾が `X` 以外の英字。
* ISBN-13に英字を含む。
* 全角数字を含む。
* 記号を含む。
* 改行またはタブを含む。

期待するメッセージ：

```text
ISBNの形式が正しくありません。
```

桁数エラーが先に発生しないよう、10文字または13文字に調整します。

---

## 57. ISBNチェックデジットテスト

次をテストします。

* 有効なISBN-10の末尾を不正な値へ変更する。
* 有効なISBN-13の末尾を不正な値へ変更する。
* 有効な末尾 `X` のISBN-10を不正な数字へ変更する。

期待するメッセージ：

```text
ISBNのチェックデジットが正しくありません。
```

---

## 58. ISBN境界テスト

次を確認します。

* ISBN-10末尾が `0`。
* ISBN-10末尾が `X`。
* ISBN-13のチェックデジットが `0`。
* すべてASCII数字だがチェックデジットが不正。
* 全角数字だけで10文字または13文字。

---

# 雑誌コードテストレビュー

## 59. 雑誌コードの有効値

次をテストします。

```text
12345
00001
1234507
0000001
```

確認内容：

* 5桁を受け入れる。
* 7桁を受け入れる。
* 先頭0を許可する。
* 戻り値が `None` になる。

---

## 60. 雑誌コードの桁数テスト

次をテストします。

```text
空文字列
4桁
6桁
8桁
```

期待するメッセージ：

```text
雑誌コードは5桁または7桁で入力してください。
```

---

## 61. 雑誌コードの文字種テスト

5文字または7文字に調整した上で、次をテストします。

* 英字を含む。
* 全角数字を含む。
* ハイフンを含む。
* 空白を含む。
* 記号を含む。
* 改行またはタブを含む。

期待するメッセージ：

```text
雑誌コードは半角数字で入力してください。
```

---

# 読了年月テストレビュー

## 62. 読了年月の有効値

次をテストします。

```text
0001-01
1999-12
2026-07
9999-12
```

確認内容：

* 年の最小値を受け入れる。
* 年の最大値を受け入れる。
* 月の最小値を受け入れる。
* 月の最大値を受け入れる。
* 戻り値が `None` になる。

---

## 63. 読了年月の形式テスト

次をテストします。

```text
202607
2026/07
2026-7
26-07
2026--07
2026-007
```

期待するメッセージ：

```text
読了年月はYYYY-MM形式で入力してください。
```

---

## 64. 読了年月の文字種テスト

次をテストします。

* 年部分に英字を含む。
* 月部分に英字を含む。
* 全角数字を含む。
* 全角ハイフンを含む。
* 半角空白を含む。
* 改行を含む。
* タブを含む。

期待するメッセージ：

```text
読了年月はYYYY-MM形式で入力してください。
```

---

## 65. 読了年月の年範囲テスト

次の値をテストします。

```text
0000-01
```

期待するメッセージ：

```text
読了年月の年は0001から9999で入力してください。
```

---

## 66. 読了年月の月範囲テスト

次の値をテストします。

```text
2026-00
2026-13
2026-99
```

期待するメッセージ：

```text
読了年月の月は01から12で入力してください。
```

---

## 67. 非公開関数の直接テスト

ISBN Validatorの次の非公開関数は、原則として直接テストしません。

```text
_validate_isbn10()
_validate_isbn13()
```

公開関数 `validate_isbn()` を通して動作を確認します。

非公開関数の実装詳細ではなく、公開APIの動作をテストするためです。

---

## 68. 型に関する方針

Validatorの型ヒントは、すべて `str` とします。

```python
def validate_isbn(
    isbn: str,
) -> None:
```

実行時に、`int` や `None` を明示的に型検証する処理は追加しません。

型ヒントに従った呼び出しを前提とします。

誤った型が渡された場合の挙動は、初期Versionの保証対象外とします。

---

## 69. エラーメッセージの正規表現

pytestの `match` は正規表現として扱われます。

今回のメッセージには、正規表現上の重大な特殊文字は含まれていないため、そのまま使用できます。

必要になった場合は、次を使用します。

```python
import re

match=re.escape(
    "エラーメッセージ"
)
```

初期Versionでは必須としません。

---

## 70. 実装時の注意事項

### 70.1 `str.isdigit()` だけを使用しない

次の実装は行いません。

```python
if not isbn.isdigit():
    ...
```

`str.isdigit()` は、全角数字などもTrueとするためです。

正式にはASCII範囲を明示します。

```python
all(
    "0" <= character <= "9"
    for character in isbn
)
```

---

### 70.2 Validator内で値を修正しない

次の実装は禁止します。

```python
isbn = isbn.replace("-", "")
```

```python
isbn = isbn.upper()
```

```python
completion_month = completion_month.strip()
```

これらは `BookService` の責務です。

---

### 70.3 エラーをまとめて返さない

初期Versionでは、最初に検出したエラーで `ValueError` を送出します。

次のような複数エラーの収集は行いません。

```python
errors = []
```

GUIでは、1件ずつ修正してもらう方針とします。

---

### 70.4 技術情報をメッセージへ含めない

次のようなメッセージは使用しません。

```text
Expected check digit 4 but got 5.
```

```text
ValueError in _validate_isbn13.
```

GUIで利用者へ表示できる日本語メッセージだけを使用します。

---

### 70.5 外部ライブラリを使用しない

ISBN検証ライブラリや日付検証ライブラリは導入しません。

Python標準機能だけで十分に実装できます。

---

## 71. 初期Versionで導入しないもの

次の機能は、初期Versionでは導入しません。

```text
Validatorクラス
共通基底クラス
Protocol
独自例外クラス
ValidationResult
エラーコード
複数エラーの同時返却
国際化
メッセージカタログ
ロギング
全角文字の自動変換
ISBNの自動正規化
ISBNプレフィックス検証
雑誌コードのチェックデジット
JANコード検証
ISSN検証
書籍名Validator
著者名Validator
出版社名Validator
出版年月Validator
未来年月の禁止
リアルタイム入力検証
外部ライブラリ
```

---

## 72. 将来の拡張条件

次の状況が発生した場合に、設計変更を検討します。

### 独自例外の導入

```text
GUIで検証項目ごとに処理を分ける
エラーコードが必要になる
外部APIの検証エラーと区別する
```

### 全角文字の正規化

```text
利用者の入力ミスが多い
GUIで全角入力が頻発する
入力利便性を優先する
```

### ISBNプレフィックス検証

```text
ISBN以外の13桁コードが登録される
978または979だけに限定する要件が確定する
```

### 雑誌コード仕様の強化

```text
入力元の仕様が確定する
7桁だけに統一できる
チェックデジット規則が確定する
```

### 読了年月仕様の変更

```text
年月不明を表す必要が生じる
未来年月を禁止する
和暦入力へ対応する
日単位の読了日を保存する
```

---

## 73. 設計間の整合性

### 73.1 `BookService` との整合性

| 確認項目                      | 結果 |
| ------------------------- | -- |
| Serviceが正規化を担当する          | 一致 |
| Validatorは正規化済み文字列を受け取る   | 一致 |
| `None` の場合はValidatorを呼ばない | 一致 |
| 無効時に `ValueError` を送出する   | 一致 |
| GUIで例外メッセージを表示できる         | 一致 |
| ValidatorはRepositoryを呼ばない | 一致 |

---

### 73.2 `BookItem` との整合性

| 確認項目                    | 結果 |
| ----------------------- | -- |
| モデル自身は入力検証を行わない         | 一致 |
| Serviceが検証済みの値でモデルを生成する | 一致 |
| ISBNを文字列として保持する         | 一致 |
| 雑誌コードを文字列として保持する        | 一致 |
| 読了年月を文字列として保持する         | 一致 |
| 任意項目は `None` を許可する      | 一致 |

---

### 73.3 データベース設計との整合性

| 確認項目                   | 結果 |
| ---------------------- | -- |
| ISBNはTEXTとして保存する       | 一致 |
| 雑誌コードはTEXTとして保存する      | 一致 |
| 読了年月はTEXTとして保存する       | 一致 |
| 任意項目はNULLを許可する         | 一致 |
| 重複はValidatorで拒否しない     | 一致 |
| ValidatorはSQLiteへ接続しない | 一致 |

---

### 73.4 プロジェクト構成との整合性

| 確認項目                          | 結果 |
| ----------------------------- | -- |
| Validatorを `validators` に配置する | 一致 |
| テストを `tests/validators` に配置する | 一致 |
| 関数ごとにモジュールを分ける                | 一致 |
| 標準ライブラリだけで実装する                | 一致 |
| 過剰な抽象化を避ける                    | 一致 |

---

## 74. 正式なファイル構成

Design Freeze後に、次のファイルを作成します。

```text
src/book_manager/validators/__init__.py
src/book_manager/validators/isbn_validator.py
src/book_manager/validators/magazine_code_validator.py
src/book_manager/validators/completion_month_validator.py
```

テストファイルは、次のとおりです。

```text
tests/validators/test_isbn_validator.py
tests/validators/test_magazine_code_validator.py
tests/validators/test_completion_month_validator.py
```

---

## 75. 実装順序

次の順序で実装する方針を承認します。

```text
validators/__init__.pyを作成する
↓
ISBN Validatorを実装する
↓
雑誌コードValidatorを実装する
↓
読了年月Validatorを実装する
↓
ISBN Validatorテストを作成する
↓
雑誌コードValidatorテストを作成する
↓
読了年月Validatorテストを作成する
↓
Validatorテストを実行する
↓
全テストを実行する
```

実装とテストは、別コミットとします。

---

## 76. コミット単位

Validator設計とレビュー文書は、次のコミットとして管理します。

```text
docs: Validator設計を正式承認
```

実装とテストは、次のように分けます。

```text
feat: Validatorを追加
test: Validatorテストを追加
```

---

## 77. Design Freeze判定

Validator設計Version 0.1を、初期実装におけるDesign Freeze版として承認します。

```text
Approved
Design Freeze
```

正式な設計基準は、次のとおりです。

```text
validator_design.md        : Version 0.1
validator_design_review.md : Version 0.1
implementation style       : 関数
valid return value         : None
invalid result             : ValueError
normalization              : BookService
ISBN                       : ISBN-10 / ISBN-13
magazine code              : 5桁または7桁
completion month           : YYYY-MM
external libraries         : 使用しない
Python                     : 3.12以上
```

---

## 78. Design Freeze後の変更手順

検証仕様、公開関数、例外メッセージまたは責務を変更する場合は、次の手順を行います。

```text
変更理由を整理する
↓
BookServiceへの影響を確認する
↓
GUIへの影響を確認する
↓
BookItemへの影響を確認する
↓
データベース設計への影響を確認する
↓
validator_design.mdを更新する
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

## 79. 次の作業

Design Freeze後は、次の順序で進めます。

```text
ISBN Validatorを実装する
↓
雑誌コードValidatorを実装する
↓
読了年月Validatorを実装する
↓
Validatorテストを作成する
↓
Validatorテストを実行する
↓
全テストを実行する
↓
実装とテストを分けてコミットする
↓
BookServiceを実装する
```
