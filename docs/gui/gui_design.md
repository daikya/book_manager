# GUI設計書

Version : 0.2
Last Updated : 2026-07-22
Status : Approved / Design Freeze

---

## 1. 目的

この文書は、`book_manager` プロジェクトにおけるGUI層の設計を定義するものです。

GUIは、利用者による書籍情報の入力、一覧表示、検索、登録、更新、削除および重複候補確認を担当します。

GUIはアプリケーションロジックやデータベース処理を直接実装せず、Design Freeze済みの `BookService` を通じて処理を行います。

---

## 2. 対象範囲

初期Versionでは、次の機能を対象とします。

```text
書籍一覧表示
書籍名検索
ISBN検索
雑誌コード検索
書籍情報入力
新規登録
既存データ編集
削除
重複候補確認
入力エラー表示
処理結果表示
一覧再読み込み
入力欄クリア
アプリケーション終了
```

---

## 3. 対象外

初期Versionでは、次の機能を対象外とします。

```text
openBDからの書籍情報取得
Google Booksからの書籍情報取得
ISBNスキャナー
バーコード読み取り
画像表示
書影取得
著者マスタ管理
出版社マスタ管理
CSVインポート
CSVエクスポート
バックアップ画面
設定画面
複数画面構成
タブ構成
ページング
列の並び替え保存
ウィンドウサイズ保存
テーマ切り替え
多言語対応
ドラッグアンドドロップ
ショートカットキーの詳細設定
Undo／Redo
ログ表示画面
```

外部API連携は、GUI基本機能完成後の別工程で設計します。

---

## 4. GUI技術

初期Versionでは、Python標準ライブラリのTkinterを使用します。

```text
tkinter
tkinter.ttk
tkinter.messagebox
```

外部GUIライブラリは使用しません。

対象Python Versionは、プロジェクト方針に従いPython 3.12以上とします。

---

## 5. GUIの基本方針

GUI設計では、次の方針を採用します。

```text
単一ウィンドウ構成
一覧と入力フォームを同一画面に配置
主要操作をボタンで実行
一覧選択と入力フォームを連動
BookServiceを通じて処理
GUIからRepositoryを直接呼ばない
GUIからSQLiteを直接操作しない
GUIからValidatorを直接呼ばない
入力エラーはダイアログで表示
重大でない処理失敗は利用者へ明示
処理成功後は一覧を更新
```

---

## 6. アーキテクチャ

GUIを含む正式な依存方向は、次のとおりです。

```text
GUI
↓
BookService
↓
BookRepository
↓
SQLite
```

入力値検証の依存方向は、次のとおりです。

```text
GUI
↓
BookService
↓
Validators
```

GUIは、`BookService` の公開APIだけを使用します。

---

## 7. GUIの責務

GUIが担当する処理は、次のとおりです。

```text
ウィンドウ表示
ウィジェット生成
入力値取得
入力値表示
一覧表示
一覧選択の管理
検索条件取得
BookService呼び出し
確認ダイアログ表示
エラーダイアログ表示
成功メッセージ表示
一覧再読み込み
フォームクリア
選択状態解除
ウィンドウ終了処理
```

---

## 8. GUIに含めない責務

次の処理をGUIへ含めません。

```text
SQL生成
SQLite接続
データベース初期化処理
BookRepositoryのCRUD処理
ISBN正規化
任意文字列の正規化
入力値のValidation
日時生成
created_at設定
updated_at設定
重複候補の検索ロジック
BookItemの永続化
外部APIアクセス
```

これらはDatabase層、Repository層、Service層または将来のAPI層が担当します。

---

## 9. GUIクラス

初期Versionでは、GUI全体を管理するクラスを1つ作成します。

クラス名：

```python
class BookManagerApplication:
    ...
```

配置場所：

```text
src/book_manager/gui/book_manager_application.py
```

GUIの起動処理は、別ファイルへ配置します。

```text
src/book_manager/main.py
```

---

## 10. GUIパッケージ構成

初期Versionでは、次の構成とします。

```text
src/book_manager/
├── gui/
│   ├── __init__.py
│   └── book_manager_application.py
└── main.py
```

テストは、次の場所へ配置します。

```text
tests/gui/
└── test_book_manager_application.py
```

---

## 11. コンストラクタ

`BookManagerApplication` は、Tkinterのルートウィンドウと `BookService` を受け取ります。

```python
def __init__(
    self,
    root: tk.Tk,
    service: BookService,
) -> None:
    ...
```

GUIクラス自身が、次のオブジェクトを生成しません。

```text
SQLite connection
BookRepository
BookService
```

これらは起動処理で生成し、GUIへ注入します。

---

## 12. 起動処理

`main.py` は、次の順序でアプリケーションを起動します。

```text
データベースパスを決定する
↓
データベースを初期化する
↓
BookRepositoryを生成する
↓
BookServiceを生成する
↓
Tkルートウィンドウを生成する
↓
BookManagerApplicationを生成する
↓
mainloopを開始する
```

概念コード：

```python
def main() -> None:
    database_path = ...
    initialize_database(database_path)

    repository = BookRepository(database_path)
    service = BookService(repository)

    root = tk.Tk()

    BookManagerApplication(
        root,
        service,
    )

    root.mainloop()
```

---

## 13. メインウィンドウ

初期Versionでは、単一のメインウィンドウを使用します。

ウィンドウタイトル：

```text
書籍管理
```

初期サイズ案：

```text
幅：1200
高さ：760
```

最小サイズ案：

```text
幅：1000
高さ：650
```

ウィンドウサイズは固定せず、利用者が変更できるものとします。

---

## 14. 画面全体構成

