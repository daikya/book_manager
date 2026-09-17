# 一覧表示状態の保存・復元 設計書

## 1. 文書の目的

本書は、Book Manager Version 2.4で追加する「メイン画面の一覧表示状態の保存・復元」について、保存形式、責務分担、起動・終了時の処理、異常時の扱い、設定画面からの初期化方法、および試験方針を定義する。

Version 2.3で実装したメインウィンドウ状態の保存・復元とは独立した機能として扱い、一覧表示の調整内容だけを専用ファイルへ保存する。

## 2. 対象範囲

### 2.1 保存・復元する項目

- 書籍一覧の各列の幅
- 並び順に使用する列
- 昇順・降順

### 2.2 対象列

列幅の保存対象は、表紙列 `#0` と `BookManagerApplication.TREE_COLUMNS` に定義された全列とする。

| 列ID | 表示内容 | 初期幅 | 最小幅 | 配置 | 伸縮 | 並び替え |
|---|---|---:|---:|---|---|---|
| `#0` | 表紙 | 60 | 60 | 中央 | しない | 非対応 |
| `id` | ID | 60 | 50 | 中央 | しない | 対応 |
| `title` | 書籍名 | 250 | 160 | 左 | する | 対応 |
| `author` | 著者名 | 160 | 100 | 左 | する | 対応 |
| `publisher` | 出版社 | 140 | 100 | 左 | する | 対応 |
| `publication_format` | 形態 | 90 | 80 | 中央 | しない | 非対応 |
| `isbn` | ISBN | 130 | 110 | 左 | しない | 非対応 |
| `magazine_code` | 雑誌コード | 100 | 90 | 中央 | しない | 非対応 |
| `completion_month` | 読了年月 | 90 | 80 | 中央 | しない | 対応 |
| `reading_status` | 読書状態 | 80 | 70 | 中央 | しない | 対応 |
| `is_favorite` | お気に入り | 60 | 50 | 中央 | しない | 対応 |
| `rating` | 評価 | 100 | 90 | 中央 | しない | 対応 |
| `tags` | タグ | 180 | 120 | 左 | する | 非対応 |

列の `anchor`、`minwidth`、`stretch` は現行定義を維持し、保存対象にしない。保存するのは実際の `width` のみとする。

### 2.3 対象外

次の項目はVersion 2.4では保存しない。

- 検索条件
- 選択中の書籍
- スクロール位置
- 列の表示・非表示
- 列の並び順
- サブウィンドウの位置とサイズ
- テーマ、フォント、表示倍率
- 利用者データの保存先

検索条件を保存すると、次回起動時に条件が残り、登録済みの書籍が消えたように見える可能性がある。そのため、検索条件は明示的に対象外とする。

## 3. 設計方針

### 3.1 独立した状態として保存する

一覧表示状態は、ウィンドウ位置・サイズとは更新理由や復旧単位が異なる。したがって、既存の `window_state.json` には追加せず、`list_view_state.json` に保存する。

これにより、一覧表示状態だけを初期化でき、一方のファイル破損が他方の復元を妨げない。

### 3.2 起動と終了を妨げない

一覧表示状態は利便性のための補助情報であり、書籍データそのものではない。

- 読み込み失敗時は既定値で起動する
- 保存失敗時もアプリケーションを終了する
- 削除失敗時は設定画面へエラーを表示し、動作を継続する

### 3.3 現在の列定義を正とする

保存ファイルに存在する列だけを復元対象とするのではなく、アプリケーションが現在持つ列定義を正とする。

- 現在存在する列で、保存値も存在する場合は保存幅を適用する
- 現在存在する列で、保存値がない場合は既定幅を維持する
- 保存ファイルにだけ存在する未知の列は無視する

この方針により、将来の列追加・削除でも起動できる。

### 3.4 並び順は内部識別子で保存する

表示ラベルではなく、Serviceへ渡す内部識別子を保存する。日本語ラベル変更の影響を受けず、一覧取得処理と意味を一致させるためである。

| 画面表示 | 保存値 `sort_by` |
|---|---|
| 登録順 | `registered` |
| 書籍名 | `title` |
| 著者名 | `author` |
| 出版社 | `publisher` |
| 読了年月 | `completion_month` |
| 読書状態 | `reading_status` |
| お気に入り | `is_favorite` |
| 評価 | `rating` |

