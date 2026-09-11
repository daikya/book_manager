# 設定画面・ウィンドウ配置 詳細設計書

## 1. 文書情報

| 項目 | 内容 |
| --- | --- |
| 対象アプリケーション | Book Manager |
| 対象Version | 2.1.0 |
| 対象OS | Windows 11 |
| GUI | Tkinter |
| 関連ロードマップ | `docs/book_manager_roadmap.md` Version 2.1 |
| 主題 | 設定画面、Google Books APIキー管理、利用者データ関連パスの表示、サブウィンドウ中央配置 |

---

## 2. 目的

Version 2.1では、次の二点を改善する。

1. 利用者がGoogle Books APIキーや利用者データの保存場所を、アプリケーション内から確認・操作できるようにする。
2. アプリケーション独自のサブウィンドウを親画面の中央付近へ表示し、画面間の関係を分かりやすくする。

Version 2.0で確立した利用者データ保存先、配布方法および既存データ保持方針は変更しない。

---

## 3. 背景

Version 2.0.0では、Windowsインストーラーを使用してPython未導入環境へBook Managerを導入できるようになった。一方で、Google Books APIキーはPowerShellなどを使用してWindowsの利用者環境変数へ設定する必要がある。

また、次の場所はREADMEまたはエクスプローラーから手作業で確認している。

* データベース
* バックアップ
* 表紙画像キャッシュ
* ログ

さらに、タグ管理、読書履歴、読書集計などの`tk.Toplevel`画面は親画面の位置を基準にしておらず、画面左上へ表示される場合がある。

Version 2.1では、これらを設定画面と共通配置処理によって改善する。

---

## 4. 対象範囲

### 4.1 対象

* メイン画面から開く設定画面
* Google Books APIキーの設定状態表示
* Google Books APIキーの登録・変更・削除
* 現在のプロセスへのAPIキー反映
* 利用者データ関連パスの表示
* 利用者データ関連フォルダーをエクスプローラーで開く操作
* アプリケーション名とVersionの表示
* 親ウィンドウを基準としたサブウィンドウの中央配置
* 画面外へ配置しないための座標補正
* Model、Service、GUIおよび配置ヘルパーの自動テスト
* ソース版とWindows配布版での実画面確認

### 4.2 対象外

* 利用者データ保存先の変更
* バックアップ間隔または保存世代数の設定
* バックアップ、キャッシュまたはログの削除
* テーマ、配色、フォントまたは言語の変更
* メイン画面およびサブウィンドウの位置・サイズの永続化
* APIキーの接続試験専用ボタン
* Windows Credential Managerなどへの秘密情報保存
* 自動更新
* Tkinter標準のメッセージボックス、ファイル選択画面、文字列入力画面の位置制御
* 複数モニター固有APIを利用した高度なモニター判定

---

## 5. 基本方針

### 5.1 設定画面

設定画面はメイン画面を親とするモーダルな`tk.Toplevel`として実装する。

* 同時に複数の設定画面を開かない。
* 親画面の中央付近へ表示する。
* APIキーを通常の文字列として表示しない。
* パスは参照専用とする。
* 設定画面を閉じても書籍入力中の値や選択状態を変更しない。

### 5.2 APIキー

既存仕様と同じ`GOOGLE_BOOKS_API_KEY`を使用する。

永続化先はWindows利用者単位の環境変数とし、マシン全体の環境変数は変更しない。現在のプロセスの`os.environ`にも反映する。

APIキーはログ、例外メッセージ、完了メッセージおよびテスト失敗時の表示へ含めない。

### 5.3 パス

パスの正は`book_manager.config.paths.ApplicationPaths`とする。設定画面で`%LOCALAPPDATA%`などから再計算しない。

### 5.4 Version

Versionの正は`pyproject.toml`の`project.version`とする。実行時はパッケージメタデータから取得し、GUIへVersion文字列を重複してハードコードしない。

Windows配布版には、実行時のVersion取得に必要なパッケージメタデータを含める。

### 5.5 ウィンドウ配置

配置座標の計算とTkinterウィンドウへの適用を分離する。

座標計算はTkinterへ依存しない純粋関数とし、境界条件を単体テストできるようにする。

---