画面は、大きく次の5領域に分けます。

```text
検索領域
↓
書籍一覧領域
↓
入力フォーム領域
↓
操作ボタン領域
↓
状態表示領域
```

概念図：

```text
┌──────────────────────────────────────────────┐
│ 検索条件                                     │
├──────────────────────────────────────────────┤
│ 書籍一覧                                     │
│                                              │
│                                              │
├──────────────────────────────────────────────┤
│ 入力フォーム                                 │
│                                              │
├──────────────────────────────────────────────┤
│ 新規登録 更新 削除 クリア 再読み込み 終了    │
├──────────────────────────────────────────────┤
│ 件数・編集状態                               │
└──────────────────────────────────────────────┘
```

---

## 15. レイアウト方式

GUIレイアウトには、原則として `grid()` を使用します。

理由：

* 行と列を明示しやすい。
* 入力フォームへ適している。
* ウィンドウサイズ変更に対応しやすい。
* `pack()` との混在による混乱を避けられる。

同一親ウィジェット内では、`grid()` と `pack()` を混在させません。

ウィンドウサイズ変更へ対応するため、必要な行と列へ `weight` を設定します。

---

## 16. フレーム構成

メインウィンドウ内に、次のフレームを作成します。

```text
search_frame
list_frame
form_frame
button_frame
status_frame
```

役割：

| フレーム           | 役割         |
| -------------- | ---------- |
| `search_frame` | 検索条件と検索操作  |
| `list_frame`   | 書籍一覧       |
| `form_frame`   | 書籍情報入力     |
| `button_frame` | 登録・更新・削除など |
| `status_frame` | 件数や編集状態の表示 |

後続処理で参照しないフレームは、インスタンス属性ではなくローカル変数として保持しても構いません。

---

# 検索領域

## 17. 検索機能

初期Versionでは、次の検索方法を用意します。

```text
書籍名部分一致検索
ISBN完全一致検索
雑誌コード完全一致検索
全件表示
```

検索種類は、Comboboxで選択します。

候補：

```text
書籍名
ISBN
雑誌コード
```

---

## 18. 検索ウィジェット

検索領域には、次のウィジェットを配置します。

| 項目         | ウィジェット         |
| ---------- | -------------- |
| 検索種類       | `ttk.Combobox` |
| 検索文字列      | `ttk.Entry`    |
| 検索ボタン      | `ttk.Button`   |
| 全件表示ボタン    | `ttk.Button`   |
| 検索条件クリアボタン | `ttk.Button`   |

検索種類は、初期値を「書籍名」とします。

Comboboxは `readonly` とします。

---

## 19. 書籍名検索

検索種類が「書籍名」の場合、次を呼び出します。

```python
service.search_books_by_title(keyword)
```

空文字列の場合は、Serviceの仕様に従って全件表示になります。

---

## 20. ISBN検索

検索種類が「ISBN」の場合、次を呼び出します。

```python
service.find_books_by_isbn(keyword)
```

Service側で、次の処理が行われます。

```text
前後空白除去
ハイフン除去
半角空白除去
Validation
```

GUIはISBNを加工しません。

---

## 21. 雑誌コード検索

検索種類が「雑誌コード」の場合、次を呼び出します。

```python
service.find_books_by_magazine_code(keyword)
```

GUIは、前後空白除去やValidationを行いません。

---

## 22. 検索結果

検索結果は、書籍一覧TreeViewへ表示します。

検索結果が0件の場合は、一覧を空にして状態表示を更新します。

例：

```text
検索結果：0件
```

0件であることをエラーダイアログにはしません。

---

## 23. 検索エラー

ISBNまたは雑誌コードの形式が不正な場合、`BookService` から `ValueError` が送出されます。

GUIはこれを捕捉し、次のダイアログを表示します。

タイトル：

```text
検索エラー
```

本文：

```text
ValueErrorのメッセージ
```

例：

```text
ISBNのチェックデジットが正しくありません。
```

---

## 24. 全件表示

「全件表示」ボタンでは、次を呼び出します。

```python
service.get_all_books()
```

同時に次を行います。

```text
検索文字列を空にする
検索種類を書籍名へ戻す
一覧を再描画する
状態表示を更新する
```

---

# 書籍一覧領域

## 25. 一覧ウィジェット

書籍一覧には、`ttk.Treeview` を使用します。

TreeViewは、次の用途で使用します。

```text
一覧表示
行選択
編集対象選択
削除対象選択
```

複数選択は許可せず、単一選択とします。

```python
selectmode="browse"
```

---

## 26. 一覧表示項目

初期Versionでは、次の列を表示します。

| 列                    | 表示名   |
| -------------------- | ----- |
| `id`                 | ID    |
| `title`              | 書籍名   |
| `author`             | 著者名   |
| `publisher`          | 出版社   |
| `publication_format` | 出版形態  |
| `isbn`               | ISBN  |
| `magazine_code`      | 雑誌コード |
| `completion_month`   | 読了年月  |

次の項目は一覧には表示しません。

```text
内容紹介
備考
created_at
updated_at
```

これらは入力フォームへの表示で確認します。

---

## 27. ID列

ID列は、内部識別と利用者の確認のため表示します。

入力フォームにはID編集欄を設けません。

IDは読み取り専用です。

---

## 28. 列幅

初期の列幅案は、次のとおりです。

| 列     |   幅 |
| ----- | --: |
| ID    |  60 |
| 書籍名   | 250 |
| 著者名   | 160 |
| 出版社   | 140 |
| 出版形態  |  90 |
| ISBN  | 130 |
| 雑誌コード | 100 |
| 読了年月  |  90 |

