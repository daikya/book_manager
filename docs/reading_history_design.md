# 読書履歴管理機能 設計書

## 1. 目的

本設計書は、book_manager Version 1.8で追加する読書履歴管理機能の設計を定義する。

Version 1.3では、書籍の現在状態を表す読書ステータスと、過去に読了した年月を表す読了年月を追加した。

Version 1.8では、一冊の書籍に対して一回目の読書と再読を含む複数回の記録を残せるようにする。

読書開始日、読了日および読書メモを一回ごとの履歴として管理し、過去の記録を失わずに時系列で確認できることを目的とする。

---

## 2. 背景

現在の`reading_status`は、書籍の現在状態を表す。

```text
未設定
未読
読書中
読了
```

現在の`completion_month`は、一つの読了年月を`YYYY-MM`形式で保持する。

この構成では、次の情報を同時に保持できない。

* 一回目に読み始めた日
* 一回目に読み終えた日
* 再読を始めた日
* 再読を終えた日
* 読書回ごとのメモ

Version 1.8では、`book_items`へ履歴用カラムを繰り返し追加せず、専用テーブルによる一対多関係で管理する。

---

## 3. 対象範囲

Version 1.8では、次の機能を実装対象とする。

* 一冊の書籍への複数読書履歴の登録
* 読書開始日の記録
* 読了日の記録
* 読書回ごとのメモ
* 読書履歴の変更
* 読書履歴の削除
* 書籍ごとの読書履歴一覧
* 読書履歴の新しい順による表示
* 既存データを維持したデータベース移行
* 書籍削除時の読書履歴削除
* 読書履歴に関する自動テスト
* Windows実環境でのGUI確認

---

## 4. 対象外

Version 1.8では、次の機能を実装しない。

* 読書時間を計測するタイマー
* 読書中ページ数
* 読書進捗率
* 年間読書目標
* カレンダー表示
* 読書冊数・読書時間の集計とグラフ
* 読書履歴を条件とする検索・並べ替え
* 読書履歴専用CSVのエクスポート・インポート
* 既存の書籍CSVへ複数履歴を埋め込む処理
* 外部サービスとの同期
* 複数書籍への一括登録
* 読書履歴の自動生成

必要性が確認できた機能は、Version 1.9以降の候補とする。

---

## 5. 用語

| 用語 | 意味 |
|---|---|
| 読書履歴 | 一冊の書籍を一回読んだ記録 |
| 読書開始日 | その回の読書を開始した日 |
| 読了日 | その回の読書を終了した日 |
| 読書メモ | その回の読書に関する任意の記録 |
| 現在の読書状態 | `book_items.reading_status`が表す現在状態 |
| 読了年月 | `book_items.completion_month`が表す既存の年月情報 |
| 再読 | 同じ書籍に二件目以降の読書履歴を登録すること |

---

## 6. 基本方針

読書履歴管理機能は、次の方針で実装する。

* 一冊の書籍へ複数の読書履歴を登録できる。
* 一回目の読書と再読を同じモデルで扱う。
* 書籍と読書履歴は一対多関係とする。
* 読書履歴は`book_items`とは別テーブルへ保存する。
* 読書開始日と読了日は完全な日付として保存する。
* 日付はISO 8601に沿った`YYYY-MM-DD`形式とする。
* 読書開始日と読了日はそれぞれ未設定を許可する。
* 読書開始日と読了日の両方がある場合、開始日は読了日以前とする。
* 読書メモは任意入力とする。
* 日付とメモがすべて未設定の履歴は登録しない。
* 読書履歴は新しい記録から表示する。
* 入力値の正規化と検証はService層で行う。
* Repositoryは検証済みのモデルを永続化する。
* GUIはRepositoryを直接呼び出さない。
* 既存の読書状態・読了年月を自動変更しない。
* 既存書籍から読書履歴を自動生成しない。

---

## 7. 既存の読書情報との関係

### 7.1 役割の分離

既存項目と読書履歴は、次のように役割を分ける。

| 項目 | 役割 |
|---|---|
| `reading_status` | 書籍の現在の読書状態 |
| `completion_month` | 従来から利用している代表的な読了年月 |
| `reading_histories` | 一回ごとの読書開始日・読了日・メモ |

例えば、次の状態を正常なデータとして扱う。

