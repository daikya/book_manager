# 読書記録集計・可視化機能 設計書

## 1. 目的

本設計書は、book_manager Version 1.9で追加する読書記録の集計・可視化機能を定義する。

Version 1.8では、一冊の書籍へ複数の読書履歴を登録し、読書開始日、読了日および読書メモを一回ごとの記録として管理できるようにした。

Version 1.9では、蓄積した読書履歴から基本的な読書実績を集計し、数値と月別棒グラフで振り返れるようにする。

個人利用で理解しやすい集計へ範囲を限定し、既存の読書履歴管理機能を変更せずに読み取り専用の集計機能として追加する。

---

## 2. 背景

現在の読書履歴画面では、選択した一冊の履歴を新しい順に確認できる。

一方、次のような蔵書全体の状況は確認できない。

* 登録した読書履歴の総数
* 読書履歴を持つ書籍数
* 読了日を記録した回数
* 再読した書籍数
* 年ごとの読了数
* 月ごとの読了数

Version 1.9では、既存の`reading_histories`を集計元として、これらを一つの専用画面で確認できるようにする。

---

## 3. 対象範囲

Version 1.9では、次を実装対象とする。

* 読書履歴総数の集計
* 読書履歴を持つ書籍数の集計
* 読了記録数の集計
* 再読書籍数の集計
* 読了記録が存在する年の取得
* 選択した年の月別読了数の集計
* 全体集計値を表示する専用画面
* 対象年を選択するGUI
* 1月から12月までの月別集計表示
* Tkinterの`Canvas`による月別棒グラフ
* データがない場合の空状態表示
* Repository・Service・GUIの自動テスト
* Windows実環境での表示確認

---

## 4. 対象外

Version 1.9では、次を実装しない。

* 読書時間の計測と集計
* ページ数や進捗率の集計
* 年間読書目標と達成率
* 任意の日付範囲による集計
* タグ別・著者別・出版社別の集計
* 読書状態・お気に入り・評価の集計
* 円グラフや折れ線グラフ
* グラフ描画用外部ライブラリの追加
* 集計結果の画像・PDF・CSV出力
* 集計画面からの書籍または履歴の編集
* 読書履歴専用CSVの入出力
* 外部サービスとの同期

必要性が確認できた機能はVersion 2.0以降の候補とする。

---

## 5. 用語

| 用語 | 定義 |
|---|---|
| 読書履歴総数 | `reading_histories`に存在する全行数 |
| 履歴のある書籍数 | 読書履歴を一件以上持つ重複しない書籍数 |
| 読了記録数 | `completed_on`が設定された読書履歴数 |
| 再読書籍数 | 読書履歴を二件以上持つ書籍数 |
| 対象年 | 読了日が存在する暦年 |
| 月別読了数 | 指定年・指定月に`completed_on`を持つ読書履歴数 |
| 空状態 | 読書履歴または読了記録が存在しない状態 |

「冊数」は書籍数、「回数」または「記録数」は履歴数を表す。

---

## 6. 基本方針

* 集計元は`reading_histories`とする。
* 読書状態と読了年月は集計元に使用しない。
* 一つの読書履歴を一回分の読書記録として数える。
* 同じ書籍の複数履歴は、それぞれ別の履歴として数える。
* 読了日がない履歴は読書履歴総数へ含め、読了記録数には含めない。
* 再読書籍数は読了日の有無にかかわらず、履歴が二件以上ある書籍を数える。
* 年別・月別集計は`completed_on`を基準とする。
* 集計画面は読み取り専用とする。
* GUIはRepositoryを直接呼び出さない。
* 集計SQLはRepositoryへ配置する。
* 集計結果の整形と入力検証はServiceへ配置する。
* グラフはTkinterの`Canvas`で描画する。
* Version 1.9ではデータベース構造を変更しない。

---

## 7. 集計定義

### 7.1 読書履歴総数

`reading_histories`の全行を数える。

```sql
SELECT COUNT(*)
FROM reading_histories
```

開始日・読了日がなく、メモだけの履歴も一件として含める。