書籍名列を優先的に伸縮させます。

---

## 29. スクロールバー

一覧には、次のスクロールバーを配置します。

```text
縦スクロールバー
横スクロールバー
```

TreeViewとスクロールバーを連動させます。

---

## 30. 一覧の並び順

初期Versionでは、RepositoryおよびServiceから返される順序をそのまま使用します。

基本順序：

```text
ID降順
```

GUI側で独自の並べ替えは行いません。

列ヘッダークリックによるソートは将来機能とします。

---

## 31. 一覧行の識別

TreeViewの各行には、`BookItem.id` を文字列化して `iid` に設定します。

```python
tree.insert(
    "",
    "end",
    iid=str(book.id),
    values=(...),
)
```

`BookItem.id` が `None` のデータは、TreeViewへ追加しません。

保存済みデータにIDがない場合はデータ不整合として扱い、開発時に検出できるようにします。

---

## 32. 一覧選択時の処理

利用者が一覧行を選択した場合、次の処理を行います。

```text
選択されたiidからIDを取得
↓
service.get_book()を呼び出す
↓
取得したBookItemを入力フォームへ表示
↓
編集対象IDとして内部保持
```

TreeViewに表示されていない項目も、`get_book()` で再取得してフォームへ表示します。

---

## 33. ダブルクリック

初期Versionでは、ダブルクリックに特別な処理を割り当てません。

単一クリックによる選択だけで入力フォームへ表示します。

---

## 34. 選択解除

フォームクリア時には、TreeViewの選択も解除します。

```python
tree.selection_remove(
    tree.selection()
)
```

内部で保持している編集対象IDも `None` に戻します。

---

# 入力フォーム領域

## 35. 正式な入力項目

初期Versionの正式な入力項目は、次の9項目です。

| 項目    | 必須 | 入力形式              | ウィジェット         |
| ----- | -- | ----------------- | -------------- |
| 書籍名   | 必須 | 文字列               | `ttk.Entry`    |
| 著者名   | 任意 | 文字列               | `ttk.Entry`    |
| 出版社   | 任意 | 文字列               | `ttk.Entry`    |
| 出版形態  | 任意 | 選択または文字列          | `ttk.Combobox` |
| ISBN  | 任意 | ISBN-10またはISBN-13 | `ttk.Entry`    |
| 雑誌コード | 任意 | 5桁または7桁           | `ttk.Entry`    |
| 読了年月  | 任意 | `YYYY-MM`         | `ttk.Entry`    |
| 内容紹介  | 任意 | 複数行               | `tk.Text`      |
| 備考    | 任意 | 複数行               | `tk.Text`      |

出版年月は初期Versionの対象に含めません。

出版年月を将来追加する場合は、Database、Model、Repository、ServiceおよびGUIの設計変更を別工程で行います。

---

## 36. 書籍名入力

書籍名には、`ttk.Entry` を使用します。

書籍名は必須項目です。

GUIでは必須マークを表示します。

```text
書籍名 *
```

必須確認自体は `BookService` が担当します。

---

## 37. 著者名入力

著者名には、`ttk.Entry` を使用します。

初期Versionでは、複数著者も1つの文字列として入力します。

著者マスタや著者候補選択は導入しません。

---

## 38. 出版社入力

出版社には、`ttk.Entry` を使用します。

出版社マスタや候補入力は、初期Versionでは導入しません。

---

## 39. 出版形態入力

出版形態には、`ttk.Combobox` を使用します。

初期候補：

```text
文庫
単行本
新書
雑誌
電子書籍
その他
```

Comboboxは自由入力を許可します。

理由：

* 出版形態が候補だけに限定できない可能性がある。
* 将来の形式追加に対応しやすい。
* 初期Versionでマスタ管理を導入しない。

空欄も許可します。

---

## 40. ISBN入力

ISBNには、`ttk.Entry` を使用します。

利用者は、次の形式で入力できます。

```text
9784101010014
978-4-10-101001-4
```

GUI側では、ハイフン除去などを行いません。

入力値は、そのまま `BookService` へ渡します。

---

## 41. 雑誌コード入力

雑誌コードには、`ttk.Entry` を使用します。

初期Versionで有効な値：

```text
5桁の半角数字
7桁の半角数字
```

GUI側で入力制限は行いません。

ServiceおよびValidatorによって検証します。

---

## 42. 読了年月入力

読了年月には、`ttk.Entry` を使用します。

形式：

```text
YYYY-MM
```

例：

```text
2026-07
```

入力欄の近くに形式例を表示します。

```text
例：2026-07
```

日付選択ウィジェットは使用しません。

---

## 43. 内容紹介入力

内容紹介には、`tk.Text` を使用します。

理由：

* 長文になる可能性がある。
* 複数行入力が必要。
* `ttk.Entry` では適さない。

高さの初期値案：

```text
4行
```

縦スクロールバーを付けます。

---

## 44. 備考入力

備考には、`tk.Text` を使用します。

高さの初期値案：

```text
4行
```

縦スクロールバーを付けます。

---

## 45. 入力変数

単一行入力には、`tk.StringVar` を使用します。

```python
self._title_var = tk.StringVar()
self._isbn_var = tk.StringVar()
self._magazine_code_var = tk.StringVar()
self._author_var = tk.StringVar()
self._publisher_var = tk.StringVar()
self._publication_format_var = tk.StringVar()
self._completion_month_var = tk.StringVar()
```

内容紹介と備考は、`Text.get()` で取得します。

末尾にTkinterが自動付加する改行を含めないため、次の形式を使用します。

```python
text_widget.get(
    "1.0",
    "end-1c",
)
```

