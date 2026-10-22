# 著者管理を含む配布版の検証

公開済みVersion 2.7.0のDB（Schema 8）から、著者管理を含む開発版（Schema 9）への移行を確認する。版番号は検証中は現在値を使用する。正式公開用の版番号変更は検証後に行う。2026年10月22日の検証専用インストーラーまでの確認は完了。最終結果は末尾に記録する。

## 確認済みのソース版

- 2026年10月22日、Windowsで全2308件＋13 subtests成功。
- 著者管理・複数著者選択・関連付け・著者ID検索・未関連書籍の整理・検索付き著者統合を実機確認済み。
- 書影の実領域への縮小・サイズ変更時の再描画と、原著者名の新規著者登録への引き継ぎを実機確認済み（3e6e292）。
- ソース版確認時点では配布版の検証は未完了だったが、その後の結果を本書末尾に記録した。

## 1. ビルド

プロジェクト直下で仮想環境を有効にする。起動中のBook Managerと、dist内のEXEは終了する。

```powershell
python -m pytest -q tests/test_verify_v27_database_migration.py
if ($LASTEXITCODE -ne 0) { throw "移行検証スクリプトのテストに失敗しました。" }

python -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "アプリの依存関係の準備に失敗しました。" }

python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "ビルド用依存関係の準備に失敗しました。" }

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& .\scripts\build_windows.ps1 -SkipArchive
```

build_windows.ps1内で全体テストを実行する。今回追加したスクリプトのテストは8件。成功時の全体件数は2316件＋13 subtests。生成先はdist\BookManager\BookManager.exe。フォルダー配布物での検証を先に行い、インストーラーは後の工程で確認する。

## 2. 実利用DBのコピーで移行を検証

元DBに対しては読取専用接続だけを使用する。アプリをすべて終了し、次のコマンドを実行する。