```text
読書状態：読書中
読了年月：2025-05
読書履歴：2025-05-01 ～ 2025-05-20
読書履歴：2026-09-01 ～ 未設定
```

これは、2025年5月に一度読了し、2026年9月から再読中であることを表す。

### 7.2 自動連携を行わない

Version 1.8では、読書履歴を登録・変更・削除しても、次の項目を自動変更しない。

* `reading_status`
* `completion_month`

読書状態や読了年月を編集しても、読書履歴を自動登録・変更・削除しない。

理由は次のとおりである。

* 読書状態は現在状態、履歴は過去を含む一回ごとの記録であり役割が異なる。
* `completion_month`は年月単位、`completed_on`は日単位で精度が異なる。
* 再読中でも過去の読了年月を保持する既存仕様がある。
* 自動連携による意図しないデータ変更を防止できる。
* 既存の読書ステータス管理設計との整合性を維持できる。

GUIでは、読書履歴画面に次の説明を表示する。

```text
読書履歴を変更しても、書籍の読書状態と読了年月は自動変更されません。
```

### 7.3 既存データから履歴を生成しない

Version 6からVersion 7へのマイグレーションでは、既存書籍の`completion_month`や`reading_status`から読書履歴を生成しない。

例えば`completion_month = "2025-05"`から、読了日を次のように推測しない。

```text
2025-05-01
2025-05-31
```

実際の日付を判断できないため、推測した履歴を作成すると不正確なデータになる。

移行後の既存書籍は読書履歴0件として扱い、利用者が必要な履歴だけを明示的に登録する。

---

## 8. 日付仕様

### 8.1 保存形式

読書開始日と読了日は、次の形式で保存する。

```text
YYYY-MM-DD
```

例：

```text
2026-09-07
```

SQLiteでは`TEXT`、Pythonでは`str | None`として扱う。

時刻とタイムゾーンは保存しない。

### 8.2 未設定

未設定はSQLiteで`NULL`、Pythonで`None`、GUIで空文字として扱う。

空文字をデータベースへ保存しない。

### 8.3 正規化

Serviceは入力値の前後空白を除去する。

正規化後に空文字となる場合は`None`へ変換する。

全角数字、スラッシュ区切り、年月だけの入力は自動変換しない。

### 8.4 形式と実在日の検証

次を満たす日付だけを許可する。

* 長さが10文字である。
* 5文字目と8文字目が`-`である。
* 年月日が半角数字である。
* 年が0001から9999である。
* 実在する暦日である。

次の値はエラーとする。

```text
2026/09/07
2026-9-7
２０２６-０９-０７
2026-02-30
0000-01-01
```

検証にはPython標準ライブラリの`datetime.date.fromisoformat()`を利用し、その前に厳密な文字列形式を確認する。

### 8.5 日付の前後関係

読書開始日と読了日の両方が設定されている場合、次を満たす必要がある。

```text
started_on <= completed_on
```

同じ日に読み始めて読み終えた履歴は許可する。

違反時のメッセージは次のとおりとする。

```text
読書開始日は読了日以前の日付を入力してください。
```

---

## 9. 読書メモ仕様

読書メモはPythonの`str | None`として扱う。

Serviceは前後の空白を除去し、正規化後に空文字となる場合は`None`へ変換する。

Version 1.8では文字数上限を設けない。SQLiteの`TEXT`として保存する。

改行を許可する。

書籍本体の`notes`とは別の情報として扱う。

```text
book_items.notes
→ 書籍全体に関する備考

reading_histories.notes
→ 一回の読書に関するメモ
```

日付と読書メモがすべて未設定の場合は、次の`ValueError`とする。

```text
読書開始日、読了日、読書メモのいずれかを入力してください。
```

---

## 10. Model

### 10.1 配置場所

```text
src/book_manager/models/reading_history.py
```

### 10.2 クラス

```python
from dataclasses import dataclass


@dataclass(slots=True)
class ReadingHistory:
    """一回分の読書履歴を表すデータモデル。"""

    book_item_id: int
    id: int | None = None
    started_on: str | None = None
    completed_on: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
```

### 10.3 Modelの責務

`ReadingHistory`はデータ保持だけを担当する。

次の処理は行わない。

* 日付形式の検証
* 日付の前後関係の検証
* 入力値の正規化
* SQLiteへの接続
* GUI処理
* 現在日時の生成

