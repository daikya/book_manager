# Windowsインストーラーの検証

`& .\scripts\build_windows_installer.ps1 -VerificationBuild` で検証専用品を生成する。
EXEの再ビルドは不要。検証済みのdist/BookManagerを使用する。

- アプリ名: Book Manager Verification
- AppId: 9130FA9D-4E63-488F-AF66-2B8E41347BC5
- 初期インストール先: %LOCALAPPDATA%/Programs/BookManagerVerification
- 成果物: dist/installer/BookManager-Verification-2.6.0-windows-x64-setup.exe（Versionはpyproject.tomlから取得）
- ショートカットとインストール直後のアプリ自動起動は作成しない。
- 通常版のAppId・初期保存先・成果物名は既定ビルドで維持する。

## 実機確認

1. 検証専用setupを起動し、既定のBookManagerVerificationへインストールする。
2. BOOK_MANAGER_HOMEを既に照合成功した検証用保存先に設定し、インストール先のBookManager.exeを直接起動する。
3. 660件の表示、Excel取込画面の表示・キャンセル、候補検索・比較反映のキャンセルを確認する。取込・登録・更新・削除はしない。
4. アプリ終了後、verify_real_excel_migration.py --mode verify で全行照合する。
5. 検証版のunins000.exeからアンインストールし、通常版のEXE・アンインストール登録と、検証用DBが残ることを確認する。

同じ実行ファイルを使用するため、データ保存先の自動分離は行わない。
検証版EXEをエクスプローラーから直接起動せず、BOOK_MANAGER_HOMEを指定して起動すること。
PowerShellの環境変数は起動後finallyで復元する。
本検証はインストール・起動・アンインストール確認であり、通常版の上書き更新テストとは区別する。

## 2026年10月21日の確認結果

- 検証専用setupの生成・インストール・起動に成功。
- インストール先EXEの終了後、書籍660件・読書履歴660件の全行照合はPASS。元Excelの変更なし。
- 検証版のアンインストール後、検証版EXEは存在せず、検証用DBと通常版EXEは存在することを確認。
- 上記の検証版削除時、通常版のアンインストール登録の内容比較は未実施。通常版への上書き更新は次項で確認した。
- 上記の検証専用成果物は版番号2.6.0の開発版。正式2.7.0の結果は次項を参照。

## Version 2.7.0の通常版更新確認（2026年10月21日）

- Windows全体テスト: 2097 passed, 13 subtests passed。
- 正式ZIP・通常版インストーラー・各SHA-256ファイルの生成に成功。
- 通常利用データ全体を退避し、コピーの50ファイルをSHA-256で照合。
- 通常版への上書き更新後、起動前の利用者データ50ファイルのSHA-256がすべて一致。
- FileVersion・ProductVersionはいずれも2.7.0。
- 起動後の既存データ・設定・データ入出力メニュー・候補検索・比較画面と、通常ショートカットからの再起動を実機確認。
- GitHub Releaseでの公開は未完了。

生成時のSHA-256（公開時にも対象ファイルと照合する）：

| 成果物 | SHA-256 |
|---|---|
| BookManager-2.7.0-windows-x64.zip | 58DAA2735ACE2C42F301A7E898A352B49D4019F044ED3E4A0BF67C36617708D1 |
| BookManager-2.7.0-windows-x64-setup.exe | C0F822DB910141AFDDB7F6FAE1A164D6E9B58594C1355F0B9086212FFF4FFCEA |