初期値は `registered`、降順とする。

## 4. 保存先

### 4.1 通常環境

```text
%LOCALAPPDATA%\book_manager\list_view_state.json
```

### 4.2 検証環境

`BOOK_MANAGER_HOME` が設定されている場合は、その直下へ保存する。

```text
%BOOK_MANAGER_HOME%\list_view_state.json
```

### 4.3 パス定義

`src/book_manager/config/paths.py` に次を追加する。

```python
LIST_VIEW_STATE_FILE_NAME = "list_view_state.json"
```

`ApplicationPaths` には次のプロパティを追加する。

```python
@property
def list_view_state_path(self) -> Path:
    return self.root_directory / LIST_VIEW_STATE_FILE_NAME
```

## 5. JSON形式

### 5.1 保存例

```json
{
  "schema_version": 1,
  "column_widths": {
    "#0": 60,
    "id": 60,
    "title": 250,
    "author": 160,
    "publisher": 140,
    "publication_format": 90,
    "isbn": 130,
    "magazine_code": 100,
    "completion_month": 90,
    "reading_status": 80,
    "is_favorite": 60,
    "rating": 100,
    "tags": 180
  },
  "sort_by": "registered",
  "descending": true
}
```

### 5.2 項目定義

| 項目 | 型 | 必須 | 内容 |
|---|---|---|---|
| `schema_version` | 整数 | 必須 | 保存形式のVersion。初版は `1` |
| `column_widths` | オブジェクト | 必須 | 列IDと幅の対応 |
| `sort_by` | 文字列 | 必須 | 並び替えの内部識別子 |
| `descending` | 真偽値 | 必須 | `true` は降順、`false` は昇順 |

### 5.3 文字コードと改行

- UTF-8（BOMなし）
- JSONはインデント2
- ファイル末尾に改行を付ける

## 6. Model設計

### 6.1 ファイル

```text
src/book_manager/models/list_view_state.py
```

### 6.2 クラス

```python
@dataclass(frozen=True, slots=True)
class ListViewState:
    schema_version: int
    column_widths: dict[str, int]
    sort_by: str
    descending: bool
```

外部から受け取った辞書の変更がModel内部へ波及しないよう、生成時に `column_widths` をコピーする。

### 6.3 定数

```python
CURRENT_SCHEMA_VERSION = 1

SUPPORTED_SORT_KEYS = (
    "registered",
    "title",
    "author",
    "publisher",
    "completion_month",
    "reading_status",
    "is_favorite",
    "rating",
)

MIN_STORED_COLUMN_WIDTH = 1
MAX_STORED_COLUMN_WIDTH = 4096
```

上限は、破損・手編集された極端な値によって一覧が操作不能になることを防ぐために設ける。

### 6.4 検証規則

- `schema_version` は整数であり、真偽値ではない
- `schema_version` は `CURRENT_SCHEMA_VERSION` と一致する
- `column_widths` は辞書である
- 列IDは空でない文字列である
- 列幅は整数であり、真偽値ではない
- 列幅は `1` 以上 `4096` 以下である
- `sort_by` は `SUPPORTED_SORT_KEYS` のいずれかである
- `descending` は真偽値である

列幅辞書は部分的でもよい。列追加前の保存ファイルを読み込めるようにするためである。未知の列IDもModelでは許容し、GUIで適用対象から除外する。

### 6.5 変換処理

次の責務をModelに持たせる。

- `from_dict()`：JSON由来の辞書を検証してModelへ変換する
- `to_dict()`：JSONへ保存できる辞書へ変換する
- `default()`：全列の既定値ではなく、既定の並び順と空の列幅辞書を持つ状態を返す

列の既定幅はGUIの列定義に属するため、Modelへ重複定義しない。

## 7. Store設計

### 7.1 ファイル

```text
src/book_manager/config/list_view_state_store.py
```

### 7.2 クラス

```python
class ListViewStateStore:
    def __init__(self, state_path: Path) -> None: ...
    def load(self) -> ListViewState | None: ...
    def save(self, state: ListViewState) -> None: ...
    def delete(self) -> None: ...
```

