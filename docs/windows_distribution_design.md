# Windows実行ファイル作成・配布設計書

## 1. 文書の目的

本設計書は、book_manager Version 2.0で実施するWindows実行ファイル化について定義する。

Pythonや仮想環境を導入していないWindows環境でbook_managerを起動できるようにし、後続のWindowsインストーラー作成へ引き渡せる、再現可能で安全なビルド成果物を作ることを目的とする。

本設計は、次の既存方針を前提とする。

* 利用者データは`%LOCALAPPDATA%\book_manager`配下へ保存する。
* アプリケーション本体と利用者データを分離する。
* ソース版と配布版で同じデータ形式と既定保存先を使用する。
* Version 1.9以前のデータは、移動や削除をせず安全に複製する。
* Version 2.0のデータベーススキーマは、必要がない限りVersion 7を維持する。
* Version 2.0の正式配布物は、後続工程で作成するWindowsインストーラーとする。

---

## 2. 対象範囲

### 2.1 対象

本設計書では、次を対象とする。

* PyInstallerの導入方法
* `onedir`形式によるWindows実行ファイルの作成
* PyInstaller specファイル
* Windows用ビルドスクリプト
* GUIアプリケーションとしてのコンソール非表示
* Tkinter、Pillow、Requestsおよび証明書情報の同梱
* アプリケーション名、Version情報およびアイコンの組み込み
* 配布版で参照するパスの整理
* 配布版でのログ出力
* ビルド生成物の構成
* Git管理対象と除外対象
* ZIP形式による中間成果物の作成
* 実行ファイル単体での動作確認
* Python未導入環境を想定した確認
* インストーラー工程へ渡す成果物と条件

### 2.2 対象外

次は本設計書の対象外とし、後続のインストーラー設計またはVersion 2.1以降で扱う。

* インストーラー作成ツールの詳細仕様
* スタートメニュー登録
* デスクトップショートカット作成
* 上書きインストールとアンインストール
* アプリケーション内からの自動更新
* コード署名証明書の取得
* Microsoft Storeでの公開
* macOS版およびLinux版の作成
* `onefile`形式の正式採用
* CIによる自動ビルド

---

## 3. 現状

### 3.1 起動方法

現在は、リポジトリルートで仮想環境を有効にし、次のコマンドで起動している。

```powershell
python main.py
```

正式なエントリーポイントは、リポジトリルートの`main.py`である。

### 3.2 ソース構成

Pythonパッケージは`src`レイアウトで管理している。

```text
book_manager\
├── main.py
├── pyproject.toml
├── requirements.txt
└── src\
    └── book_manager\
```

PyInstallerが`book_manager`パッケージを確実に検出できるように、specファイルの`pathex`へ`src`を明示する。

### 3.3 主な依存関係

配布版で必要な主な依存関係は次のとおりである。

| 分類 | 依存関係 | 用途 |
|---|---|---|
| Python標準 | Tkinter / Tcl / Tk | GUI |
| Python標準 | SQLite | 利用者データベース |
| 外部 | Pillow | 表紙画像の読み込みと表示 |
| 外部 | Requests | 外部書誌情報および表紙画像の取得 |
| 外部 | certifi | HTTPS通信用CA証明書 |
| ビルド | PyInstaller | Windows実行ファイルの作成 |

`pytest`、`pluggy`、`iniconfig`および`Pygments`などのテスト専用依存関係は、配布物へ明示的に追加しない。

### 3.4 利用者データ

利用者データは、配布物やインストール先へ含めない。

```text
%LOCALAPPDATA%\book_manager\
├── data\
│   └── books.db
├── backups\
├── cache\
│   └── covers\
└── logs\
```

`logs`は本設計で追加する。データベース、バックアップ、表紙画像、ログのいずれも、PyInstallerの出力先へ保存してはならない。

---

## 4. 基本方針

Windows実行ファイル作成には、次の方針を適用する。

1. PyInstallerを使用する。
2. Version 2.0では`onedir`形式を正式なビルド方式とする。
3. 実行ファイル名は`BookManager.exe`とする。
4. 出力ディレクトリ名は`BookManager`とする。
5. 正式ビルドではコンソールウィンドウを表示しない。
6. ビルド設定はspecファイルへ集約する。
7. ビルド操作はPowerShellスクリプトで再現可能にする。
8. 利用者データおよび開発用データを配布物へ含めない。
9. ビルド前に全自動テストを実行する。
10. ビルド後に配布物だけを別のディレクトリへコピーして起動確認する。
11. Windows実行ファイルの実動作は、自動テストだけでなく実画面で確認する。
12. 正式配布前にPython未導入環境または同等の隔離環境で確認する。
13. ビルド中に警告が出た場合は、内容を確認してから成果物を採用する。
14. ビルド生成物はGitへコミットしない。