これは業務上の正規化ではなく、Tkinter固有の値取得処理です。

---

## 46. 編集対象ID

GUIクラス内で、現在の編集対象IDを保持します。

```python
self._selected_book_id: int | None
```

初期値：

```python
None
```

一覧選択時にIDを設定し、フォームクリア時に `None` へ戻します。

---

# 操作ボタン領域

## 47. 操作ボタン

初期Versionでは、次のボタンを配置します。

```text
新規登録
更新
削除
入力クリア
再読み込み
終了
```

---

## 48. 新規登録ボタン

「新規登録」ボタンは、入力フォームの内容を新しい書籍として登録します。

一覧で既存書籍が選択されている場合でも、新規登録として動作します。

ただし、誤操作防止のため確認ダイアログを表示します。

```text
現在、既存の書籍が選択されています。
入力内容を新しい書籍として登録しますか？
```

利用者が登録を承認した場合、選択中の既存データは変更せず、新しい書籍として登録します。

登録成功後は、新しく登録された書籍へ一覧選択を移します。

---

## 49. 更新ボタン

「更新」ボタンは、現在選択されている書籍を更新します。

編集対象IDが `None` の場合は、処理を行わず警告を表示します。

タイトル：

```text
更新対象なし
```

本文：

```text
更新する書籍を一覧から選択してください。
```

---

## 50. 削除ボタン

「削除」ボタンは、現在選択されている書籍を削除します。

編集対象IDが `None` の場合は、警告を表示します。

削除前には確認ダイアログを表示します。

```text
「吾輩は猫である」を削除しますか？
この操作は元に戻せません。
```

---

## 51. 入力クリアボタン

「入力クリア」ボタンでは、次の処理を行います。

```text
すべての入力欄を空にする
TreeViewの選択を解除する
編集対象IDをNoneにする
書籍名入力欄へフォーカスを移す
```

データベースの内容は変更しません。

---

## 52. 再読み込みボタン

「再読み込み」ボタンでは、次の処理を行います。

```text
service.get_all_books()を呼び出す
↓
一覧を再描画する
↓
状態表示を更新する
```

入力フォームは原則として変更しません。

ただし、選択中の書籍が存在しなくなっていた場合は、選択を解除してフォームをクリアします。

---

## 53. 終了ボタン

「終了」ボタンでは、アプリケーションを終了します。

未保存の入力値がある場合の終了確認は、初期Versionでは実装しません。

---

# 新規登録フロー

## 54. 新規登録の基本フロー

新規登録処理は、次の順序で行います。

```text
入力フォームから値を取得
↓
既存書籍の選択状態を確認
↓
選択中の場合は新規登録確認
↓
重複候補を検索
↓
候補がある場合は重複確認
↓
利用者が登録を継続
↓
service.add_book()を呼び出す
↓
成功メッセージ
↓
一覧再読み込み
↓
登録した書籍を選択
↓
入力フォームへ登録結果を表示
```

---

## 55. 入力値取得

GUIは、各入力欄から値を文字列として取得します。

```python
title = self._title_var.get()
isbn = self._isbn_var.get()
description = self._description_text.get(
    "1.0",
    "end-1c",
)
```

GUIでは、`strip()` や空文字列から `None` への変換を行いません。

Serviceへそのまま渡します。

---

## 56. 重複候補確認

登録前に、次を呼び出します。

```python
candidates = service.find_duplicate_candidates(
    isbn=isbn,
    magazine_code=magazine_code,
)
```

ISBNと雑誌コードの両方が空の場合は、空リストが返ります。

---

## 57. 重複候補がない場合

重複候補が0件の場合は、そのまま登録処理へ進みます。

```python
service.add_book(...)
```

---

## 58. 重複候補がある場合

重複候補が1件以上ある場合は、確認ダイアログを表示します。

タイトル：

```text
重複候補があります
```

本文例：

```text
同じISBNまたは雑誌コードを持つ書籍が登録されています。

・ID 15：吾輩は猫である
・ID 8：吾輩は猫である 新装版

このまま新しい書籍として登録しますか？
```

利用者が「はい」を選択した場合だけ登録します。

「いいえ」の場合は登録を中止し、入力内容を保持します。

---

## 59. 重複候補の表示件数

初期Versionでは、確認ダイアログに最大5件まで表示します。

6件以上ある場合は、次の文言を追加します。

```text
ほかにも候補があります。
```

---

## 60. 重複候補はエラーではない

重複候補が存在しても、登録禁止にはしません。

最終判断は利用者が行います。

`add_book()` は重複を理由に失敗しません。

---

## 61. 登録成功

登録成功後は、情報ダイアログを表示します。

タイトル：

```text
登録完了
```

本文：

```text
書籍情報を登録しました。
```

その後、一覧を再読み込みします。

---

## 62. 登録エラー

`BookService.add_book()` が `ValueError` を送出した場合は、次のダイアログを表示します。

タイトル：

```text
入力エラー
```

本文：

```text
ValueErrorのメッセージ
```

エラー発生時は、入力内容を保持します。

---

# 更新フロー

## 63. 更新の基本フロー

更新処理は、次の順序で行います。

```text
編集対象IDを確認
↓
入力フォームから値を取得
↓
重複候補を検索
↓
自分自身のIDを候補から除外
↓
候補が残る場合は重複確認
↓
更新確認ダイアログ
↓
更新用BookItemを生成
↓
service.update_book()を呼び出す
↓
成功時に一覧再読み込み
↓
更新した書籍を再選択
↓
入力フォームを更新
```

重複確認は、通常の更新確認より先に行います。

これにより、重複候補を確認した後で最終的な更新意思を確認できます。

---

