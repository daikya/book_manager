# book_manager Windowsインストーラー設計

## 1. 目的

本書は、Version 2.0で作成するWindowsインストーラーの設計を定義する。

PyInstallerで作成済みの`onedir`成果物を、Pythonや仮想環境を意識せず導入・起動できる形でWindowsへ配置する。

また、上書き更新、アンインストールおよび再インストールを行っても、書籍データ、バックアップ、表紙画像キャッシュおよびログを誤って削除しないことを最優先とする。

---

## 2. 対象Version

本設計の対象は、Version 2.0.0とする。

実装中は`pyproject.toml`のVersion 1.9.0を維持し、インストーラーの全検証が完了した後に2.0.0へ更新する。

---

## 3. 前提

本設計は、次が完了していることを前提とする。

* 利用者データ保存先が`%LOCALAPPDATA%\book_manager`へ一元化されている。
* Version 1.9以前の既存データを新保存先へ安全に移行できる。
* PyInstallerによる`onedir`ビルドを再現できる。
* `dist\BookManager\BookManager.exe`から主要機能を利用できる。
* 実行ファイル、タイトルバーおよびタスクバーへ専用アイコンを表示できる。
* 配布版のログを`%LOCALAPPDATA%\book_manager\logs`へ記録できる。
* 検証用ZIPとSHA-256チェックサムを生成できる。
* 全1092件の自動テストが成功している。

---

## 4. 使用ツール

### 4.1 採用ツール

Windowsインストーラーの作成にはInno Setupを使用する。

開発時に動作確認したVersionは次のとおりである。

```text
Inno Setup 7.1.0 64-bit
```

### 4.2 採用理由

Inno Setupは、次の要件を標準機能で扱える。

* 利用者単位の非管理者インストール
* ファイル一式の配置
* スタートメニューショートカット
* 任意のデスクトップショートカット
* 同一`AppId`による上書き更新
* アンインストール
* 専用アイコン
* Version情報
* LZMA2圧縮
* コマンドラインコンパイル

### 4.3 Version管理

Inno Setup本体はアプリケーションの実行時依存関係ではなく、開発者がインストーラーを作成するためのビルドツールとして扱う。

`requirements-build.txt`はPython向けビルド依存関係だけを管理するため、Inno Setupを記載しない。

動作確認済みVersionは、本設計書とビルドスクリプトの検証条件へ記録する。

---

## 5. 配布方式

### 5.1 正式配布物

Version 2.0の正式なWindows配布物は、次のインストーラーとする。

```text
BookManager-2.0.0-windows-x64-setup.exe
```

チェックサムは次のファイルで提供する。

```text
BookManager-2.0.0-windows-x64-setup.exe.sha256.txt
```

### 5.2 ポータブルZIP

PyInstaller工程で生成するZIPは、インストーラー作成前の検証と障害調査に利用する。

インストーラー検証後、GitHub Releaseへ同時掲載するかを最終判断する。

### 5.3 対応アーキテクチャ

Version 2.0ではWindows x64だけを正式対象とする。

32ビットWindowsとWindows on ARMのネイティブ版は対象外とする。

---

## 6. インストール方式

### 6.1 利用者単位

インストーラーは利用者単位で動作し、管理者権限を要求しない。

Inno Setupでは次を指定する。

```ini
PrivilegesRequired=lowest
```

### 6.2 インストール先

既定のインストール先は次とする。

```text
%LOCALAPPDATA%\Programs\BookManager
```

Inno Setupでは次の定数を使用する。

```ini
DefaultDirName={localappdata}\Programs\BookManager
```

### 6.3 利用者データとの分離

アプリケーション本体と利用者データは、次のように分離する。

```text
本体:
%LOCALAPPDATA%\Programs\BookManager

利用者データ:
%LOCALAPPDATA%\book_manager
```

インストーラーは利用者データ保存先へファイルを配置しない。

アンインストーラーにも、利用者データ保存先を削除する指定を追加しない。

---