---

## 5. `onedir`形式の採用

### 5.1 採用理由

Version 2.0では、PyInstallerの`onedir`形式を採用する。

主な理由は次のとおりである。

* 実行時の一時展開が不要で、起動動作を把握しやすい。
* 同梱されたDLL、Tcl/Tk、Pillowおよび証明書情報を確認しやすい。
* 欠落した依存物の調査がしやすい。
* ウイルス対策ソフトによる誤検知の要因を、`onefile`形式より抑えやすい。
* 後続のインストーラーへ、ディレクトリ一式をそのまま組み込める。
* 問題発生時に、構成ファイル単位で切り分けやすい。

### 5.2 `onefile`を採用しない理由

`onefile`形式は配布ファイルが1つになる利点がある一方、起動時の一時展開、調査の難しさ、誤検知および起動時間への影響がある。

Version 2.0では、インストーラーが利用者向けの単一導入手段となるため、PyInstaller成果物そのものを1ファイルにする必要はない。

### 5.3 配布単位

PyInstallerが生成した次のディレクトリ全体を1つのアプリケーションとして扱う。

```text
dist\
└── BookManager\
    ├── BookManager.exe
    └── _internal\
        └── ...
```

`BookManager.exe`だけを取り出して配布または移動してはならない。

---

## 6. 配布名

名称は次のとおりとする。

| 項目 | 値 |
|---|---|
| 製品名 | Book Manager |
| 内部パッケージ名 | `book-manager` |
| 実行ファイル名 | `BookManager.exe` |
| 出力ディレクトリ名 | `BookManager` |
| specファイル名 | `book_manager.spec` |
| 中間ZIP名 | `BookManager-2.0.0-windows-x64.zip` |
| 会社名・発行者名 | `daikya` |

ファイル名には空白を使用せず、画面上の製品名には必要に応じて空白を使用する。

---

## 7. 追加するファイル構成

実装後の関連構成は次のとおりとする。

```text
book_manager\
├── assets\
│   └── windows\
│       └── book_manager.ico
├── packaging\
│   └── pyinstaller\
│       └── book_manager.spec
├── scripts\
│   └── build_windows.ps1
├── src\
│   └── book_manager\
│       └── config\
│           └── paths.py
├── tests\
│   └── config\
│       └── test_paths.py
├── docs\
│   └── windows_distribution_design.md
├── main.py
├── pyproject.toml
├── requirements.txt
└── requirements-build.txt
```

`assets/windows/book_manager.ico`はアプリケーション本体の静的資源であり、Git管理対象とする。

---

## 8. 依存関係の管理

### 8.1 現状の課題

現在の`requirements.txt`には、実行時依存関係とテスト用依存関係が混在している。また、`pyproject.toml`の`dependencies`は空である。

この状態でもビルドは可能だが、アプリケーション実行に必要な依存関係と、開発・テスト・ビルドだけに必要な依存関係を区別しにくい。

### 8.2 Version 2.0での扱い

実行ファイル作成では、既存開発環境への影響を抑えるため、次の段階で整理する。

1. 現在の`requirements.txt`は直ちに大きく再編しない。
2. PyInstaller専用に`requirements-build.txt`を追加する。
3. 使用したPyInstallerのVersionを固定する。
4. 実行時依存関係と開発用依存関係の本格的な分離は、ビルド成功後に別コミットで検討する。

`requirements-build.txt`は、少なくとも次の形式とする。

```text
pyinstaller==<動作確認済みVersion>
```

Version番号は、実際にWindowsでインストールし、ビルドと動作確認に成功したVersionへ固定する。未検証の最新版を設計段階で固定しない。

### 8.3 ビルド環境

正式ビルドは、次の条件を満たすWindows環境で行う。

* 64ビット版Windows
* 64ビット版Python 3.11
* プロジェクト専用仮想環境
* `requirements.txt`を導入済み
* `requirements-build.txt`を導入済み
* 全pytestが成功する状態

Windows用実行ファイルはWindows上で作成する。別OS上でのクロスビルドは行わない。

---

## 9. specファイル

### 9.1 配置

specファイルは次へ配置する。

```text
packaging/pyinstaller/book_manager.spec
```