`BookItem`へ`reading_histories`属性は追加しない。

理由は、書籍一覧・検索・CSVなど、履歴を必要としない通常処理で全履歴を読み込むことを避けるためである。

---

## 11. Validator

### 11.1 配置場所

```text
src/book_manager/validators/reading_history_validator.py
```

### 11.2 公開関数

```python
def validate_reading_date(
    value: str,
    *,
    field_name: str,
) -> None:
    ...

def validate_reading_history_dates(
    started_on: str | None,
    completed_on: str | None,
) -> None:
    ...
```

`validate_reading_date()`は、`field_name`を利用して次の形式のメッセージを返す。

```text
読書開始日はYYYY-MM-DD形式で入力してください。
読書開始日に実在する日付を入力してください。
読了日はYYYY-MM-DD形式で入力してください。
読了日に実在する日付を入力してください。
```

`validate_reading_history_dates()`は、設定されている各日付を検証した後、前後関係を検証する。

未設定値の`None`は許可する。

### 11.3 テスト

```text
tests/validators/test_reading_history_validator.py
```

少なくとも次を確認する。

* 正常な開始日を許可する。
* 正常な読了日を許可する。
* 閏年の2月29日を許可する。
* 不正な形式を拒否する。
* 全角数字を拒否する。
* 存在しない日付を拒否する。
* 0000年を拒否する。
* 開始日と読了日が同じ日であることを許可する。
* 開始日が読了日より後の場合に拒否する。
* 片方だけが設定されている場合に許可する。

---

## 12. データベース

### 12.1 スキーマVersion

現在のSQLiteスキーマVersionは6である。

読書履歴追加後は次の値とする。

```python
SCHEMA_VERSION = 7
```

### 12.2 テーブル名

```text
reading_histories
```

既存の`book_items`、`tags`および`book_item_tags`は変更しない。

### 12.3 カラム定義

| カラム名 | SQLite型 | NULL | 説明 |
|---|---|---|---|
| `id` | INTEGER | 不可 | 読書履歴ID。自動採番 |
| `book_item_id` | INTEGER | 不可 | 対象書籍ID |
| `started_on` | TEXT | 可 | 読書開始日。`YYYY-MM-DD` |
| `completed_on` | TEXT | 可 | 読了日。`YYYY-MM-DD` |
| `notes` | TEXT | 可 | 読書メモ |
| `created_at` | TEXT | 不可 | 登録日時。`YYYY-MM-DD HH:MM:SS` |
| `updated_at` | TEXT | 不可 | 更新日時。`YYYY-MM-DD HH:MM:SS` |

### 12.4 CREATE TABLE

```sql
CREATE TABLE IF NOT EXISTS reading_histories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_item_id INTEGER NOT NULL,
    started_on TEXT,
    completed_on TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (book_item_id)
        REFERENCES book_items (id)
        ON DELETE CASCADE,
    CHECK (
        started_on IS NOT NULL
        OR completed_on IS NOT NULL
        OR notes IS NOT NULL
    ),
    CHECK (
        started_on IS NULL
        OR completed_on IS NULL
        OR started_on <= completed_on
    )
)
```

SQLiteのCHECK制約は、空履歴と明らかな日付逆転を防ぐ補助として利用する。

日付の厳密な形式と実在日はService層で検証する。

### 12.5 インデックス

書籍IDごとの履歴取得に使用するため、次のインデックスを追加する。

```sql
CREATE INDEX IF NOT EXISTS idx_reading_histories_book_item_id
ON reading_histories (book_item_id)
```

### 12.6 外部キー

`reading_histories.book_item_id`は`book_items.id`を参照する。

```text
book_items 1 ─── 0..N reading_histories
```

`ON DELETE CASCADE`により、書籍削除時に関連する読書履歴を削除する。

すべてのSQLite接続で`PRAGMA foreign_keys = ON`を有効にする既存仕様を利用する。

---

## 13. マイグレーション

### 13.1 Version 6から7への移行

`MIGRATE_VERSION_6_TO_7`を追加する。

```python
MIGRATE_VERSION_6_TO_7 = (
    CREATE_READING_HISTORIES_TABLE,
    CREATE_READING_HISTORIES_BOOK_ITEM_ID_INDEX,
)
```

