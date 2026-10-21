# 実利用Excel全体の移行検証

2026年10月21日。元Excelは変更せず、専用DBだけを使用する。

## 添付Excelの確認結果

- シート：シート（1枚）、A～Gの7列。
- 見出し：書籍名／著者名／出版社／出版形態／開始月／読了月／あらすじ。
- 実データ：Excel 2～661行の660件。662～1369行は708行の空欄。
- 事前検査：エラー0、注意1320（読書状態の提案660、年月精度の保持660）。
- 登録予定：書籍660、読書履歴660、読了652、読書中8。タグ・タグ関連は0。
- 開始・読了年月の範囲：2004-10～2026-10。日を推測して補わない。
- 出版形態：Kindle444、Audible89、文庫72、単行本24、文庫本16、電子書籍10、新書3、大型本2。
- 全7項目が同一の実データ行に重複なし。タイトルだけの重複を除外する処理は行わない。
- ISBN・参照ISBNの列はないため未設定。出版社の「なし」や著者の「(著)」等は元の文字列として保持する。
- 既存仕様により前後の空白・末尾改行を除去する。該当セル数は書籍名24、著者438、出版社4、内容紹介70。内部の空白・改行や出版形態の表記は統一しない。
- 元Excel SHA-256：c3bf738407e1ab16ab73e477c2d17a23b9d6667ecd0e6c6597186a4d1315d538。

Linuxで実アプリのBookService・事前検査・ExcelImportService・Repository・BackupService・初期化処理を使用し、専用SQLiteへ660件を登録した。元セルから独立に作った期待値とDBを全行照合し、不一致0。書籍・履歴・ISBN等の未設定項目を検査した。SQLite integrity_check=ok、foreign_key_check=0、取込前バックアップが空DBで整合性ok、元Excelのハッシュ不変を確認した。通常利用DBはこの環境にないため、利用者の通常DBのハッシュ不変を確認したという意味ではない。

WindowsのGUIからの全件取込・照合は次の手順で行う。

## 配置

`scripts/verify_real_excel_migration.py` をプロジェクト内の同じ相対パスへ配置する。新しい依存はない。実利用Excelをリポジトリへコミットする必要はない。

## Windows GUIでの検証

1. book_managerを終了する。
2. プロジェクトフォルダーのPowerShellで、下のブロックを実行する。
3. Excelファイルのフルパスを入力する。専用の新規保存先と空DBを準備した後にGUIが開く。
4. 「データ入出力」からExcel取込を選び、同じExcelを指定する。
5. 列を下表どおりに割り当てる。読了月は「読了年月」ではなく「読了日・年月」に割り当てることで読書履歴も作成する。
6. 660件、エラー0件、注意1320件を確認して、一度だけ取り込む。
7. 一覧で件数・内容紹介・年月を確認し、編集・追加・削除せずアプリを閉じる。
8. 自動的に読み取り専用の全行照合が走る。Result: PASSを確認する。

| Excel列 | 割り当て先 |
|---|---|
| A 書籍名 | 書籍名 |
| B 著者名 | 著者名 |
| C 出版社 | 出版社 |
| D 出版形態 | 出版形態 |
| E 開始月 | 読書開始日・年月 |
| F 読了月 | 読了日・年月 |
| G あらすじ | 内容紹介 |

その他の項目は「取り込まない」。除外行の指定は不要。空欄708行は自動でスキップされる。

```powershell
$excelPath = (Read-Host "Excelファイルのフルパス").Trim('"')
$verificationHome = Join-Path $env:TEMP ("book_manager_excel_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
$previousBookManagerHome = $env:BOOK_MANAGER_HOME

try {
    python scripts/verify_real_excel_migration.py --excel "$excelPath" --work-dir "$verificationHome" --mode prepare
    if ($LASTEXITCODE -ne 0) { throw "検証用DBの準備に失敗しました。" }

    $env:BOOK_MANAGER_HOME = $verificationHome
    Write-Host "検証用保存先: $verificationHome"
    python main.py
    if ($LASTEXITCODE -ne 0) { throw "アプリの実行に失敗しました。" }

    python scripts/verify_real_excel_migration.py --excel "$excelPath" --work-dir "$verificationHome" --mode verify
    if ($LASTEXITCODE -ne 0) { throw "照合に失敗しました。verification_report.jsonを確認してください。" }
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

環境変数はこのPowerShellプロセスだけ変更し、終了後は元へ戻す。空DBを先に作るため、起動時に旧DBを自動移行する経路には入らない。通常の保存先で起動した別のアプリを同時に操作しない。

## 結果ファイル

`$verificationHome` 配下に次を作成する。

- `data/books.db`：検証用DB。
- `backups/`：GUI取込時のバックアップ（バックアップ設定によって起動時バックアップも含む）。
- `verification_report.json`：検査件数、各集計、SQLite整合性、不一致項目、元Excelのハッシュ。
- `row_checks.csv`：Excel行番号、書籍ID、PASS/FAIL、不一致項目。書籍名や内容紹介の全文は含めない。

verifyモードはDBを読み取り専用で開く。結果ファイルは再生成する。

## GUIを使わず登録処理を再検証する場合

新しい専用フォルダーを指定して `--mode import` を実行する。実アプリの取込Serviceと必須バックアップを実行してから照合する。prepare/importは既存フォルダーへの実行を拒否する。同じExcelの二重取込を避けるため、GUI検証で既に使用した保存先には実行しない。

検証スクリプトが意図的な書籍名の不一致を検出すること、既存フォルダーへの取込を拒否すること、verifyでDBハッシュが変わらないことも確認済み。

正式な通常DBへの取込とVersion 2.7配布版の検証は別工程。通常DBへはこの検証スクリプトで登録しない。