ルート直下へ自動生成されたspecファイルをそのまま残さず、正式な設定ファイルとして上記へ配置する。

### 9.2 基本設定

specファイルでは、少なくとも次を明示する。

* エントリーポイント：`main.py`
* ソース探索パス：`src`
* 実行ファイル名：`BookManager`
* `console=False`
* `onedir`形式
* Windowsアイコン
* Windows Version情報
* UPX無効
* 必要なデータファイル
* 必要なhidden import

### 9.3 パス解決

specファイル内のパスは、コマンドを実行したカレントディレクトリだけに依存させない。

ビルドスクリプトはリポジトリルートを明示してPyInstallerを実行し、specファイルではプロジェクトルートと`src`を正規化して使用する。

### 9.4 hidden import

最初のビルドでは、不要なhidden importを推測で大量追加しない。PyInstaller標準hookによる検出結果を利用し、実際のビルド警告または実行時エラーで不足が確認されたものだけを追加する。

確認対象は次のとおりである。

* `PIL.Image`
* `PIL.ImageTk`
* `requests`
* `certifi`
* Tkinter / Tcl / Tk

### 9.5 データファイル

Version 2.0の現行実装では、アプリケーション起動に必要な独自データファイルは原則として存在しない。

次はデータファイルとして同梱しない。

* `data/books.db`
* `backups`配下のファイル
* `cache/covers`配下のファイル
* `.env`
* `config.local.json`
* テストデータ
* 設計書
* Git管理情報

アイコンは実行ファイルのVersion資源として使用するが、実行時に外部ファイルとして読み込む必要がなければ、別ファイルとして配布先へコピーしない。

### 9.6 UPX

Version 2.0ではUPXを使用しない。

圧縮よりも、ビルドの単純さ、調査のしやすさおよび誤検知リスクの低減を優先する。

---

## 10. アプリケーションアイコン

### 10.1 形式

Windows実行ファイル用に、次のICOファイルを用意する。

```text
assets/windows/book_manager.ico
```

ICOには複数サイズを含める。

* 16×16
* 24×24
* 32×32
* 48×48
* 64×64
* 128×128
* 256×256

### 10.2 用途

同じアイコンを、次で使用する。

* `BookManager.exe`
* Tkinterメインウィンドウ
* 後続のインストーラー
* スタートメニューショートカット
* 必要に応じてデスクトップショートカット

### 10.3 未準備時の扱い

アイコンが完成する前は、PyInstallerの既定アイコンで試験ビルドしてよい。ただし、正式なVersion 2.0成果物は専用アイコンを組み込んで作り直す。

アイコン作成と組み込みは、実行ファイル化と分けてコミットできる。

---

## 11. Version情報

### 11.1 正式なVersion源

アプリケーションVersionの正式な管理元は`pyproject.toml`とする。

```toml
[project]
version = "2.0.0"
```

ビルド用スクリプトは`pyproject.toml`からVersionを読み取り、ZIP名およびWindows Version情報へ反映する。

### 11.2 Windows Version資源

`BookManager.exe`には、少なくとも次を設定する。

| 項目 | 値 |
|---|---|
| FileDescription | Book Manager |
| ProductName | Book Manager |
| CompanyName | daikya |
| InternalName | BookManager |
| OriginalFilename | BookManager.exe |
| FileVersion | `pyproject.toml`のVersion |
| ProductVersion | `pyproject.toml`のVersion |

Version資源ファイルをビルド時に生成する場合、生成物は一時ビルド領域へ置き、Git管理対象にしない。生成処理自体はビルドスクリプトへ記録する。

### 11.3 アプリケーション内表示

Version 2.0では、利用者が実行中のVersionを確認できる手段を用意する。

候補は「バージョン情報」ダイアログである。表示値をソースへ重複して直接記述せず、パッケージメタデータまたはビルド時に生成した単一のVersion情報から取得する。

PyInstallerでパッケージメタデータを利用する場合は、specファイルで必要なmetadataを同梱する。

---

## 12. 配布版のパス

### 12.1 利用者データパス

配布版でも、既定の利用者データルートは次とする。

```text
%LOCALAPPDATA%\book_manager
```

`ApplicationPaths`を利用し、実行ファイルの配置先、作業ディレクトリおよびPyInstaller内部ディレクトリを利用者データ保存先にしない。

### 12.2 アプリケーション資源パス

アプリケーション本体に同梱する読み取り専用資源と、利用者が作成する書き込み可能データを明確に分ける。