## 64. 更新用BookItem

GUIは、選択中のIDと入力値を使って更新用 `BookItem` を生成します。

```python
book_item = BookItem(
    id=self._selected_book_id,
    title=self._title_var.get(),
    isbn=self._isbn_var.get(),
    magazine_code=self._magazine_code_var.get(),
    author=self._author_var.get(),
    publisher=self._publisher_var.get(),
    publication_format=(
        self._publication_format_var.get()
    ),
    description=self._get_description(),
    completion_month=(
        self._completion_month_var.get()
    ),
    notes=self._get_notes(),
)
```

`created_at` と `updated_at` は、GUIでは設定しません。

Serviceが既存値と現在日時を使用します。

---

## 65. 更新時の重複確認

更新時にも、ISBNまたは雑誌コードの重複候補を確認します。

```python
candidates = service.find_duplicate_candidates(
    isbn=isbn,
    magazine_code=magazine_code,
)
```

取得後、自分自身のIDを候補から除外します。

```python
candidates = [
    candidate
    for candidate in candidates
    if candidate.id != self._selected_book_id
]
```

候補が残る場合は、重複確認ダイアログを表示します。

利用者が「いいえ」を選択した場合は、更新処理を中止し、入力内容を保持します。

---

## 66. 更新確認

重複候補確認が完了した後、更新確認ダイアログを表示します。

タイトル：

```text
更新確認
```

本文：

```text
選択中の書籍情報を更新しますか？
```

利用者が「いいえ」を選択した場合は、入力内容を保持して処理を終了します。

---

## 67. 更新成功

`service.update_book()` が `True` を返した場合、情報ダイアログを表示します。

タイトル：

```text
更新完了
```

本文：

```text
書籍情報を更新しました。
```

その後、一覧を再読み込みし、同じIDの書籍を再選択します。

---

## 68. 更新対象なし

`service.update_book()` が `False` を返した場合、対象データが存在しません。

警告ダイアログ：

タイトル：

```text
更新できません
```

本文：

```text
更新対象の書籍が見つかりませんでした。
一覧を再読み込みしてください。
```

その後、一覧を再読み込みし、フォームをクリアします。

---

## 69. 更新エラー

`ValueError` が送出された場合は、入力エラーダイアログを表示します。

入力内容と一覧選択は保持します。

---

# 削除フロー

## 70. 削除の基本フロー

削除処理は、次の順序で行います。

```text
編集対象IDを確認
↓
削除確認ダイアログ
↓
service.delete_book()を呼び出す
↓
成功時に完了メッセージ
↓
一覧再読み込み
↓
入力フォームクリア
```

---

## 71. 削除成功

`service.delete_book()` が `True` を返した場合、情報ダイアログを表示します。

タイトル：

```text
削除完了
```

本文：

```text
書籍情報を削除しました。
```

---

## 72. 削除対象なし

`service.delete_book()` が `False` を返した場合、警告ダイアログを表示します。

タイトル：

```text
削除できません
```

本文：

```text
削除対象の書籍が見つかりませんでした。
一覧を再読み込みしてください。
```

その後、一覧を再読み込みし、フォームをクリアします。

---

# フォーム表示

## 73. BookItemからフォームへの反映

一覧選択時は、`BookItem` の各値を入力フォームへ設定します。

`None` は空文字列として表示します。

```python
self._isbn_var.set(
    book_item.isbn or ""
)
```

Textウィジェットは、既存内容を削除してから設定します。

```python
text_widget.delete(
    "1.0",
    tk.END,
)
text_widget.insert(
    "1.0",
    value or "",
)
```

---

## 74. フォームクリア

フォームクリアでは、すべてのStringVarを空文字列にします。

Textウィジェットも空にします。

編集対象IDを `None` にします。

TreeViewの選択を解除します。

---

## 75. 編集状態表示

現在、既存データを編集中であることを利用者が確認できるようにします。

状態表示例：

```text
編集中：ID 15
```

新規入力状態：

```text
新規登録
```

---

# 状態表示

## 76. ステータスバー

画面下部に状態表示領域を設けます。

表示例：

```text
全 125件
```

```text
検索結果 3件
```

```text
編集中：ID 15
```

件数表示と編集状態表示は、別々のラベルとして配置しても構いません。

---

## 77. 初期表示

アプリケーション起動時は、全書籍を一覧表示します。

状態表示：

```text
全 N件
```

フォームは空の新規登録状態とします。

---

## 78. 読み込み失敗

初期読み込みや再読み込みで予期しない例外が発生した場合は、エラーダイアログを表示します。

タイトル：

```text
読み込みエラー
```

本文：

```text
書籍情報を読み込めませんでした。
```

同時に、開発時の調査用として標準エラーへトレースバックを出力します。

```python
except Exception:
    traceback.print_exc()
    messagebox.showerror(
        "読み込みエラー",
        "書籍情報を読み込めませんでした。",
    )
```

初期Versionでは、ログファイルへの保存は行いません。

---

# ダイアログ方針

## 79. ダイアログ種別

初期Versionでは、次の `messagebox` を使用します。

| 用途          | 関数              |
| ----------- | --------------- |
| 成功通知        | `showinfo()`    |
| 注意・対象なし     | `showwarning()` |
| 入力エラー・処理エラー | `showerror()`   |
| 登録・更新・削除確認  | `askyesno()`    |

---

## 80. ダイアログのタイトル

タイトルは、処理内容を明確にします。

```text
登録完了
入力エラー
重複候補があります
更新確認
更新できません
削除確認
削除完了
検索エラー
読み込みエラー
処理エラー
```

「エラー」だけの曖昧なタイトルは使用しません。