```powershell
$sourceDb = (Read-Host "Version 2.7.0のDBパス（通常保存先ならEnter）").Trim('"')
if ([string]::IsNullOrWhiteSpace($sourceDb)) {
    $sourceDb = Join-Path $env:LOCALAPPDATA "book_manager\data\books.db"
}
$authorMigrationHome = Join-Path $env:TEMP (
    "book_manager_author_migration_" + (Get-Date -Format "yyyyMMdd_HHmmss")
)
$previousBookManagerHome = $env:BOOK_MANAGER_HOME

try {
    python scripts/verify_v27_database_migration.py `
        --mode prepare `
        --source-db "$sourceDb" `
        --work-dir "$authorMigrationHome"
    if ($LASTEXITCODE -ne 0) { throw "移行検証用DBの準備に失敗しました。" }

    $env:BOOK_MANAGER_HOME = $authorMigrationHome
    Write-Host "移行検証用保存先: $authorMigrationHome"
    $exePath = Join-Path $PWD.Path "dist\BookManager\BookManager.exe"
    if (-not (Test-Path -LiteralPath $exePath)) { throw "検証するEXEが見つかりません。" }
    $app = Start-Process -FilePath $exePath -PassThru -Wait
    if ($app.ExitCode -ne 0) { throw "EXEの実行に失敗しました。終了コード: $($app.ExitCode)" }

    python scripts/verify_v27_database_migration.py `
        --mode verify `
        --work-dir "$authorMigrationHome"
    if ($LASTEXITCODE -ne 0) { throw "移行後の照合に失敗しました。検証レポートを確認してください。" }
}
finally {
    if ($null -eq $previousBookManagerHome) {
        Remove-Item Env:BOOK_MANAGER_HOME -ErrorAction SilentlyContinue
    }
    else {
        $env:BOOK_MANAGER_HOME = $previousBookManagerHome
    }
}
```

**この初回起動では既存データの閲覧だけ行い、書籍・著者の登録、更新、削除やデータ復元は行わない。** 著者3テーブルが空で追加され、原著者名を自動分割・自動関連付けしていないことも検査するため。

閲覧項目：起動、既存書籍の件数・著者名・参照ISBN・読書年月・タグ・履歴、キャッシュがある書影。移行の照合前に書誌情報の再取得は行わない。

書影キャッシュは元DBが通常のdataディレクトリ内にある場合にコピーする。バックアップDBを指定した場合はキャッシュをコピーしない。元DBがキャッシュを絶対パスで参照している場合は既存パスからの読取表示になる。

### 照合内容

- Schema 8→9。
- 元DBのSHA-256が不変。
- 既存全テーブルの列・全行のハッシュ・件数とsqlite_sequenceが不変。
- 新しいauthors、author_aliases、book_item_authorsが存在し、すべて0件。
- DB整合性検査・外部キー検査の成功。
- schema_backups/before_v8_to_v9_*.dbの内容が移行前DBと一致。

検証用保存先にはauthor_migration_baseline.jsonとauthor_migration_verification_report.jsonを保存する。レポートにパス・テーブル別件数・照合結果を記録し、書籍名や著者名の一覧は保存しない。

元DBが既にSchema 9だった場合、prepareは停止する。DBを8へ書き戻さず、元データ保存先のdata/schema_backupsにある実際のbefore_v8_to_v9_*.dbを指定して検証する。存在しない場合は移行元を別途確認する。

## 3. 移行照合PASS後の工程

1. 移行済み検証用保存先を再利用し、EXEで著者登録・原名引き継ぎ・関連付け・検索・整理・統合・書影表示を確認する。
2. 著者・別名・関連を含む完全データZIPを出力し、別の空の検証用保存先へ復元する。件数だけでなく、同姓同名の識別メモ・別名・共著順・原著者名を照合する。
3. バックアップ作成・変更・復元で著者情報と関連が戻ることを確認する。
4. 検証専用インストーラーでの起動・同操作・アンインストール後のデータ保持を確認する。
5. 結果記録と版番号更新、正式配布物の再ビルド・更新確認後に公開する。

著者データを追加したあとは、初回移行用verifyは期待どおりFAILになるため再利用しない。初回のPASSレポートを保持し、以後の検証は別の記録として扱う。

## 2026年10月22日のEXE確認結果

- Windowsで全2316件＋13 subtests成功、最新ソースのEXEビルド成功。
- 通常利用DBのコピーでSchema 8→9の移行照合PASS。書籍31件、履歴30件、タグ7件、タグ関連43件を保持。新しい著者3テーブルは0件。元DBのSHA-256不変、移行前バックアップ1件の一致を確認。
- 移行照合の保存先：`C:\Users\takesuzu\AppData\Local\Temp\book_manager_author_migration_20261022_134422`。
- そのコピーでEXEの著者管理・関連付け・検索・整理・統合・書影と画面配置の実機6項目を確認済み。
- 操作確認済み保存先：`C:\Users\takesuzu\AppData\Local\Temp\book_manager_author_exe_20261022_134638`。

## 4. EXEによる完全データZIP出力・復元の照合

追加スクリプト：`scripts/verify_author_package_restore.py`。テスト：`tests/test_verify_author_package_restore.py`（11件）。このスクリプト追加でEXEの再ビルドは必要ない。

prepareは操作確認済みDBを読取専用で記録し、`work-dir/restore_home/data/books.db`へ空のSchema 9 DBを作る。元DBに著者・別名・書籍著者関連が各1件以上あることを確認する。不足していれば操作確認用EXEで登録してからprepareを実行する。

1. すべてのBook Managerを終了する。
2. `--mode prepare --source-home <操作確認済み保存先> --work-dir <新しい検証用作業先>`を実行する。
3. 操作確認済み保存先をBOOK_MANAGER_HOMEへ指定してEXEを起動する。「データ入出力 ▼」→「完全データをZIPへエクスポート」で、`work-dir/author_full_data.zip`へ出力し、終了する。この起動ではデータを編集しない。
4. `work-dir/restore_home`をBOOK_MANAGER_HOMEへ指定してEXEを起動する。「完全データZIPをインポート」でそのZIPを指定し、確認画面の件数を見て復元する。同姓同名・別名・識別メモ・共著順が表示されることを確認し、編集せず終了する。
5. `--mode verify --work-dir <検証用作業先>`で照合する。

照合内容：元DBのSHA-256不変、ZIP内8CSVと形式3、復元DBの整合性・外部キー、書籍・タグ・タグ関連・読書履歴・著者・別名・順序付き関連の全項目。各テーブルは件数と正規化した全行ハッシュで比較する。識別メモや原著者名、内容紹介、日付精度、登録・更新日時も比較に含める。同姓同名を名前で統合しない。

復元でDB内部IDは再採番されるため、書籍・タグ・著者を元のID順の連番へ対応付けて関連を比較する。sqlite_sequenceと書影キャッシュの保存パスは比較しない。書影URLは比較する。画像ファイル自体は完全データZIPに含まれないため、キャッシュ画像のコピーはこの照合には含めない。

作業先に`author_package_baseline.json`と`author_package_verification_report.json`を保存する。レポートにはテーブル別件数とハッシュを記録し、書籍名や著者名の一覧は保存しない。

### 復元照合の列順修正と今回の再照合

旧版から移行したDBではreference_isbnがALTER TABLEで末尾へ追加され、新規DBではISBNの直後に定義される。内容が同じでも物理的な列順が異なるため、照合スクリプトは列名をソートして全行を比較する。列を除外するのではなく、同じ列名に対応する値を同じ順序でハッシュ化する。

今回、元データはprepare後に別名2件→3件、著者関連7件→8件へ変更されていた。旧基準と初回FAILレポートを保持し、現在の出力元と復元先を別途照合する。

```powershell
python scripts/verify_author_package_restore.py `
    --mode compare-current `
    --work-dir "$env:TEMP\book_manager_author_zip_20261022_140307"