| 種別 | 基準 |
|---|---|
| 利用者データ | `ApplicationPaths.root_directory` |
| PyInstaller同梱資源 | 実行時のbundle基準パス |
| 実行ファイル位置 | `Path(sys.executable).parent` |
| ソース版プロジェクト資源 | リポジトリルート |

現在は外部読み込みが必要な独自資源がないため、bundle基準パスを直ちに追加する必要はない。将来、画像や設定テンプレートを同梱する場合に専用関数を追加する。

### 12.3 旧データ探索

配布版は、利用者のホームディレクトリやドライブ全体を探索しない。

Version 1.9以前には正式インストーラーが存在しないため、既存利用者はVersion 2.0のソース版を旧プロジェクトルートから一度起動して移行するか、文書化された手動移行を行う。

PyInstaller内部の`__file__`や`_internal`ディレクトリを、旧データの一般的な探索起点として使用しない。配布版で旧データを一意に特定できない場合は、新規利用として扱う。

### 12.4 `BOOK_MANAGER_HOME`

環境変数`BOOK_MANAGER_HOME`による保存先上書きは、開発、テストおよび障害調査用として配布版でも維持する。

一般利用者向けの通常手順では設定を要求しない。

---

## 13. ログ出力

### 13.1 必要性

正式配布版は`console=False`で作成するため、現在の`traceback.print_exc()`だけでは、起動エラーや通信エラーの詳細を利用者が確認できない。

そのため、実行ファイル化の前にファイルログを追加する。

### 13.2 保存先

ログは次へ保存する。

```text
%LOCALAPPDATA%\book_manager\logs\book_manager.log
```

`ApplicationPaths`へ次を追加する。

* `log_directory`
* `log_path`

`ensure_application_directories()`で`log_directory`を作成する。

### 13.3 記録対象

少なくとも次を記録する。

* アプリケーション起動
* アプリケーションVersion
* データ移行の判定結果
* データ移行の警告と例外
* データベース初期化失敗
* 自動バックアップ失敗
* GUI構築前後の致命的例外
* 捕捉されなかった例外

### 13.4 記録しない情報

次はログへ記録しない。

* Google Books APIキー
* 書籍の内容紹介や備考の全文
* CSV内容の全文
* 通信レスポンス本文の全文
* 認証情報や環境変数一覧

### 13.5 ローテーション

ログが無制限に増加しないよう、サイズによるローテーションを採用する。

初期値は次を目安とする。

* 1ファイル最大：1 MiB
* 世代数：3
* 文字コード：UTF-8

ログの正確な値は実装時にテストで固定する。

### 13.6 利用者向け案内

致命的エラーダイアログには、内部例外をそのまま表示しない。次の趣旨を表示する。

```text
アプリケーションを起動できませんでした。
詳細はログファイルを確認してください。
```

ログファイルの場所も案内できるようにする。

---

## 14. ビルドスクリプト

### 14.1 配置

```text
scripts/build_windows.ps1
```

### 14.2 責務

ビルドスクリプトは、次を順番に実行する。

1. Windows上で実行されていることを確認する。
2. リポジトリルートを決定する。
3. 仮想環境のPythonを使用していることを確認する。
4. `pyproject.toml`からVersionを読み取る。
5. PyInstallerをimportできることを確認する。
6. 全pytestを実行する。
7. 対象を限定して旧`build`および`dist/BookManager`を削除する。
8. Windows Version資源を一時生成する。
9. specファイルからPyInstallerを実行する。
10. `dist/BookManager/BookManager.exe`の存在を確認する。
11. 開発用データが混入していないことを確認する。
12. 必要に応じてZIPを作成する。
13. SHA-256チェックサムを作成する。
14. 成果物のパスとVersionを表示する。

### 14.3 実行方法

リポジトリルートから次のように実行する。

```powershell
.\scripts\build_windows.ps1
```

試験時間を短縮する目的でpytestを省略できるオプションを用意する場合でも、正式ビルドでは省略しない。

### 14.4 削除対象

スクリプトが自動削除してよい対象は、リポジトリ内の次の生成物に限定する。

* `build/pyinstaller`
* `dist/BookManager`
* 当該Version用の中間ZIP
* 当該Version用のチェックサム

利用者データ、`%LOCALAPPDATA%\book_manager`、リポジトリの`data`、`backups`および`cache`は削除しない。

---

## 15. ビルド成果物

### 15.1 PyInstaller成果物