保存エラー用に専用例外を用意する。

```python
class ListViewStateStoreError(RuntimeError):
    pass
```

### 7.3 読み込み

`load()` は次の場合に `None` を返し、警告ログを残す。

- ファイルが存在しない
- ファイルを読み取れない
- JSONとして解析できない
- ルートがオブジェクトではない
- 必須項目がない
- 型または値が不正である
- 未対応の `schema_version` である

一覧表示状態を理由に起動を中断しないため、これらを呼び出し元へ例外として伝播しない。

### 7.4 保存

`save()` は既存の `WindowStateStore` と同じ原子的保存方式を使用する。

1. 親ディレクトリを作成する
2. 同じディレクトリへ一時ファイルを作成する
3. UTF-8、インデント2、末尾改行付きでJSONを書き込む
4. `flush()` と `os.fsync()` を実行する
5. `os.replace()` で本ファイルへ置き換える
6. 失敗時は一時ファイルを可能な範囲で削除する
7. 失敗内容を `ListViewStateStoreError` として通知する

同一ディレクトリ内で置換することで、別ドライブ間移動を避け、書き込み途中のJSONが本ファイルとして残る可能性を下げる。

### 7.5 削除

`delete()` は `missing_ok=True` 相当で動作し、ファイルがなくても成功とする。削除に失敗した場合は `ListViewStateStoreError` を送出する。

## 8. GUIへの組み込み

### 8.1 依存性注入

`BookManagerApplication.__init__()` に任意依存として追加する。

```python
list_view_state_store: ListViewStateStore | None = None
```

Storeが渡されない既存テストや限定利用では、保存・復元・初期化を行わず、現在の既定動作を維持する。

### 8.2 内部状態

```python
self._list_view_state_store = list_view_state_store
self._list_view_state_save_suppressed = False
```

初期化後に同じセッションの終了処理で直ちに再保存されないよう、抑止フラグを持つ。

### 8.3 起動時の処理順序

現在の起動処理へ、ウィジェット作成後かつ最初の一覧取得前に復元処理を挿入する。

```python
self._configure_root()
self._create_widgets()
self._restore_list_view_state()
self._refresh_tag_options()
self._load_all_books()
```

この順序には次の意味がある。

- 列幅を設定するには `Treeview` が作成済みである必要がある
- 並び順は最初の `_load_all_books()` より前に復元する必要がある
- 検索条件は復元しないため、起動時は従来どおり全件表示する

### 8.4 列幅の復元

復元対象の列IDは次の順で組み立てる。

```python
("#0", *self.TREE_COLUMNS)
```

各列について次の処理を行う。

1. 保存値がなければ何もしない
2. 現在の列定義から `minwidth` を取得する
3. 保存幅を `minwidth` 以上へ補正する
4. 安全上限 `4096` 以下へ補正する
5. `self._book_tree.column(column_id, width=restored_width)` を実行する

未知の列IDは処理対象として列挙されないため、自動的に無視される。`anchor`、`minwidth`、`stretch` は変更しない。

`stretch=True` の列はウィンドウサイズに応じてTk側で再調整される場合がある。保存値はレイアウト計算の基準幅として復元し、常に最終表示幅が1ピクセル単位で一致することまでは保証しない。

### 8.5 並び順の復元

内部識別子から画面表示へ変換する逆引き表を用意する。

```python
SORT_KEY_TYPE_MAP = {
    "registered": "登録順",
    "title": "書籍名",
    "author": "著者名",
    "publisher": "出版社",
    "completion_month": "読了年月",
    "reading_status": "読書状態",
    "is_favorite": "お気に入り",
    "rating": "評価",
}
```

復元時は次を設定する。

```python
self._sort_type_var.set(SORT_KEY_TYPE_MAP[state.sort_by])
self._sort_direction_var.set(
    "descending" if state.descending else "ascending"
)
```

変数設定時には `_on_sort_changed()` を直接呼ばない。直後の `_load_all_books()` が復元後の値を使って一度だけ一覧を取得する。

### 8.6 列見出しと並び順UIの同期

既存の次の操作は維持する。