### 13.2 移行内容

Version 6のデータベースに対して、次だけを実行する。

1. `reading_histories`テーブルを作成する。
2. `book_item_id`インデックスを作成する。
3. `PRAGMA user_version`を7へ更新する。

既存テーブルの再作成や既存レコードの更新は行わない。

### 13.3 過去Versionからの連続移行

`initialize_database()`は、各Versionから7まで順番に移行できるようにする。

```text
Version 1 → 2 → 3 → 4 → 5 → 6 → 7
Version 2 → 3 → 4 → 5 → 6 → 7
Version 3 → 4 → 5 → 6 → 7
Version 4 → 5 → 6 → 7
Version 5 → 6 → 7
Version 6 → 7
```

### 13.4 マイグレーションテスト

少なくとも次を確認する。

* 新規DBへ`reading_histories`が作成される。
* 新規DBへインデックスが作成される。
* Version 6から7へ移行できる。
* Version 1から7まで連続移行できる。
* 書籍情報が保持される。
* 読書状態・読了年月・お気に入り・評価・タグが保持される。
* 既存書籍に読書履歴が自動生成されない。
* 移行を複数回実行しても結果が変わらない。
* Version 7より新しいDBを拒否する。
* 書籍削除時に関連履歴が削除される。

---

## 14. ReadingHistoryRepository

### 14.1 配置場所

```text
src/book_manager/repositories/reading_history_repository.py
```

テストは次に配置する。

```text
tests/repositories/test_reading_history_repository.py
```

### 14.2 Repositoryを分離する理由

`BookRepository`は書籍情報とタグ関連を担当している。

読書履歴は独立したライフサイクルを持ち、書籍一覧取得時に常時読み込む必要がないため、`ReadingHistoryRepository`へ分離する。

これにより、`BookRepository`の肥大化を防ぎ、履歴機能を独立してテストできる。

### 14.3 コンストラクター

```python
class ReadingHistoryRepository:
    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        ...
```

既存Repositoryと同様に、データベース接続はメソッドごとに作成し、確実に閉じる。

### 14.4 公開メソッド

```python
def add(
    self,
    reading_history: ReadingHistory,
) -> ReadingHistory:
    ...

def get_by_id(
    self,
    reading_history_id: int,
) -> ReadingHistory | None:
    ...

def get_by_book_id(
    self,
    book_item_id: int,
) -> list[ReadingHistory]:
    ...

def update(
    self,
    reading_history: ReadingHistory,
) -> bool:
    ...

def delete(
    self,
    reading_history_id: int,
) -> bool:
    ...
```

### 14.5 登録

`add()`は、次をINSERTする。

```text
book_item_id
started_on
completed_on
notes
created_at
updated_at
```

SQLiteが採番した`id`を設定した新しい`ReadingHistory`を返す。

存在しない`book_item_id`の場合は外部キー制約により登録を拒否する。

### 14.6 書籍ごとの取得

`get_by_book_id()`は、指定書籍の履歴だけを返す。

表示順は次のとおりとする。

```sql
ORDER BY
    COALESCE(completed_on, started_on, substr(created_at, 1, 10)) DESC,
    id DESC
```

読了日がある履歴は読了日、読了日がない履歴は開始日、両方ない履歴は登録日を基準にする。

同じ基準日の場合は、新しく登録した履歴を先に表示する。

### 14.7 更新

`update()`は、次を更新する。

```text
started_on
completed_on
notes
updated_at
```

`id`、`book_item_id`および`created_at`は変更しない。

存在しない履歴IDの場合は`False`を返す。

### 14.8 削除

`delete()`は、履歴IDに対応する一件を削除する。

存在しない履歴IDの場合は`False`を返す。

### 14.9 Repositoryテスト

少なくとも次を確認する。

* 履歴を登録できる。
* 未設定値を`NULL`として登録できる。
* 自動採番IDを返す。
* IDで取得できる。
* 存在しないIDでは`None`を返す。
* 書籍IDごとに複数履歴を取得できる。
* 別書籍の履歴を含めない。
* 履歴を新しい順に取得できる。
* 履歴を更新できる。
* IDと書籍IDと登録日時を更新しない。
* 存在しない履歴を更新すると`False`を返す。
* 履歴を削除できる。
* 存在しない履歴を削除すると`False`を返す。
* 存在しない書籍へ登録できない。
* 書籍削除時に関連履歴が削除される。
* SQLパラメーターを安全にバインドする。