```text
dist\
└── BookManager\
    ├── BookManager.exe
    └── _internal\
        ├── Pythonランタイム
        ├── Tcl/Tk
        ├── Pillow関連ファイル
        ├── Requests関連ファイル
        ├── CA証明書
        └── その他の依存DLL
```

PyInstallerのVersionにより内部構成は変わり得るため、個々の内部ファイル名を恒久的な仕様にはしない。

### 15.2 中間ZIP

インストーラー作成前の検証用として、`dist/BookManager`全体をZIP化してよい。

```text
dist\BookManager-2.0.0-windows-x64.zip
```

ZIPを展開したとき、トップレベルに`BookManager`ディレクトリが1つ存在する構成とする。

このZIPは検証用の中間成果物であり、Version 2.0 GitHub Releaseで必ず公開するものではない。

### 15.3 チェックサム

中間ZIPおよび後続のインストーラーにはSHA-256チェックサムを作成する。

```powershell
Get-FileHash `
    .\dist\BookManager-2.0.0-windows-x64.zip `
    -Algorithm SHA256
```

---

## 16. 配布物へ含めてはならないもの

ビルド後、次が`dist/BookManager`に含まれていないことを自動または目視で確認する。

* `data/books.db`
* `data/book_manager.db`
* `*.db-wal`
* `*.db-shm`
* `backups`ディレクトリ
* 実データを含む`cache/covers`
* `.env`
* `config.local.json`
* `GOOGLE_BOOKS_API_KEY`
* `tests`ディレクトリ
* `.git`ディレクトリ
* `.venv`ディレクトリ
* ログファイル
* 利用者名を含む設定ファイル

APIキーは実行ファイルへ埋め込まない。環境変数が設定されていない場合も、現在のフォールバック方針により利用可能な範囲で動作させる。

---

## 17. Git管理方針

### 17.1 Git管理対象

次はGit管理対象とする。

* `packaging/pyinstaller/book_manager.spec`
* `scripts/build_windows.ps1`
* `requirements-build.txt`
* `assets/windows/book_manager.ico`
* ログ機能のソースコードとテスト
* 実行ファイル化に必要なソースコード修正とテスト
* 本設計書

### 17.2 Git管理対象外

次はGit管理対象外とする。

* `build/`
* `dist/`
* PyInstallerの一時ファイル
* 生成したWindows Version資源
* 生成したZIP
* 生成したチェックサム
* PyInstaller警告ファイル

既存の`.gitignore`では`build/`と`dist/`が除外されている。追加の一時生成先を設ける場合だけ、必要な除外規則を追加する。

---

## 18. コンソール非表示と例外処理

### 18.1 正式ビルド

正式ビルドでは`console=False`を設定し、起動時にコンソールウィンドウを表示しない。

### 18.2 調査用ビルド

初回の問題調査では、一時的に`console=True`の調査用ビルドを作成してよい。ただし、正式成果物とファイル名または出力先を区別し、誤配布しない。

### 18.3 起動前例外

Tkinterのルート生成前に例外が発生した場合も、次のいずれかで原因を確認できるようにする。

* ファイルログ
* 致命的エラーダイアログ
* 調査用コンソールビルド

ログ初期化そのものに失敗した場合は、ダイアログだけで安全に終了する。

---

## 19. 自動テスト

実行ファイル化に伴い、少なくとも次を自動テストする。

### 19.1 パス

* ログディレクトリとログファイルパスを生成できる。
* 必要なログディレクトリを作成できる。
* 利用者データパスが実行場所に依存しない。
* `BOOK_MANAGER_HOME`による明示指定が維持される。

### 19.2 ログ

* ログ設定を初期化できる。
* 例外情報をログへ記録できる。
* ログをローテーションできる。
* ログ初期化失敗時に起動処理が予期せず再帰しない。
* APIキーなどの秘密情報を意図的に出力しない。

### 19.3 起動

* ソース版の`main()`が従来どおり起動処理を組み立てる。
* 移行処理がDB初期化より前に行われる。
* 配布版を想定した実行環境でも利用者データパスが変わらない。
* 起動中の致命的例外をログへ記録して終了できる。
* 自動バックアップ失敗は警告し、アプリケーションを継続できる。

### 19.4 ビルドスクリプト

ビルドスクリプトのすべてをpytestで検証する必要はないが、Version読み取りや成果物検査などをPython関数へ分離した場合は単体テストを追加する。

最終的には、既存テストを含む全pytestを実行する。

```powershell
pytest -q
```

---

## 20. ビルド後の検査

### 20.1 静的検査