---

## 81. 技術用語

利用者向けメッセージには、次のような内部技術用語を表示しません。

```text
SQLite
Repository
ValueError
Traceback
SQL
BookItem
Exception
```

Validatorから返される日本語メッセージは、そのまま表示できます。

---

# イベントハンドラ

## 82. イベントハンドラ方針

GUIクラス内のイベントハンドラは、`_on_` で始めます。

```python
def _on_search(
    self,
    event: tk.Event | None = None,
) -> None:
    ...

def _on_show_all(self) -> None:
    ...

def _on_tree_select(
    self,
    event: tk.Event,
) -> None:
    ...

def _on_add(self) -> None:
    ...

def _on_update(self) -> None:
    ...

def _on_delete(self) -> None:
    ...

def _on_clear(self) -> None:
    ...

def _on_reload(self) -> None:
    ...

def _on_exit(self) -> None:
    ...
```

検索処理は、検索ボタンとEnterキーの両方から呼び出せるようにします。

---

## 83. ウィジェット生成メソッド

ウィジェット生成処理は、次の非公開メソッドへ分割します。

```python
def _configure_root(self) -> None:
    ...

def _create_widgets(self) -> None:
    ...

def _create_search_frame(self) -> None:
    ...

def _create_list_frame(self) -> None:
    ...

def _create_form_frame(self) -> None:
    ...

def _create_button_frame(self) -> None:
    ...

def _create_status_frame(self) -> None:
    ...
```

---

## 84. データ表示メソッド

一覧やフォーム操作は、次の非公開メソッドへ分割します。

```python
def _load_all_books(self) -> None:
    ...

def _display_books(
    self,
    books: list[BookItem],
) -> None:
    ...

def _display_book_in_form(
    self,
    book_item: BookItem,
) -> None:
    ...

def _clear_form(self) -> None:
    ...

def _select_book_in_tree(
    self,
    book_id: int,
) -> None:
    ...
```

---

## 85. 入力値取得メソッド

入力値取得は、必要に応じて共通化します。

```python
def _get_description(self) -> str:
    ...

def _get_notes(self) -> str:
    ...

def _create_book_item_from_form(
    self,
) -> BookItem:
    ...
```

新規登録では、`BookService.add_book()` のキーワード引数を直接使用します。

---

## 86. 重複候補メソッド

重複候補表示は、次のメソッドへ分離します。

```python
def _confirm_duplicate_candidates(
    self,
    candidates: list[BookItem],
    *,
    excluded_book_id: int | None = None,
) -> bool:
    ...
```

戻り値：

```text
登録または更新を続行する：True
処理を中止する：False
```

---

# キーボード操作

## 87. Enterキー

検索入力欄でEnterキーを押した場合、検索を実行します。

```python
search_entry.bind(
    "<Return>",
    self._on_search,
)
```

---

## 88. Escapeキー

初期Versionでは、Escapeキーへフォームクリアを割り当てません。

誤操作を防ぐためです。

---

## 89. Deleteキー

Deleteキーによる削除は、初期Versionでは実装しません。

削除ボタンと確認ダイアログを使用します。

---

## 90. ショートカット

初期Versionでは、検索欄でのEnterキー以外のショートカットを導入しません。

WindowsのCtrlキーとmacOSのCommandキーの差異は、将来の設計対象とします。

---

# フォーカス制御

## 91. 初期フォーカス

起動時は、書籍名入力欄へフォーカスを設定します。

---

## 92. 登録後のフォーカス

登録後は、登録した書籍を一覧選択状態にします。

書籍名入力欄へ自動では戻しません。

---

## 93. クリア後のフォーカス

入力クリア後は、書籍名入力欄へフォーカスを移します。

---

## 94. エラー後のフォーカス

初期Versionでは、エラー項目を自動判定してフォーカス移動する機能は実装しません。

エラーメッセージを確認し、利用者が該当欄を修正します。

---

# TreeView更新

## 95. 一覧再描画

一覧更新時は、既存の全行を削除してから再描画します。

```python
for item_id in tree.get_children():
    tree.delete(item_id)
```

その後、取得した `BookItem` を順番に追加します。

初期Versionでは差分更新を行いません。

---

## 96. 空値の表示

一覧上で `None` は空文字列として表示します。

```python
book.author or ""
```

文字列 `"None"` は表示しません。

---

## 97. 長文項目

内容紹介と備考はTreeViewに表示しません。

長文による一覧幅の問題を避けます。

---

# 例外処理

## 98. `ValueError`

`BookService` の `ValueError` は、利用者の入力に起因するエラーとして扱います。

GUIは例外メッセージをそのまま表示します。

```python
except ValueError as error:
    messagebox.showerror(
        "入力エラー",
        str(error),
    )
```

---

## 99. 予期しない例外

データベース障害などの予期しない例外は、一般的なメッセージへ置き換えて利用者へ表示します。

同時に、開発時の調査用として `traceback.print_exc()` を実行します。

```python
except Exception:
    traceback.print_exc()
    messagebox.showerror(
        "処理エラー",
        "処理中にエラーが発生しました。",
    )
```

利用者向けダイアログには、例外の詳細やトレースバックを表示しません。

初期Versionでは、ログファイルへの保存は行いません。

---

## 100. 例外の握りつぶし

例外を何もせず無視する実装は行いません。

次のいずれかを行います。

```text
利用者へ通知する
標準エラーへトレースバックを出力する
上位へ再送出する
```

---

# データ状態

## 101. 一覧とフォームの整合性

登録、更新、削除後は、必ず一覧を再読み込みします。

これにより、画面表示とデータベース状態を一致させます。

---

## 102. 外部変更