- 並び順コンボボックス
- 昇順・降順ラジオボタン
- 対応列の見出しクリック
- 同じ見出しの再クリックによる昇順・降順の反転

すべての操作は既存の `_sort_type_var` と `_sort_direction_var` を更新するため、終了時はこの2変数から最新状態を取得できる。Version 2.4では見出しへの矢印表示は追加しない。

## 9. 終了時の保存

### 9.1 状態の採取

終了時にTreeviewへ問い合わせ、実際の表示幅を採取する。

```python
column_widths = {
    column_id: int(self._book_tree.column(column_id, "width"))
    for column_id in ("#0", *self.TREE_COLUMNS)
}
```

列幅変更イベントを個別に監視しない。終了時のTreeviewが最新状態を保持しているためである。

並び順は `_get_sort_settings()` の戻り値を利用する。

```python
sort_by, descending = self._get_sort_settings()
```

### 9.2 保存条件

次の場合は保存しない。

- `list_view_state_store` が渡されていない
- 設定画面から初期化され、`_list_view_state_save_suppressed` が `True`
- Treeviewがまだ利用可能な状態ではない

### 9.3 終了順序

```python
def _on_exit(self) -> None:
    self._save_list_view_state_on_exit()
    self._save_window_state_on_exit()
    self.root.destroy()
```

一覧表示状態とウィンドウ状態の保存処理は、それぞれのメソッド内で例外を捕捉する。一方の失敗によって他方の保存や `root.destroy()` を妨げない。

保存失敗時はエラーログを残すが、終了確認ダイアログは追加しない。

## 10. 設定画面からの初期化

### 10.1 表示位置

設定画面の「アプリケーション情報」へ、既存の「ウィンドウ配置」とは別の行として追加する。

```text
一覧表示        [初期状態に戻す]
```

別々のボタンにすることで、利用者がウィンドウ配置を残したまま列幅と並び順だけを初期化できる。

### 10.2 確認内容

実行前に確認ダイアログを表示する。

```text
保存されている一覧の列幅と並び順を初期状態に戻します。
変更は次回起動時から反映されます。よろしいですか。
```

### 10.3 成功時

1. `ListViewStateStore.delete()` を実行する
2. `_list_view_state_save_suppressed = True` を設定する
3. 完了メッセージを表示する
4. 現在表示中の列幅と並び順は変更しない
5. 次回起動時に既定値を使用する

現在の画面を直ちに変更しないことで、再描画や検索結果再取得による意図しない影響を避ける。

初期化後に終了しても抑止フラグによりファイルは再作成されない。次回起動後は抑止フラグが初期値へ戻るため、その終了時から再び保存される。

### 10.4 失敗時

- ファイル削除に失敗した場合はエラーダイアログを表示する
- 抑止フラグは変更しない
- 現在の表示状態を維持する
- アプリケーションを継続利用できる

### 10.5 Storeがない場合

Storeが渡されていない場合は、ボタンを無効化するか、操作時に利用できない旨を通知する。既存テストとの互換性を優先する場合は、操作時通知を採用する。

## 11. 異常系と互換性

| 状況 | 動作 |
|---|---|
| ファイルがない | 既定の列幅、登録順・降順で起動 |
| JSONが壊れている | 警告ログを残し、既定値で起動 |
| 未対応schema | 警告ログを残し、既定値で起動 |
| 列幅の型・範囲が不正 | ファイル全体を無効として既定値で起動 |
| 保存ファイルに未知の列がある | その列を無視し、既知の列を復元 |
| 現在の列が保存ファイルにない | その列は既定幅を維持 |
| 並び順の識別子が不正 | ファイル全体を無効として既定値で起動 |
| 読み込みに失敗 | 起動を継続 |
| 終了時の保存に失敗 | ログを残して終了を継続 |
| 初期化時の削除に失敗 | 画面へ通知し、抑止しない |

未知のトップレベル項目は将来拡張のため無視してよい。ただし、既知の必須項目については厳密に検証する。

## 12. `main.py`への組み込み

`ApplicationPaths` から保存先を取得し、Storeを生成してGUIへ渡す。