### 7.2 履歴のある書籍数

`book_item_id`の重複を除いて数える。

```sql
SELECT COUNT(DISTINCT book_item_id)
FROM reading_histories
```

外部キー制約と`ON DELETE CASCADE`により、削除済み書籍の履歴は残らない。

### 7.3 読了記録数

`completed_on IS NOT NULL`の履歴を数える。

```sql
SELECT COUNT(*)
FROM reading_histories
WHERE completed_on IS NOT NULL
```

開始日やメモの有無は条件にしない。

### 7.4 再読書籍数

同一の`book_item_id`を持つ履歴が二件以上ある書籍を数える。

```sql
SELECT COUNT(*)
FROM (
    SELECT book_item_id
    FROM reading_histories
    GROUP BY book_item_id
    HAVING COUNT(*) >= 2
)
```

Version 1.9では、一件目を初回読書、二件目以降を再読記録とみなす。読了日がない履歴も履歴数へ含める。

### 7.5 対象年

`completed_on`の先頭4文字から、重複しない年を取得する。

```sql
SELECT DISTINCT CAST(substr(completed_on, 1, 4) AS INTEGER) AS year
FROM reading_histories
WHERE completed_on IS NOT NULL
ORDER BY year DESC
```

既存のValidatorとデータベース制約により、読了日は`YYYY-MM-DD`形式で保存される。

### 7.6 月別読了数

指定年の`completed_on`を対象として、月ごとの履歴数を取得する。

```sql
SELECT
    CAST(substr(completed_on, 6, 2) AS INTEGER) AS month,
    COUNT(*) AS completed_count
FROM reading_histories
WHERE substr(completed_on, 1, 4) = ?
GROUP BY month
ORDER BY month ASC
```

プレースホルダーには4桁へ整形した対象年を渡す。この方式により、上限の9999年でも翌年10000年を生成せず安全に集計できる。

Repositoryは記録が存在する月だけを返し、Serviceが不足する月を0件で補完する。

---

## 8. Model設計

### 8.1 配置場所

```text
src/book_manager/models/reading_statistics.py
```

### 8.2 全体集計Model

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReadingStatisticsSummary:
    """読書履歴の全体集計を表す。"""

    total_history_count: int
    books_with_history_count: int
    completed_history_count: int
    reread_book_count: int
```

### 8.3 月別集計Model

```python
@dataclass(frozen=True, slots=True)
class MonthlyReadingCount:
    """一か月分の読了記録数を表す。"""

    year: int
    month: int
    completed_count: int
```

### 8.4 Modelの責務

Modelは集計結果の保持だけを担当する。

次は行わない。

* SQLiteへの接続
* SQLの実行
* 対象年の検証
* 0件の月の補完
* GUI表示文字列の生成
* グラフ描画

`frozen=True`として、取得済み集計結果の意図しない変更を防止する。

---

## 9. Repository設計

### 9.1 配置場所

既存ファイルへ集計処理を追加する。

```text
src/book_manager/repositories/reading_history_repository.py
```

### 9.2 公開メソッド

```python
def get_statistics_summary(
    self,
) -> ReadingStatisticsSummary:
    ...

def get_completed_years(
    self,
) -> list[int]:
    ...

def get_monthly_completed_counts(
    self,
    year: int,
) -> dict[int, int]:
    ...