## 7. アプリケーション識別子

### 7.1 AppId

上書き更新とアンインストール情報を一貫して扱うため、固定の`AppId`を使用する。

```text
{{0E99B7C8-54CB-4D31-9DE3-F36E2B6F2A8C}
```

この値はVersion間で変更しない。

### 7.2 表示名

```text
AppName=Book Manager
```

### 7.3 発行者

```text
AppPublisher=daikya
```

コード署名を行わないため、Windowsの警告画面で確認される署名済み発行者名とは異なる。

---

## 8. Version管理

### 8.1 正式なVersion源

Versionの正本は`pyproject.toml`の`project.version`とする。

次を同じ値にする。

* アプリケーションのFileVersion
* アプリケーションのProductVersion
* Inno Setupの`AppVersion`
* `VersionInfoVersion`
* `VersionInfoTextVersion`
* インストーラーのファイル名
* Gitタグ
* GitHub Release名

### 8.2 Versionの受け渡し

PowerShellビルドスクリプトが`pyproject.toml`からVersionを読み取り、Inno Setupへ定義値として渡す。

```text
--define=AppVersion=2.0.0
```

`.iss`ファイルへVersionを重複して固定記載しない。

### 8.3 ビルド前検証

Versionは、少なくとも次を満たすことを確認する。

* 空文字列ではない。
* `major.minor.patch`形式である。
* PyInstaller成果物のVersionと一致する。

---

## 9. インストール対象

### 9.1 対象ディレクトリ

次のディレクトリ以下を再帰的にインストールする。

```text
dist\BookManager\
```

### 9.2 必須ファイル

少なくとも次が存在しなければ、インストーラー作成を開始しない。

```text
dist\BookManager\BookManager.exe
dist\BookManager\_internal\
```

### 9.3 含めないもの

次をインストーラーへ含めない。