複数ユーザーまたは別プロセスが同じSQLiteファイルを変更した場合、GUIは自動検知しません。

利用者が「再読み込み」ボタンを押すことで最新状態を取得します。

自動監視は初期Versionの対象外です。

---

## 103. 更新競合

初期Versionでは、楽観的ロックや更新競合検出を実装しません。

更新対象が存在するかどうかだけを確認します。

`updated_at` を使った競合判定は、将来機能とします。

---

# クロスプラットフォーム

## 104. 対象OS

初期Versionでは、次のOSを正式な動作確認対象とします。

```text
Windows
macOS
```

Linuxは動作する可能性がありますが、正式な確認対象外とします。

---

## 105. フォント

特定の日本語フォントを固定指定しません。

Tkinterのシステム既定フォントを使用します。

---

## 106. パス

GUI内でWindows専用のパス表記を使用しません。

データベースパスには `pathlib.Path` を使用します。

---

## 107. ウィンドウ表示差

Tkinterの見た目はOSごとに異なります。

初期Versionでは、完全に同じ見た目にすることを目標としません。

操作性と機能の一貫性を優先します。

---

# アクセシビリティと操作性

## 108. ラベル

すべての入力欄に、対応するラベルを表示します。

Entryだけを配置して意味を推測させる設計にはしません。

---

## 109. ボタン名

ボタン名には、動作が明確な日本語を使用します。

```text
新規登録
更新
削除
入力クリア
全件表示
再読み込み
```

次のような曖昧な名称は使用しません。

```text
実行
OK
処理
```

---

## 110. 色への依存

状態やエラーを色だけで表現しません。

ダイアログ、文字列、選択状態を併用します。

---

## 111. ウィジェット状態

初期Versionでは、更新ボタンと削除ボタンを常時有効にします。

対象が選択されていない場合は、押下時に警告します。

---

# テスト方針

## 112. GUIテストの基本方針

GUIテストは、次の2種類に分けます。

```text
非表示状態でのGUIロジック自動テスト
手動操作テスト
```

Tkinterの完全な自動操作テストは、初期Versionでは行いません。

---

## 113. 自動テスト対象

初期Versionの自動テストは、画面とデータの接続部分に絞ります。

```text
GUIクラスを生成できる
初期の選択IDがNoneである
BookItemをフォームへ反映できる
フォームをクリアできる
一覧を再描画できる
Noneを空文字列として表示できる
更新用BookItemを生成できる
```

Service層ですでに確認済みの次の業務ロジックは、GUIテストで過剰に再検証しません。

```text
正規化
Validation
登録ロジック
検索ロジック
重複候補統合
更新日時処理
削除ロジック
```

---

## 114. 手動テスト対象

次の項目は、初期Versionでは手動確認とします。

```text
各ボタンの操作
ダイアログの表示内容
検索入力欄でのEnter操作
TreeViewの選択操作
スクロール操作
フォーカス移動
ウィンドウサイズ変更
Windowsでの表示
macOSでの表示
```

---

## 115. GUIテスト用Service

GUI自動テストでは、実際の `BookService` と一時SQLiteを使用する方式を第一候補とします。

```text
tmp_path
↓
SQLite
↓
BookRepository
↓
BookService
↓
GUI
```

これにより、実際の画面データフローを確認できます。

必要に応じて、ダイアログだけは `unittest.mock` で置き換えます。

---

## 116. GUIテスト時のTk

テストでは、Tkルートウィンドウを生成し、画面を非表示にします。

```python
root = tk.Tk()
root.withdraw()
```

テスト終了時は、必ず破棄します。

```python
root.destroy()
```

fixtureを使用する場合も、`yield` 後に必ず `destroy()` を実行します。

---

## 117. Tkinterテストの環境制約

Tkinterの自動テストは、実行環境によって失敗する可能性があります。

特に、次の環境では注意が必要です。

```text
GUIを利用できないCI環境
ディスプレイのないLinux環境
Tkが導入されていないPython環境
macOSのPython配布元によるTkバージョン差
```

macOSでは、使用しているPythonの配布元やTkのVersionによって、ウィジェット表示やテスト動作が異なる場合があります。

初期Versionでは、WindowsおよびmacOSの開発端末上でテストを実施します。

Tkを生成できないCI環境への対応は、初期Versionの対象外とします。

---

## 118. 手動テスト項目

最低限、次の手動テストを行います。

### 起動

```text
アプリケーションが起動する
初期一覧が表示される
書籍名欄へ入力できる
```

### 登録

```text
正常な書籍を登録できる
必須項目不足でエラーになる
不正ISBNでエラーになる
重複候補確認が表示される
重複を承認して登録できる
既存書籍選択中に新規登録確認が表示される
```

### 検索

```text
書籍名検索ができる
ISBN検索ができる
雑誌コード検索ができる
不正な検索値でエラーになる
全件表示へ戻せる
```

### 更新

```text
一覧選択でフォームへ反映される
入力値を変更して更新できる
更新時に自分自身が重複候補から除外される
別書籍と重複する場合に確認が表示される
重複確認後に更新確認が表示される
更新後もcreated_atが保持される
更新対象なしで警告される
```

### 削除

```text
削除確認が表示される
削除をキャンセルできる
削除を実行できる
削除後に一覧から消える
```

### 画面

```text
一覧をスクロールできる
内容紹介を複数行入力できる
備考を複数行入力できる
ウィンドウサイズを変更できる
Windowsで文字化けしない
macOSで文字化けしない
```

---

# GUI実装順序

## 119. 実装手順

GUIは、次の順序で実装します。