---

## 15. ReadingHistoryService

### 15.1 配置場所

```text
src/book_manager/services/reading_history_service.py
```

テストは次に配置する。

```text
tests/services/test_reading_history_service.py
```

### 15.2 依存関係

```text
BookManagerApplication
↓
ReadingHistoryService
├── ReadingHistoryValidator
├── ReadingHistoryRepository
└── BookRepository
    ↓
    SQLite
```

`BookRepository`は対象書籍の存在確認に使用する。

### 15.3 コンストラクター

```python
class ReadingHistoryService:
    def __init__(
        self,
        repository: ReadingHistoryRepository,
        book_repository: BookRepository,
        now_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        ...
```

### 15.4 公開メソッド

```python
def add_history(
    self,
    *,
    book_item_id: int,
    started_on: str | None = None,
    completed_on: str | None = None,
    notes: str | None = None,
) -> ReadingHistory:
    ...

def get_history(
    self,
    reading_history_id: int,
) -> ReadingHistory | None:
    ...

def get_histories_for_book(
    self,
    book_item_id: int,
) -> list[ReadingHistory]:
    ...

def update_history(
    self,
    reading_history: ReadingHistory,
) -> bool:
    ...

def delete_history(
    self,
    reading_history_id: int,
) -> bool:
    ...
```

### 15.5 登録処理

`add_history()`は次の順序で処理する。

1. `book_item_id`に対応する書籍が存在することを確認する。
2. 日付とメモを正規化する。
3. 日付形式と前後関係を検証する。
4. 少なくとも一つの入力値があることを確認する。
5. 登録日時と更新日時を生成する。
6. `ReadingHistory`を生成する。
7. Repositoryへ登録を依頼する。

対象書籍が存在しない場合は、次の`ValueError`とする。

```text
対象の書籍が見つかりません。
```

### 15.6 取得処理

`get_histories_for_book()`は、対象書籍が存在しない場合に空リストを返さず`ValueError`とする。

書籍が存在し、履歴がない場合は空リストを返す。

これにより、「書籍が存在しない」と「履歴が0件」を区別する。

### 15.7 更新処理

`update_history()`では、更新対象の既存履歴を取得する。

存在しない場合は`False`を返す。

次の値は既存値を維持する。

```text
id
book_item_id
created_at
```

日付とメモを正規化・検証し、`updated_at`だけを現在日時へ更新する。

GUIから渡された`book_item_id`で履歴を別の書籍へ移動できないようにする。

### 15.8 削除処理

`delete_history()`はRepositoryへ削除を依頼し、成否を`bool`で返す。

読書状態と読了年月は変更しない。

### 15.9 日時形式

登録日時と更新日時は、既存`BookService`と同じ形式を使用する。

```text
YYYY-MM-DD HH:MM:SS
```

### 15.10 Serviceテスト

少なくとも次を確認する。

* 入力値の前後空白を除去する。
* 空文字を`None`へ変換する。
* 正常な履歴を登録できる。
* 開始日だけの履歴を登録できる。
* 読了日だけの履歴を登録できる。
* メモだけの履歴を登録できる。
* すべて未設定の履歴を拒否する。
* 不正な日付を拒否する。
* 開始日が読了日より後の場合に拒否する。
* 存在しない書籍への登録を拒否する。
* 書籍ごとの履歴を取得できる。
* 存在しない書籍の履歴取得を拒否する。
* 履歴を更新できる。
* 更新時にID・書籍ID・登録日時を維持する。
* 存在しない履歴の更新で`False`を返す。
* 履歴を削除できる。
* 読書状態と読了年月を変更しない。
* 現在日時を差し替えてテストできる。

---

## 16. GUI

### 16.1 Serviceの受け渡し

`BookManagerApplication`のコンストラクターへ`ReadingHistoryService`を追加する。

```python
def __init__(
    self,
    root: tk.Tk,
    service: BookService,
    csv_export_service: CsvExportService,
    csv_import_service: CsvImportService,
    backup_service: BackupService,
    reading_history_service: ReadingHistoryService,
) -> None:
    ...
```