if ($LASTEXITCODE -ne 0) {
    throw "現在の出力元と復元先の照合に失敗しました。"
}
```

compare-currentは現在の出力元を読取専用で取得し、復元済みDBの7テーブル全項目と照合する。照合前後の元DBのハッシュとWALも確認する。元のauthor_package_baseline.jsonとauthor_package_verification_report.jsonは書き換えず、author_package_current_verification_report.jsonへ結果を保存する。`Source matches original baseline: False`はprepare後の変更を示し、`Source unchanged during comparison: True`と`Result: PASS`なら現在の出力元と復元先が一致し、照合中にも元DBが変わっていないことを示す。

## 5. 2026年10月22日の最終検証結果

| 検証 | 結果 |
| --- | --- |
| Windowsソース版の全体テスト | 2308件＋13 subtests成功 |
| 移行スクリプト追加後のWindowsビルド時全体テスト | 2316件＋13 subtests成功 |
| 修正後の復元照合スクリプト | Windowsで11件成功 |
| 最新の検証スクリプト込み全体テスト | LinuxでWindows専用モジュールの読込を補助し2327件＋13 subtests成功 |
| EXEで実利用DBのSchema 8→9移行 | PASS。既存データ・元DBハッシュ・移行前バックアップを確認 |
| EXEの著者機能・書影・画面配置 | 実機6項目成功 |
| EXEの完全データZIP出力・空DBへの復元 | 現在の出力元との全項目照合PASS |
| EXEのバックアップ作成・変更・復元 | 著者・別名・関連付けを含む全項目照合PASS |
| 検証専用インストーラー | ビルド・インストール成功。インストール版の実機4項目とデータ照合PASS |
| 検証版アンインストール | 検証版EXEなし、検証用DBあり、通常版EXEあり。アンインストール後の全項目照合PASS |

最終照合件数：書籍31件、読書履歴30件、タグ7件、タグ関連43件、著者4件、別名3件、書籍著者関連8件。書籍原著者名・識別メモ・共著順・日時等を含む7テーブルの論理内容が一致した。照合中の出力元DBは不変。

初回prepare後の出力元変更により旧基準とのハッシュは一致しない。初回FAILの記録を保持し、物理列順を正規化したcompare-currentの結果で現在の出力元と復元先の一致を確認した。

検証専用インストーラー：BookManager-Verification-2.7.0-windows-x64-setup.exe。
SHA-256：C0F5F3F79CAA7332262558E955A5EC3643B443F93D19BC89DB27345B4E0617AF。
これは著者管理を含む開発ソースから作成した検証物であり、公開済みVersion 2.7.0とは区別する。

次工程：検証スクリプト・テスト・結果記録をコミットし、正式版の版番号と公開資料を更新する。その版番号で正式配布物を再ビルドし、通常版への更新と利用者データ保持を確認してからタグ・Releaseを公開する。