## 6. 画面仕様

### 6.1 メイン画面

メイン画面下部の操作ボタン領域へ、`設定`ボタンを追加する。

想定する配置は次のとおりである。

```text
...  タグ管理  読書履歴  読書集計  設定                         終了
```

既存の最小ウィンドウ幅でボタンが欠ける場合は、ボタン間隔または配置方法を調整する。書籍一覧の表示行数を減らしてはならない。

### 6.2 設定画面の概要

| 項目 | 仕様 |
| --- | --- |
| タイトル | 設定 |
| 種類 | `tk.Toplevel` |
| 親 | メイン画面 |
| モーダル | `transient`、`grab_set`、`wait_window` |
| 初期サイズ | 内容の要求サイズを基準とする |
| 最小サイズ | 全項目と操作ボタンを表示できる大きさ |
| リサイズ | 横方向を許可し、長いパスを確認できるようにする |
| 初期位置 | 親画面の中央 |
| 閉じる操作 | `閉じる`ボタン、タイトルバーの閉じるボタン、Escキー |

### 6.3 画面構成

設定画面は、次の三つの領域で構成する。

#### 6.3.1 外部サービス

| 表示・入力項目 | 内容 |
| --- | --- |
| Google Books APIキー | マスク付き入力欄 |
| 設定状態 | `設定済み`または`未設定` |
| 保存 | 入力値を登録または変更する |
| 削除 | 確認後に登録値を削除する |
| 補足 | 利用者環境変数へ保存されることを案内する |

入力欄は`show="*"`を指定する。設定画面を開いた時点では、登録済みの実値を入力欄へ復元しない。

設定済みの場合も入力欄は空とし、値の変更を行う場合だけ新しい値を入力する。この方法により、画面表示やTkinter変数から既存キーが偶発的に露出する範囲を狭める。

#### 6.3.2 利用者データ

| 項目 | 表示内容 | 操作 |
| --- | --- | --- |
| データベース | `database_path` | 親フォルダーを開く |
| バックアップ | `backup_directory` | フォルダーを開く |
| 表紙画像 | `cover_cache_directory` | フォルダーを開く |
| ログ | `log_path` | 親フォルダーを開く |

パスは読み取り専用の`ttk.Entry`または選択可能な`tk.Text`で表示し、利用者がコピーできるようにする。

#### 6.3.3 アプリケーション情報

| 項目 | 表示内容 |
| --- | --- |
| アプリケーション名 | Book Manager |
| Version | パッケージメタデータから取得した値 |
| 利用者データ | `root_directory` |

### 6.4 APIキー保存操作

1. 利用者が新しいAPIキーを入力する。
2. `保存`を押す。
3. 前後の空白を除去する。
4. 空文字列の場合はエラーを表示し、保存しない。
5. 利用者環境変数へ保存する。
6. 現在のプロセスへ反映する。
7. 起動済みのGoogle Booksクライアントへ反映する。
8. 入力欄を空に戻す。
9. 状態表示を`設定済み`へ更新する。
10. 完了メッセージを表示する。

完了メッセージにはAPIキーを含めない。

### 6.5 APIキー削除操作

1. 利用者が`削除`を押す。
2. 未設定の場合は、未設定であることを案内する。
3. 設定済みの場合は確認画面を表示する。
4. 利用者がキャンセルした場合は何も変更しない。
5. 利用者環境変数から削除する。
6. 現在のプロセスから削除する。
7. 起動済みのGoogle Booksクライアントへ未設定を反映する。
8. 入力欄を空に戻す。
9. 状態表示を`未設定`へ更新する。
10. 完了メッセージを表示する。

### 6.6 フォルダーを開く操作

Windowsでは`os.startfile`を使用して対象フォルダーをエクスプローラーで開く。

* ディレクトリを対象とする。
* データベースとログはファイルそのものではなく親ディレクトリを開く。
* 対象ディレクトリが存在しない場合は、`mkdir(parents=True, exist_ok=True)`で作成する。
* ファイルが同名で存在するなど作成できない場合は、エラーを表示する。
* OS呼び出しが失敗した場合は、対象パスと簡潔な説明を表示する。
* APIキーなどの秘密情報をエラーへ含めない。

---