アプリケーションのエントリーポイントで`ReadingHistoryRepository`と`ReadingHistoryService`を生成し、GUIへ渡す。

### 16.2 起動方法

メイン画面の操作ボタン領域へ、次のボタンを追加する。

```text
読書履歴
```

書籍一覧で書籍を選択していない場合は、次の警告を表示する。

```text
読書履歴を表示する書籍を選択してください。
```

### 16.3 読書履歴ダイアログ

選択中の書籍に対して、モーダルな`tk.Toplevel`を表示する。

タイトルは次のとおりとする。

```text
読書履歴
```

画面上部へ対象書籍名を表示する。

```text
対象書籍：書籍名
```

書籍名が長い場合も画面幅を過度に拡大しないよう、折り返しまたは省略表示を検討する。

### 16.4 入力項目

| 項目 | ウィジェット | 入力例 |
|---|---|---|
| 読書開始日 | `ttk.Entry` | `2026-09-01` |
| 読了日 | `ttk.Entry` | `2026-09-07` |
| 読書メモ | `tk.Text` | 再読で新しい発見があった。 |

日付欄の近くへ`YYYY-MM-DD`を表示する。

### 16.5 履歴一覧

`ttk.Treeview`へ次の列を表示する。

| 列 | 内容 |
|---|---|
| 開始日 | `started_on`。未設定は空欄 |
| 読了日 | `completed_on`。未設定は空欄 |
| 読書メモ | 改行を空白へ置換した先頭部分 |

Treeviewの`iid`には読書履歴IDの文字列表現を使用する。

一覧ではメモ全体を表示せず、履歴選択時に入力欄へ全文を復元する。

### 16.6 操作ボタン

読書履歴ダイアログへ次のボタンを配置する。

```text
新規登録
更新
削除
入力クリア
閉じる
```

### 16.7 新規登録

入力内容を`ReadingHistoryService.add_history()`へ渡す。

登録成功後は次を行う。

1. 履歴一覧を再読み込みする。
2. 入力欄をクリアする。
3. 新規入力状態へ戻す。
4. 完了メッセージを表示する。

### 16.8 履歴選択

Treeviewで履歴を選択した場合、IDで最新データを取得し、開始日・読了日・メモを入力欄へ表示する。

選択中の履歴IDをGUI内部へ保持する。

### 16.9 更新

履歴未選択時は警告する。

選択中の履歴へ入力内容を反映し、Serviceへ更新を依頼する。

更新成功後は一覧と入力欄を最新状態へ更新する。

### 16.10 削除

履歴未選択時は警告する。

削除前に次の確認を表示する。

```text
選択した読書履歴を削除しますか？
```

削除成功後は一覧を再読み込みし、入力欄と選択状態をクリアする。

### 16.11 エラー表示

`ValueError`のメッセージは利用者へそのまま表示する。

予期しない例外はトレースバックを記録し、次の一般的なメッセージを表示する。

```text
読書履歴を処理できませんでした。
```

### 16.12 ダイアログを開いている間の書籍削除

読書履歴ダイアログはモーダル表示とするため、ダイアログを開いている間はメイン画面から対象書籍を削除できない。

これにより、操作中に対象書籍がなくなる状態を防止する。

### 16.13 GUIテスト

```text
tests/gui/test_reading_history.py
```

少なくとも次を確認する。

* 書籍未選択時に警告する。
* 選択中の書籍IDをServiceへ渡す。
* 履歴一覧へ日付とメモ概要を表示する。
* 履歴0件でも正常に表示する。
* 履歴選択時に入力欄へ値を復元する。
* 新規登録時に入力値をServiceへ渡す。
* 登録後に一覧と入力欄を更新する。
* 履歴未選択時に更新しない。
* 更新時に選択中の履歴IDを使用する。
* 履歴未選択時に削除しない。
* 削除確認のキャンセル時に削除しない。
* 削除成功後に一覧と入力欄を更新する。
* `ValueError`をメッセージ表示する。
* 入力クリアで新規入力状態へ戻る。

---

## 17. バックアップ・復元

読書履歴は既存のSQLiteデータベースファイル内へ保存する。

SQLite Backup APIを利用する既存バックアップには、`reading_histories`テーブルも自動的に含まれる。

復元時は、既存のスキーマVersion検証とデータベース全体の置換により読書履歴も復元される。