ビルド直後に次を確認する。

1. `BookManager.exe`が存在する。
2. `BookManager.exe`以外の必要ファイルが`_internal`へ存在する。
3. 実行ファイルのアイコンが設定されている。
4. ファイルのプロパティに正しいVersionが表示される。
5. 利用者DBやバックアップが含まれていない。
6. APIキーや`.env`が含まれていない。
7. PyInstallerの警告ファイルを確認した。
8. ZIP内のディレクトリ構成が正しい。
9. SHA-256チェックサムを取得できる。

### 20.2 依存関係検査

ビルドした環境の仮想環境を有効にしていない状態で、`BookManager.exe`を起動する。

Pythonやプロジェクトソースへの偶発的な依存を避けるため、`dist/BookManager`をリポジトリ外の一時確認用ディレクトリへコピーして実行する。

---

## 21. Windows実環境での確認

### 21.1 新規利用相当

既存の実データを変更せずに新規利用を確認するため、`BOOK_MANAGER_HOME`へ専用の一時確認用ディレクトリを指定する。

確認項目は次のとおりである。

1. Pythonを直接起動せず`BookManager.exe`から起動できる。
2. コンソールウィンドウが表示されない。
3. 指定した利用者データディレクトリが作成される。
4. 空のデータベースが初期化される。
5. 書籍を新規登録できる。
6. 書籍情報を更新・削除できる。
7. 検索と並べ替えができる。
8. お気に入り、評価および読書状態を利用できる。
9. タグを登録・設定・絞り込みできる。
10. 読書履歴を登録・更新・削除できる。
11. 読書集計を表示できる。
12. 外部書誌情報を取得できる。
13. 表紙画像を取得して再起動後も表示できる。
14. CSVをエクスポート・インポートできる。
15. バックアップと復元ができる。
16. 再起動後も登録データを利用できる。
17. ログファイルが所定の場所に作成される。

確認用ディレクトリは、実データの`%LOCALAPPDATA%\book_manager`と混同しない明示的なパスを使用する。

### 21.2 既存利用者データ

既にソース版で新保存先への移行が完了している環境では、次を確認する。

1. 配布版が`%LOCALAPPDATA%\book_manager\data\books.db`を参照する。
2. 移行完了メッセージが再表示されない。
3. 既存の書籍24件が表示される。
4. 表紙画像が表示される。
5. タグ、読書履歴および読書集計を利用できる。
6. 既存バックアップを一覧・復元できる。
7. 配布版で変更した内容をソース版でも確認できる。
8. ソース版で変更した内容を配布版でも確認できる。

### 21.3 実データ保護

実データを使う確認の前に、最新バックアップが存在することを確認する。

削除や復元などの破壊的操作は、`BOOK_MANAGER_HOME`で分離した確認用データを使って行う。実データでは、参照、登録、軽微な更新および再起動確認を中心とする。

### 21.4 Python未導入相当

正式確認では、次のいずれかを使用する。

* Pythonを導入していない別のWindows端末
* Windows Sandbox
* 新規Windows仮想マシン

確認環境へは、`dist/BookManager`または中間ZIPだけを渡す。プロジェクトソース、仮想環境および開発用環境変数は渡さない。

Windows Sandboxは終了時に状態が消えるため、新規起動確認には適しているが、更新・アンインストール・再インストールの一連確認には永続的な仮想マシンまたは別端末を使用する。

---

## 22. セキュリティと安全性

### 22.1 秘密情報

`GOOGLE_BOOKS_API_KEY`をspecファイル、ビルドスクリプト、実行ファイルまたは設定ファイルへ埋め込まない。

ビルド時の環境変数を列挙または成果物へ保存しない。

### 22.2 利用者データ

PyInstallerは、リポジトリ全体をデータファイルとして収集しない。必要な静的資源だけを明示する。

実データが配布物へ混入していないことを、ファイル名だけでなく拡張子とディレクトリ名でも検査する。

### 22.3 外部通信

Requestsが使用するCA証明書を確実に同梱し、TLS証明書検証を無効化しない。

外部APIへの通信失敗は、既存の例外処理方針に従って利用者へ案内する。

### 22.4 未署名実行ファイル

Version 2.0ではコード署名証明書を必須としないため、Windowsまたはブラウザーが未署名アプリケーションとして警告する可能性がある。

警告を回避するためにセキュリティ機能を恒久的に無効化する手順は案内しない。GitHub Release、ファイル名、VersionおよびSHA-256チェックサムにより、取得元と同一性を確認できるようにする。

