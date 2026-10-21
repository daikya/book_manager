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
- 通常版のアンインストール登録の内容比較と、通常版への上書きインストールは別途確認する。
- 今回の成果物は版番号2.6.0の開発版。正式2.7.0の再ビルド・最終確認・公開は未実施。