個別のバックアップ処理は追加しない。

少なくとも、読書履歴を含むVersion 7データベースをバックアップ・復元できることをテストまたは実機で確認する。

---

## 18. CSVとの関係

既存CSVは一行につき一冊の書籍を表す。

一冊に複数存在する読書履歴を同じ行へ追加すると、区切り形式や改行の扱いが複雑になり、旧形式との互換性も分かりにくくなる。

そのため、Version 1.8では既存の15列CSV形式を変更しない。

既存の`completion_month`と`reading_status`は従来どおり入出力する。

読書履歴専用CSVが必要になった場合は、Version 1.9以降に別形式として設計する。

---

## 19. エラー処理

### 19.1 ValueError

次の入力・業務エラーは`ValueError`とする。

* 日付形式が不正である。
* 実在しない日付である。
* 読書開始日が読了日より後である。
* 日付とメモがすべて未設定である。
* 対象書籍が存在しない。

### 19.2 存在しない履歴

取得は`None`、更新と削除は`False`を返す。

GUIは対象が見つからないことを警告し、履歴一覧を再読み込みする。

### 19.3 SQLite例外

RepositoryはSQLite例外を不必要に握りつぶさない。

接続は`finally`で閉じ、更新処理は`with connection:`によるトランザクションで実行する。

---

## 20. セキュリティ・安全性

* SQL値はプレースホルダーでバインドする。
* GUI入力をSQL文字列へ直接連結しない。
* 読書メモはデータとして保存し、コードとして実行しない。
* 外部キー制約をすべての接続で有効にする。
* 削除前に確認ダイアログを表示する。
* マイグレーションでは既存書籍を更新しない。
* マイグレーション全体を一つのトランザクションで実行する。

---

## 21. 性能方針

Version 1.8では個人利用規模を前提とする。

履歴は選択中の一冊分だけを取得し、全書籍の履歴を起動時に読み込まない。

`book_item_id`へインデックスを作成し、書籍ごとの取得を効率化する。

履歴一覧にページングは追加しない。

大量履歴による性能問題が確認された場合は、Version 1.9以降でページングや取得件数制限を検討する。

---

## 22. 変更対象ファイル

主な新規ファイルは次のとおりである。

```text
src/book_manager/models/reading_history.py
src/book_manager/repositories/reading_history_repository.py
src/book_manager/services/reading_history_service.py
src/book_manager/validators/reading_history_validator.py
tests/models/test_reading_history.py
tests/repositories/test_reading_history_repository.py
tests/services/test_reading_history_service.py
tests/validators/test_reading_history_validator.py
tests/gui/test_reading_history.py
docs/reading_history_design.md
```

主な変更ファイルは次のとおりである。

```text
src/book_manager/database/schema.py
src/book_manager/database/initializer.py
src/book_manager/gui/book_manager_application.py
main.py
tests/database/test_initialization.py
```

実装完了後、次の文書を更新する。

```text
docs/database/database_design.md
docs/gui/gui_design.md
docs/documentation_guide.md
README.md
CHANGELOG.md
docs/book_manager_roadmap.md
```

既存の`BookItem`、`BookRepository`、`BookService`およびCSV Serviceは、原則として変更しない。

---

## 23. 実装順序

次の順序で実装する。

1. `reading_history_design.md`を確定する。
2. `ReadingHistory`モデルを追加する。
3. 読書履歴Validatorを追加する。
4. Model・Validatorテストを追加する。
5. `schema.py`へVersion 7のテーブルとインデックスを追加する。
6. `initializer.py`へVersion 6から7への移行を追加する。
7. データベース初期化・移行・外部キーテストを追加する。
8. `ReadingHistoryRepository`を追加する。
9. Repositoryテストを追加する。
10. `ReadingHistoryService`を追加する。
11. Serviceテストを追加する。
12. エントリーポイントでRepositoryとServiceを構成する。
13. GUIへ読書履歴ダイアログを追加する。
14. GUIテストを追加する。
15. 関連するfocused pytestを段階ごとに実行する。
16. 全pytestを実行する。
17. Windows実環境で主要操作を確認する。
18. 関連設計書と利用者向け文書を更新する。
19. Version 1.8のリリースレビューを行う。

---

## 24. focused pytest