## 7. Model設計

### 7.1 `ApplicationSettingsSnapshot`

設定画面へ表示する値を、不変Modelとしてまとめる。

想定ファイル：

```text
src/book_manager/models/application_settings.py
```

想定定義：

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ApplicationSettingsSnapshot:
    google_books_api_key_is_configured: bool
    application_name: str
    application_version: str
    root_directory: Path
    database_path: Path
    backup_directory: Path
    cover_cache_directory: Path
    log_path: Path
```

APIキーの実値はSnapshotへ保持しない。

### 7.2 Modelの責務

* 設定画面へ表示する非秘密情報を保持する。
* APIキーの設定有無だけを保持する。
* GUIとServiceの間で個別引数が増えることを防ぐ。

### 7.3 Modelが行わないこと

* 環境変数の読み書き
* ディレクトリ作成
* Version取得
* 入力検証
* GUI表示

---

## 8. Service設計

### 8.1 `ApplicationSettingsService`

想定ファイル：

```text
src/book_manager/services/application_settings_service.py
```

主な公開メソッドは次のとおりとする。

```python
class ApplicationSettingsService:
    def get_snapshot(self) -> ApplicationSettingsSnapshot:
        ...

    def save_google_books_api_key(self, api_key: str) -> None:
        ...

    def delete_google_books_api_key(self) -> None:
        ...

    def open_directory(self, directory: Path) -> None:
        ...
```

### 8.2 コンストラクター依存

```python
def __init__(
    self,
    application_paths: ApplicationPaths,
    application_name: str,
    application_version: str,
    environment: MutableMapping[str, str] | None = None,
    user_environment_store: UserEnvironmentStore | None = None,
    directory_opener: Callable[[Path], None] | None = None,
) -> None:
    ...
```

テストでは環境変数、Windows利用者環境およびエクスプローラー起動を差し替えられるようにする。

### 8.3 APIキー検証

保存時は次を検証する。

* 型が`str`である。
* 前後空白を除去した結果が空でない。
* 改行文字を含まない。
* NUL文字を含まない。

APIキー固有の文字種や長さはGoogle側で変更される可能性があるため、Version 2.1では過度に制限しない。

### 8.4 利用者環境変数の永続化

Windows利用者環境変数は、`HKEY_CURRENT_USER\Environment`の`GOOGLE_BOOKS_API_KEY`として扱う。

実装では、Windows固有処理を次のProtocolへ分離する。

```python
from typing import Protocol


class UserEnvironmentStore(Protocol):
    def get(self, name: str) -> str | None:
        ...

    def set(self, name: str, value: str) -> None:
        ...

    def delete(self, name: str) -> None:
        ...
```

本番実装では`winreg`を使用する。`setx.exe`には依存しない。

登録後は、必要に応じて`WM_SETTINGCHANGE`を通知し、将来起動するプロセスが変更を認識できるようにする。通知失敗だけで登録自体を失敗扱いにするかは実装時にテスト可能な形で明確にする。少なくともアプリケーション内の現在プロセスには確実に反映する。

### 8.5 設定状態の判定

設定状態は、次の優先順位で判定する。

1. 現在のプロセスの`GOOGLE_BOOKS_API_KEY`
2. Windows利用者環境の`GOOGLE_BOOKS_API_KEY`

空文字列または空白だけの値は未設定として扱う。

### 8.6 エラー

Serviceは利用者向け文章を組み立てず、原因を保持した例外を送出する。

想定する例外：

```python
class ApplicationSettingsError(Exception):
    """設定処理に失敗した場合の基底例外。"""


class ApplicationSettingsValidationError(
    ApplicationSettingsError
):
    """設定値が不正な場合の例外。"""


class UserEnvironmentUpdateError(
    ApplicationSettingsError
):
    """利用者環境変数を更新できない場合の例外。"""


class DirectoryOpenError(ApplicationSettingsError):
    """対象フォルダーを開けない場合の例外。"""