---

## 23. 障害時の調査

### 23.1 起動しない場合

次の順で確認する。

1. `%LOCALAPPDATA%\book_manager\logs\book_manager.log`
2. Windowsのエラーダイアログ
3. PyInstallerビルド時の警告ファイル
4. `console=True`の調査用ビルド
5. Windowsイベントビューアー

### 23.2 外部通信だけ失敗する場合

次を確認する。

* CA証明書が同梱されている。
* Requestsとurllib3が正しく含まれている。
* プロキシまたはセキュリティソフトの影響がない。
* APIキーを必要としないフォールバックが動作する。

### 23.3 画像だけ表示されない場合

次を確認する。

* PillowとImageTkが含まれている。
* Tcl/Tkが含まれている。
* `cover_image_path`が利用者データルート基準で解決されている。
* `%LOCALAPPDATA%\book_manager\cache\covers`を参照している。
* 旧絶対パスとの互換処理が維持されている。

### 23.4 配布版だけデータが空の場合

次を確認する。

* `BOOK_MANAGER_HOME`が意図せず設定されていない。
* `%LOCALAPPDATA%`が想定した利用者を指している。
* 実行ファイル位置へ空DBを作成していない。
* ソース版と配布版が同じ`ApplicationPaths`を使用している。

---

## 24. インストーラー工程への引き渡し

次をすべて満たした後、Windowsインストーラーの詳細設計へ進む。

* `onedir`ビルドが再現可能である。
* `BookManager.exe`を直接起動できる。
* コンソールウィンドウが表示されない。
* 専用アイコンとVersion情報が表示される。
* 利用者データが`%LOCALAPPDATA%\book_manager`へ保存される。
* 開発用データが配布物へ含まれない。
* ファイルログで障害調査できる。
* Python未導入相当の環境で起動できる。
* 主要機能の実画面確認が完了している。
* 全pytestが成功している。

インストーラーは`dist/BookManager`ディレクトリ全体をアプリケーション本体として取り込む。

---

## 25. 実装順序

実装は次の順序で進める。

1. 本設計書を確定する。
2. 本設計書をコミットする。
3. `ApplicationPaths`へログ保存先を追加する。
4. ログ初期化処理と自動テストを追加する。
5. 起動時例外と主要警告をログへ記録する。
6. 全pytestで回帰がないことを確認する。
7. PyInstallerをWindows仮想環境へ導入する。
8. 動作確認済みPyInstaller Versionを`requirements-build.txt`へ固定する。
9. 専用アイコンを用意する。
10. Version情報の生成方法を実装する。
11. `book_manager.spec`を作成する。
12. `build_windows.ps1`を作成する。
13. `onedir`形式で試験ビルドする。
14. PyInstaller警告を確認し、必要な依存物だけを追加する。
15. リポジトリ外へコピーして配布版を起動する。
16. `BOOK_MANAGER_HOME`を使用して新規利用相当の確認を行う。
17. 既存の利用者データを使用して互換性を確認する。
18. Python未導入相当のWindows環境で確認する。
19. ZIPとSHA-256チェックサムを試験作成する。
20. インストーラー設計へ進む。

---

## 26. コミット計画

### 26.1 配布設計

対象：

```text
docs/windows_distribution_design.md
```

コミット例：

```text
docs: Windows実行ファイル作成の設計を追加する
```

### 26.2 ログ基盤

対象例：

```text
src/book_manager/config/paths.py
src/book_manager/config/logging.py
tests/config/test_paths.py
tests/config/test_logging.py
main.py
tests/test_main.py
```

コミット例：

```text
feat: 配布版向けのファイルログを追加する
```

標準ライブラリの`logging.py`と名前が衝突する懸念がある場合は、`logging_config.py`などの明確な名前を使用する。

### 26.3 アイコン

対象例：

```text
assets/windows/book_manager.ico
src/book_manager/gui/book_manager_application.py
```

コミット例：

```text
feat: アプリケーションアイコンを追加する
```

### 26.4 PyInstaller設定

対象例：

```text
requirements-build.txt
packaging/pyinstaller/book_manager.spec
scripts/build_windows.ps1
.gitignore
```

コミット例：

```text
build: Windows実行ファイルのビルド設定を追加する
```

プロジェクトで`build:`プレフィックスを採用しない場合は、既存規約に合わせて次を使用する。

```text
chore: Windows実行ファイルのビルド設定を追加する
```

### 26.5 ビルド調整