* `data\*.db`
* `backups\`
* `cache\covers\`
* `logs\`
* `.env`
* `config.local.json`
* Google Books APIキー
* テストファイル
* ソースコード
* `.git\`
* `.venv\`
* PyInstallerの`build\`

PyInstaller成果物だけを入力元とし、リポジトリ全体をワイルドカードで収集しない。

---

## 10. Inno Setup構成

### 10.1 配置先

Inno Setupスクリプトは次へ配置する。

```text
packaging\inno_setup\book_manager.iss
```

### 10.2 主要設定

```ini
[Setup]
AppId={{0E99B7C8-54CB-4D31-9DE3-F36E2B6F2A8C}
AppName=Book Manager
AppVersion={#AppVersion}
AppPublisher=daikya
DefaultDirName={localappdata}\Programs\BookManager
DefaultGroupName=Book Manager
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible
OutputDir=..\..\dist\installer
OutputBaseFilename=BookManager-{#AppVersion}-windows-x64-setup
SetupIconFile=..\..\assets\windows\book_manager.ico
UninstallDisplayIcon={app}\BookManager.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern dynamic
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
```

実際の相対パスは、`.iss`ファイルの配置場所を基準として検証する。

### 10.3 言語

Version 2.0では、日本語と英語を用意する。

```ini
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
```

### 10.4 ファイル

```ini
[Files]
Source: "..\..\dist\BookManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
```

### 10.5 デスクトップショートカット

デスクトップショートカットは既定で作成せず、利用者が選択できる任意タスクとする。

```ini
[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加アイコン:"; Flags: unchecked
```

### 10.6 ショートカット

スタートメニューショートカットは常に作成する。

```ini
[Icons]
Name: "{group}\Book Manager"; Filename: "{app}\BookManager.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Book Manager"; Filename: "{app}\BookManager.exe"; WorkingDir: "{app}"; Tasks: desktopicon
```

### 10.7 インストール後の起動

完了画面では、利用者が選択した場合だけアプリケーションを起動する。

サイレントインストールでは起動しない。

```ini
[Run]
Filename: "{app}\BookManager.exe"; Description: "Book Managerを起動する"; Flags: nowait postinstall skipifsilent
```

---

## 11. 上書き更新

### 11.1 更新判定

固定`AppId`と同じインストール先を使用し、旧Versionからの上書き更新として認識させる。

### 11.2 更新対象

更新するのはアプリケーション本体だけとする。

`%LOCALAPPDATA%\book_manager`配下は、更新処理の対象外とする。

### 11.3 実行中のアプリケーション

アプリケーションが起動中の場合は、Inno Setupのアプリケーション終了確認を利用する。

強制終了によるSQLiteデータ破損を避けるため、利用者が通常終了してから更新を継続する運用を基本とする。

### 11.4 同一Versionの再インストール

同一Versionを再インストールした場合も、本体ファイルを正常な成果物へ復元できることを確認する。

利用者データは変更しない。

---

## 12. アンインストール

### 12.1 削除対象

アンインストールでは、次を削除する。

* インストール先のアプリケーション本体
* スタートメニューショートカット
* 作成を選択したデスクトップショートカット
* Inno Setupのアンインストール情報

### 12.2 保持対象

次は削除しない。

```text
%LOCALAPPDATA%\book_manager\data\books.db
%LOCALAPPDATA%\book_manager\backups\
%LOCALAPPDATA%\book_manager\cache\covers\
%LOCALAPPDATA%\book_manager\logs\
```

### 12.3 利用者への案内

READMEとリリースノートへ、アンインストール後も利用者データが残ることを明記する。

完全削除が必要な場合の手動削除方法は案内するが、アンインストーラーから自動削除する選択肢はVersion 2.0では追加しない。

---

## 13. 再インストール

アンインストール後に同じVersionを再インストールし、保持された利用者データをそのまま利用できることを確認する。

再インストール時に既存データ移行を誤って再実行せず、新保存先のデータベースを優先する。

---

## 14. コード署名と警告

Version 2.0ではコード署名証明書を必須としない。

そのため、ダウンロード時または初回実行時に、Windows SmartScreenやブラウザーが未署名アプリケーションとして警告する可能性がある。

READMEとGitHub Releaseには、次を正確に案内する。

* 配布元が公式GitHub Releaseであることを確認する。
* SHA-256チェックサムを確認できること。
* 警告を無条件に回避するよう促さないこと。
* 不審な配布元から取得したファイルを実行しないこと。

---

## 15. ビルドスクリプト

### 15.1 配置先

```text
scripts\build_windows_installer.ps1
```

### 15.2 責務

ビルドスクリプトは次を行う。

1. Windows上で実行されていることを確認する。
2. プロジェクトルートを決定する。
3. `pyproject.toml`からVersionを取得する。
4. Version形式を検証する。
5. `dist\BookManager\BookManager.exe`の存在を確認する。
6. Inno Setup 7の`ISCC.exe`を探索する。
7. `.iss`ファイルへVersionを渡してコンパイルする。
8. インストーラーの存在を確認する。
9. SHA-256チェックサムを生成する。
10. 成果物のパスを表示する。

### 15.3 ISCC.exeの探索順序

少なくとも次を探索する。

```text
%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe
%ProgramFiles%\Inno Setup 7\ISCC.exe
%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe
%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
%ProgramFiles%\Inno Setup 6\ISCC.exe
%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
```

Version 2.0の正式な動作確認対象はInno Setup 7.1.0とする。

見つからない場合は、探索した場所と導入方法を示して停止する。

### 15.4 既存成果物

既存のインストーラーとチェックサムは、出力先とファイル名を限定して削除する。

`dist`全体や利用者データを再帰的に削除しない。

### 15.5 実行方法

```powershell
.\scripts\build_windows_installer.ps1
```

PyInstaller成果物から続けて作成する場合は、既存のWindowsビルドスクリプトを先に実行する。

---

## 16. 自動テスト

インストーラー設定とビルドスクリプトについて、少なくとも次を自動テストで確認する。

* 固定`AppId`が設定されている。
* `PrivilegesRequired=lowest`が設定されている。
* インストール先が利用者単位である。
* 利用者データ保存先をインストール対象にしていない。
* 利用者データを削除する`[UninstallDelete]`が存在しない。
* PyInstallerの`onedir`成果物だけを入力としている。
* スタートメニューショートカットが作成される。
* デスクトップショートカットが任意選択である。
* インストーラーへ専用アイコンが設定されている。
* Versionを外部定義から受け取る。
* インストーラー名へVersionとx64が含まれる。
* `ISCC.exe`の利用者単位とシステム単位の候補を探索する。
* インストーラーのSHA-256チェックサムを生成する。
* 不正なVersionや不足した`onedir`成果物で処理を停止する。
* 既存の全pytestに回帰がない。

Inno Setupの実コンパイル、インストールおよびアンインストール自体はWindows実環境で確認する。

---

## 17. Windows実環境での確認

### 17.1 ビルド

1. PyInstallerの`onedir`成果物を作成する。
2. インストーラービルドスクリプトを実行する。
3. インストーラーとSHA-256ファイルが生成されることを確認する。
4. SHA-256ファイルと実際のハッシュが一致することを確認する。
5. インストーラーのVersion情報と専用アイコンを確認する。

### 17.2 新規導入

1. Book Managerが未導入の利用者環境を用意する。
2. 管理者権限を要求せずインストールできることを確認する。
3. 既定の利用者単位フォルダーへ本体が配置されることを確認する。
4. スタートメニューから起動できることを確認する。
5. 選択した場合だけデスクトップショートカットが作成されることを確認する。
6. 初回起動で利用者データ用ディレクトリが作成されることを確認する。
7. Pythonや仮想環境なしで起動できることを確認する。

### 17.3 主要機能

インストール版で、少なくとも次を確認する。

* 書籍の登録・更新・削除・検索
* 外部書誌情報取得
* 表紙画像の取得・表示
* タグ管理
* 読書状態・お気に入り・評価
* 読書履歴
* 読書集計
* CSVエクスポート・インポート
* バックアップ・復元
* ログ出力
* 再起動後のデータ保持

### 17.4 上書き更新

1. 旧Version相当のインストール状態を用意する。
2. 書籍データと表紙画像を用意する。
3. 新しいインストーラーを実行する。
4. 本体が更新されることを確認する。
5. 利用者データが保持されることを確認する。
6. 更新後のアプリケーションを起動できることを確認する。

### 17.5 同一Versionの再インストール

1. Version 2.0.0をインストールする。
2. 同じインストーラーを再実行する。
3. インストールが正常に完了することを確認する。
4. 利用者データが保持されることを確認する。

### 17.6 アンインストール

1. Windowsの「インストールされているアプリ」からアンインストールする。
2. 本体とショートカットが削除されることを確認する。
3. `%LOCALAPPDATA%\book_manager`が残ることを確認する。
4. `books.db`、バックアップ、表紙画像およびログが残ることを確認する。

### 17.7 再インストール

1. アンインストール後に同じインストーラーを実行する。
2. アプリケーションを起動する。
3. 保持された書籍データ、タグ、読書履歴、表紙画像を利用できることを確認する。

### 17.8 Python未導入環境

Windows Sandbox、仮想マシンまたは別端末を使用し、Pythonを導入せずに次を確認する。

* インストール
* 起動
* 主要機能
* ログ
* アンインストール

実利用データをWindows Sandboxへ持ち込む場合は、複製した検証用データだけを使用する。

---

## 18. セキュリティ

* コード署名を行わないことを明示する。
* APIキーをインストーラーへ埋め込まない。
* 利用者データをインストーラーへ含めない。
* インストーラーへリポジトリ全体を収集しない。
* SHA-256チェックサムを提供する。
* インストール後に外部プログラムを無条件で実行しない。
* 管理者権限を要求しない。
* アンインストールで利用者データを削除しない。

---

## 19. Git管理

### 19.1 Git管理対象

```text
docs/windows_installer_design.md
packaging/inno_setup/book_manager.iss
scripts/build_windows_installer.ps1
tests/scripts/test_windows_installer_configuration.py
```

### 19.2 Git管理対象外

```text
dist/installer/
*.sha256.txt
```

既存の`.gitignore`で不足する場合は、生成物だけを対象として追加する。

---

## 20. 実装順序

1. 本設計書を確定する。
2. Inno Setupスクリプトを作成する。
3. 設定内容の自動テストを追加する。
4. PowerShellビルドスクリプトを作成する。
5. focused pytestを実行する。
6. PyInstaller成果物からインストーラーを作成する。
7. インストーラーとチェックサムを検査する。
8. 新規導入相当の確認を行う。
9. 同一Versionの再インストールを確認する。
10. 上書き更新を確認する。
11. アンインストール後の利用者データ保持を確認する。
12. 再インストール後のデータ再利用を確認する。
13. Python未導入環境で確認する。
14. README、CHANGELOG、ロードマップおよび本設計書へ結果を反映する。
15. Versionを2.0.0へ更新する。
16. 全pytestと最終ビルドを実行する。
17. GitタグとGitHub Releaseを公開する。

---

## 21. コミット計画

### 21.1 設計

```text
docs: Windowsインストーラーの設計を追加する
```

### 21.2 実装

```text
feat: Windowsインストーラーのビルド基盤を追加する
```

### 21.3 調整

問題が判明した場合だけ、内容に応じた独立コミットとする。

```text
fix: Windowsインストーラーの設定を修正する
```

### 21.4 文書

```text
docs: Windowsインストーラーの検証結果を反映する
```

---

## 22. 完成条件

本設計は、次をすべて満たした時点で完成とする。

* [ ] Inno Setup 7.1.0でインストーラーを再現できる。
* [ ] インストーラーが管理者権限を要求しない。
* [ ] 本体が利用者単位のフォルダーへ配置される。
* [ ] スタートメニューから起動できる。
* [ ] デスクトップショートカットを任意選択できる。
* [ ] インストーラーへ専用アイコンと正しいVersionが設定される。
* [ ] Python未導入環境でインストールして起動できる。
* [ ] 同一Versionを再インストールできる。
* [ ] 旧Version相当から上書き更新できる。
* [ ] 更新後も利用者データを利用できる。
* [ ] アンインストールで本体とショートカットが削除される。
* [ ] アンインストール後も利用者データが保持される。
* [ ] 再インストール後に保持されたデータを利用できる。
* [ ] インストーラーのSHA-256チェックサムを生成できる。
* [ ] 利用者データと秘密情報が配布物へ含まれない。
* [ ] 関連するfocused pytestがすべて成功する。
* [ ] 全pytestが成功する。
* [ ] Windows実環境で主要操作を確認する。
* [ ] 既存機能に回帰がない。

---

## 23. 正式な設計判断

Version 2.0のWindowsインストーラーでは、次を正式な設計判断とする。

1. Inno Setupを使用する。
2. 動作確認済みVersionは7.1.0とする。
3. Windows x64を正式対象とする。
4. 利用者単位でインストールする。
5. 管理者権限を要求しない。
6. 本体の既定配置先は`%LOCALAPPDATA%\Programs\BookManager`とする。
7. 固定`AppId`をVersion間で維持する。
8. スタートメニューショートカットを作成する。
9. デスクトップショートカットは任意選択とする。
10. 利用者データをインストーラーの管理対象にしない。
11. アンインストール時に利用者データを削除しない。
12. Versionの正本は`pyproject.toml`とする。
13. インストーラーとチェックサムをスクリプトから再現可能にする。
14. Version 2.0ではコード署名を必須としない。
15. Python未導入環境で確認してから正式リリースする。

---

**Version 2.0 Windowsインストーラー方針：アプリケーション本体だけを利用者単位で安全に導入・更新・削除し、利用者データはライフサイクルから独立して保持する。**