```

例外本文へAPIキーの値を含めない。

---

## 9. 起動中クライアントへの反映

### 9.1 課題

現在のGoogle Booksクライアントは、アプリケーション起動時に環境変数から取得したAPIキーを受け取る。`os.environ`だけを更新しても、生成済みクライアントが古い値を保持する可能性がある。

### 9.2 方針

Google Booksクライアントへ、APIキーを差し替える公開メソッドを追加する。

```python
def set_api_key(self, api_key: str | None) -> None:
    """以後のリクエストで使用するAPIキーを変更する。"""
```

設定画面で保存または削除が成功した後、GUIへ注入したコールバックを通してこのメソッドを呼び出す。

```python
on_google_books_api_key_changed: Callable[
    [str | None],
    None,
]
```

### 9.3 呼び出し順序

保存時：

1. 利用者環境へ永続化する。
2. 現在の`os.environ`へ反映する。
3. クライアント更新コールバックを呼び出す。
4. GUIの状態を更新する。

削除時も同じ順序で、値には`None`を使用する。

コールバックの失敗時はログへ例外を記録し、利用者へ「設定は保存されたが、現在の画面へ反映するため再起動が必要」であることを案内する。APIキーの値は記録しない。

---

## 10. Version取得設計

### 10.1 公開関数

想定ファイル：

```text
src/book_manager/config/version.py
```

想定定義：

```python
from importlib.metadata import PackageNotFoundError, version


PACKAGE_NAME = "book-manager"


def get_application_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "開発版"
```

### 10.2 配布版

PyInstaller設定で`book-manager`のパッケージメタデータを収集する。配布版の設定画面に表示するVersion、実行ファイルのVersion情報、ZIP名およびインストーラー名が一致することを確認する。

### 10.3 テスト

* パッケージVersionを取得できる。
* メタデータが存在しない場合に`開発版`を返す。
* 配布版ビルド設定がメタデータを含む。

---

## 11. ウィンドウ配置設計

### 11.1 想定ファイル

```text
src/book_manager/gui/window_positioning.py
```

### 11.2 値オブジェクト

座標計算には、次の不変Modelを使用する。

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowRectangle:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ScreenSize:
    width: int
    height: int
```

### 11.3 純粋な座標計算

```python
def calculate_centered_position(
    parent: WindowRectangle,
    child_width: int,
    child_height: int,
    screen: ScreenSize,
    margin: int = 0,
) -> tuple[int, int]:
    ...
```

基本座標は次式で求める。

```text
x = parent.x + (parent.width - child_width) // 2
y = parent.y + (parent.height - child_height) // 2
```

その後、画面内へ収める。

```text
minimum_x = margin
minimum_y = margin
maximum_x = max(margin, screen.width - child_width - margin)
maximum_y = max(margin, screen.height - child_height - margin)

x = min(maximum_x, max(minimum_x, x))
y = min(maximum_y, max(minimum_y, y))
```

子画面が画面より大きい場合は、左上を`margin`へ合わせる。Version 2.1では子画面の縮小は行わない。

### 11.4 Tkinterへの適用

```python
def center_window_on_parent(
    child: tk.Toplevel,
    parent: tk.Misc,
    *,
    margin: int = 0,
) -> None:
    ...
```

処理順序：

1. `child.update_idletasks()`を呼び出す。
2. 子画面の要求サイズまたは設定済みサイズを取得する。
3. 親画面の位置とサイズを取得する。
4. 画面サイズを取得する。
5. 純粋関数で座標を計算する。
6. `child.geometry(f"+{x}+{y}")`を設定する。

固定サイズを指定する画面では、既存の`800x600`などを維持した後で中央配置する。

### 11.5 親画面情報が利用できない場合

親画面の幅または高さが1以下の場合、次の順で代替する。

1. `parent.update_idletasks()`後に再取得する。
2. それでも不正な場合は画面全体の中央を基準にする。

親画面が最小化状態の場合も、取得値が正常でなければ画面中央を使用する。

### 11.6 表示タイミング

画面の部品を作成し終え、要求サイズが確定した後、`wait_window()`より前に中央配置を行う。

表示途中の移動を避ける必要がある場合は、次の手順を用いる。

1. `child.withdraw()`
2. 部品作成
3. `center_window_on_parent()`
4. `child.deiconify()`
5. `child.focus_set()`
6. `child.wait_window()`

既存画面へ適用する際は、フォーカス、`grab_set`および閉じる処理の順序をテストする。