依存関係や資源同梱の修正が必要な場合は、内容に応じて独立したコミットとする。

```text
fix: Windows配布版の依存ファイルを補完する
```

---

## 27. 完成条件

Windows実行ファイル作成は、次をすべて満たした時点で完成とする。

* [x] PyInstallerの動作確認済みVersionが固定されている。
* [x] specファイルから`onedir`ビルドを再現できる。
* [x] PowerShellスクリプトから正式ビルドを実行できる。
* [x] Pythonを直接起動せず`BookManager.exe`を起動できる。
* [ ] Python未導入相当のWindows環境で起動できる。
* [x] コンソールウィンドウが表示されない。
* [x] Tkinter、SQLite、Pillow、RequestsおよびCA証明書が利用できる。
* [x] アプリケーション名、Versionおよびアイコンが正しく表示される。
* [x] 利用者データが`%LOCALAPPDATA%\book_manager`へ保存される。
* [x] ソース版と配布版が同じ利用者データを参照できる。
* [x] 開発用DB、バックアップ、表紙画像および秘密情報が配布物へ含まれない。
* [x] 配布版の例外詳細をファイルログで確認できる。
* [ ] 新規利用相当の環境で主要機能を利用できる。
* [x] 既存利用者データで主要機能を利用できる。
* [x] ZIPとSHA-256チェックサムを作成できる。
* [x] 関連するfocused pytestがすべて成功する。
* [x] 全pytestが成功する。
* [x] Windows実環境で主要操作を確認する。
* [x] 既存機能に回帰がない。
* [x] インストーラー工程へ渡せる`dist/BookManager`が完成している。

### 27.1 実装・検証結果

Windows実行ファイル作成工程では、次を完了した。

* PyInstaller 6.22.2と`pyinstaller-hooks-contrib` 2026.7をビルド用依存関係として固定した。
* `packaging/pyinstaller/book_manager.spec`と`scripts/build_windows.ps1`を追加し、`onedir`形式の正式ビルドを再現可能にした。
* `pyproject.toml`を基準とするWindows Version情報生成処理を追加した。
* Windows実行ファイルとTkinter GUIへ共通の専用アイコンを設定した。
* `%LOCALAPPDATA%\book_manager\logs\book_manager.log`へローテーション付きログを記録できるようにした。
* 検証用ZIPとSHA-256チェックサムを生成し、チェックサムの一致を確認した。
* PyInstaller警告ファイルを確認し、列挙された項目が任意依存または対象外プラットフォーム向けであることを確認した。
* プロジェクト外の一時フォルダーへZIPを展開し、既存データ、表紙画像、主要機能、専用アイコンおよびログをWindows実環境で確認した。
* 自動バックアップは、前回作成から24時間未満の場合に仕様どおり省略されることを確認した。
* 全1092件の自動テストが成功した。

Python未導入相当の新規環境での確認は、インストーラー工程と合わせて実施する。この確認が完了するまでは、本設計の完成条件をすべて達成したものとは扱わない。

---

## 28. 正式な設計判断

Version 2.0のWindows実行ファイル作成では、次を正式な設計判断とする。

1. PyInstallerを使用する。
2. 正式なビルド方式は`onedir`とする。
3. 実行ファイル名は`BookManager.exe`とする。
4. 正式ビルドではコンソールを表示しない。
5. specファイルとPowerShellスクリプトをGit管理する。
6. PyInstallerはWindows上の専用仮想環境で実行する。
7. 動作確認済みPyInstaller Versionを固定する。
8. 利用者データは配布物へ含めない。
9. 利用者データは`%LOCALAPPDATA%\book_manager`へ保存する。
10. 配布版は利用者のディレクトリを広範囲に探索しない。
11. `data`、`backups`、`cache`および`logs`をインストール先へ作成しない。
12. Requestsの証明書検証を無効にしない。
13. APIキーを実行ファイルへ埋め込まない。
14. 配布版向けにローテーション付きファイルログを追加する。
15. Windows Version情報は`pyproject.toml`のVersionを基準に生成する。
16. 専用ICOを実行ファイルとGUIで共通使用する。
17. UPXは使用しない。
18. 中間ZIPは検証用とし、正式公開を必須にしない。
19. ビルド後に配布物への実データ混入を検査する。
20. Python未導入相当のWindows環境で確認してからインストーラー工程へ進む。

---

**Version 2.0 Windows配布方針：利用者データを本体から分離したまま、再現可能な`onedir`ビルドによって、安全に導入できるWindowsアプリケーションの土台を作る。**