```text
guiパッケージを作成する
↓
BookManagerApplicationの骨格を作成する
↓
メインウィンドウを設定する
↓
検索領域を作成する
↓
一覧領域を作成する
↓
入力フォームを作成する
↓
操作ボタンを作成する
↓
状態表示を作成する
↓
全件読み込みを実装する
↓
一覧選択処理を実装する
↓
検索処理を実装する
↓
フォームクリアを実装する
↓
新規登録を実装する
↓
重複確認を実装する
↓
更新処理を実装する
↓
削除処理を実装する
↓
main.pyを実装する
↓
GUI自動テストを作成する
↓
手動テストを実施する
```

---

## 120. コミット単位

GUI実装は、次のように分けます。

```text
feat: GUIの基本画面を追加
feat: GUIの一覧表示と検索を追加
feat: GUIの登録機能を追加
feat: GUIの更新と削除を追加
feat: アプリケーション起動処理を追加
test: GUIテストを追加
docs: GUI手動テスト結果を追加
```

1コミット1テーマの開発指針を維持します。

---

# 初期Versionで導入しないもの

## 121. 未導入項目

初期Versionでは、次を導入しません。

```text
MVCフレームワーク
MVVM
Presenter
Controllerクラス
依存性注入コンテナ
イベントバス
非同期処理
スレッド処理
外部テーマ
カスタムウィジェットライブラリ
TreeView列ソート
ページング
詳細表示専用ダイアログ
入力中のリアルタイムValidation
自動保存
Undo／Redo
ドラッグアンドドロップ
画像表示
外部API検索
書影表示
CSV機能
印刷
```

---

# 将来拡張

## 122. 外部API連携

将来、次の機能を追加する可能性があります。

```text
ISBN入力
↓
書籍情報取得ボタン
↓
openBD検索
↓
Google Books検索
↓
候補表示
↓
入力フォームへ反映
```

GUIから直接APIを呼び出さず、専用Serviceを経由します。

---

## 123. 著者マスタ

著者表記の正規化が必要になった場合、著者選択または候補表示を追加します。

初期Versionでは、文字列入力だけとします。

---

## 124. 出版社マスタ

出版社名の表記ゆれが問題になった場合、出版社マスタを追加します。

---

## 125. 一覧ソート

列ヘッダークリックによる並び替えを将来追加できます。

候補：

```text
ID
書籍名
著者名
出版社
読了年月
```

---

## 126. 詳細画面

内容紹介や備考を広く表示する必要が生じた場合、詳細表示ダイアログを追加します。

---

## 127. 入力支援

将来の入力支援候補：

```text
読了年月の選択
ISBNの自動整形
出版形態候補管理
入力履歴
著者候補
出版社候補
```

---

## 128. 設定保存

将来、次の画面状態を保存する可能性があります。

```text
ウィンドウサイズ
ウィンドウ位置
TreeView列幅
最後に選択した検索種類
```

初期Versionでは保存しません。

---

# 設計上の注意事項

## 129. GUIからRepositoryを呼ばない

次の実装は禁止します。

```python
self._repository.get_all()
```

正式には、Serviceを使用します。

```python
self._service.get_all_books()
```

---

## 130. GUIからValidatorを呼ばない

次の実装は禁止します。

```python
validate_isbn(
    self._isbn_var.get()
)
```

正式には、Serviceの公開メソッドを呼びます。

---

## 131. GUIで日時を設定しない

次の実装は禁止します。

```python
created_at=datetime.now()
```

日時は `BookService` が設定します。

---

## 132. GUIで正規化しない

次の実装は禁止します。

```python
isbn = isbn.replace(
    "-",
    "",
)
```

```python
author = author.strip()
```

正規化はServiceが担当します。

---

## 133. SQLを書かない

GUIモジュール内にSQLを記述しません。

```sql
SELECT *
FROM book_items
```

このような処理はRepositoryだけが担当します。

---

## 134. `BookItem` の利用範囲

GUIは、次の場合に `BookItem` を使用します。

```text
一覧表示
選択書籍のフォーム反映
更新用モデル生成
重複候補表示
```

新規登録では、`BookService.add_book()` の引数を使用します。

---

# Design Freeze

## 135. 確定事項

次の項目を正式に確定します。

```text
Tkinterを使用する
単一ウィンドウとする
BookServiceをDIする
GUIからRepositoryを呼ばない
GUIからValidatorを呼ばない
検索領域を設ける
TreeViewで一覧表示する
単一行選択とする
入力項目を9項目とする
出版年月は含めない
登録前に重複候補を確認する
更新時は自分自身を重複候補から除外する
更新時は重複確認後に更新確認を行う
削除前に確認する
ValueErrorを利用者へ表示する
予期しない例外ではtraceback.print_exc()を実行する
一覧再読み込みで画面とDBを同期する
WindowsとmacOSを対象とする
GUI自動テストと手動テストを併用する
GUI自動テストは画面とデータの接続部分に絞る
```

---

## 136. Design Freeze後の変更

Design Freeze後に、次の変更を行う場合は設計書を更新します。

```text
画面構成変更
入力項目追加
一覧列追加
検索方法追加
Service API変更
新しいダイアログ追加
複数画面化
外部API機能追加
GUIクラス分割
操作フロー変更
```

変更手順：

```text
変更理由を整理する
↓
BookServiceへの影響を確認する
↓
BookItemへの影響を確認する
↓
GUI設計書を更新する
↓
レビューする
↓
Versionを更新する
↓
実装とテストを変更する
```

---

## 137. 正式状態

```text
GUI design : Approved
Review     : Complete
Freeze     : Design Freeze
```

本設計書に基づき、GUI基本画面の実装へ進みます。