### 11.7 対象画面

| 画面 | 現状 | Version 2.1 |
| --- | --- | --- |
| タグ選択 | `tk.Toplevel` | 親画面中央へ配置 |
| タグ管理 | `tk.Toplevel` | 親画面中央へ配置 |
| 読書履歴 | `800x600` | サイズを維持して中央へ配置 |
| 読書集計 | `900x650` | サイズを維持して中央へ配置 |
| 設定 | 新規 | 親画面中央へ配置 |

`simpledialog`、`messagebox`および`filedialog`は対象外とする。ただし、すべて適切な`parent`を渡す既存方針は維持する。

### 11.8 複数モニター

Version 2.1ではTkinterが返す画面サイズを利用する。負の座標を使用する副モニターなど、複雑な構成へ完全対応するためのWindows Monitor API導入は行わない。

実環境で問題が確認された場合は、Version 2.2以降でモニター別ワークエリア取得を検討する。

---

## 12. GUIと依存関係

### 12.1 `BookManagerApplication`への追加依存

```python
def __init__(
    self,
    root: tk.Tk,
    service: BookService,
    csv_export_service: CsvExportService,
    csv_import_service: CsvImportService,
    backup_service: BackupService,
    reading_history_service: ReadingHistoryService,
    application_settings_service: ApplicationSettingsService,
    on_google_books_api_key_changed: Callable[
        [str | None],
        None,
    ],
) -> None:
    ...
```

既存GUIテストへの影響を抑えるため、新しい依存を省略可能にする暫定対応は行わない。全生成箇所を更新し、必須依存として明確にする。

### 12.2 `main.py`

`main.py`では、次を行う。

1. `ApplicationPaths`を生成する。
2. アプリケーションVersionを取得する。
3. `ApplicationSettingsService`を生成する。
4. `GoogleBooksClient`を生成する。
5. APIキー変更コールバックとして`GoogleBooksClient.set_api_key`を渡す。
6. `BookManagerApplication`へ設定Serviceとコールバックを渡す。

### 12.3 ログ

次の事象は、APIキーの値を含めずに記録する。

* APIキーを登録または変更した。
* APIキーを削除した。
* 利用者環境変数の更新に失敗した。
* 対象フォルダーを開けなかった。
* 起動中クライアントへの反映に失敗した。

設定画面を開いたことやパスを表示したことは、通常は記録しない。

---

## 13. セキュリティ設計

### 13.1 APIキーの非表示

* Snapshotへ実値を格納しない。
* GUIを開いたときに実値を入力欄へ設定しない。
* 入力欄へマスクを設定する。
* 完了・確認・エラーメッセージへ実値を含めない。
* ログへ実値を含めない。
* `repr`を含む例外連鎖へ値を渡さない。

### 13.2 保存方式の説明

Windows利用者環境変数は、同じWindows利用者権限で確認できる。暗号化された秘密情報保管庫ではない。

設定画面とREADMEでは、次の趣旨を簡潔に案内する。

> APIキーは現在のWindows利用者の環境変数へ保存されます。共有PCでは、同じWindowsアカウントを利用する人が値を確認できる可能性があります。

### 13.3 Git管理

* 実際のAPIキーをテストデータへ使用しない。
* `.env`および`config.local.json`の既存除外を維持する。
* ドキュメントの例では`YOUR_API_KEY`などのダミー値を使用する。
* スクリーンショットへAPIキーを含めない。

---

## 14. エラー処理

| 事象 | 動作 |
| --- | --- |
| APIキーが空 | 入力エラーを表示し、変更しない |
| APIキーの永続化失敗 | エラーを表示し、現在クライアントを変更しない |
| 現在クライアントへの反映失敗 | 保存済みであることと再起動が必要なことを表示する |
| 削除対象が未設定 | 情報メッセージを表示する |
| フォルダー作成失敗 | 対象パスとエラー概要を表示する |
| エクスプローラー起動失敗 | 対象パスとエラー概要を表示する |
| Version取得失敗 | `開発版`と表示する |
| 中央配置失敗 | 画面生成を中止せず、ウィンドウマネージャー既定位置で表示する |

中央配置は操作性改善であり、配置処理の例外によって主要機能を利用不能にしてはならない。