```python
list_view_state_store = ListViewStateStore(
    application_paths.list_view_state_path,
)

application = BookManagerApplication(
    ...,
    window_state_store=window_state_store,
    list_view_state_store=list_view_state_store,
)
```

既存の依存性注入と同様にキーワード引数を使い、引数順変更の影響を避ける。

## 13. ログ方針

次の事象をログへ記録する。

- 壊れた保存ファイルを無視したこと
- 未対応schemaを無視したこと
- 読み込みに失敗したこと
- 終了時保存に失敗したこと
- 設定画面からの削除に失敗したこと

ログへ列幅一覧を毎回出力する必要はない。障害調査に必要な保存先、例外種別、理由を記録する。

## 14. 実装対象ファイル

### 14.1 新規作成

```text
src/book_manager/models/list_view_state.py
src/book_manager/config/list_view_state_store.py
tests/models/test_list_view_state.py
tests/config/test_list_view_state_store.py
tests/gui/test_main_list_view_state_gui.py
```

### 14.2 変更

```text
main.py
src/book_manager/config/paths.py
src/book_manager/gui/book_manager_application.py
tests/config/test_paths.py
tests/test_main.py
tests/gui/test_application_settings_gui.py
```

実装時のテスト配置に応じて、設定画面の初期化試験を `test_main_list_view_state_gui.py` に集約してもよい。

## 15. 自動テスト方針

### 15.1 Model

- 正常な状態を生成できる
- `to_dict()` と `from_dict()` を往復できる
- 部分的な列幅辞書を許容する
- 未知の列IDを許容する
- schemaの型と値を検証する
- 列幅辞書の型を検証する
- 空の列IDを拒否する
- 列幅の文字列、浮動小数点、真偽値を拒否する
- 列幅の下限・上限外を拒否する
- 未対応の `sort_by` を拒否する
- `descending` の非真偽値を拒否する
- 入力辞書を後から変更してもModelへ影響しない

### 15.2 Store

- ファイルがない場合に `None` を返す
- 正常なJSONを読み込める
- 正常に保存できる
- UTF-8、インデント2、末尾改行で保存する
- 原子的に置換する
- 保存失敗時に一時ファイルを可能な範囲で削除する
- 壊れたJSONを無視する
- ルートがオブジェクトでないJSONを無視する
- 必須項目不足を無視する
- 未対応schemaを無視する
- 不正な列幅または並び順を無視する
- 存在するファイルを削除できる
- 存在しないファイルの削除を成功扱いにする
- 削除失敗を専用例外へ変換する

### 15.3 Paths

- 通常の利用者データルート配下になる
- `BOOK_MANAGER_HOME` 指定時に検証先配下になる
- ファイル名が `list_view_state.json` である
- パス参照だけではファイルやディレクトリを作成しない

### 15.4 GUI復元

- Storeなしで既定動作を維持する
- ファイルなしで既定幅、登録順・降順を維持する
- 全列の保存幅を復元する
- 部分的な保存幅では未保存列の既定幅を維持する
- 未知の列IDを無視する
- 最小幅未満にならないよう補正する
- 保存した並び順を最初の一覧取得へ使用する
- 復元時に余分な再検索を行わない
- 検索条件や選択状態を復元しない

### 15.5 GUI保存

- 終了時に現在の全列幅を採取する
- コンボボックスで変更した並び順を保存する
- 見出しクリックで変更した並び順を保存する
- 昇順・降順を保存する
- 終了1回につき1回保存する
- Storeなしでは保存しない
- 保存失敗時もウィンドウ状態保存と終了を行う
- ウィンドウ状態保存失敗時も一覧表示状態は保存済みになる

### 15.6 初期化

- 確認でキャンセルした場合は削除しない
- 確認後に保存ファイルを削除する
- 成功後に同じセッションでは再保存しない
- 現在の表示は直ちに変更しない
- 削除失敗時にエラーを表示する
- 削除失敗時は保存抑止しない
- 次回起動で既定値になる
- さらに次の終了時には保存が再開する

### 15.7 回帰試験

- 既存の列見出し並び替え
- 並び順コンボボックスとラジオボタン
- 検索後の並び替え
- 選択行の維持
- ウィンドウ状態の保存・復元・初期化
- 設定画面のバックアップ機能
- サブウィンドウの中央配置
- 全テスト