実装段階ごとに、少なくとも次を実行する。

```powershell
pytest .\tests\models\test_reading_history.py .\tests\validators\test_reading_history_validator.py -q
```

```powershell
pytest .\tests\database\test_connection.py .\tests\database\test_initialization.py -q
```

```powershell
pytest .\tests\repositories\test_reading_history_repository.py -q
```

```powershell
pytest .\tests\services\test_reading_history_service.py -q
```

```powershell
pytest .\tests\gui\test_reading_history.py .\tests\gui\test_reading_status.py -q
```

最終確認では全テストを実行する。

```powershell
pytest -q
```

---

## 25. GUI実機確認

Windows実環境で、少なくとも次を確認する。

1. 書籍未選択時に読書履歴ボタンから警告が表示される。
2. 選択中の書籍について読書履歴画面を開ける。
3. 対象書籍名が正しく表示される。
4. 読書開始日だけの履歴を登録できる。
5. 読了日だけの履歴を登録できる。
6. 読書メモだけの履歴を登録できる。
7. 開始日・読了日・メモを持つ履歴を登録できる。
8. 一冊へ複数の履歴を登録できる。
9. 履歴が新しい順に表示される。
10. 履歴を選択すると入力欄へ内容が復元される。
11. 履歴を変更できる。
12. 履歴を削除できる。
13. 削除確認をキャンセルできる。
14. 不正な日付でエラーが表示される。
15. 実在しない日付でエラーが表示される。
16. 開始日が読了日より後の場合にエラーが表示される。
17. すべて空欄の履歴を登録できない。
18. 読書履歴の操作で読書状態と読了年月が変わらない。
19. アプリ再起動後も履歴が保持される。
20. 書籍削除時に関連履歴も削除される。
21. バックアップ・復元後も履歴が保持される。
22. 読書履歴がない既存書籍を従来どおり操作できる。
23. 既存の登録・更新・削除・検索・並べ替え・タグ操作が正常に動作する。
24. 最小ウィンドウサイズでも主要操作が可能である。

---

## 26. 完了条件

Version 1.8の読書履歴管理機能は、少なくとも次の条件を満たした時点で完成とする。

* [ ] 一冊へ複数の読書履歴を登録できる。
* [ ] 読書開始日・読了日・読書メモを記録できる。
* [ ] 読書履歴を変更・削除できる。
* [ ] 日付形式と実在日を検証できる。
* [ ] 読書開始日と読了日の前後関係を検証できる。
* [ ] 読書履歴を新しい順に取得・表示できる。
* [ ] 読書履歴がない書籍を従来どおり扱える。
* [ ] 読書状態・読了年月と読書履歴を独立して管理できる。
* [ ] 書籍削除時に関連履歴を安全に削除できる。
* [ ] 既存データを失わずにスキーマVersion 7へ移行できる。
* [ ] バックアップ・復元で読書履歴を保持できる。
* [ ] 関連するfocused pytestがすべて成功する。
* [ ] 全pytestが成功する。
* [ ] Windows実環境で主要操作を確認する。
* [ ] 既存機能に回帰がない。

---

## 27. 設計上の決定事項

Version 1.8では、次を正式な設計判断とする。

* 読書履歴は一回の読書につき一件とする。
* 一冊へ複数の読書履歴を登録できる。
* 書籍と読書履歴は一対多関係とする。
* テーブル名は`reading_histories`とする。
* `ReadingHistory`を`BookItem`とは別モデルとする。
* `ReadingHistoryRepository`と`ReadingHistoryService`を独立して追加する。
* 日付は`YYYY-MM-DD`形式のTEXTとして保存する。
* 日付とメモの少なくとも一つを必須とする。
* 読書開始日は読了日以前とする。
* 読書状態・読了年月と読書履歴は自動連携しない。
* 既存データから読書履歴を自動生成しない。
* 読書履歴は新しい記録から表示する。
* 書籍削除時は`ON DELETE CASCADE`で関連履歴を削除する。
* スキーマVersionを6から7へ更新する。
* 既存の15列CSV形式は変更しない。
* 履歴画面は選択中の一冊を対象とするモーダルダイアログとする。

---

**Version 1.8 読書履歴管理方針：現在状態と過去の記録を分離し、一冊ごとの読書と再読を正確かつ安全に蓄積する。**