---

## 15. 自動テスト設計

### 15.1 Modelテスト

想定ファイル：

```text
tests/models/test_application_settings.py
```

確認項目：

* 全項目を保持できる。
* frozenである。
* slotsが有効である。
* APIキーの実値を保持するフィールドがない。

### 15.2 Serviceテスト

想定ファイル：

```text
tests/services/test_application_settings_service.py
```

確認項目：

* 未設定のSnapshotを返す。
* 現在プロセスに値がある場合は設定済みと判定する。
* 利用者環境だけに値がある場合も設定済みと判定する。
* 保存時に前後空白を除去する。
* 空白だけの値を拒否する。
* 改行とNUL文字を拒否する。
* 利用者環境へ値を保存する。
* 現在プロセスへ値を反映する。
* 削除時に両方から値を削除する。
* 未設定での削除を安全に繰り返せる。
* 永続化失敗時に現在プロセスを変更しない。
* Snapshotへ実値を含めない。
* 指定フォルダーを作成して開く。
* 作成済みフォルダーを開く。
* フォルダー作成失敗を専用例外へ変換する。
* OS呼び出し失敗を専用例外へ変換する。

### 15.3 Versionテスト

想定ファイル：

```text
tests/config/test_version.py
```

確認項目：

* パッケージメタデータのVersionを返す。
* パッケージが見つからない場合に`開発版`を返す。

### 15.4 ウィンドウ配置テスト

想定ファイル：

```text
tests/gui/test_window_positioning.py
```

純粋関数で、少なくとも次を確認する。

* 親子が通常サイズの場合に中央座標を返す。
* 親の原点が0以外でも正しく計算する。
* 奇数差の切り捨てが一貫している。
* 左端を越える場合に0へ補正する。
* 上端を越える場合に0へ補正する。
* 右端を越える場合に画面内へ補正する。
* 下端を越える場合に画面内へ補正する。
* 子画面が画面より大きい場合に0へ配置する。
* marginを考慮する。
* 幅、高さまたはmarginが不正な場合に拒否する。
* Tkinter適用関数が期待するgeometryを設定する。
* 親サイズが不正な場合に画面中央へフォールバックする。

### 15.5 GUIテスト

想定ファイル：

```text
tests/gui/test_application_settings_gui.py
```

確認項目：

* 設定ボタンを生成する。
* 設定ボタンから設定画面を開く。
* 設定画面へ`transient`と`grab_set`を適用する。
* Snapshotの設定状態、Versionおよび各パスを表示する。
* APIキー入力欄をマスクする。
* 設定済みの実値を入力欄へ復元しない。
* 保存時にServiceと変更コールバックを呼ぶ。
* 保存成功後に入力欄と状態表示を更新する。
* 保存失敗時にエラーを表示する。
* 削除前に確認する。
* 削除のキャンセル時にServiceを呼ばない。
* 削除成功後に状態表示を更新する。
* 各フォルダーを開く処理を呼ぶ。
* 閉じるボタンとEscキーで画面を閉じる。
* 設定画面へ中央配置処理を適用する。
* タグ選択、タグ管理、読書履歴および読書集計へ中央配置処理を適用する。

GUIテストでは、実際のレジストリ、利用者環境変数、エクスプローラーおよび利用者データへアクセスしない。

### 15.6 既存テスト

`BookManagerApplication`のコンストラクター引数追加に伴い、既存GUIテストの生成処理を更新する。

同じ依存生成が多数のテストへ重複する場合は、テスト用Factoryまたはfixtureへ集約する。ただし、既存テストを一度に大きく再編せず、Version 2.1に必要な範囲へ限定する。

### 15.7 focused pytest

```powershell
pytest .\tests\models\test_application_settings.py -q
```

```powershell
pytest .\tests\services\test_application_settings_service.py -q
```

```powershell
pytest .\tests\config\test_version.py -q
```

```powershell
pytest .\tests\gui\test_window_positioning.py -q
```

```powershell
pytest .\tests\gui\test_application_settings_gui.py -q
```

```powershell
pytest .\tests\gui -q
```

最終確認：

```powershell
pytest -q
```

---

## 16. Windows実環境確認