```

### 9.3 `get_statistics_summary()`

全体集計の4項目を取得し、`ReadingStatisticsSummary`として返す。

データがない場合はすべて0を返す。

複数のSQLに分けず、可能な範囲で一回の問い合わせにまとめる。ただし可読性とテスト容易性を損なう複雑なSQLにはしない。

### 9.4 `get_completed_years()`

読了記録が存在する年を新しい順で返す。

読了記録がない場合は空のリストを返す。

### 9.5 `get_monthly_completed_counts()`

指定年の記録が存在する月と件数を辞書で返す。

例：

```python
{
    1: 2,
    3: 1,
    12: 4,
}
```

記録がない月は辞書へ含めない。指定年に読了記録がない場合は空の辞書を返す。

### 9.6 接続と例外

既存のCRUDメソッドと同様に、`create_connection()`で接続し、`finally`で閉じる。

SQLite例外はRepositoryで握りつぶさず、呼び出し元へ伝播する。

SQLの年条件にはプレースホルダーを使用する。

### 9.7 インデックス

Version 1.9では新しいインデックスを追加しない。

理由は次のとおりである。

* 個人利用規模を前提としている。
* 読書履歴の件数は書籍一覧より限定的である。
* 現時点では性能上の問題を確認していない。
* インデックス追加にはスキーマVersion更新とマイグレーションが必要になる。

実測で問題が確認された場合に`completed_on`のインデックスを検討する。

---

## 10. Service設計

### 10.1 配置場所

既存ファイルへ集計処理を追加する。

```text
src/book_manager/services/reading_history_service.py
```

### 10.2 公開メソッド

```python
def get_statistics_summary(
    self,
) -> ReadingStatisticsSummary:
    ...

def get_completed_years(
    self,
) -> list[int]:
    ...

def get_monthly_reading_counts(
    self,
    year: int,
) -> list[MonthlyReadingCount]:
    ...
```

### 10.3 全体集計

`get_statistics_summary()`はRepositoryから取得した集計値を返す。

各値が0以上の整数であることを前提とし、Modelの型によってGUIへ項目の意味を明確に伝える。

### 10.4 対象年一覧

`get_completed_years()`はRepositoryが返す年一覧を新しい順でGUIへ渡す。

不正な年が含まれている場合は`ValueError`とする。ただし通常は既存の入力検証とデータベース制約により発生しない。

### 10.5 月別集計

`get_monthly_reading_counts()`は年を検証し、Repositoryの辞書を1月から12月までのModelへ変換する。

例：

```python
[
    MonthlyReadingCount(
        year=2026,
        month=1,
        completed_count=2,
    ),
    MonthlyReadingCount(
        year=2026,
        month=2,
        completed_count=0,
    ),
    # 3月から11月を省略
    MonthlyReadingCount(
        year=2026,
        month=12,
        completed_count=4,
    ),
]
```

返却リストは常に1月から12月までの12件とする。

### 10.6 年の検証

対象年は`int`とし、次の範囲だけを許可する。

```text
1 <= year <= 9999
```

`bool`は`int`のサブクラスであるため、対象年として拒否する。

違反時は次の`ValueError`とする。

```text
集計対象年は1から9999までの整数で指定してください。
```

対象年に記録がないことはエラーにせず、12か月すべて0件として返す。

---

## 11. GUI設計

### 11.1 起動方法

メイン画面の操作ボタン領域へ次のボタンを追加する。

```text
読書集計
```

書籍の選択状態にかかわらず開けるボタンとする。

`読書履歴`ボタンの右側、`終了`ボタンの左側へ配置する。

ボタン追加後は余白列と終了ボタンの列番号を調整し、既存ボタンが最小ウィンドウ幅で操作できることを確認する。

### 11.2 ダイアログ

集計画面は`tk.Toplevel`を使用する。

```text
タイトル：読書集計
初期サイズ：900x650
最小サイズ：760x540
```

メイン画面に対するモーダルダイアログとする。

```python
dialog.transient(self._root)
dialog.grab_set()
```

集計画面を複数同時に開かない。

### 11.3 画面構成

```text
┌──────────────────────────────────────────────┐
│ 読書集計                                     │
├──────────────────────────────────────────────┤
│ 履歴総数    履歴のある書籍    読了記録    再読書籍 │
│   12回          8冊             10回        3冊 │
├──────────────────────────────────────────────┤
│ 対象年 [2026 ▼]                              │
├──────────────────────────────────────────────┤
│                                              │
│             月別読了数 棒グラフ              │
│                                              │
├──────────────────────────────────────────────┤
│ 1月 2件  2月 0件  ...  12月 1件              │
├──────────────────────────────────────────────┤
│                                      [閉じる]│
└──────────────────────────────────────────────┘
```

### 11.4 全体集計表示

次の4項目を上部へ表示する。

| 表示名 | 値 | 単位 |
|---|---:|---|
| 履歴総数 | `total_history_count` | 回 |
| 履歴のある書籍 | `books_with_history_count` | 冊 |
| 読了記録 | `completed_history_count` | 回 |
| 再読書籍 | `reread_book_count` | 冊 |

0の場合も`0回`または`0冊`と明示する。

### 11.5 対象年

対象年は`ttk.Combobox`で表示し、`state="readonly"`とする。

読了記録が存在する年を新しい順で設定し、初期表示は最新年とする。

対象年変更時に月別数値と棒グラフを再描画する。

読了記録がない場合は値を空にし、Comboboxを`disabled`とする。

### 11.6 月別数値

1月から12月までを暦順に表示する。

各月は次の形式とする。

```text
1月 2件
2月 0件
```

画面幅に応じて2行または複数列に配置してよいが、月順を維持する。

### 11.7 棒グラフ

棒グラフは`tk.Canvas`へ描画する。

#### 描画規則

* 横軸は1月から12月とする。
* 各月の棒を同じ幅で描画する。
* 棒の高さは対象年の最大月件数に対する比率で求める。
* 最大件数が0の場合はすべて高さ0とする。
* 棒の下に月を表示する。
* 棒の上または内側へ件数を表示する。
* 0件の月も月ラベルと`0`を表示する。
* 背景色と文字色は既存Tkinterテーマで判読できる色とする。
* Canvasの幅または高さが小さい場合も負の座標を生成しない。

棒の高さは概ね次で求める。

```python
bar_height = (
    drawable_height * completed_count / maximum_count
    if maximum_count > 0
    else 0
)
```

Canvasの`<Configure>`イベントで、現在のサイズに合わせて再描画する。

### 11.8 空状態

読書履歴がない場合は全体集計をすべて0で表示する。

読了記録がない場合は、グラフ領域へ次を表示する。

```text
読了記録がありません。
```

読書履歴は存在するが読了日がない場合も同じ表示とする。

### 11.9 エラー処理

集計処理で予期しない例外が発生した場合は、次のタイトルでエラーダイアログを表示する。

```text
読書集計エラー
```

本文は次のとおりとする。

```text
読書集計を表示できませんでした。
```

例外詳細は利用者向けメッセージへ直接表示しない。

---

## 12. GUI内部メソッド

`BookManagerApplication`へ、概ね次の責務を持つメソッドを追加する。

```python
def _on_show_reading_statistics(self) -> None:
    """読書集計画面を開く。"""