## 16. 実機確認項目

検証専用の `BOOK_MANAGER_HOME` を使用し、通常の利用者データから分離して確認する。

1. 初回起動時に既定の列幅、登録順・降順で表示される
2. 複数列の幅を変更して終了すると `list_view_state.json` が作成される
3. 再起動すると調整した列幅が復元される
4. コンボボックスで並び順と方向を変更し、再起動後も復元される
5. 列見出しクリックで並び順と方向を変更し、再起動後も復元される
6. 検索条件を指定して終了しても、再起動時は検索条件なしで全件表示される
7. JSONを破損させても既定値で起動できる
8. 未知の列をJSONへ追加しても既知の列が復元される
9. 設定画面から初期化するとファイルが削除される
10. 初期化したセッションを終了してもファイルが再作成されない
11. 次回起動時は既定値となり、その終了時にはファイルが再作成される
12. ウィンドウ配置の保存・復元・初期化が従来どおり動作する
13. アンインストール後も `list_view_state.json` を含む利用者データが保持される
14. 再インストール後も一覧表示状態を復元できる

## 17. 実装順序

1. `ListViewState` Modelと単体テスト
2. `ListViewStateStore` と単体テスト
3. `ApplicationPaths` への保存先追加
4. 列幅と並び順の復元
5. 終了時の保存
6. 設定画面からの初期化
7. `main.py` の依存性注入
8. GUI回帰試験と全テスト
9. 検証専用環境での実機確認
10. 配布版、更新、アンインストール、再インストール確認
11. README、CHANGELOG、ロードマップ、文書一覧の更新

Version 2.4のソース版では、1から9までを完了した。10の配布版、更新、アンインストールおよび再インストール確認は未実施である。

## 18. 完了条件

- 列幅を変更し、再起動後に復元できる
- 並び順と昇順・降順を変更し、再起動後に復元できる
- 検索条件は再起動時に復元されない
- 保存ファイルがない、壊れている、古い場合も既定値で起動できる
- 列追加・削除後も既知の保存値だけを安全に適用できる
- 設定画面から一覧表示状態だけを初期化できる
- 初期化直後の終了で保存ファイルが再作成されない
- 一覧表示状態とウィンドウ状態の一方の保存失敗が他方や終了を妨げない
- 既存機能の回帰試験と全テストが成功する
- 配布版でVersion 2.4.0として実機確認できる

## 19. 将来拡張

Version 2.4完了後に必要性を再評価する。

- 列の表示・非表示
- 列の並び順変更
- 列幅を画面解像度やDPIへ追従させる仕組み
- 保存対象項目を利用者が選べる設定
- 複数の一覧レイアウトプリセット

これらを追加する場合は `schema_version` を更新し、旧形式からの移行または安全な既定値フォールバックを設計する。

## 20. 実装・検証結果（2026年9月17日時点）

設計した`ListViewState`、`ListViewStateStore`、`ApplicationPaths.list_view_state_path`、GUIでの復元・保存・初期化、および`main.py`からの依存性注入を実装した。正常終了時にはTreeviewが保持する全13列の実際の幅と並べ替え状態を保存する。列幅の変更時に`stretch=True`の他列も追従する既存動作は変更しない。

全1489件の自動テストが成功した。検証専用の`BOOK_MANAGER_HOME`を使用したWindowsソース版では、次を確認した。

- 初回起動時の既定列幅と登録順・降順
- 列幅、コンボボックスおよび見出しクリックによる並べ替え状態の保存と復元
- 検索条件を保存・復元しないこと
- 一覧表示状態だけの初期化、同じセッションでの再作成防止、次回起動後の保存再開
- 壊れたJSONから既定表示で起動し、終了時に正常な13列の状態へ再作成すること
- 未知の列を無視し、不足する既知の列へ既定値を補い、利用可能な列幅と並べ替え状態を維持して正規化すること
- 一覧表示状態の初期化がウィンドウ状態とDBへ影響しないこと

ソース版の実装と検証は完了した。Version 2.4.0の配布版、Version 2.3.0からの上書き更新、アンインストールおよび再インストール後の状態保持は未検証であり、正式リリース前に確認する。