### 16.1 ソース版

1. `python main.py`で起動できる。
2. 設定画面を開ける。
3. 設定画面が親画面の中央付近へ表示される。
4. APIキーの設定状態が正しい。
5. 新しいAPIキーを保存できる。
6. 再起動せず書誌情報と表紙画像を取得できる。
7. APIキーを削除できる。
8. APIキーが画面とログへ露出しない。
9. データ、バックアップ、表紙画像およびログの各フォルダーを開ける。
10. Versionが正しく表示される。
11. タグ選択、タグ管理、読書履歴および読書集計が親画面の中央付近へ表示される。
12. 親画面を画面端へ移動しても、サブウィンドウが操作可能な範囲へ表示される。
13. 既存の主要機能を利用できる。

### 16.2 配布版

1. Version 2.0.0から2.1.0へ上書き更新できる。
2. 既存の利用者データを保持する。
3. 既存の利用者環境変数を設定済みとして認識する。
4. 設定画面からAPIキーを変更・削除できる。
5. 設定変更がアプリケーション再起動後も保持される。
6. 設定画面のVersion、実行ファイルのVersionおよびインストーラーのVersionが2.1.0で一致する。
7. 各フォルダーをエクスプローラーで開ける。
8. 主要なサブウィンドウが親画面中央付近へ表示される。
9. アンインストール後も利用者データと利用者環境変数を削除しない。
10. 再インストール後も既存データとAPIキー設定を利用できる。

---

## 17. 実装順序

### 17.1 設計

1. 本設計書を確定する。
2. 既存GUIの全`tk.Toplevel`生成箇所を確認する。
3. APIキーの現在の参照経路を確認する。

### 17.2 共通処理

4. `ApplicationSettingsSnapshot`を追加する。
5. Version取得処理を追加する。
6. 利用者環境変数Storeを追加する。
7. `ApplicationSettingsService`を追加する。
8. Google BooksクライアントへAPIキー変更処理を追加する。
9. ウィンドウ配置ヘルパーを追加する。

### 17.3 GUI

10. 既存サブウィンドウへ中央配置を適用する。
11. 設定画面を追加する。
12. `main.py`の依存生成を更新する。

### 17.4 検証と配布

13. focused pytestを実行する。
14. 全pytestを実行する。
15. Windowsソース版で実画面確認を行う。
16. README、CHANGELOG、ロードマップおよび本設計書を更新する。
17. Versionを2.1.0へ更新する。
18. Windows実行ファイルとインストーラーを作成する。
19. Version 2.0.0からの上書き更新を確認する。
20. Version 2.1.0を公開する。

---

## 18. 想定変更ファイル

### 18.1 新規

```text
src/book_manager/config/version.py
src/book_manager/gui/window_positioning.py
src/book_manager/models/application_settings.py
src/book_manager/services/application_settings_service.py
tests/config/test_version.py
tests/gui/test_application_settings_gui.py
tests/gui/test_window_positioning.py
tests/models/test_application_settings.py
tests/services/test_application_settings_service.py
docs/settings_and_window_layout_design.md
```

Windows利用者環境変数Storeを別モジュールへ分離する場合は、次も追加する。

```text
src/book_manager/config/user_environment.py
tests/config/test_user_environment.py
```

### 18.2 変更

```text
main.py
src/book_manager/gui/book_manager_application.py
src/book_manager/metadata/google_books_client.py
packaging/pyinstaller/book_manager.spec
tests/test_main.py
既存GUIテスト
README.md
CHANGELOG.md
docs/book_manager_roadmap.md
docs/documentation_guide.md
pyproject.toml
```

実装中に必要性が確認できたファイルだけを変更し、単なる形式統一のための広範囲な修正は同じコミットへ含めない。

---

## 19. コミット方針

1コミット1テーマを維持する。想定コミットは次のとおりである。

```text
docs: 設定画面とウィンドウ配置の設計を追加する
feat: アプリケーション設定のModelを追加する
feat: APIキーの設定処理をServiceへ追加する
feat: サブウィンドウの中央配置処理を追加する
feat: GUIへ設定画面を追加する
fix: 既存サブウィンドウを親画面中央へ表示する
docs: Version 2.1の実装結果を反映する
chore: Versionを2.1.0に更新する
docs: Version 2.1.0のリリース記録を追加する
```