def _open_reading_statistics_dialog(self) -> None:
    """読書集計ダイアログを構築する。"""

def _load_reading_statistics(self) -> None:
    """全体集計と対象年を読み込む。"""

def _on_reading_statistics_year_changed(
    self,
    event: tk.Event[tk.Misc] | None = None,
) -> None:
    """対象年に応じて月別集計を更新する。"""

def _draw_monthly_reading_chart(
    self,
    monthly_counts: list[MonthlyReadingCount],
) -> None:
    """月別読了数をCanvasへ描画する。"""
```

実装時に既存GUIの命名やテスト容易性に合わせて、補助メソッドへ分割してよい。

---

## 13. データベースへの影響

Version 1.9ではテーブル、カラム、制約およびインデックスを変更しない。

```text
SCHEMA_VERSION = 7
```

を維持する。

マイグレーションは追加しない。

集計画面は`SELECT`だけを実行し、データベースを書き換えない。

---

## 14. 既存機能への影響

### 14.1 読書履歴管理

既存の登録・取得・変更・削除メソッドは変更しない。

集計値はダイアログを開くたびに取得し、最新の読書履歴を反映する。

### 14.2 読書状態・読了年月

既存の`reading_status`と`completion_month`は集計へ使用せず、変更もしない。

### 14.3 CSV

既存のCSV形式は変更しない。

読書履歴と集計結果はCSVへ追加しない。

### 14.4 バックアップ・復元

データベース構造を変更しないため、Version 1.8で確認した読書履歴のバックアップ・復元仕様を維持する。

### 14.5 書籍一覧

書籍一覧の列、検索、並べ替えおよび4行表示を変更しない。

操作ボタン追加によって既存ボタンの表示が崩れないことをWindows実環境で確認する。

---

## 15. テスト方針

### 15.1 Modelテスト

```text
tests/models/test_reading_statistics.py
```

少なくとも次を確認する。

* 全体集計Modelを生成できる。
* 月別集計Modelを生成できる。
* `frozen=True`により値を変更できない。
* 値比較ができる。

### 15.2 Repositoryテスト

既存ファイルへ追加する。

```text
tests/repositories/test_reading_history_repository.py
```

少なくとも次を確認する。

* データがない場合に全体集計がすべて0になる。
* メモだけの履歴も履歴総数へ含まれる。
* 履歴のある書籍を重複なく数える。
* 読了日がある履歴だけを読了記録として数える。
* 二件以上の履歴を持つ書籍だけを再読書籍として数える。
* 対象年を新しい順で重複なく取得する。
* 読了日がない履歴を対象年へ含めない。
* 指定年の月別件数を取得する。
* 同じ月の複数履歴を正しく数える。
* 年境界の記録を正しく分離する。
* SQLインジェクションにつながる文字列連結を行わない。

### 15.3 Serviceテスト

既存ファイルへ追加する。

```text
tests/services/test_reading_history_service.py
```

少なくとも次を確認する。

* 全体集計をRepositoryから取得する。
* 対象年を新しい順で取得する。
* 月別集計を1月から12月までの12件で返す。
* 記録がない月を0件で補完する。
* 記録がない年を12か月すべて0件で返す。
* 1年と9999年を許可する。
* 0年、10000年、文字列および`bool`を拒否する。
* Repositoryへ検証済みの年を渡す。

### 15.4 GUIテスト

```text
tests/gui/test_reading_statistics.py
```

既存の`tests/gui/test_reading_history_gui.py`と異なるファイル名にし、pytestのモジュール名衝突を防ぐ。

少なくとも次を確認する。

* 読書集計ボタンから画面を開く。
* 書籍未選択でも画面を開ける。
* 4種類の全体集計値を表示する。
* 最新年を初期選択する。
* 対象年変更時に月別集計を再取得する。
* 1月から12月までの数値を表示する。
* 0件の月を表示する。
* Canvasへ12か月分を描画する。
* Canvasサイズ変更時に再描画する。
* 読了記録がない場合に空状態を表示する。
* 予期しない例外でエラーダイアログを表示する。
* 閉じるボタンでダイアログを閉じる。

### 15.5 回帰テスト

全pytestを実行し、次を含む既存機能に回帰がないことを確認する。

* 書籍の登録・変更・削除
* 検索・絞り込み・並べ替え
* タグ管理
* 読書履歴管理
* CSVエクスポート・インポート
* バックアップ・復元
* 表紙画像表示

---

## 16. focused pytest

Modelテスト：

```powershell
pytest .\tests\models\test_reading_statistics.py -q
```

Repositoryテスト：

```powershell
pytest .\tests\repositories\test_reading_history_repository.py -q
```

Serviceテスト：

```powershell
pytest .\tests\services\test_reading_history_service.py -q
```

GUIテスト：

```powershell
pytest .\tests\gui\test_reading_statistics.py -q
```

最終確認：

```powershell
pytest -q
```

---

## 17. 変更対象ファイル

### 17.1 新規作成

```text
src/book_manager/models/reading_statistics.py
tests/models/test_reading_statistics.py
tests/gui/test_reading_statistics.py
docs/reading_statistics_design.md
```

### 17.2 変更

```text
src/book_manager/repositories/reading_history_repository.py
src/book_manager/services/reading_history_service.py
src/book_manager/gui/book_manager_application.py
tests/repositories/test_reading_history_repository.py
tests/services/test_reading_history_service.py
```

必要に応じて、実装完了時に次の文書を更新する。

```text
README.md
CHANGELOG.md
docs/book_manager_roadmap.md
docs/documentation_guide.md
docs/reading_history_design.md
```

---

## 18. 実装順序

1. 本設計書をレビューし、集計定義を確定する。
2. `ReadingStatisticsSummary`と`MonthlyReadingCount`を追加する。
3. Modelテストを追加する。
4. Repositoryへ全体集計、対象年、月別集計を追加する。
5. Repositoryのfocused pytestを実行する。
6. Serviceへ年検証と12か月補完を追加する。
7. Serviceのfocused pytestを実行する。
8. GUIへ読書集計ボタンと専用ダイアログを追加する。
9. 全体集計、対象年、月別数値および棒グラフを表示する。
10. GUIのfocused pytestを実行する。
11. Windows実環境で集計値とグラフを確認する。
12. 全pytestで回帰確認する。
13. 設計書と実装の差異を確認する。
14. README、CHANGELOG、ロードマップおよびドキュメントガイドを更新する。
15. Version 1.9のリリースレビューを行う。

---

## 19. Windows実環境での確認項目

1. 書籍を選択していなくても読書集計画面を開ける。
2. 履歴総数が実データと一致する。
3. 履歴のある書籍数が実データと一致する。
4. 読了記録数が実データと一致する。
5. 再読書籍数が実データと一致する。
6. 最新年が初期選択される。
7. 対象年を変更すると月別数値が更新される。
8. 対象年を変更すると棒グラフが更新される。
9. 0件の月も表示される。
10. グラフの棒と件数を判読できる。
11. 集計画面をサイズ変更しても主要情報を確認できる。
12. 集計画面を閉じて再度開ける。
13. 履歴を追加・変更・削除した後、再度開くと最新値になる。
14. 集計画面を開いても書籍情報と読書履歴が変更されない。
15. 最小ウィンドウサイズで既存の操作ボタンを使用できる。

空状態は、一時データベースまたは読了日のない履歴だけの状態でも確認する。

---

## 20. 完了条件

Version 1.9の読書記録集計・可視化機能は、少なくとも次を満たした時点で完成とする。

* [ ] 読書履歴総数を確認できる。
* [ ] 読書履歴を持つ書籍数を確認できる。
* [ ] 読了記録数を確認できる。
* [ ] 再読書籍数を確認できる。
* [ ] 読了記録が存在する年を新しい順で取得できる。
* [ ] 選択した年の月別読了数を確認できる。
* [ ] 月別集計が常に1月から12月まで表示される。
* [ ] 月別読了数をCanvasの棒グラフで確認できる。
* [ ] 読書履歴がない場合も安全に表示できる。
* [ ] 読了記録がない場合も安全に表示できる。
* [ ] 集計画面が書籍情報と読書履歴を変更しない。
* [ ] データベースのスキーマVersion 7を維持できる。
* [ ] 関連するfocused pytestがすべて成功する。
* [ ] 全pytestが成功する。
* [ ] Windows実環境で主要な集計値とグラフを確認する。
* [ ] 既存機能に回帰がない。

---

## 21. 設計上の決定事項

Version 1.9では、次を正式な設計判断とする。

* 集計元は`reading_histories`とする。
* 一つの履歴を一回分の読書記録として数える。
* 再読書籍は履歴を二件以上持つ書籍と定義する。
* 年別・月別読了数は`completed_on`を基準とする。
* 読了日がない履歴は読了数へ含めない。
* 0件の月はServiceで補完する。
* 月別集計は常に1月から12月までの12件を返す。
* 集計結果専用の不変Modelを追加する。
* 集計SQLは`ReadingHistoryRepository`へ追加する。
* 集計結果の整形と年の検証は`ReadingHistoryService`へ追加する。
* 集計画面は読み取り専用とする。
* グラフはTkinterの`Canvas`で描画する。
* グラフ用の外部ライブラリは追加しない。
* スキーマVersionは7を維持する。
* 既存CSV形式は変更しない。

---

**Version 1.9 読書記録集計・可視化方針：蓄積した読書履歴を安全に集計し、日々の読書を分かりやすく振り返れる形で表示する。**