中央配置をGUI設定画面と同時に実装する場合でも、共通配置処理と既存画面への適用はレビュー可能な単位へ分ける。

---

## 20. 完成条件

* [x] メイン画面から設定画面を開ける。
* [x] 設定画面が親画面の中央付近へ表示される。
* [x] APIキーの設定状態を確認できる。
* [x] APIキーを登録・変更・削除できる。
* [x] 登録・変更・削除を現在のアプリケーションへ反映できる。
* [x] APIキーを画面、ログおよび例外へ露出しない。
* [x] APIキー設定をアプリケーション再起動後も保持できる。
* [x] データベース、バックアップ、表紙画像キャッシュおよびログの場所を確認できる。
* [x] 各対象フォルダーをエクスプローラーで開ける。
* [x] Versionを設定画面へ表示できる。
* [x] タグ選択、タグ管理、読書履歴および読書集計を親画面中央付近へ表示できる。
* [x] 親画面が画面端にある場合も、サブウィンドウを操作可能な範囲へ表示できる。
* [x] 既存GUIのモーダル動作とサイズに回帰がない。
* [x] 関連するfocused pytestがすべて成功する。
* [x] 全pytestが成功する。
* [x] Windowsソース版で実画面確認が完了している。
* [x] Windows配布版で上書き更新と実画面確認が完了している。
* [x] 既存機能に回帰がない。

---

## 21. 設計上の決定

Version 2.1では、次を正式な設計判断とする。

* 設定画面はメイン画面を親とするモーダル画面とする。
* APIキーは`GOOGLE_BOOKS_API_KEY`としてWindows利用者環境へ保存する。
* APIキーの実値をSnapshotおよび設定画面の初期値へ含めない。
* APIキー変更は現在のプロセスと起動済みGoogle Booksクライアントへ反映する。
* 利用者データ関連パスは参照専用とする。
* パスは既存の`ApplicationPaths`を正とする。
* Versionはパッケージメタデータから取得する。
* サブウィンドウの座標計算を純粋関数として分離する。
* アプリケーション独自の主要な`tk.Toplevel`を親画面中央へ表示する。
* 中央配置に失敗しても画面自体の表示を妨げない。
* Tkinter標準ダイアログの位置制御と高度な複数モニター対応は対象外とする。

---

## 22. 実装結果

Version 2.1では、本設計に基づく設定画面とウィンドウ配置改善のソース版実装を完了した。

主な結果は次のとおりである。

* `ApplicationSettingsSnapshot`を追加し、APIキーの実値を含めず設定画面の表示情報を保持するようにした。
* `WindowsUserEnvironmentStore`と`ApplicationSettingsService`を追加し、APIキーをWindows利用者環境変数へ永続化できるようにした。
* `GoogleBooksClient.set_api_key()`を追加し、設定変更を起動中のクライアントへ反映できるようにした。
* パッケージメタデータからアプリケーションVersionを取得する処理を追加した。
* 座標計算とTkinterへの適用を行う共通ウィンドウ配置処理を追加した。
* 設定、タグ選択、タグ管理、読書履歴および読書集計を親画面の中央付近へ表示するようにした。
* 設定画面へAPIキー管理、利用者データ関連パス、フォルダーを開く操作およびアプリケーション情報を追加した。
* 関連するfocused pytest、全GUIテストおよび全1194件のpytestが成功した。
* Windowsソース版で設定画面の9項目と、既存サブウィンドウ中央表示の6項目を確認した。
* Version 2.1.0のWindows実行ファイル、検証用ZIPおよびWindowsインストーラーを作成した。
* Version 2.0.0からの上書き更新後も、利用者データとAPIキー設定が保持されることを確認した。
* アンインストール後も利用者データとAPIキー設定が保持され、再インストール後に再利用できることを確認した。

Windows配布版では、設定画面、APIキー管理、フォルダー表示、主要サブウィンドウの中央表示および既存機能に問題がないことを確認した。

---

**Version 2.1 設定画面・ウィンドウ配置方針：設定を見える場所へ集約し、関連する画面を親画面の中央へ自然に表示する。**
