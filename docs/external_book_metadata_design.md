# 外部書誌情報取得機能 設計書

|項目|内容|
|:--|:--|
|文書名|外部書誌情報取得機能 設計書|
|プロジェクト|book_manager|
|バージョン|1.0|
|状態|Design Freeze|
|作成者|daikya / ChatGPT|
|最終更新日|2026-07-24|

---

# 改訂履歴

|Version|日付|内容|
|:--|:--|:--|
|1.0|2026-07-24|Design Freeze版 初版作成|

---

# 目次

1. はじめに
2. 設計方針
3. 要件整理
4. システム構成
5. 全体アーキテクチャ
6. データモデル
7. クラス設計
8. API Client設計
9. Service設計
10. Repositoryとの責務分離
11. GUI連携
12. ISBN処理
13. Google Books連携
14. openBD連携
15. データ統合
16. エラー設計
17. 例外設計
18. HTTP通信設計
19. GUI反映ルール
20. ログ設計
21. 設定管理
22. テスト方針
23. シーケンス図
24. クラス図
25. コンポーネント図
26. ADR
27. セキュリティ
28. 将来拡張
29. 受入条件
30. 詳細クラス設計
31. データ変換仕様
32. 運用・保守設計
33. 実装レビュー基準
34. Implementation Checklist
35. トレーサビリティ
36. 参考資料
37. 変更履歴

---

# 1. はじめに

## 1.1 目的

本設計書は、book_manager に追加する「外部書誌情報取得機能」の設計内容を定義することを目的とする。

利用者が ISBN を入力すると、外部サービスから書誌情報を取得し、入力フォームへ反映できる機能を実現する。

本設計書では、機能仕様だけでなく、責務分離、アーキテクチャ、例外設計、保守性および将来の拡張性を考慮した設計方針を定義する。

---

## 1.2 対象読者

本書は以下の読者を対象とする。

- book_manager 開発者
- 将来の保守担当者
- 設計レビュー実施者
- テスト担当者
- 将来の自分

---

## 1.3 対象範囲

本設計書が対象とする機能は次のとおりである。

- ISBN入力
- ISBN-10／ISBN-13対応
- Google Books API
- openBD API
- 書誌情報取得
- データ統合
- GUI反映
- エラー処理
- テスト設計

以下は本設計書の対象外とする。

- SQLite設計
- GUI全体設計
- 書籍管理CRUD
- バックアップ機能
- エクスポート機能

これらは別設計書で管理する。

---

## 1.4 設計書の位置付け

本設計書は book_manager の Design Freeze 文書として位置付ける。

実装は、本設計書を基準として進める。

設計内容を変更する場合は、設計書または ADR を更新したうえで実装を行う。

実装のみを先行させることは避ける。

---

## 1.5 設計方針

本機能では、次の方針を採用する。

- GUIとビジネスロジックを分離する。
- 外部APIへの依存を最小限に抑える。
- API仕様変更に強い構造とする。
- テスト容易性を重視する。
- 将来のAPI追加を容易にする。
- 既存の書籍管理機能へ影響を与えない。
- 外部取得機能は交換可能な構造とする。
- 利用者が取得結果を確認したうえで保存する。

本設計では、保守性・可読性・拡張性を優先し、短期的な実装容易性のみを理由として責務を混在させない。

---
# 2. 設計方針

## 2.1 基本方針

外部書誌情報取得機能は、既存の書籍管理機能から独立した補助機能として実装する。

外部APIから取得した情報は、利用者による入力作業を補助するために使用する。取得結果を直接データベースへ保存することはせず、いったんGUIの入力フォームへ反映する。

利用者は取得結果を確認し、必要に応じて修正したうえで、既存の登録または更新操作によって保存する。

本機能の基本方針は次のとおりである。

* 外部API取得処理と既存CRUD処理を分離する。
* GUIへHTTP通信処理を記述しない。
* 外部API固有のレスポンス形式をGUIへ持ち込まない。
* 複数の取得元を交換可能な構造とする。
* 一つの外部サービスが利用できない場合でも、可能な範囲で処理を継続する。
* 取得できなかった項目を理由に、取得済みの有効な項目を破棄しない。
* 外部APIの結果を正しい情報であると無条件に仮定しない。
* 利用者が内容を確認してから保存できる構造とする。
* 既存データベース設計への影響を最小限にする。
* テスト時に実際の外部APIへ接続しなくても検証できるようにする。

---

## 2.2 責務分離

本機能では、次の責務を明確に分離する。

| 構成要素                | 主な責務                              |
| :------------------ | :-------------------------------- |
| GUI                 | ISBN入力、取得開始、上書き確認、取得結果の表示、エラー通知   |
| BookMetadataService | ISBN検証、Client呼び出し、取得結果の統合、最終結果の返却 |
| BookMetadataClient  | 外部サービスごとのHTTP通信およびレスポンス変換         |
| FetchedBookData     | 取得した書誌情報を保持する内部データモデル             |
| BookService         | 書籍の登録、更新、削除、検索などの既存業務処理           |
| Repository          | SQLiteへの永続化処理                     |

外部書誌情報取得機能は、既存の `BookService` および `Repository` に直接組み込まない。

`BookService` は書籍管理に関する業務処理を担当し、外部APIへの接続は担当しない。

`Repository` はSQLiteとのやり取りだけを担当し、ISBNから書誌情報を取得する処理は担当しない。

---

## 2.3 外部APIの抽象化

外部APIごとの差異は、各 `BookMetadataClient` の内部へ閉じ込める。

Google BooksとopenBDでは、エンドポイント、パラメータ、レスポンス形式、項目名およびエラー形式が異なる。

これらの違いを `BookMetadataService` やGUIが直接認識すると、外部APIを追加または変更するたびに複数の層を修正する必要が生じる。

そのため、すべてのClientは共通インターフェースを実装し、取得結果を共通の `FetchedBookData` へ変換して返す。

概念上の共通インターフェースは次のとおりである。

```python
class BookMetadataClient(Protocol):
    @property
    def source_name(self) -> str:
        ...

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        ...
```

`BookMetadataService` は、各Clientの具体的なクラスではなく、この共通契約に依存する。

---

## 2.4 Protocolの採用

外部API Clientの共通契約には、Pythonの `Protocol` を採用する。

抽象基底クラスではなく `Protocol` を採用する理由は次のとおりである。

* 特定の基底クラスの継承を強制しない。
* 必要なメソッドとプロパティだけを契約として定義できる。
* テスト用Fake Clientを容易に作成できる。
* 将来、HTTP以外の取得元を追加しやすい。
* Client実装間の不要な結合を避けられる。
* 構造的部分型によって柔軟な差し替えができる。

例えば、将来ローカルCSV、別のWeb API、キャッシュサーバーなどを取得元として追加する場合でも、同じProtocolへ適合させることで `BookMetadataService` を変更せずに利用できる。

---

## 2.5 Service層の採用

GUIから各外部API Clientを直接呼び出さず、`BookMetadataService` を経由する。

Service層を設ける理由は次のとおりである。

* ISBNの正規化処理を一か所へ集約できる。
* ISBN-10からISBN-13への変換を一か所で行える。
* Clientの呼び出し順序を管理できる。
* 複数の取得結果を統合できる。
* Clientごとの失敗を集約できる。
* GUIから外部APIの存在を隠蔽できる。
* 単体テストが容易になる。
* 将来のClient追加時にGUIを変更せずに済む。

GUIは「ISBNから書誌情報を取得する」というユースケースだけを認識し、どのAPIを使用するかは認識しない。

---

## 2.6 Google Books優先方針

第1段階では、Google Booksを第1取得元、openBDを第2取得元とする。

呼び出し順序は次のとおりである。

```text
1. Google Books
2. openBD
```

Google Booksを優先する理由は次のとおりである。

* ISBN検索を利用できる。
* 一般的な書誌項目を取得できる。
* 書籍によっては内容紹介や表紙画像URLを取得できる。
* 国際的な書籍データを取得できる可能性がある。
* 第1段階の主要取得元として扱いやすい。

ただし、Google Booksの情報が常に完全または正確であるとは限らない。

取得結果に不足がある場合は、openBDの結果で空欄を補完する。

---

## 2.7 openBD補完方針

openBDは、第1段階ではGoogle Booksを補完する取得元として利用する。

openBDから取得した値は、Google Booksで取得できなかった項目だけに使用する。

Google Booksですでに値が取得できている項目を、openBDの値で上書きしない。

openBDを補完Clientとして扱う理由は次のとおりである。

* 国内書籍の情報を補完できる可能性がある。
* Google Booksで欠落している項目を取得できる場合がある。
* 一つの外部サービスへの依存を避けられる。
* 将来、提供状況が変化してもClient単位で切り離せる。

openBDを必須の依存先とはしない。

openBDが利用できない場合でも、Google Booksから有効な結果を取得できていれば、その結果を利用者へ返す。

---

## 2.8 空欄補完方式

複数の取得元から得た結果は、先順位の値を優先し、後順位の値は空欄だけを補完する。

例を次に示す。

| 項目      | Google Books | openBD | 統合結果         |
| :------ | :----------- | :----- | :----------- |
| 書籍名     | 取得あり         | 取得あり   | Google Books |
| 著者名     | 取得あり         | 取得あり   | Google Books |
| 出版社     | 未取得          | 取得あり   | openBD       |
| 内容紹介    | 未取得          | 未取得    | 未設定          |
| 表紙画像URL | 取得あり         | 取得あり   | Google Books |

この方式により、取得元によって値が異なる場合でも、結果が予測可能になる。

多数決、文字数比較、更新日比較などによる自動判定は、第1段階では行わない。

---

## 2.9 部分成功の許容

外部書誌情報取得では、すべての項目が取得できるとは限らない。

例えば、書籍名、著者名、出版社は取得できても、内容紹介が取得できない場合がある。

その場合でも、取得済みの情報は有効な結果として扱う。

また、一つのClientが通信エラーになっても、別のClientから有効な結果を取得できた場合は、取得処理全体を失敗としない。

次の状態を区別する。

| 状態                        | 扱い     |
| :------------------------ | :----- |
| 一つ以上のClientから有効な情報を取得     | 成功     |
| 一部項目のみ取得                  | 成功     |
| 一つのClientが失敗し、別のClientが成功 | 成功     |
| すべてのClientが対象なし           | 対象書籍なし |
| すべてのClientが失敗し、有効結果なし     | 取得エラー  |

---

## 2.10 自動保存を行わない方針

外部APIから情報を取得した時点では、データベースへ保存しない。

取得結果はGUIの入力フォームへ反映するだけとする。

自動保存を行わない理由は次のとおりである。

* 外部データが誤っている可能性がある。
* 著者名や出版社名に表記ゆれがある。
* 利用者が出版形態などを修正する場合がある。
* 既存データを誤って上書きする危険を避ける。
* 取得操作と登録操作の責務を分離する。
* 現在のCRUD操作との一貫性を保つ。

保存は、利用者が既存の登録または更新操作を実行した場合に限る。

---

## 2.11 同期処理としての実装

第1段階では、外部API取得処理を同期処理として実装する。

非同期処理やバックグラウンドスレッドは導入しない。

理由は次のとおりである。

* 初期実装の複雑性を抑えられる。
* Tkinterのスレッド制約を考慮した追加設計が不要になる。
* エラー処理を単純化できる。
* テストが容易になる。
* timeoutを設定することで無制限な待機を防げる。

ただし、取得中は取得ボタンを無効化し、二重実行を防止する。

将来、操作性に問題が生じた場合は、スレッド化または非同期化を別の設計変更として検討する。

---

## 2.12 設計判断

本設計では、少ないコード量よりも責務の明確さを優先する。

GUIから直接Google BooksおよびopenBDを呼び出す方が初期コード量は少なくなるが、次の問題が発生する。

* GUIが肥大化する。
* API追加時にGUI修正が必要になる。
* HTTP通信の単体テストが難しくなる。
* API固有のJSON構造が画面処理へ混入する。
* エラー処理が重複する。
* 取得結果の統合規則が分散する。

これらを避けるため、Client、Service、GUIを分離する。

---

# 3. 要件整理

## 3.1 機能要件

外部書誌情報取得機能の機能要件を以下に示す。

| ID     | 要件                                |
| :----- | :-------------------------------- |
| FR-001 | 利用者はISBNを入力して書誌情報を取得できる。          |
| FR-002 | ISBN-10およびISBN-13を受け付ける。          |
| FR-003 | ハイフンおよび空白を含むISBNを入力できる。           |
| FR-004 | 入力ISBNの形式とチェックデジットを検証する。          |
| FR-005 | ISBN-10は外部API問い合わせ時にISBN-13へ変換する。 |
| FR-006 | Google Booksから書誌情報を取得する。          |
| FR-007 | openBDから書誌情報を取得する。                |
| FR-008 | 複数の取得結果を優先順位に従って統合する。             |
| FR-009 | 後順位の取得元は空欄だけを補完する。                |
| FR-010 | 取得結果をGUIの入力フォームへ反映する。             |
| FR-011 | 取得時点ではデータベースへ保存しない。               |
| FR-012 | 既存の入力値がある場合は上書き確認を行う。             |
| FR-013 | 利用者が確認を拒否した場合は取得処理を開始しない。         |
| FR-014 | 取得中は取得ボタンを無効化する。                  |
| FR-015 | 取得成功時はステータスバーへ結果を表示する。            |
| FR-016 | エラー時は内容に応じたダイアログを表示する。            |
| FR-017 | 一部の取得元が失敗しても、有効な結果があれば表示する。       |
| FR-018 | 取得対象外の項目を変更しない。                   |
| FR-019 | 取得できなかった項目で既存値を消去しない。             |
| FR-020 | 利用者は取得結果を修正してから登録できる。             |

---

## 3.2 取得対象項目

第1段階で外部サービスから取得する項目は次のとおりである。

| 項目       |    取得対象   |    GUI反映    |   DB保存  |
| :------- | :-------: | :---------: | :-----: |
| ISBN     |     対象    |      する     | 既存項目へ保存 |
| 書籍名      |     対象    |      する     | 既存項目へ保存 |
| 著者名      |     対象    |      する     | 既存項目へ保存 |
| 出版社      |     対象    |      する     | 既存項目へ保存 |
| 出版形態     |  可能な場合のみ  |      する     | 既存項目へ保存 |
| 内容紹介     |     対象    |      する     | 既存項目へ保存 |
| 出版日      | 参考情報として取得 |    原則しない    |   しない   |
| 表紙画像URL  | 参考情報として取得 | 第1段階では表示しない |   しない   |
| 取得元      |    内部管理   |   成功表示に使用   |   しない   |
| Rawレスポンス | デバッグ・テスト用 |    表示しない    |   しない   |

出版日と表紙画像URLは `FetchedBookData` には保持できるが、第1段階では既存DBへ保存しない。

---

## 3.3 取得対象外項目

次の項目は外部書誌情報取得によって変更しない。

* 雑誌コード
* 読了年月
* 備考
* 利用者が手入力した管理情報
* データベース内部ID
* 作成日時
* 更新日時
* その他のアプリケーション管理項目

これらは外部書誌情報ではなく、利用者またはアプリケーションが管理する情報である。

---

## 3.4 ISBN入力要件

ISBN入力では次の形式を受け付ける。

```text
4101109184
4-10-110918-4
9784163917733
978-4-16-391773-3
```

正規化時には、次の文字を除去する。

* 半角ハイフン
* 全角ハイフンとして許容すると決めた文字
* 半角空白
* 全角空白

正規化後の文字列に対して、桁数、使用可能文字およびチェックデジットを検証する。

ISBN-10では、末尾のチェックデジットとして `X` または `x` を許容する。

---

## 3.5 外部API取得要件

外部API通信では次を満たす。

* HTTPSを使用する。
* `requests.Session` を使用する。
* Sessionを外部から注入できる。
* 接続timeoutを設定する。
* 読み取りtimeoutを設定する。
* HTTPステータスを確認する。
* JSON解析エラーを処理する。
* HTTP 429を専用エラーとして扱う。
* APIキーをソースコードへ直接記述しない。
* APIキーをログへ出力しない。
* 自動テストでは実APIへ接続しない。

timeoutは次をDesign Freeze値とする。

```python
timeout = (5, 10)
```

各値の意味は次のとおりである。

| 値   | 意味          |
| :-- | :---------- |
| 5秒  | 接続timeout   |
| 10秒 | 読み取りtimeout |

---

## 3.6 GUI要件

GUIには、ISBN欄の近くへ書誌情報取得ボタンを配置する。

ボタン名は、実装時の既存画面との整合性を考慮して決定する。

候補例は次のとおりである。

```text
書籍情報取得
ISBNから取得
書誌情報取得
```

取得処理中は、同じ操作を連続実行できないようにボタンを無効化する。

処理終了後は、成功または失敗にかかわらずボタンを有効状態へ戻す。

---

## 3.7 上書き確認要件

書誌情報取得によって変更される可能性がある入力欄に、すでに値が存在する場合は、通信開始前に確認ダイアログを表示する。

確認対象は次の項目とする。

* 書籍名
* 著者名
* 出版社
* 出版形態
* 内容紹介

ISBN欄そのものは検索キーであるため、上書き確認対象に含めない。

利用者がキャンセルした場合は、外部API Clientを呼び出さない。

---

## 3.8 GUI反映要件

取得結果をGUIへ反映する際は、次の規則を適用する。

* 取得値が `None` の項目は変更しない。
* 空文字列は有効な取得値として扱わない。
* 取得対象項目だけを変更する。
* 雑誌コード、読了年月、備考を変更しない。
* データベースへの登録処理を実行しない。
* 取得元をステータス表示へ利用できる。
* 取得結果を利用者が編集できる状態を維持する。

---

## 3.9 成功時の表示要件

取得成功時は、通常の情報ダイアログを表示せず、ステータスバーへ結果を表示する。

表示例は次のとおりである。

```text
書籍情報を取得しました。
```

取得元を含める場合は次のように表示する。

```text
書籍情報を取得しました。取得元: Google Books、openBD
```

成功のたびにモーダルダイアログを表示すると操作を中断するため、通常成功時はステータス表示を採用する。

---

## 3.10 エラー表示要件

エラーは内容に応じて分類し、利用者が次に取るべき行動を判断できる表現とする。

| エラー      | 表示方法     | 例                               |
| :------- | :------- | :------------------------------ |
| ISBN形式不正 | 警告ダイアログ  | ISBNの形式を確認してください。               |
| 対象書籍なし   | 情報ダイアログ  | 該当する書籍情報が見つかりませんでした。            |
| 利用制限     | 警告ダイアログ  | APIの利用制限に達しました。時間をおいて再試行してください。 |
| 接続失敗     | エラーダイアログ | インターネット接続を確認してください。             |
| 応答不正     | エラーダイアログ | 書籍情報サービスから正しい応答を取得できませんでした。     |
| 想定外エラー   | エラーダイアログ | 書籍情報の取得中にエラーが発生しました。            |

内部例外の詳細、URL、APIキー、スタックトレースをそのまま利用者へ表示しない。

---

## 3.11 非機能要件

### 3.11.1 保守性

* 外部APIごとの実装を独立させる。
* API仕様変更の影響範囲をClient内に限定する。
* 統合ルールをServiceへ集約する。
* GUIへAPI固有処理を記述しない。
* 設計意図をDocstringおよび設計書へ残す。

### 3.11.2 拡張性

* 新しい取得元をClient追加で対応できる。
* Clientの優先順位を登録順で変更できる。
* GUIを変更せずに取得元を追加できる。
* 将来キャッシュや非同期処理を追加できる。

### 3.11.3 テスト容易性

* Sessionを差し替えられる。
* ClientをFakeへ差し替えられる。
* Fixture JSONで変換処理を検証できる。
* 自動テストで外部ネットワークを使用しない。
* Service単体で統合規則を検証できる。

### 3.11.4 可用性

* 一つのClient障害で全体を直ちに失敗させない。
* 一部項目だけでも有効結果として扱う。
* 外部APIが利用できなくても既存CRUD機能は利用できる。
* timeoutによって無制限待機を防止する。

### 3.11.5 セキュリティ

* APIキーを環境変数から取得する。
* APIキーをリポジトリへ保存しない。
* HTTPSを利用する。
* 外部データを信頼済みデータとして扱わない。
* HTMLやスクリプトをGUIで実行しない。
* Rawレスポンスに認証情報を含めない。

---

## 3.12 制約

本機能には次の制約がある。

* 外部APIの提供状況に依存する。
* APIごとに書誌情報の収録範囲が異なる。
* ISBNが正しくても情報が登録されていない場合がある。
* 同一書籍でも取得元によって表記が異なる場合がある。
* 著者名の完全な正規化は第1段階では行わない。
* 出版形態を必ず判定できるとは限らない。
* 内容紹介が取得できない書籍がある。
* 表紙画像URLが恒久的に有効とは限らない。
* API利用規約や仕様が将来変更される可能性がある。

---

## 3.13 受入れの前提

本機能は、外部APIから完全な書誌情報を必ず取得することを保証するものではない。

第1段階の受入れ基準は、次の状態を実現することである。

* 有効なISBNから取得処理を開始できる。
* 一つ以上の取得元から有効な書誌情報を得られる。
* 取得できた項目をフォームへ反映できる。
* 不足項目を別の取得元で補完できる。
* 取得失敗時にアプリが異常終了しない。
* 既存CRUD処理へ影響を与えない。
* 利用者が確認してから保存できる。

---

# 4. システム構成

## 4.1 全体構成

book_manager全体の基本構成は次のとおりである。

```text
GUI
 ↓
BookService
 ↓
Repository
 ↓
SQLite
```

外部書誌情報取得機能は、これとは別の経路として追加する。

```text
GUI
 ↓
BookMetadataService
 ↓
BookMetadataClient
 ├─ GoogleBooksClient
 └─ OpenBdClient
```

二つの経路は、GUIの入力フォームを共有するが、処理責務は分離する。

---

## 4.2 既存CRUD経路

既存の書籍登録、更新、削除および検索は、次の経路を使用する。

```text
GUI
 ↓
BookService
 ↓
Repository
 ↓
SQLite
```

各構成要素の責務は次のとおりである。

| 構成要素        | 責務                 |
| :---------- | :----------------- |
| GUI         | 利用者入力と画面表示         |
| BookService | 書籍管理の業務処理、検証、モデル変換 |
| Repository  | SQL発行、永続化、検索       |
| SQLite      | 書籍データの保存           |

外部書誌情報取得機能は、この経路を変更しない。

---

## 4.3 外部取得経路

外部書誌情報取得では、次の経路を使用する。

```text
GUI
 ↓
BookMetadataService
 ↓
BookMetadataClient
 ↓
外部API
```

各構成要素の責務は次のとおりである。

| 構成要素                | 責務                       |
| :------------------ | :----------------------- |
| GUI                 | ISBN入力、上書き確認、結果反映、通知     |
| BookMetadataService | ISBN処理、Client制御、統合、例外集約  |
| BookMetadataClient  | 外部API通信、レスポンス解析、内部形式への変換 |
| 外部API               | 書誌情報の提供                  |

取得結果は `FetchedBookData` としてGUIへ返される。

---

## 4.4 二つのServiceの分離

`BookService` と `BookMetadataService` は、それぞれ別のユースケースを担当する。

| Service             | 担当                   |
| :------------------ | :------------------- |
| BookService         | 書籍データの登録、更新、削除、検索    |
| BookMetadataService | ISBNから外部書誌情報を取得し統合する |

`BookMetadataService` は `BookService` を呼び出さない。

`BookService` も `BookMetadataService` を呼び出さない。

GUIがそれぞれを必要な操作に応じて呼び出す。

この分離により、外部APIが停止していても書籍管理機能は継続して利用できる。

---

## 4.5 データの流れ

外部書誌情報取得から保存までのデータの流れは次のとおりである。

```text
1. 利用者がISBNを入力する。
2. GUIが上書き確認を行う。
3. GUIがBookMetadataServiceを呼び出す。
4. ServiceがISBNを正規化・検証する。
5. Serviceが問い合わせ用ISBN-13を生成する。
6. Serviceが各Clientを順番に呼び出す。
7. Clientが外部APIレスポンスをFetchedBookDataへ変換する。
8. Serviceが取得結果を統合する。
9. GUIが統合結果を入力フォームへ反映する。
10. 利用者が内容を確認・修正する。
11. 利用者が登録または更新を実行する。
12. GUIがBookServiceを呼び出す。
13. BookServiceがRepositoryを通じてSQLiteへ保存する。
```

外部APIから取得したデータが、`BookMetadataService` から直接SQLiteへ保存される経路は作らない。

---

## 4.6 依存関係

依存方向は次のとおりとする。

```text
GUI
 ├─ depends on → BookService
 └─ depends on → BookMetadataService

BookService
 └─ depends on → Repository

BookMetadataService
 ├─ depends on → BookMetadataClient Protocol
 └─ depends on → FetchedBookData

GoogleBooksClient
 ├─ conforms to → BookMetadataClient Protocol
 └─ creates → FetchedBookData

OpenBdClient
 ├─ conforms to → BookMetadataClient Protocol
 └─ creates → FetchedBookData

Repository
 └─ depends on → SQLite
```

次の依存は禁止する。

```text
Repository → BookMetadataService
BookService → GoogleBooksClient
BookService → OpenBdClient
Client → GUI
Client → Repository
FetchedBookData → SQLite
```

---

## 4.7 オブジェクト生成

具象Clientの生成と組み立ては、アプリケーション起動時の構成箇所で行う。

例を次に示す。

```python
session = requests.Session()

google_books_client = GoogleBooksClient(
    session=session,
    api_key=google_books_api_key,
)

openbd_client = OpenBdClient(
    session=session,
)

metadata_service = BookMetadataService(
    clients=[
        google_books_client,
        openbd_client,
    ],
)
```

生成した `BookMetadataService` はGUIへ注入する。

GUI内部でClientを直接生成しない。

---

## 4.8 Sessionの扱い

HTTP通信には `requests.Session` を使用する。

Sessionを利用する目的は次のとおりである。

* 接続を再利用できる。
* 共通ヘッダーを管理できる。
* テスト時にFake Sessionへ差し替えられる。
* Client内部で毎回通信オブジェクトを生成せずに済む。
* 将来リトライ設定などを集中管理できる。

Google BooksとopenBDで同一Sessionを共有してもよいが、Client間の独立性を重視して別Sessionを注入する構成も許容する。

第1段階では、アプリケーション構成箇所からSessionを注入できることを必須とする。

---

## 4.9 設定値

外部書誌情報取得に関する設定値の候補は次のとおりである。

| 設定                 | 管理方法               |
| :----------------- | :----------------- |
| Google Books APIキー | 環境変数               |
| 接続timeout          | コード定数または設定オブジェクト   |
| 読み取りtimeout        | コード定数または設定オブジェクト   |
| Client登録順序         | アプリケーション構成         |
| openBD使用有無         | 将来の設定またはClient登録有無 |
| User-Agent         | 必要に応じてSession設定    |

第1段階では、過度な設定ファイル化を行わない。

変更の可能性が高い値、秘密情報および環境依存値だけを外部設定とする。

---

## 4.10 外部取得機能が利用できない場合

外部取得機能が利用できない場合でも、book_manager本体は起動し、既存CRUD機能を使用できなければならない。

例えば次の場合である。

* インターネットへ接続できない。
* Google Booksが停止している。
* openBDが停止している。
* APIキーが設定されていない。
* API利用制限に達している。
* 外部APIのレスポンス仕様が変更された。

外部API障害を理由に、SQLiteの既存データを閲覧・編集できなくしてはならない。

---

## 4.11 システム境界

本機能のシステム境界は次のとおりである。

```text
book_manager内部
────────────────────────────
GUI
BookMetadataService
BookMetadataClient
FetchedBookData
ISBN処理
例外変換
────────────────────────────
外部システム
Google Books API
openBD API
```

外部システムが返すJSONは、Client境界を越えてそのまま内部へ持ち込まない。

Clientは外部形式を内部の `FetchedBookData` へ変換する責任を持つ。

---

# 5. 全体アーキテクチャ

## 5.1 アーキテクチャ概要

外部書誌情報取得機能は、レイヤー分離と依存性逆転を意識した構造とする。

全体像を次に示す。

```text
┌─────────────────────────────────────┐
│                GUI                  │
│ ISBN入力・確認・結果反映・通知      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│       BookMetadataService           │
│ ISBN処理・Client制御・結果統合      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      BookMetadataClient Protocol    │
│      共通の外部取得インターフェース │
└─────────────┬───────────────┬───────┘
              │               │
              ▼               ▼
┌──────────────────────┐ ┌──────────────────────┐
│ GoogleBooksClient    │ │ OpenBdClient         │
│ Google Books固有処理 │ │ openBD固有処理       │
└──────────┬───────────┘ └──────────┬───────────┘
           │                        │
           ▼                        ▼
┌──────────────────────┐ ┌──────────────────────┐
│ Google Books API     │ │ openBD API           │
└──────────────────────┘ └──────────────────────┘
```

---

## 5.2 GUI層

GUI層は、利用者とのやり取りだけを担当する。

主な責務は次のとおりである。

* ISBN入力値を取得する。
* 既存入力値の有無を確認する。
* 必要に応じて上書き確認を表示する。
* 取得ボタンの有効・無効を切り替える。
* `BookMetadataService` を呼び出す。
* `FetchedBookData` をフォームへ反映する。
* 成功メッセージをステータスバーへ表示する。
* 例外に応じたダイアログを表示する。

GUI層は次の処理を行わない。

* HTTPリクエストの生成
* URLやクエリパラメータの組み立て
* JSON解析
* ISBN-10からISBN-13への変換
* 複数Client結果の統合
* API固有エラーの解析
* APIキー管理
* データベースへの自動保存

---

## 5.3 Application Service層

`BookMetadataService` は、ISBNから書誌情報を取得するユースケースを実現する。

主な責務は次のとおりである。

* ISBNの正規化
* ISBNの形式検証
* チェックデジット検証
* ISBN-10からISBN-13への変換
* Clientの順次呼び出し
* Clientごとの例外収集
* 取得結果の統合
* 最終的な成功または失敗の判定
* GUIへ返す例外の選択

Serviceは、個々の外部APIのURLやJSON構造を認識しない。

---

## 5.4 Client層

Client層は外部サービスとの境界である。

各Clientは次の処理を担当する。

* リクエストURLとパラメータの生成
* HTTP通信
* HTTPステータスの判定
* API固有レスポンスの解析
* ISBN一致候補の選択
* 内部データモデルへの変換
* 外部例外からアプリケーション例外への変換

Clientは、GUIへメッセージを表示しない。

Clientは、データベースへ書き込まない。

Clientは、別のClientの結果を参照しない。

---

## 5.5 内部データモデル

外部API ClientからServiceへ返すデータには、`FetchedBookData` を使用する。

概念的な構造は次のとおりである。

```python
@dataclass(slots=True)
class FetchedBookData:
    isbn: str
    title: str | None = None
    authors: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    publication_format: str | None = None
    description: str | None = None
    cover_image_url: str | None = None
    sources: tuple[str, ...] = ()
    raw_data: dict[str, object] = field(
        default_factory=dict,
    )
```

正式な項目名と型は、第6章以降で定義する。

---

## 5.6 依存性逆転

`BookMetadataService` は、`GoogleBooksClient` や `OpenBdClient` といった具象クラスへ直接依存しない。

共通の `BookMetadataClient` Protocolへ依存する。

```text
BookMetadataService
        │
        ▼
BookMetadataClient Protocol
        ▲
        │
 ┌──────┴─────────┐
 │                │
GoogleBooksClient OpenBdClient
```

この構造により、上位方針であるServiceが、外部API固有の下位実装に強く結合することを防ぐ。

---

## 5.7 Open/Closed Principle

本機能は、新しい取得元の追加に対して開いており、既存Serviceの修正に対して閉じた構造を目指す。

例えば新しいClientを追加する場合は、次のように構成できる。

```python
metadata_service = BookMetadataService(
    clients=[
        GoogleBooksClient(...),
        OpenBdClient(...),
        NewBookMetadataClient(...),
    ],
)
```

新しいClientが `BookMetadataClient` Protocolへ適合していれば、Serviceの主要ロジックやGUIを変更する必要はない。

---

## 5.8 単一責任の原則

各主要クラスは一つの変更理由だけを持つ。

| クラス                 | 主な変更理由            |
| :------------------ | :---------------- |
| GUIクラス              | 画面構成や操作方法の変更      |
| BookMetadataService | 取得フローや統合規則の変更     |
| GoogleBooksClient   | Google Books仕様の変更 |
| OpenBdClient        | openBD仕様の変更       |
| FetchedBookData     | 内部書誌情報モデルの変更      |
| Repository          | SQLite永続化仕様の変更    |

外部APIのレスポンス項目名が変わっただけでGUIを修正する構造にはしない。

---

## 5.9 テスト可能性

アーキテクチャ上、各層を独立してテストできるようにする。

### Clientテスト

Fake SessionまたはMock Responseを使用し、次を検証する。

* パラメータ生成
* 正常レスポンス変換
* 対象なし
* HTTPエラー
* HTTP 429
* JSON解析失敗
* ISBN不一致候補
* 欠損項目

### Serviceテスト

Fake Clientを使用し、次を検証する。

* Client呼び出し順序
* ISBN正規化
* ISBN-10変換
* 空欄補完
* 先順位優先
* 部分失敗
* すべて対象なし
* すべて失敗
* 最終例外選択

### GUIテスト

ServiceをFakeへ差し替え、次を検証する。

* 上書き確認
* キャンセル
* ボタン状態
* フォーム反映
* 非対象項目の維持
* 成功表示
* エラーダイアログ
* 自動保存されないこと

---

## 5.10 外部障害からの隔離

外部APIは、次の理由により不安定な依存先として扱う。

* 通信障害
* DNS障害
* TLS障害
* サービス停止
* レート制限
* API仕様変更
* データ欠損
* 不正なレスポンス
* 利用規約変更
* 提供終了

これらの影響をClient層で吸収し、アプリケーション全体へ直接波及させない。

外部取得処理が失敗しても、既存の書籍登録、検索、編集および削除は継続して利用できる。

---

## 5.11 同期シーケンス

第1段階の基本シーケンスは次のとおりである。

```text
利用者
  │
  │ ISBN入力・取得操作
  ▼
GUI
  │
  │ fetch_by_isbn(isbn)
  ▼
BookMetadataService
  │
  │ fetch_by_isbn(isbn13)
  ▼
GoogleBooksClient
  │
  │ HTTPS
  ▼
Google Books API
  │
  │ JSON
  ▼
GoogleBooksClient
  │
  │ FetchedBookDataまたはNone
  ▼
BookMetadataService
  │
  │ fetch_by_isbn(isbn13)
  ▼
OpenBdClient
  │
  │ HTTPS
  ▼
openBD API
  │
  │ JSON
  ▼
OpenBdClient
  │
  │ FetchedBookDataまたはNone
  ▼
BookMetadataService
  │
  │ 統合結果
  ▼
GUI
  │
  │ フォーム反映
  ▼
利用者
```

---

## 5.12 設計上の禁止事項

次の実装は禁止する。

### GUIから直接APIを呼ぶ

```python
def on_fetch_clicked(self):
    response = requests.get(...)
```

### GUIでJSONを解析する

```python
title = response_json["items"][0]["volumeInfo"]["title"]
```

### Clientからダイアログを表示する

```python
messagebox.showerror(...)
```

### ClientからDBへ保存する

```python
repository.insert(...)
```

### ServiceでAPI固有キーを参照する

```python
volume_info = payload["volumeInfo"]
```

### 取得成功時に自動登録する

```python
metadata = service.fetch_by_isbn(isbn)
book_service.create(metadata)
```

これらは責務の混在、テスト困難および将来変更の影響拡大を招くため採用しない。

---

## 5.13 全体アーキテクチャの設計判断

本アーキテクチャは、小規模なデスクトップアプリケーションとしてはクラス数が増える。

しかし、外部APIは変更頻度と障害可能性が高く、既存CRUD処理とは性質が異なる。

そのため、初期実装の短さよりも、次を優先する。

* 外部API変更への耐性
* 既存機能との分離
* テスト可能性
* Client追加の容易さ
* エラー処理の一貫性
* 設計意図の明確さ

以上を、外部書誌情報取得機能の基本アーキテクチャとする。

---
# 6. データモデル

## 6.1 データモデルの目的

外部APIから取得した書誌情報は、API固有のJSON構造のままアプリケーション内部で扱わない。

各Clientは、取得したデータを共通の内部データモデルである `FetchedBookData` へ変換する。

`FetchedBookData` を使用する目的は次のとおりである。

* 外部APIごとのレスポンス形式の違いを吸収する。
* `BookMetadataService` がAPI固有の項目名を認識しないようにする。
* GUIが共通形式で取得結果を扱えるようにする。
* 複数の取得結果を同じ規則で統合できるようにする。
* テスト用データを簡単に作成できるようにする。
* 既存の書籍モデルと外部取得結果を分離する。

---

## 6.2 `BookItem` との分離

既存の書籍管理データには、`BookItem` を使用する。

外部APIから取得した一時的な情報には、`FetchedBookData` を使用する。

この二つは用途が異なるため、同じモデルを使用しない。

| モデル             | 用途                  |
| :-------------- | :------------------ |
| BookItem        | 登録済みまたは登録予定の書籍データ   |
| FetchedBookData | 外部APIから取得した一時的な書誌情報 |

`BookItem` には、利用者が管理する次のような項目が含まれる。

* 雑誌コード
* 読了年月
* 備考
* データベースID
* 作成日時
* 更新日時

これらは外部APIから取得する情報ではない。

一方、`FetchedBookData` には、外部取得処理に必要な次のような情報を保持する。

* 出版日
* 表紙画像URL
* 取得元
* Rawレスポンス

これらは第1段階ではデータベースへ保存しない。

---

## 6.3 `FetchedBookData` の定義

`FetchedBookData` は、次のような `dataclass` として定義する。

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FetchedBookData:
    """外部サービスから取得した書誌情報を保持する。"""

    isbn: str
    title: str | None = None
    authors: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    publication_format: str | None = None
    description: str | None = None
    cover_image_url: str | None = None
    sources: tuple[str, ...] = ()
    raw_data: dict[str, Any] = field(
        default_factory=dict,
    )
```

実装時には、プロジェクト全体の命名規則に合わせて型やDocstringを調整してよい。

ただし、モデルの責務と項目の意味は変更しない。

---

## 6.4 各フィールドの定義

| フィールド              | 型               |  必須 | 説明                |
| :----------------- | :-------------- | :-: | :---------------- |
| isbn               | str             |  必須 | 利用者が入力した正規化済みISBN |
| title              | str | None      |  任意 | 書籍名               |
| authors            | str | None      |  任意 | GUIへ反映する著者名文字列    |
| publisher          | str | None      |  任意 | 出版社名              |
| publication_date   | str | None      |  任意 | 取得元が返した出版日        |
| publication_format | str | None      |  任意 | 文庫、単行本、電子書籍など     |
| description        | str | None      |  任意 | 内容紹介              |
| cover_image_url    | str | None      |  任意 | 表紙画像のURL          |
| sources            | tuple[str, ...] |  任意 | 有効な情報を提供した取得元     |
| raw_data           | dict[str, Any]  |  任意 | 取得元別のRawレスポンス     |

---

## 6.5 ISBNフィールド

`FetchedBookData.isbn` には、利用者が入力したISBNを正規化した値を保持する。

正規化では、ハイフンおよび空白を除去する。

ISBN-10を入力した場合でも、保存候補として保持するISBNは、原則として正規化済みISBN-10とする。

外部APIへの問い合わせに使用したISBN-13へ、自動的に置き換えない。

例を次に示す。

```text
入力値:
4-10-110918-4

正規化済み入力値:
4101109184

外部API問い合わせ値:
9784101109180

FetchedBookData.isbn:
4101109184
```

問い合わせ用ISBNと利用者入力値を分離することで、利用者が入力した識別子を維持する。

---

## 6.6 著者フィールド

外部APIでは、著者情報が配列として返される場合がある。

`FetchedBookData.authors` では、GUIへ反映できる一つの文字列に変換して保持する。

複数著者の区切り文字は、全角読点「、」を基本とする。

例を次に示す。

```text
APIレスポンス:
["山田太郎", "鈴木花子"]

FetchedBookData.authors:
山田太郎、鈴木花子
```

著者の順序は、取得元が返した順序を維持する。

第1段階では、姓と名の並び替え、生没年の除去、役割表記の分離など、高度な著者名正規化は行わない。

---

## 6.7 出版日フィールド

`publication_date` は文字列として保持する。

外部APIによって、出版日の精度が異なる可能性があるため、無理にPythonの日付型へ変換しない。

想定される形式は次のとおりである。

```text
2026
2026-07
2026-07-24
200305
```

第1段階では、外部取得結果として保持するだけとし、既存データベースへ保存しない。

将来、出版日を正式な管理項目へ追加する場合は、日付精度を保持できる別設計を行う。

---

## 6.8 出版形態フィールド

`publication_format` は、既存アプリケーションで使用する出版形態へ明確に対応できる場合だけ設定する。

初期候補は次のとおりである。

```text
文庫
単行本
電子書籍
```

外部APIが返す分類情報から出版形態を確実に判断できない場合は、`None` とする。

推測だけで出版形態を設定してはならない。

例えば、Google Booksの `printType` が `BOOK` であっても、それだけでは文庫か単行本かを判定できない。

---

## 6.9 内容紹介フィールド

`description` には、外部APIから取得した内容紹介を文字列として保持する。

次の処理を行う。

* 前後の空白を除去する。
* 空文字列は `None` にする。
* 必要な改行は保持する。
* HTMLをそのまま実行しない。
* スクリプトを解釈しない。
* 文字化けした値を無理に修正しない。

内容紹介が取得できない場合は、`None` とする。

取得できなかったことを理由に、GUIへすでに入力されている内容紹介を消去してはならない。

---

## 6.10 表紙画像URLフィールド

`cover_image_url` には、画像自体ではなくURL文字列だけを保持する。

第1段階では、次の処理を行わない。

* 画像ファイルのダウンロード
* データベースへの画像保存
* URLの永続保存
* GUIでの表紙画像表示
* 画像キャッシュ
* 画像形式の変換

表紙画像URLは、将来の拡張に備えた参考情報として保持する。

外部サービスが返すURLは、将来も有効であることを保証しない。

---

## 6.11 取得元フィールド

`sources` には、有効な書誌情報を提供した取得元を保持する。

例を次に示す。

```python
("Google Books",)
```

```python
("Google Books", "openBD")
```

取得元の順序は、Clientの呼び出し優先順位を維持する。

同じ取得元を重複して含めない。

`sources` は、次の用途に使用する。

* 成功時のステータス表示
* テスト時の統合結果確認
* デバッグ
* 将来の取得元表示

第1段階ではデータベースへ保存しない。

---

## 6.12 Rawデータフィールド

`raw_data` には、取得元別のRawレスポンスを保持できる。

推奨形式を次に示す。

```python
{
    "Google Books": {
        "query": {
            "isbn": "9784163917733",
        },
        "response": {
            # Google Booksレスポンス
        },
    },
    "openBD": {
        "query": {
            "isbn": "9784163917733",
        },
        "response": {
            # openBDレスポンス
        },
    },
}
```

Rawデータは次の目的に限って使用する。

* Client変換処理のテスト
* 障害調査
* 開発時のデバッグ
* 将来の項目追加検討

RawデータはSQLiteへ保存しない。

また、次の情報を含めてはならない。

* APIキー
* Authorizationヘッダー
* Cookie
* セッショントークン
* その他の秘密情報

---

## 6.13 空値の扱い

外部APIから取得した空文字列は、内部モデルでは `None` として扱う。

次の値は、有効な取得値として扱わない。

```python
None
""
" "
"\t"
"\n"
```

共通の文字列正規化関数を用意することを推奨する。

```python
def normalize_optional_text(
    value: object,
) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    return normalized or None
```

統合処理では、`None` だけでなく空白だけの文字列も空欄として判定する。

---

## 6.14 モデルの変更可能性

第1段階では、`FetchedBookData` を通常の変更可能な `dataclass` として定義する。

ただし、Clientが生成した後にGUIがモデル自体を書き換える使い方は避ける。

GUIへ反映する際は、モデルの値を入力フォームへ設定するだけとする。

将来、次の要件が生じた場合は `frozen=True` を検討する。

* キャッシュのキーとして使用する。
* ハッシュ可能な値として扱う。
* 生成後の変更を厳密に禁止する。
* 並列処理で安全に共有する。

---

## 6.15 モデルの配置

推奨ファイル配置は次のとおりである。

```text
src/
└── book_manager/
    └── models/
        ├── book_item.py
        └── fetched_book_data.py
```

既存のモデル構成が異なる場合は、プロジェクト全体の構成へ合わせてよい。

ただし、外部API Clientファイル内に `FetchedBookData` を直接定義しない。

複数ClientとServiceから参照される共通モデルとして独立させる。

---

## 6.16 データモデルの設計判断

既存の `BookItem` を外部取得結果にも流用すると、次の問題が発生する。

* 外部取得時点では存在しない必須項目への対応が必要になる。
* データベース項目と一時的な取得項目が混在する。
* Rawレスポンスや取得元を `BookItem` へ追加する必要が生じる。
* 外部取得だけで保存可能な完成データと誤認しやすくなる。
* GUI反映前に不要な変換が増える。

そのため、外部取得結果専用の `FetchedBookData` を採用する。

---

# 7. クラス設計

## 7.1 クラス一覧

外部書誌情報取得機能の主要クラスを次に示す。

| クラスまたはProtocol              | 役割                      |
| :-------------------------- | :---------------------- |
| FetchedBookData             | 外部取得結果を保持する             |
| BookMetadataClient          | Client共通契約を定義する         |
| GoogleBooksClient           | Google Booksから取得する      |
| OpenBdClient                | openBDから取得する            |
| BookMetadataService         | ISBN処理、Client制御、結果統合を行う |
| BookMetadataError           | 外部書誌情報取得例外の基底クラス        |
| BookMetadataConnectionError | 接続失敗を表す                 |
| BookMetadataResponseError   | 不正応答を表す                 |
| BookMetadataRateLimitError  | 利用制限を表す                 |
| BookMetadataNotFoundError   | 対象書籍なしを表す               |

---

## 7.2 クラス間の関係

```text
GUI
 │
 │ uses
 ▼
BookMetadataService
 │
 │ depends on
 ▼
BookMetadataClient Protocol
 ▲                       ▲
 │ implements            │ implements
 │                       │
GoogleBooksClient     OpenBdClient
 │                       │
 └──────────┬────────────┘
            │ creates
            ▼
     FetchedBookData
```

例外は各ClientとServiceから送出され、GUIが最終的に表示へ変換する。

---

## 7.3 `BookMetadataClient`

`BookMetadataClient` は、外部書誌情報取得Clientが満たす共通契約を定義する。

```python
from typing import Protocol

from book_manager.models.fetched_book_data import (
    FetchedBookData,
)


class BookMetadataClient(Protocol):
    @property
    def source_name(self) -> str:
        """取得元名を返す。"""
        ...

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        """ISBNから書誌情報を取得する。"""
        ...
```

Clientは、対象書籍が見つからない場合に `None` を返す。

通信やレスポンスに異常がある場合は、対応するアプリケーション例外を送出する。

---

## 7.4 `GoogleBooksClient`

概念的なコンストラクタを次に示す。

```python
class GoogleBooksClient:
    def __init__(
        self,
        session: requests.Session,
        api_key: str | None = None,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._timeout = timeout
```

主な責務は次のとおりである。

* Google Books用パラメータ生成
* APIキーの付加
* HTTP通信
* HTTPステータス判定
* Volume候補の取得
* ISBN一致候補の選択
* `volumeInfo` の解析
* `FetchedBookData` への変換
* Google Books固有エラーの変換

---

## 7.5 `OpenBdClient`

概念的なコンストラクタを次に示す。

```python
class OpenBdClient:
    def __init__(
        self,
        session: requests.Session,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        self._session = session
        self._timeout = timeout
```

主な責務は次のとおりである。

* openBD用パラメータ生成
* HTTP通信
* HTTPステータス判定
* 対象なしレスポンスの判定
* 要約情報の解析
* 必要に応じた詳細情報の解析
* `FetchedBookData` への変換
* openBD固有エラーの変換

---

## 7.6 `BookMetadataService`

概念的なコンストラクタを次に示す。

```python
class BookMetadataService:
    def __init__(
        self,
        clients: list[BookMetadataClient],
    ) -> None:
        self._clients = tuple(clients)
```

Client一覧は、外部から注入する。

Service内部で具象Clientを生成しない。

主な責務は次のとおりである。

* ISBN正規化
* ISBN検証
* ISBN-10からISBN-13への変換
* Clientの順次呼び出し
* Clientエラーの収集
* 取得結果の統合
* 最終的な成功判定
* 最終例外の選択

---

## 7.7 例外クラス

例外階層は次の構造とする。

```text
BookMetadataError
├─ BookMetadataConnectionError
├─ BookMetadataResponseError
├─ BookMetadataRateLimitError
└─ BookMetadataNotFoundError
```

概念的な定義を次に示す。

```python
class BookMetadataError(Exception):
    """外部書誌情報取得に関する基底例外。"""


class BookMetadataConnectionError(BookMetadataError):
    """外部サービスへの接続失敗。"""


class BookMetadataResponseError(BookMetadataError):
    """外部サービスからの応答不正。"""


class BookMetadataRateLimitError(BookMetadataError):
    """外部サービスの利用制限。"""


class BookMetadataNotFoundError(BookMetadataError):
    """対象書籍情報が見つからない。"""
```

詳細な例外設計は、第16章および第17章で定義する。

---

## 7.8 可視性

Client内部の補助メソッドは、原則として非公開メソッドとする。

例を次に示す。

```python
def _build_params(...):
    ...

def _request_json(...):
    ...

def _select_matching_item(...):
    ...

def _convert_response(...):
    ...
```

公開メソッドは、原則として `fetch_by_isbn()` に限定する。

API固有の細かい変換処理を、他の層から直接呼び出さない。

---

## 7.9 クラスの状態

各Clientは、次の構成情報だけをインスタンス状態として保持する。

* Session
* timeout
* APIキー
* 必要な固定設定

前回取得結果や前回ISBNなど、検索ごとに変化する情報をインスタンス変数へ保持しない。

`BookMetadataService` も、Client一覧以外の検索状態を保持しない。

これにより、複数回の検索が互いに影響しない。

---

## 7.10 クラス生成箇所

クラスの生成は、アプリケーション起動処理または依存関係を組み立てる専用箇所で行う。

```python
session = requests.Session()

clients: list[BookMetadataClient] = [
    GoogleBooksClient(
        session=session,
        api_key=google_books_api_key,
    ),
    OpenBdClient(
        session=session,
    ),
]

metadata_service = BookMetadataService(
    clients=clients,
)

application = BookManagerApplication(
    book_service=book_service,
    metadata_service=metadata_service,
)
```

GUIイベント内でClientやServiceを都度生成しない。

---

## 7.11 Docstring

公開クラスと公開メソッドにはDocstringを記述する。

Docstringには、少なくとも次を記述する。

* クラスまたはメソッドの責務
* 引数の意味
* 戻り値
* 送出する主な例外
* `None` を返す条件

例を次に示す。

```python
def fetch_by_isbn(
    self,
    isbn: str,
) -> FetchedBookData | None:
    """ISBNに対応する書誌情報を取得する。

    Args:
        isbn:
            検証済みの問い合わせ用ISBN-13。

    Returns:
        書誌情報が見つかった場合は取得結果。
        対象が見つからない場合はNone。

    Raises:
        BookMetadataConnectionError:
            外部サービスへ接続できない場合。
        BookMetadataRateLimitError:
            利用制限に達した場合。
        BookMetadataResponseError:
            応答を正しく解析できない場合。
    """
```

---

## 7.12 型ヒント

対象モジュールでは、原則として次を使用する。

```python
from __future__ import annotations
```

公開インターフェースには型ヒントを付ける。

`dict` や `list` を過度に具体化できない外部JSONについては、無理に複雑な型を定義せず、境界内部で安全に型確認を行う。

`Any` は外部レスポンス境界とRawデータに限定して使用する。

---

## 7.13 クラス設計上の禁止事項

次の設計を禁止する。

* `BookMetadataService` 内で `requests.get()` を直接呼ぶ。
* Client内でTkinterウィジェットを操作する。
* Client内でRepositoryを呼ぶ。
* `FetchedBookData` 内でHTTP通信を行う。
* GUIクラスをClientへ渡す。
* Client間で互いを呼び出す。
* グローバル変数で検索結果を共有する。
* APIキーをクラス定数として直接記述する。
* 外部レスポンス全体を `BookItem` へ格納する。

---

# 8. API Client設計

## 8.1 Clientの共通責務

各API Clientは、外部サービスとの通信境界として、次の責務を持つ。

1. 問い合わせパラメータを生成する。
2. Sessionを使用してHTTPSリクエストを送信する。
3. HTTPステータスを判定する。
4. JSONレスポンスを取得する。
5. 対象書籍の有無を判定する。
6. 必要な書誌項目を抽出する。
7. 内部データモデルへ変換する。
8. 外部例外をアプリケーション例外へ変換する。

---

## 8.2 Clientへの入力

`fetch_by_isbn()` に渡されるISBNは、Serviceで次の処理を完了した問い合わせ用ISBN-13とする。

* ハイフン除去
* 空白除去
* 桁数検証
* チェックデジット検証
* ISBN-10からISBN-13への変換

したがって、ClientはISBN変換処理を重複して実装しない。

ただし、防御的処理として空文字列などを受け取った場合は、`ValueError` またはアプリケーション例外としてもよい。

---

## 8.3 Clientからの戻り値

対象ISBNの有効な書誌情報を取得できた場合は、`FetchedBookData` を返す。

対象が登録されていない場合は、`None` を返す。

```python
FetchedBookData | None
```

次の状態は区別する。

| 状態          | 戻り値または例外                    |
| :---------- | :-------------------------- |
| 対象書籍を取得     | FetchedBookData             |
| 正常応答だが対象なし  | None                        |
| 接続失敗        | BookMetadataConnectionError |
| HTTP 429    | BookMetadataRateLimitError  |
| その他のHTTP異常  | BookMetadataResponseError   |
| JSON解析失敗    | BookMetadataResponseError   |
| 想定外のレスポンス構造 | BookMetadataResponseError   |

---

## 8.4 `source_name`

各Clientは、取得元を識別する `source_name` を提供する。

```python
@property
def source_name(self) -> str:
    return "Google Books"
```

初期値は次のとおりとする。

```text
Google Books
openBD
```

`source_name` は次の用途に使用する。

* `FetchedBookData.sources`
* Rawデータのキー
* ログ
* 成功時の取得元表示
* テスト結果

実行中に値を変更しない。

---

## 8.5 Session注入

Clientは、コンストラクタで `requests.Session` を受け取る。

```python
def __init__(
    self,
    session: requests.Session,
    timeout: tuple[int, int] = (5, 10),
) -> None:
    self._session = session
    self._timeout = timeout
```

Sessionを注入する理由は次のとおりである。

* テストでFake Sessionへ置き換えられる。
* 接続再利用ができる。
* 共通ヘッダーを設定できる。
* Client内部でSession生成を固定しない。
* 将来の通信設定変更へ対応しやすい。

---

## 8.6 HTTPリクエスト

リクエストは、原則として次の形式で実行する。

```python
response = self._session.get(
    self.BASE_URL,
    params=params,
    timeout=self._timeout,
)
```

URLへクエリ文字列を直接連結せず、`params` を使用する。

次の形式は採用しない。

```python
url = f"{base_url}?isbn={isbn}&key={api_key}"
response = requests.get(url)
```

`params` を使用することで、文字列連結ミスやエンコード問題を避ける。

---

## 8.7 HTTPステータス処理

Clientは、HTTPレスポンスを受け取った後、ステータスを確認する。

HTTP 429は、他のHTTPエラーより先に判定する。

概念例を次に示す。

```python
if response.status_code == 429:
    raise BookMetadataRateLimitError(
        f"{self.source_name}の利用制限に達しました。"
    )

try:
    response.raise_for_status()
except requests.HTTPError as exc:
    raise BookMetadataResponseError(
        f"{self.source_name}から正常な応答を"
        "取得できませんでした。"
    ) from exc
```

利用者向けのメッセージと、開発者向けログ情報は分離する。

---

## 8.8 接続例外処理

`requests` が送出する接続関連例外は、`BookMetadataConnectionError` へ変換する。

対象例は次のとおりである。

* `requests.ConnectionError`
* `requests.Timeout`
* DNS関連エラー
* TLS接続エラー
* プロキシ接続エラー

概念例を次に示す。

```python
try:
    response = self._session.get(
        self.BASE_URL,
        params=params,
        timeout=self._timeout,
    )
except requests.RequestException as exc:
    raise BookMetadataConnectionError(
        f"{self.source_name}へ接続できませんでした。"
    ) from exc
```

ただし、HTTP応答が返った後のエラーと、接続自体が成立しないエラーは可能な範囲で区別する。

---

## 8.9 JSON解析

JSON解析に失敗した場合は、`BookMetadataResponseError` とする。

```python
try:
    payload = response.json()
except ValueError as exc:
    raise BookMetadataResponseError(
        f"{self.source_name}の応答を解析できませんでした。"
    ) from exc
```

JSONとして解析できても、期待するトップレベル型でない場合は、不正応答として扱う。

例を次に示す。

```python
if not isinstance(payload, dict):
    raise BookMetadataResponseError(
        f"{self.source_name}の応答形式が不正です。"
    )
```

openBDのように配列を返すAPIでは、Clientごとに期待するトップレベル型を判定する。

---

## 8.10 レスポンス変換

レスポンス変換では、辞書キーが必ず存在すると仮定しない。

次のような直接参照を避ける。

```python
title = payload["items"][0]["volumeInfo"]["title"]
```

代わりに、型と存在を確認しながら取得する。

```python
items = payload.get("items")

if not isinstance(items, list):
    return None
```

外部サービスは、同じHTTP 200でも項目欠損や構造差を含む場合があるため、防御的に解析する。

---

## 8.11 ISBN候補照合

検索APIから結果が返った場合でも、その候補が入力ISBNに一致するとは限らない。

Clientは、レスポンス内のISBNを正規化し、問い合わせISBNと比較する。

一致候補だけを採用する。

一致候補がない場合は `None` を返す。

検索結果の先頭要素を無条件に採用してはならない。

---

## 8.12 文字列正規化

Clientは、外部データを `FetchedBookData` へ設定する前に、文字列を共通ルールで正規化する。

* 文字列型か確認する。
* 前後空白を除去する。
* 空文字列を `None` にする。
* API固有のオブジェクトを文字列化しない。
* 必要以上の表記変更を行わない。

著者配列などの複合値は、Client内で内部モデル向けの文字列へ変換する。

---

## 8.13 Rawデータ

各Clientは、必要に応じてRawレスポンスを `FetchedBookData.raw_data` へ設定する。

```python
raw_data={
    self.source_name: {
        "query": {
            "isbn": isbn,
        },
        "response": payload,
    },
}
```

RawデータにAPIキーを含めない。

リクエストパラメータ全体を保存する場合は、APIキーを除外またはマスクする。

---

## 8.14 Clientの独立性

各Clientは、他のClientの存在や優先順位を認識しない。

例えば `OpenBdClient` は、Google Booksで値が取得できたかどうかを判断しない。

Clientは、自分の取得元から得られる情報を可能な範囲で返す。

どの値を採用するかは、`BookMetadataService` が統合規則に従って決定する。

---

## 8.15 リトライ方針

第1段階では、Client内部で自動リトライを行わない。

理由は次のとおりである。

* 取得時間が予測しにくくなる。
* GUIの同期処理時間が長くなる。
* 429時に不要な再試行を行う可能性がある。
* テストが複雑になる。
* 外部サービスへ過剰な負荷を与える可能性がある。

一時的な通信失敗時は、利用者が再度取得操作を行う。

将来自動リトライを導入する場合は、回数、待機時間、対象ステータスおよびGUI応答性を別途設計する。

---

## 8.16 API Client設計上の禁止事項

次の実装は禁止する。

* timeoutを指定しない通信
* APIキーのハードコード
* Client内でのGUI表示
* Client内でのDB保存
* 検索結果先頭の無条件採用
* API固有JSONのServiceへの返却
* 例外の握りつぶし
* すべてのエラーを `None` で返す実装
* Rawレスポンスへの秘密情報保存
* 自動テストからの実API呼び出し

---

# 9. Service設計

## 9.1 Serviceの目的

`BookMetadataService` は、ISBNから複数の外部サービスを使用して書誌情報を取得するユースケースを実現する。

Serviceは、GUIと各Clientの間に位置し、外部取得処理全体を制御する。

---

## 9.2 公開インターフェース

Serviceの主な公開メソッドは、次の一つとする。

```python
def fetch_by_isbn(
    self,
    isbn: str,
) -> FetchedBookData:
    """ISBNから統合済み書誌情報を取得する。"""
```

有効な結果を取得できた場合は、統合済み `FetchedBookData` を返す。

最終的に有効な結果がない場合は、理由に応じた例外を送出する。

Serviceの公開メソッドが `None` を返す設計にはしない。

対象なしは `BookMetadataNotFoundError` としてGUIへ通知する。

---

## 9.3 コンストラクタ

Serviceは、Client一覧をコンストラクタで受け取る。

```python
class BookMetadataService:
    def __init__(
        self,
        clients: list[BookMetadataClient],
    ) -> None:
        if not clients:
            raise ValueError(
                "書誌情報取得Clientが登録されていません。"
            )

        self._clients = tuple(clients)
```

Client一覧はタプルとして保持し、生成後に外部から変更されないようにする。

Clientの呼び出し順序は、渡された順序とする。

---

## 9.4 処理手順

`fetch_by_isbn()` の処理手順は次のとおりである。

1. 入力ISBNを正規化する。
2. 正規化済みISBNを検証する。
3. 問い合わせ用ISBN-13を生成する。
4. Client一覧を登録順に処理する。
5. 各Clientから取得結果または例外を受け取る。
6. 有効な取得結果を保持する。
7. Clientごとのエラーを保持する。
8. 有効結果があれば統合する。
9. 統合結果に有効な書誌項目があれば返す。
10. 有効結果がなければ最終例外を決定する。

---

## 9.5 疑似コード

Service全体の疑似コードを次に示す。

```python
def fetch_by_isbn(
    self,
    isbn: str,
) -> FetchedBookData:
    normalized_isbn = normalize_isbn(isbn)
    validate_isbn(normalized_isbn)

    query_isbn = convert_to_isbn13(
        normalized_isbn,
    )

    results: list[FetchedBookData] = []
    errors: list[BookMetadataError] = []

    for client in self._clients:
        try:
            result = client.fetch_by_isbn(
                query_isbn,
            )
        except BookMetadataError as exc:
            errors.append(exc)
            continue

        if result is not None:
            results.append(result)

    if results:
        merged = self._merge_results(
            input_isbn=normalized_isbn,
            results=results,
        )

        if self._has_useful_metadata(merged):
            return merged

    raise self._build_final_error(errors)
```

実際のメソッド分割は実装時に調整してよい。

ただし、処理責務を一つの巨大なメソッドへ集約しない。

---

## 9.6 ISBN正規化

Serviceは、利用者入力を最初に正規化する。

正規化では次を行う。

* 文字列であることを確認する。
* 前後空白を除去する。
* 半角空白を除去する。
* 全角空白を除去する。
* 許容するハイフンを除去する。
* ISBN-10末尾の `x` を `X` へ統一する。

正規化後のISBNは、統合結果の `isbn` として使用する。

---

## 9.7 ISBN検証

Serviceは正規化後のISBNに対して、次を検証する。

* 10桁または13桁である。
* 使用可能文字だけで構成されている。
* ISBN-10のチェックデジットが正しい。
* ISBN-13のチェックデジットが正しい。
* ISBN-13の接頭辞が許容範囲である。

不正な場合は、外部Clientを呼び出す前に `ValueError` または専用入力例外を送出する。

第1段階では、既存Validatorの設計と整合させる。

---

## 9.8 問い合わせ用ISBN

外部APIへの問い合わせにはISBN-13を使用する。

ISBN-10が入力された場合は、次の手順でISBN-13へ変換する。

1. ISBN-10の末尾チェックデジットを除去する。
2. 先頭に `978` を付加する。
3. ISBN-13のチェックデジットを計算する。
4. 13桁の問い合わせ用ISBNを生成する。

ISBN-13が入力された場合は、その値を問い合わせに使用する。

問い合わせ用ISBNは、利用者入力の保存値とは区別する。

---

## 9.9 Client呼び出し

Clientは、登録された順序ですべて呼び出す。

初期順序は次のとおりである。

```text
Google Books
openBD
```

Google Booksから完全に見える結果を取得できても、第1段階ではopenBDも呼び出す。

理由は、どの項目が不足しているかをServiceだけで判断し、後順位Clientによる補完を行うためである。

将来、通信回数を削減する最適化が必要になった場合は、別途設計する。

---

## 9.10 Client例外の扱い

一つのClientが例外を送出しても、直ちに処理全体を終了しない。

Serviceは例外を保持し、次のClientを呼び出す。

```python
for client in self._clients:
    try:
        result = client.fetch_by_isbn(query_isbn)
    except BookMetadataError as exc:
        errors.append(exc)
        continue
```

この方針により、Google Booksが失敗してもopenBDから取得できる可能性を残す。

ただし、プログラム上の想定外例外まで無条件に握りつぶしてはならない。

Clientの契約外となる例外は、ログを記録したうえで上位へ送出するか、基底例外へ変換する。

---

## 9.11 取得結果の統合

複数の `FetchedBookData` は、Clientの優先順位に従って統合する。

統合の基本規則は次のとおりである。

* 最初の有効な値を採用する。
* 後順位は空欄だけを補完する。
* 後順位の値で先順位の値を上書きしない。
* `sources` は順序を維持して結合する。
* `raw_data` は取得元別に結合する。
* 統合後のISBNには正規化済み入力ISBNを使用する。

概念例を次に示す。

```python
merged_title = (
    first.title
    or second.title
    or None
)
```

ただし、空白文字列を有効値として扱わないため、実装では共通の空値判定を使用する。

---

## 9.12 有効な書誌情報の判定

Clientから `FetchedBookData` が返っても、ISBNとRawデータしか含まれていない場合は、利用者へ返す有効結果とはみなさない。

有効な書誌情報は、少なくとも次のいずれかを含むものとする。

* 書籍名
* 著者名
* 出版社
* 出版形態
* 内容紹介
* 出版日
* 表紙画像URL

第1段階では、書籍名が取得できることを成功条件として必須にはしない。

一部情報しか取得できない書籍を許容するためである。

---

## 9.13 最終例外の決定

有効結果がない場合、ServiceはClientの結果と例外をもとに最終例外を決定する。

### すべて対象なし

すべてのClientが `None` を返した場合は、次を送出する。

```python
BookMetadataNotFoundError
```

### エラーを含み、有効結果なし

Client例外を含む場合は、次の優先順位で最終例外を選択する。

```text
1. BookMetadataRateLimitError
2. BookMetadataConnectionError
3. BookMetadataResponseError
4. BookMetadataError
```

この優先順位は、利用者が再試行方法を判断しやすくするための表示上の優先順位である。

---

## 9.14 部分成功

次の場合は成功とする。

```text
Google Books: 通信エラー
openBD: 書籍名と出版社を取得
```

この場合、openBDの結果を返す。

```text
Google Books: 書籍名と著者名を取得
openBD: HTTP 429
```

この場合、Google Booksの結果を返す。

一つ以上の有効結果がある場合は、他のClientの失敗を理由に処理全体を失敗させない。

---

## 9.15 `sources` の統合

`sources` は、有効な情報を提供した取得元を優先順位順に保持する。

同じ取得元は重複させない。

例を次に示す。

```python
("Google Books", "openBD")
```

Clientが結果を返しても、統合結果へ一つも有効な項目を提供していない場合、そのClientを `sources` に含めるかどうかは実装時に統一する。

第1段階では、`FetchedBookData` を返したClientを取得元として含める。

---

## 9.16 `raw_data` の統合

各ClientのRawデータは、取得元名をキーとして統合する。

```python
merged_raw_data = {
    **google_result.raw_data,
    **openbd_result.raw_data,
}
```

同じキーが重複しないよう、Clientごとに一意な `source_name` を使用する。

Rawデータを統合結果へ保持しても、GUIには表示せず、DBへ保存しない。

---

## 9.17 Serviceの状態管理

Serviceは、検索中の一時結果をインスタンス変数へ保存しない。

次のような状態を保持してはならない。

```python
self._last_isbn
self._last_result
self._errors
```

検索ごとの結果とエラーは、メソッド内のローカル変数として管理する。

これにより、前回の取得結果が次回検索へ混入することを防ぐ。

---

## 9.18 ServiceとGUIの境界

Serviceは、利用者向けダイアログやステータスバーを認識しない。

Serviceが返すものは、次のいずれかに限定する。

* 統合済み `FetchedBookData`
* ISBN入力に関する例外
* 外部書誌情報取得に関する例外

GUIは、受け取った結果または例外を画面表示へ変換する。

---

## 9.19 ServiceとRepositoryの境界

Serviceは、Repositoryへ依存しない。

次の処理を行わない。

* 既存書籍の検索
* 重複ISBN確認
* 書籍登録
* 書籍更新
* トランザクション制御
* SQLite接続

外部取得後の保存は、利用者が登録または更新操作を行ったときに、既存の `BookService` を通じて行う。

---

## 9.20 Serviceのテスト観点

Service単体テストでは、少なくとも次を確認する。

* Clientが登録順に呼ばれる。
* ISBN-10がISBN-13へ変換される。
* ISBN-13がそのまま問い合わせに使用される。
* 不正ISBNではClientが呼ばれない。
* Google Booksの値が優先される。
* openBDが空欄だけを補完する。
* 一部Client失敗時も成功結果を返す。
* すべて対象なしでNotFoundになる。
* すべて失敗した場合に適切な例外になる。
* `sources` が正しく統合される。
* `raw_data` が正しく統合される。
* 入力ISBNが統合結果に維持される。
* 前回検索結果が次回へ影響しない。

---

## 9.21 Service設計上の禁止事項

次の実装は禁止する。

* Service内で具象Clientを生成する。
* Service内でTkinterダイアログを表示する。
* Service内でRepositoryを呼ぶ。
* Service内でAPI固有JSONキーを参照する。
* 一つのClient失敗だけで即座に処理を終了する。
* Client例外をすべて `None` に置き換える。
* 統合時に後順位で先順位を上書きする。
* 取得結果を自動的にデータベースへ保存する。
* 前回検索結果をインスタンス状態として保持する。

---
# 10. Repositoryとの責務分離

## 10.1 分離の目的

外部書誌情報取得機能とRepositoryは、明確に責務を分離する。

Repositoryは、SQLiteへの永続化と検索を担当する。

外部書誌情報取得機能は、ISBNを基に外部サービスから一時的な書誌情報を取得する。

両者は扱うデータの性質、障害要因および変更理由が異なるため、直接依存させない。

---

## 10.2 Repositoryの責務

Repositoryが担当する処理は次のとおりである。

* 書籍データの登録
* 書籍データの更新
* 書籍データの削除
* IDによる取得
* ISBNによる検索
* 書籍名などによる検索
* 一覧取得
* SQLの発行
* SQLite接続の利用
* 永続化時のデータ変換

Repositoryは、データベース内に存在する情報だけを対象とする。

---

## 10.3 Repositoryが担当しない処理

Repositoryは次の処理を担当しない。

* Google Booksへの接続
* openBDへの接続
* ISBN-10からISBN-13への変換
* APIレスポンスの解析
* 外部取得結果の統合
* APIキーの管理
* HTTP timeoutの設定
* 外部サービスの利用制限処理
* GUIへの通知
* 取得結果の自動補完

次のようなメソッドはRepositoryへ追加しない。

```python id="f4mfc6"
def fetch_book_from_google_books(
    self,
    isbn: str,
) -> BookItem:
    ...
```

```python id="mkupzg"
def find_or_fetch_by_isbn(
    self,
    isbn: str,
) -> BookItem:
    ...
```

---

## 10.4 `BookService` の責務

`BookService` は、既存の書籍管理ユースケースを担当する。

想定される主な処理は次のとおりである。

* 登録値の検証
* 書籍登録
* 書籍更新
* 書籍削除
* 重複確認
* 検索条件の整理
* `BookItem` の生成
* Repository呼び出し

`BookService` は外部APIを呼び出さない。

---

## 10.5 `BookMetadataService` の責務

`BookMetadataService` は、外部書誌情報取得ユースケースだけを担当する。

* ISBN正規化
* ISBN検証
* 問い合わせ用ISBN生成
* 外部Client呼び出し
* 取得結果の統合
* 外部取得例外の集約

`BookMetadataService` は、書籍を登録または更新しない。

---

## 10.6 保存までの流れ

外部取得結果を保存する場合は、次の経路を使用する。

```text id="wrmhbr"
BookMetadataService
        │
        │ FetchedBookData
        ▼
       GUI
        │
        │ フォームへ反映
        ▼
     利用者確認
        │
        │ 登録または更新
        ▼
    BookService
        │
        ▼
    Repository
        │
        ▼
      SQLite
```

`BookMetadataService` からRepositoryへ直接流れる経路は作らない。

---

## 10.7 モデル変換の境界

`FetchedBookData` を `BookItem` へ直接自動変換する共通処理は、第1段階では必須としない。

理由は、外部取得対象外の項目を利用者入力から補う必要があるためである。

例えば `BookItem` の生成には、次の値が必要になる可能性がある。

* 雑誌コード
* 読了年月
* 備考
* 利用者が選択した出版形態
* その他の必須管理項目

GUIは、外部取得結果をフォームへ反映した後、既存の登録処理によってフォーム全体から `BookItem` を生成する。

---

## 10.8 重複確認

ISBNの重複確認は、外部取得処理では行わない。

重複確認は、登録または更新処理の一部として `BookService` が担当する。

外部取得ボタンを押しただけで、既存DB内の重複エラーを表示しない。

理由は、外部取得が保存を伴わない入力補助操作だからである。

---

## 10.9 トランザクション

外部書誌情報取得処理では、SQLiteトランザクションを開始しない。

取得結果は一時データであり、永続化を伴わない。

トランザクション管理は、登録、更新または削除処理を行うRepository側の責務とする。

---

## 10.10 外部API障害とDB処理

外部API障害は、SQLite処理へ影響を与えてはならない。

次の状態でも、既存データの登録、編集、検索および削除は利用できるものとする。

* Google Booksが停止している。
* openBDが停止している。
* インターネット接続がない。
* APIキーが設定されていない。
* API仕様が変更されている。
* 利用制限に達している。

外部Clientの初期化失敗によって、Repositoryや `BookService` の生成まで失敗させない構成を検討する。

---

## 10.11 将来のキャッシュ

将来、外部取得結果のキャッシュを導入する場合でも、既存のBook Repositoryへそのまま混在させない。

キャッシュを導入する場合は、例えば次の専用構成を検討する。

```text id="b8z6wr"
BookMetadataCache
BookMetadataCacheRepository
metadata_cache table
```

キャッシュと正式な書籍データは、保存目的と更新規則が異なる。

第1段階ではキャッシュを実装しない。

---

## 10.12 責務分離の効果

Repositoryと外部取得処理を分離することで、次の効果が得られる。

* SQLite設計を変更せずに外部APIを追加できる。
* 外部API障害がCRUDへ波及しない。
* Repositoryの単体テストにHTTP Mockが不要になる。
* ClientテストにSQLiteが不要になる。
* 保存前に利用者が取得結果を修正できる。
* 外部取得機能を将来削除してもDB機能を維持できる。
* モデルの役割が明確になる。

---

## 10.13 禁止事項

次の実装は禁止する。

* Repository内でHTTP通信を行う。
* `BookMetadataService` 内でSQLを発行する。
* ClientへRepositoryを注入する。
* 外部取得成功時に自動コミットする。
* Rawレスポンスを既存の書籍テーブルへ保存する。
* 外部API障害をDB例外として扱う。
* DB検索結果と外部取得結果を同一モデルで無条件に混在させる。

---

# 11. GUI連携

## 11.1 GUI連携の目的

GUIは、利用者によるISBN入力、取得操作、取得結果の確認および保存操作をつなぐ役割を持つ。

GUIは外部APIの詳細を認識せず、`BookMetadataService` の公開インターフェースだけを利用する。

---

## 11.2 配置する操作

ISBN入力欄の近くに、外部書誌情報取得用のボタンを配置する。

ボタン名は、既存GUIの文言との整合性を考慮して決定する。

推奨名称は次のいずれかとする。

```text id="6dmaqz"
ISBNから取得
書籍情報取得
書誌情報取得
```

本設計書では、説明上「取得ボタン」と表記する。

---

## 11.3 GUIイベント処理

取得ボタン押下時の基本処理は次のとおりである。

1. ISBN入力値を取得する。
2. ISBNが未入力か確認する。
3. 上書き対象欄に既存値があるか確認する。
4. 必要に応じて確認ダイアログを表示する。
5. 利用者が拒否した場合は終了する。
6. 取得ボタンを無効化する。
7. `BookMetadataService.fetch_by_isbn()` を呼び出す。
8. 成功時は取得結果をフォームへ反映する。
9. ステータスバーへ成功内容を表示する。
10. 失敗時は例外に応じた通知を表示する。
11. `finally` で取得ボタンを有効化する。

---

## 11.4 イベント処理の概念例

```python id="g83qif"
def on_fetch_metadata_clicked(self) -> None:
    isbn = self._isbn_var.get()

    if self._requires_overwrite_confirmation():
        confirmed = messagebox.askyesno(
            "確認",
            "入力済みの書誌情報を更新しますか？",
        )

        if not confirmed:
            return

    self._set_fetch_button_enabled(False)

    try:
        metadata = (
            self._metadata_service.fetch_by_isbn(
                isbn,
            )
        )
        self._apply_fetched_metadata(metadata)
        self._show_fetch_success(metadata)
    except ValueError:
        self._show_invalid_isbn_error()
    except BookMetadataNotFoundError:
        self._show_not_found_message()
    except BookMetadataRateLimitError:
        self._show_rate_limit_error()
    except BookMetadataConnectionError:
        self._show_connection_error()
    except BookMetadataResponseError:
        self._show_response_error()
    finally:
        self._set_fetch_button_enabled(True)
```

実際のメソッド名は既存GUI設計へ合わせる。

---

## 11.5 ISBN未入力時

ISBN欄が未入力または空白だけの場合は、Serviceを呼び出さず警告する。

表示例を次に示す。

```text id="wkgrsp"
ISBNを入力してください。
```

ISBN未入力は、外部サービスのエラーではなく利用者入力エラーとして扱う。

---

## 11.6 上書き確認

次の入力欄のいずれかに値が存在する場合は、取得開始前に確認を行う。

* 書籍名
* 著者名
* 出版社
* 出版形態
* 内容紹介

確認文の例を次に示す。

```text id="h58u62"
入力済みの書誌情報があります。
外部サービスから取得した情報で更新しますか？
```

利用者が「いいえ」を選択した場合は、HTTP通信を開始しない。

---

## 11.7 上書き確認の判定

上書き確認では、前後空白を除いた後に値が存在するか判定する。

```python id="nq3bmg"
def _has_text(value: str) -> bool:
    return bool(value.strip())
```

出版形態がコンボボックスの場合は、未選択状態と既定値を区別する。

既定値が実質的な未入力を表す場合は、上書き確認対象としない。

---

## 11.8 取得中の操作制御

同期処理中の二重実行を防ぐため、取得開始前に取得ボタンを無効化する。

処理完了後は、成功、対象なし、入力エラーまたは通信エラーにかかわらず、有効状態へ戻す。

有効化処理は `finally` で行う。

必要に応じて、マウスカーソルを待機状態へ変更してもよい。

ただし、カーソル変更を行う場合も `finally` で必ず元へ戻す。

---

## 11.9 フォーム反映対象

取得結果からGUIへ反映する項目は次のとおりである。

| 取得項目    |     GUI反映     |
| :------ | :-----------: |
| ISBN    |  原則として現在値を維持  |
| 書籍名     |      反映する     |
| 著者名     |      反映する     |
| 出版社     |      反映する     |
| 出版形態    | 取得できた場合だけ反映する |
| 内容紹介    |      反映する     |
| 出版日     |  第1段階では反映しない  |
| 表紙画像URL |  第1段階では反映しない  |
| 取得元     |  ステータス表示に使用する |
| Rawデータ  |     反映しない     |

---

## 11.10 非対象項目の保持

外部取得処理によって、次の項目を変更してはならない。

* 雑誌コード
* 読了年月
* 備考
* データベースID
* 作成日時
* 更新日時
* その他の利用者管理項目

反映処理は、フォーム全体を初期化してから設定する方式にしない。

対象フィールドだけを個別に更新する。

---

## 11.11 `None` の反映

取得結果が `None` の項目は、GUIの現在値を維持する。

例えば、Google BooksとopenBDのどちらからも出版社を取得できなかった場合、出版社欄を空欄にしない。

概念例を次に示す。

```python id="tj3rwh"
if metadata.publisher is not None:
    self._publisher_var.set(
        metadata.publisher,
    )
```

次のような無条件設定は行わない。

```python id="fa9o8a"
self._publisher_var.set(
    metadata.publisher or "",
)
```

---

## 11.12 取得済み空文字列

ClientとServiceの境界で空文字列は `None` に正規化される。

GUIでも防御的に、空白だけの値を反映しない。

これにより、外部APIの空欄によって利用者の入力値を消去することを防ぐ。

---

## 11.13 出版形態の反映

出版形態は、既存GUIで許容される値と完全に一致する場合だけ反映する。

例を次に示す。

```python id="5zntfk"
allowed_formats = {
    "文庫",
    "単行本",
    "電子書籍",
}

if metadata.publication_format in allowed_formats:
    self._publication_format_var.set(
        metadata.publication_format,
    )
```

未知の値をコンボボックスへ強制的に設定しない。

---

## 11.14 内容紹介の反映

内容紹介が複数行テキストウィジェットの場合は、現在の内容を削除してから取得値を挿入する。

ただし、取得値が存在する場合だけ行う。

概念例を次に示す。

```python id="2sp28g"
if metadata.description is not None:
    self._description_text.delete(
        "1.0",
        "end",
    )
    self._description_text.insert(
        "1.0",
        metadata.description,
    )
```

GUIウィジェット固有の操作はGUI層に閉じ込める。

---

## 11.15 成功表示

取得成功時は、原則としてモーダルダイアログを使用せず、ステータスバーへ表示する。

基本メッセージは次のとおりである。

```text id="p8lwi5"
書籍情報を取得しました。
```

取得元を表示する場合は次のようにする。

```text id="ao984c"
書籍情報を取得しました。取得元: Google Books、openBD
```

一部のClientが失敗していても、有効結果が得られた場合は成功として表示する。

第1段階では、部分失敗の詳細を通常利用者へ表示しない。

---

## 11.16 対象なし表示

すべての取得元で対象書籍が見つからなかった場合は、情報ダイアログを表示する。

```text id="ynzmuj"
該当する書籍情報が見つかりませんでした。
ISBNを確認するか、手動で入力してください。
```

対象なしはアプリケーション異常ではないため、重大なエラー表現を避ける。

---

## 11.17 ISBN不正表示

ISBNの形式またはチェックデジットが不正な場合は、警告ダイアログを表示する。

```text id="2jd891"
ISBNの形式が正しくありません。
10桁または13桁のISBNを確認してください。
```

詳細な計算内容や内部例外名は表示しない。

---

## 11.18 利用制限表示

HTTP 429などの利用制限時は、次のように表示する。

```text id="j9ttws"
書籍情報サービスの利用制限に達しました。
時間をおいてから再試行してください。
```

APIキーや具体的な上限値を利用者へ表示する必要はない。

---

## 11.19 接続エラー表示

接続失敗またはtimeout時は、次のように表示する。

```text id="gbvdlo"
書籍情報サービスへ接続できませんでした。
インターネット接続を確認してから再試行してください。
```

外部サービス名を表示するかどうかは、最終例外に保持する情報とUI方針に応じて決定する。

---

## 11.20 応答エラー表示

外部サービスから不正な応答を受信した場合は、次のように表示する。

```text id="wtrn6c"
書籍情報サービスから正しい応答を取得できませんでした。
時間をおいてから再試行してください。
```

JSON構造やHTTP本文をそのまま表示しない。

---

## 11.21 予期しない例外

予期しない例外が発生した場合は、ログへ詳細を記録し、利用者へ一般的なエラーを表示する。

```text id="l1z0gl"
書籍情報の取得中にエラーが発生しました。
```

ただし、開発時にすべての例外を一律に握りつぶす実装は避ける。

---

## 11.22 自動保存の禁止

フォームへ取得結果を反映した後も、登録または更新ボタンを自動実行しない。

利用者は次の操作を行える。

* 取得結果を確認する。
* 著者名を修正する。
* 出版形態を選択する。
* 内容紹介を修正する。
* 備考を入力する。
* 登録を取りやめる。

保存は既存の操作フローへ委ねる。

---

## 11.23 取得結果反映メソッド

取得結果のフォーム反映処理は、イベントハンドラ内へ直接並べず、専用メソッドへ分離する。

```python id="diw4yc"
def _apply_fetched_metadata(
    self,
    metadata: FetchedBookData,
) -> None:
    ...
```

これにより、反映規則を単体で確認しやすくする。

---

## 11.24 GUI連携のテスト観点

少なくとも次を確認する。

* ISBN未入力時にServiceを呼ばない。
* 入力済み項目がある場合に確認する。
* キャンセル時にClientを呼ばない。
* 取得中にボタンが無効になる。
* 例外発生後もボタンが有効に戻る。
* `None` の項目で既存値を消さない。
* 取得対象外項目を変更しない。
* 成功時に自動保存しない。
* 出版形態の未知値を反映しない。
* 取得元を正しく表示する。
* エラー種別ごとに適切な通知を行う。

---

## 11.25 GUI連携上の禁止事項

次の実装は禁止する。

* GUIイベント内で `requests.get()` を呼ぶ。
* GUIでAPIレスポンスJSONを解析する。
* 外部取得前にフォーム全体を初期化する。
* `None` を空文字列として無条件に反映する。
* 取得成功直後に自動登録する。
* 例外詳細をそのままダイアログへ表示する。
* 取得中に同じボタンを連打可能にする。
* エラー時にボタンを無効状態のまま残す。

---

# 12. ISBN処理

## 12.1 ISBN処理の目的

ISBN処理は、外部書誌情報取得の前提となる入力整形、形式検証および問い合わせ値生成を担当する。

外部APIへ不正なISBNを送信しないため、Client呼び出し前に必ず検証する。

---

## 12.2 ISBN処理の責務

ISBN処理には次を含む。

* 入力値の正規化
* ISBN-10の形式検証
* ISBN-13の形式検証
* チェックデジット検証
* ISBN-10からISBN-13への変換
* ISBN同士の比較用正規化
* 外部API問い合わせ値の生成

---

## 12.3 推奨配置

ISBN処理は、複数の層から再利用できる独立モジュールへ配置する。

推奨例を次に示す。

```text id="qqbo4c"
src/
└── book_manager/
    └── isbn/
        ├── __init__.py
        ├── normalizer.py
        ├── validator.py
        └── converter.py
```

小規模な段階では、一つの `isbn.py` にまとめてもよい。

ただし、GUIやClientへ計算処理を重複記述しない。

---

## 12.4 正規化

入力ISBNの正規化では、次を行う。

* 前後の空白を除去する。
* 半角空白を除去する。
* 全角空白を除去する。
* 許容するハイフンを除去する。
* ISBN-10末尾の小文字 `x` を大文字 `X` に変換する。

概念例を次に示す。

```python id="mtvu64"
def normalize_isbn(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(
            "ISBNは文字列で指定してください。"
        )

    normalized = value.strip()

    for character in (
        " ",
        "　",
        "-",
        "‐",
        "-",
        "−",
        "ー",
    ):
        normalized = normalized.replace(
            character,
            "",
        )

    if normalized.endswith("x"):
        normalized = (
            normalized[:-1] + "X"
        )

    return normalized
```

許容するハイフン文字は、実装時に過不足がないようテストで固定する。

---

## 12.5 正規化と検証の分離

正規化関数は、形式を整えるだけとする。

正規化関数内でチェックデジット検証まで行わない。

推奨する責務分離は次のとおりである。

```python id="g3armp"
normalized = normalize_isbn(input_value)
validate_isbn(normalized)
```

これにより、正規化単体と検証単体を別々にテストできる。

---

## 12.6 ISBN-10の形式

ISBN-10は10文字で構成される。

先頭9文字は数字でなければならない。

末尾1文字は、数字または `X` を許容する。

正規表現の概念例を次に示す。

```python id="4fuvi2"
r"^\d{9}[\dX]$"
```

`X` はチェックデジット10を表す。

末尾以外の `X` は許容しない。

---

## 12.7 ISBN-10チェックデジット

ISBN-10は、各桁に10から1までの重みを掛けた合計が11で割り切れることを確認する。

ISBNを次のように表す。

```text id="386g2h"
d1 d2 d3 d4 d5 d6 d7 d8 d9 d10
```

検証式は次のとおりである。

```text id="wp6j08"
10×d1
+ 9×d2
+ 8×d3
+ 7×d4
+ 6×d5
+ 5×d6
+ 4×d7
+ 3×d8
+ 2×d9
+ 1×d10
```

この合計が11の倍数であれば有効とする。

末尾 `X` は数値10として計算する。

---

## 12.8 ISBN-10検証の概念例

```python id="rv3f8g"
def is_valid_isbn10(isbn: str) -> bool:
    if len(isbn) != 10:
        return False

    if not isbn[:9].isdigit():
        return False

    if not (
        isbn[-1].isdigit()
        or isbn[-1] == "X"
    ):
        return False

    digits = [
        int(character)
        for character in isbn[:9]
    ]

    check_digit = (
        10
        if isbn[-1] == "X"
        else int(isbn[-1])
    )

    digits.append(check_digit)

    total = sum(
        digit * weight
        for digit, weight in zip(
            digits,
            range(10, 0, -1),
        )
    )

    return total % 11 == 0
```

---

## 12.9 ISBN-13の形式

ISBN-13は13桁の数字で構成される。

正規表現の概念例を次に示す。

```python id="ueqtmw"
r"^\d{13}$"
```

第1段階では、書籍ISBNとして使用される接頭辞 `978` または `979` を許容する。

---

## 12.10 ISBN-13チェックデジット

ISBN-13の先頭12桁に、左から交互に1と3を掛ける。

合計値を10の倍数へ切り上げるために必要な数が、13桁目のチェックデジットである。

計算式を次に示す。

```text id="79uyzf"
check_digit = (10 - (weighted_sum % 10)) % 10
```

---

## 12.11 ISBN-13検証の概念例

```python id="t3zkvg"
def is_valid_isbn13(isbn: str) -> bool:
    if len(isbn) != 13:
        return False

    if not isbn.isdigit():
        return False

    if not isbn.startswith(
        ("978", "979")
    ):
        return False

    weighted_sum = sum(
        int(character) * (
            1 if index % 2 == 0 else 3
        )
        for index, character
        in enumerate(isbn[:12])
    )

    expected = (
        10 - weighted_sum % 10
    ) % 10

    return expected == int(isbn[-1])
```

---

## 12.12 ISBN共通検証

共通検証関数は、桁数に応じてISBN-10またはISBN-13の検証を呼び出す。

```python id="hl6oe8"
def validate_isbn(isbn: str) -> None:
    if len(isbn) == 10:
        if is_valid_isbn10(isbn):
            return

    elif len(isbn) == 13:
        if is_valid_isbn13(isbn):
            return

    raise ValueError(
        "ISBNの形式が正しくありません。"
    )
```

GUI表示用メッセージをこの関数へ埋め込みすぎない。

必要に応じて専用例外を使用する。

---

## 12.13 ISBN-10からISBN-13への変換

ISBN-10をISBN-13へ変換する手順は次のとおりである。

1. ISBN-10が有効か確認する。
2. 末尾チェックデジットを除去する。
3. 先頭へ `978` を付加する。
4. 12桁の値からISBN-13チェックデジットを計算する。
5. チェックデジットを末尾へ付加する。

概念例を次に示す。

```python id="q5dgcp"
def convert_isbn10_to_isbn13(
    isbn10: str,
) -> str:
    if not is_valid_isbn10(isbn10):
        raise ValueError(
            "有効なISBN-10ではありません。"
        )

    body = "978" + isbn10[:9]

    weighted_sum = sum(
        int(character) * (
            1 if index % 2 == 0 else 3
        )
        for index, character
        in enumerate(body)
    )

    check_digit = (
        10 - weighted_sum % 10
    ) % 10

    return body + str(check_digit)
```

---

## 12.14 問い合わせ用ISBN生成

問い合わせ用ISBNを生成する共通関数を設ける。

```python id="ash78j"
def to_query_isbn13(
    isbn: str,
) -> str:
    validate_isbn(isbn)

    if len(isbn) == 13:
        return isbn

    return convert_isbn10_to_isbn13(
        isbn,
    )
```

Clientは、原則としてこの処理済みのISBN-13を受け取る。

---

## 12.15 ISBN比較

APIレスポンス内のISBNと問い合わせISBNを比較する場合は、両方を正規化してから比較する。

レスポンスにISBN-10しか含まれない場合は、ISBN-13へ変換して比較する。

概念例を次に示す。

```python id="k47bl7"
def isbn_matches(
    candidate: str,
    query_isbn13: str,
) -> bool:
    normalized = normalize_isbn(
        candidate,
    )

    try:
        normalized13 = to_query_isbn13(
            normalized,
        )
    except ValueError:
        return False

    return normalized13 == query_isbn13
```

---

## 12.16 入力値と問い合わせ値の保持

次の二つは明確に区別する。

| 値             | 用途           |
| :------------ | :----------- |
| 正規化済み入力ISBN   | GUI反映および保存候補 |
| 問い合わせ用ISBN-13 | 外部API検索と候補照合 |

ISBN-10を入力した利用者の値を、取得処理だけを理由にISBN-13へ変更しない。

---

## 12.17 ISBN処理のテストケース

少なくとも次を検証する。

### 正常系

```text id="5bap9h"
4101109184
4-10-110918-4
9784163917733
978-4-16-391773-3
```

### ISBN-10末尾X

```text id="ao6zkj"
097522980X
097522980x
```

### 異常系

```text id="0vfrfs"
空文字列
9桁
11桁
12桁
14桁
英字を含むISBN-13
途中にXを含むISBN-10
不正チェックデジット
978または979以外の13桁
```

### 正規化

```text id="6nbu12"
半角空白
全角空白
半角ハイフン
許容対象の各種ハイフン
前後空白
小文字x
```

---

## 12.18 ISBN処理上の禁止事項

次の実装は禁止する。

* 桁数だけで有効と判定する。
* チェックデジットを検証しない。
* GUIごとにISBN計算を重複実装する。
* Clientごとに異なるISBN正規化を行う。
* 不正ISBNを外部APIへ送信する。
* ISBN-10入力を無断でISBN-13表示へ変更する。
* API検索結果のISBNを正規化せず比較する。

---

# 13. Google Books連携

## 13.1 目的

`GoogleBooksClient` は、Google Books APIを利用し、ISBNに対応する書誌情報を取得する。

Google Booksは、第1段階における第1取得元とする。

---

## 13.2 Clientの責務

`GoogleBooksClient` は次の責務を持つ。

* Google Books APIへの問い合わせ
* ISBN検索パラメータの生成
* APIキーの設定
* HTTPレスポンスの判定
* 検索候補の解析
* ISBN一致候補の選択
* 書誌項目の抽出
* `FetchedBookData` への変換
* Google Books固有エラーの変換

---

## 13.3 エンドポイント

Google BooksのVolumes検索エンドポイントを使用する。

実装では、エンドポイントをクラス定数として管理する。

```python id="cl7vpv"
class GoogleBooksClient:
    BASE_URL = (
        "https://www.googleapis.com/"
        "books/v1/volumes"
    )
```

URLをGUIやServiceへ記述しない。

---

## 13.4 検索パラメータ

ISBN検索には、`q` パラメータを使用する。

概念例を次に示す。

```python id="bf8k4x"
params = {
    "q": f"isbn:{isbn}",
}
```

APIキーが設定されている場合は `key` を追加する。

```python id="3zxkdl"
if self._api_key:
    params["key"] = self._api_key
```

必要に応じて取得件数を制限する。

```python id="zyklb5"
params["maxResults"] = 10
```

件数は、ISBN一致候補を確認できる範囲で最小限とする。

---

## 13.5 APIキー

Google Books APIキーは、環境変数から取得する。

環境変数名の候補を次に示す。

```text id="t2lxj3"
GOOGLE_BOOKS_API_KEY
```

APIキーを次の場所へ記述しない。

* Pythonソースコード
* Git管理対象の設定ファイル
* テストFixture
* READMEの実値例
* ログ
* 例外メッセージ
* Rawデータ

APIキーが未設定の場合にキーなし通信を許容するかは、APIの利用条件と実装時の動作確認を踏まえて決定する。

キーなし通信を許容する場合でも、Clientのインターフェースは同じとする。

---

## 13.6 コンストラクタ

概念的な定義を次に示す。

```python id="roao9q"
class GoogleBooksClient:
    BASE_URL = (
        "https://www.googleapis.com/"
        "books/v1/volumes"
    )

    def __init__(
        self,
        session: requests.Session,
        api_key: str | None = None,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._timeout = timeout
```

timeoutはClient内で変更せず、注入値をそのまま使用する。

---

## 13.7 取得メソッド

公開メソッドは次の形式とする。

```python id="2921ea"
def fetch_by_isbn(
    self,
    isbn: str,
) -> FetchedBookData | None:
    ...
```

入力ISBNは、Serviceで検証済みのISBN-13を前提とする。

---

## 13.8 通信処理

通信処理の概念例を次に示す。

```python id="0ixb1o"
try:
    response = self._session.get(
        self.BASE_URL,
        params=self._build_params(isbn),
        timeout=self._timeout,
    )
except requests.RequestException as exc:
    raise BookMetadataConnectionError(
        "Google Booksへ接続できませんでした。"
    ) from exc
```

HTTP 429を専用判定した後、その他のHTTP異常を処理する。

---

## 13.9 正常レスポンスの基本構造

Google Books検索結果は、概念上次のような構造を持つ。

```json id="xvt4qi"
{
  "kind": "books#volumes",
  "totalItems": 1,
  "items": [
    {
      "id": "example",
      "volumeInfo": {
        "title": "書籍名",
        "authors": [
          "著者名"
        ],
        "publisher": "出版社",
        "publishedDate": "2026-07-24",
        "description": "内容紹介",
        "industryIdentifiers": [
          {
            "type": "ISBN_13",
            "identifier": "9784163917733"
          }
        ],
        "imageLinks": {
          "thumbnail": "https://example.com/image"
        }
      }
    }
  ]
}
```

実際のレスポンスでは、各項目が欠落する可能性がある。

---

## 13.10 対象なしの判定

次の場合は、対象書籍なしとして `None` を返す。

* `totalItems` が0
* `items` が存在しない
* `items` が空配列
* ISBN一致候補が存在しない
* 候補はあるが有効な書誌項目がない

HTTP 200で対象がないことは、通信エラーとして扱わない。

---

## 13.11 候補選択

`items` の先頭を無条件に使用しない。

各候補の `volumeInfo.industryIdentifiers` を確認し、問い合わせISBNに一致する候補を選択する。

優先順位は次のとおりである。

1. ISBN-13が完全一致する候補
2. ISBN-10をISBN-13へ変換すると一致する候補
3. 一致候補なしの場合は対象なし

タイトルが似ていることだけを理由に候補を採用しない。

---

## 13.12 識別子解析

`industryIdentifiers` は配列で返される。

各要素について、次を確認する。

* 辞書形式である。
* `identifier` が文字列である。
* ISBNとして正規化・検証できる。
* 問い合わせISBN-13と一致する。

`type` が `ISBN_10` または `ISBN_13` であることも確認する。

未知の識別子種別は無視する。

---

## 13.13 書籍名

書籍名は `volumeInfo.title` から取得する。

`subtitle` が存在する場合に結合するかどうかは、次の方針とする。

第1段階では、`title` を基本値として使用する。

`subtitle` を結合する場合は、重複や既存タイトルへの影響を確認し、統一規則を別途定める。

暫定的な結合例は次のとおりである。

```text id="7qg554"
title
title: subtitle
```

実装開始時に、取得テスト結果を踏まえて固定する。

---

## 13.14 著者名

著者名は `volumeInfo.authors` から取得する。

配列内の文字列だけを採用し、空文字列を除外する。

```python id="1a7ewg"
authors = [
    author.strip()
    for author in raw_authors
    if isinstance(author, str)
    and author.strip()
]
```

複数著者は全角読点で結合する。

```python id="d9f4cg"
authors_text = "、".join(authors)
```

有効な著者が存在しない場合は `None` とする。

---

## 13.15 出版社

出版社は `volumeInfo.publisher` から取得する。

前後空白を除去し、空文字列は `None` とする。

出版社名の表記ゆれ修正やマスタ照合は、Google Books Clientの責務としない。

---

## 13.16 出版日

出版日は `volumeInfo.publishedDate` から取得する。

Google Booksでは、年だけ、年月、年月日など、異なる精度で返される可能性がある。

そのため、文字列として保持する。

例を次に示す。

```text id="rlu3mh"
2026
2026-07
2026-07-24
```

Client内で不足する月日を補完しない。

---

## 13.17 内容紹介

内容紹介は `volumeInfo.description` から取得する。

前後空白を除去し、空文字列は `None` とする。

HTMLタグが含まれる場合でも、第1段階ではGUI上でHTMLとして実行しない。

必要に応じてプレーンテキスト化するが、過度な文字列加工は行わない。

---

## 13.18 表紙画像URL

表紙画像URLは `volumeInfo.imageLinks` から取得する。

候補キーの優先順位例は次のとおりである。

```text id="oxu8ke"
extraLarge
large
medium
small
thumbnail
smallThumbnail
```

第1段階では、利用可能な最も高い優先順位のURLを一つ保持する。

ただし、GUI表示や保存は行わない。

---

## 13.19 HTTPSへの補正

表紙画像URLが `http://` で返された場合に `https://` へ補正するかは、実際の取得結果と接続可否を確認して決定する。

無条件置換によって無効URLを生成する可能性があるため、Client実装時にテストを行う。

第1段階では、原則としてAPIが返したURLを保持する。

---

## 13.20 出版形態

Google Booksの情報だけでは、文庫、単行本などを確実に判定できない場合が多い。

`printType` が `BOOK` であることは、出版形態を表さない。

したがって、確実な判定規則が確立するまでは `publication_format` を `None` とする。

電子書籍の判定も、レスポンス項目の意味と取得テストを確認してから実装する。

推測による設定は禁止する。

---

## 13.21 Rawデータ

取得したPayloadは、次の形式でRawデータへ保持できる。

```python id="ehm001"
raw_data={
    self.source_name: {
        "query": {
            "isbn": isbn,
        },
        "response": payload,
    },
}
```

APIキーをRawデータへ含めない。

---

## 13.22 `FetchedBookData` 生成

概念例を次に示す。

```python id="7zf0uj"
return FetchedBookData(
    isbn=isbn,
    title=title,
    authors=authors,
    publisher=publisher,
    publication_date=published_date,
    publication_format=None,
    description=description,
    cover_image_url=cover_image_url,
    sources=(self.source_name,),
    raw_data={
        self.source_name: {
            "query": {
                "isbn": isbn,
            },
            "response": payload,
        },
    },
)
```

Clientが設定するISBNは問い合わせ用ISBN-13でもよい。

最終統合時にServiceが正規化済み入力ISBNへ置き換える。

---

## 13.23 HTTP 429

HTTP 429を受信した場合は、`BookMetadataRateLimitError` を送出する。

レスポンス本文に詳細が含まれていても、そのまま利用者向けメッセージへ使用しない。

Retry-Afterヘッダーがある場合は、ログまたは例外属性へ保持する設計を将来検討できる。

第1段階では、自動待機や自動再試行を行わない。

---

## 13.24 HTTP 403

HTTP 403は、APIキーの不備、権限、利用制限など複数の原因が考えられる。

第1段階では、レスポンス内容を安全に確認したうえで、次のいずれかへ変換する。

* 利用制限と明確に判定できる場合は `BookMetadataRateLimitError`
* その他は `BookMetadataResponseError`

APIキー自体を例外メッセージへ含めない。

---

## 13.25 不正レスポンス

次の場合は `BookMetadataResponseError` とする。

* JSONとして解析できない。
* トップレベルが辞書でない。
* `items` が配列でない。
* 候補要素が想定外の形式である。
* APIのエラーオブジェクトが返された。
* 正常レスポンスとして処理できない構造である。

ただし、単純な項目欠損は不正レスポンスとせず、その項目を `None` とする。

---

## 13.26 ログ項目

Google Books Clientでは、必要に応じて次をログへ記録する。

* 取得元
* 問い合わせISBN
* HTTPステータス
* 候補件数
* ISBN一致候補の有無
* 処理時間
* 例外種別

次は記録しない。

* APIキー
* 認証情報
* 不要なレスポンス全文
* 個人情報
* 秘密情報を含むヘッダー

---

## 13.27 テストFixture

Google Books Clientのテストでは、実APIを呼び出さず、保存したFixtureまたはFake Responseを使用する。

少なくとも次のFixtureを用意する。

* 全項目あり
* 著者なし
* 出版社なし
* 内容紹介なし
* 表紙画像なし
* 出版日が年だけ
* 複数候補
* 先頭候補がISBN不一致
* ISBN-10だけを持つ候補
* 対象なし
* `items` なし
* HTTP 429
* HTTP 403
* HTTP 500
* timeout
* JSON解析失敗
* 不正トップレベル型

---

## 13.28 テスト時のAPIレスポンス更新

Fixtureは、実際のGoogle Booksレスポンスを参考に作成してよい。

ただし、Fixtureへ不要な大量データを保存しない。

テスト対象となる項目だけを残した最小限のJSONとする。

実レスポンスをFixtureへ保存する場合は、APIキーや不要な識別情報が含まれていないことを確認する。

---

## 13.29 Google Books連携上の禁止事項

次の実装は禁止する。

* APIキーのハードコード
* timeoutなし通信
* `items[0]` の無条件採用
* ISBN照合なしの候補採用
* `volumeInfo` のキー直接参照
* 欠損項目を例外扱いする。
* `printType` だけで文庫や単行本を判定する。
* HTTP 429を通常の対象なしとして扱う。
* APIレスポンスをGUIへ直接返す。
* 実APIへ依存する自動テスト
* APIキーをRawデータまたはログへ保存する。

---
# 14. openBD連携

## 14.1 目的

`OpenBdClient` は、openBD APIを利用して、ISBNに対応する書誌情報を取得する。

openBDは、第1段階における第2取得元として使用する。

Google Booksで取得できなかった項目を補完する目的で利用するが、`OpenBdClient` 自体はGoogle Booksの結果を認識しない。

どの値を補完に使用するかは、`BookMetadataService` が決定する。

---

## 14.2 Clientの責務

`OpenBdClient` は次の責務を持つ。

* openBD APIへの問い合わせ
* ISBNパラメータの生成
* HTTPレスポンスの判定
* 対象書籍の有無の判定
* openBD固有レスポンスの解析
* 必要な書誌項目の抽出
* `FetchedBookData` への変換
* openBD固有エラーの変換

---

## 14.3 エンドポイント

openBDの書誌情報取得エンドポイントを使用する。

実装では、エンドポイントをクラス定数として管理する。

```python id="n4myjr"
class OpenBdClient:
    BASE_URL = (
        "https://api.openbd.jp/v1/get"
    )
```

エンドポイントをGUIまたはServiceへ記述しない。

---

## 14.4 検索パラメータ

ISBN検索には、`isbn` パラメータを使用する。

概念例を次に示す。

```python id="tcn771"
params = {
    "isbn": isbn,
}
```

Serviceから渡される、検証済みのISBN-13を使用する。

URLへISBNを直接文字列連結せず、`params` を使用する。

---

## 14.5 コンストラクタ

概念的な定義を次に示す。

```python id="uey101"
class OpenBdClient:
    BASE_URL = (
        "https://api.openbd.jp/v1/get"
    )

    def __init__(
        self,
        session: requests.Session,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        self._session = session
        self._timeout = timeout
```

openBDでは、第1段階でAPIキーを使用しない。

将来認証方式が変更された場合は、Client内部の設計変更として対応する。

---

## 14.6 取得メソッド

公開メソッドは次の形式とする。

```python id="18ki2p"
def fetch_by_isbn(
    self,
    isbn: str,
) -> FetchedBookData | None:
    ...
```

入力ISBNは、Serviceで検証済みのISBN-13を前提とする。

---

## 14.7 通信処理

通信処理の概念例を次に示す。

```python id="u4srsd"
try:
    response = self._session.get(
        self.BASE_URL,
        params={
            "isbn": isbn,
        },
        timeout=self._timeout,
    )
except requests.RequestException as exc:
    raise BookMetadataConnectionError(
        "openBDへ接続できませんでした。"
    ) from exc
```

HTTP 429を専用判定した後、その他のHTTP異常を処理する。

---

## 14.8 正常レスポンスの基本構造

openBDは、概念上、問い合わせたISBNごとに配列要素を返す。

```json id="77dxf6"
[
  {
    "onix": {
      "DescriptiveDetail": {},
      "PublishingDetail": {},
      "CollateralDetail": {}
    },
    "hanmoto": {},
    "summary": {
      "isbn": "9784163917733",
      "title": "書籍名",
      "author": "著者名",
      "publisher": "出版社",
      "pubdate": "20231027",
      "cover": "https://example.com/cover.jpg"
    }
  }
]
```

実際のレスポンスでは、`summary`、`onix`、`hanmoto` または各内部項目が欠落する可能性がある。

---

## 14.9 対象なしの判定

openBDでは、対象ISBNが見つからない場合に、配列内の要素が `null` となる場合がある。

概念例を次に示す。

```json id="0lc4kd"
[
  null
]
```

次の場合は、対象書籍なしとして `None` を返す。

* トップレベル配列が空
* 先頭要素が `null`
* 有効な辞書要素が存在しない
* ISBNが一致する要素が存在しない
* 有効な書誌項目が一つも取得できない

HTTP 200で対象がない場合は、通信エラーとして扱わない。

---

## 14.10 トップレベル型

openBDの正常レスポンスは、配列を前提とする。

次の場合は `BookMetadataResponseError` とする。

* JSONトップレベルが配列でない
* 配列要素が想定外の型
* 必要な処理を継続できない構造
* APIエラーオブジェクトが返された
* JSON解析に失敗した

ただし、配列要素が `null` である場合は対象なしとして扱う。

---

## 14.11 ISBN照合

レスポンス内のISBNは、`summary.isbn` などから取得する。

レスポンスISBNを正規化し、問い合わせISBN-13と照合する。

一致しない要素を採用しない。

openBDはISBN指定取得であるため通常は一致すると想定されるが、外部データを無条件に信頼しない。

---

## 14.12 `summary` の利用

第1段階では、取得しやすく形式が比較的単純な `summary` を優先して使用する。

想定する対応は次のとおりである。

| openBD項目          | 内部項目             |
| :---------------- | :--------------- |
| summary.isbn      | isbn             |
| summary.title     | title            |
| summary.author    | authors          |
| summary.publisher | publisher        |
| summary.pubdate   | publication_date |
| summary.cover     | cover_image_url  |

`summary` に値がない場合は、必要に応じて `onix` または `hanmoto` から補完する。

---

## 14.13 書籍名

書籍名は、原則として `summary.title` から取得する。

値が存在しない場合は、ONIX内のタイトル情報を補完候補とする。

ONIXから取得する場合は、タイトル本体、副題、シリーズ名などを混同しない。

第1段階では、書籍名として明確に判定できる値だけを使用する。

---

## 14.14 著者名

著者名は、原則として `summary.author` から取得する。

openBDの著者名には、次のような表記が含まれる場合がある。

```text id="mb9jg5"
松本,清張,1909-1992
```

```text id="zg24my"
山田太郎／著
```

```text id="qhw0x8"
山田 太郎
```

第1段階では、Clientで過度な著者名正規化を行わない。

前後空白の除去と空文字判定だけを必須とする。

生没年の除去、姓名順の変換、役割表記の分離は、著者マスタ設計と合わせて将来検討する。

---

## 14.15 著者名の補完候補

`summary.author` が存在しない場合は、ONIX内のContributor情報を確認できる。

ただし、ONIXのContributorは、著者、翻訳者、編集者、監修者など複数の役割を含む可能性がある。

第1段階では、役割を正しく判定できる場合だけ使用する。

役割不明のContributorをすべて著者名として結合しない。

---

## 14.16 出版社

出版社は、原則として `summary.publisher` から取得する。

値がない場合は、ONIX内のPublisher情報を補完候補とする。

出版社コード、販売会社、発売元などを出版社名として誤って採用しない。

---

## 14.17 出版日

出版日は、原則として `summary.pubdate` から取得する。

openBDでは、次のような形式が返される可能性がある。

```text id="tcd4ix"
20231027
202310
2023
```

第1段階では、文字列として保持する。

次のような変換は行わない。

```text id="5xq3z0"
20231027 → 2023-10-27
```

形式変換が必要な場合は、取得元の精度を維持できる共通規則を別途定める。

---

## 14.18 内容紹介

内容紹介は、`summary` だけでは取得できない場合がある。

その場合は、`hanmoto` またはONIX内の説明文を候補とする。

候補となる情報には、次のような種類が含まれる可能性がある。

* 内容紹介
* 目次
* 著者紹介
* 出版社コメント
* 書店向け販促文
* 帯文
* 短い要約
* 長い要約

第1段階では、書籍の内容紹介として適切なテキストだけを採用する。

目次や著者紹介を内容紹介へ無条件に設定しない。

---

## 14.19 内容紹介の優先順位

openBD内に複数の説明文がある場合は、次の考え方で選択する。

1. 書籍内容の要約として明確な説明文
2. 出版社による内容紹介
3. 書店向けの短い紹介文
4. その他の説明文

実際のONIXコードやhanmoto項目を確認し、Fixtureテストを基に具体的な優先順位を実装する。

項目の意味が明確でない場合は採用しない。

---

## 14.20 HTMLおよび改行

内容紹介にHTMLタグが含まれる場合でも、GUI上でHTMLとして実行しない。

次の処理を検討する。

* HTMLタグの除去
* HTMLエンティティの変換
* 改行要素のプレーンテキスト化
* 前後空白の除去
* 連続する不要な空行の整理

ただし、本文内容を損なうような過度な整形を行わない。

---

## 14.21 表紙画像URL

表紙画像URLは、原則として `summary.cover` から取得する。

値が存在しない場合は `None` とする。

第1段階では、画像取得、保存、キャッシュおよびGUI表示を行わない。

---

## 14.22 出版形態

openBDまたはONIX内に、判型、製品形態または商品形態に関する情報が含まれる場合がある。

ただし、それらを既存アプリケーションの次の分類へ変換するには、明確な対応表が必要となる。

```text id="la0w16"
文庫
単行本
電子書籍
```

第1段階では、確実な変換規則が定義できる項目だけ設定する。

判型が小さいことだけを理由に「文庫」と判定しない。

電子配信商品であることが明確な場合に限り、「電子書籍」を候補とできる。

---

## 14.23 `FetchedBookData` 生成

概念例を次に示す。

```python id="o9ihzt"
return FetchedBookData(
    isbn=isbn,
    title=title,
    authors=authors,
    publisher=publisher,
    publication_date=publication_date,
    publication_format=publication_format,
    description=description,
    cover_image_url=cover_image_url,
    sources=(self.source_name,),
    raw_data={
        self.source_name: {
            "query": {
                "isbn": isbn,
            },
            "response": payload,
        },
    },
)
```

最終統合時に、ServiceがISBNを正規化済み入力値へ置き換える。

---

## 14.24 Rawデータ

openBDのRawレスポンスは、取得元名をキーとして保持できる。

```python id="ejw43d"
raw_data={
    "openBD": {
        "query": {
            "isbn": isbn,
        },
        "response": payload,
    },
}
```

Rawレスポンスは、SQLiteへ保存しない。

また、レスポンス量が大きい場合でも、第1段階では無制限にログへ出力しない。

---

## 14.25 HTTP 429

HTTP 429を受信した場合は、`BookMetadataRateLimitError` を送出する。

openBDで現在明示的な利用制限が確認できない場合でも、HTTP共通処理として429を専用扱いする。

自動再試行は行わない。

---

## 14.26 HTTP異常

HTTP 400番台または500番台の異常応答は、原則として `BookMetadataResponseError` へ変換する。

接続自体が成立しない場合やtimeoutは、`BookMetadataConnectionError` とする。

---

## 14.27 JSON解析失敗

レスポンスをJSONとして解析できない場合は、`BookMetadataResponseError` とする。

HTMLエラーページなどがHTTP 200で返された場合も、不正応答として扱う。

レスポンス本文をそのまま利用者へ表示しない。

---

## 14.28 ログ項目

openBD Clientでは、必要に応じて次をログへ記録する。

* 取得元
* 問い合わせISBN
* HTTPステータス
* 配列要素数
* 対象要素の有無
* ISBN一致結果
* 処理時間
* 例外種別

レスポンス全文は通常ログへ記録しない。

---

## 14.29 テストFixture

openBD Clientのテストでは、実APIを呼び出さず、FixtureまたはFake Responseを使用する。

少なくとも次のFixtureを用意する。

* `summary` に全項目あり
* 著者なし
* 出版社なし
* 内容紹介なし
* 表紙画像なし
* `summary` なし
* `onix` から補完可能
* `hanmoto` から内容紹介取得
* 出版日が年月日
* 出版日が年月
* 出版日が年だけ
* 配列要素が `null`
* 空配列
* ISBN不一致
* HTTP 429
* HTTP 404
* HTTP 500
* timeout
* JSON解析失敗
* トップレベルが辞書
* 想定外の配列要素

---

## 14.30 openBD連携上の禁止事項

次の実装は禁止する。

* timeoutなし通信
* 配列先頭要素の無条件採用
* `null` を不正レスポンスとして扱う。
* ISBN照合なしの採用
* ONIX項目の意味を確認せず利用する。
* Contributorをすべて著者として結合する。
* 判型だけで文庫と判定する。
* 内容紹介以外の文章を無条件にdescriptionへ設定する。
* RawレスポンスをGUIへ直接返す。
* 実APIへ依存する自動テスト

---

# 15. データ統合

## 15.1 目的

データ統合処理は、複数の外部取得元から得た `FetchedBookData` を、一つの統合済み結果へまとめる。

第1段階では、Google Booksを先順位、openBDを後順位とする。

後順位のデータは、先順位で取得できなかった項目だけを補完する。

---

## 15.2 統合の基本原則

統合では次の原則を適用する。

* Client登録順を優先順位とする。
* 最初に取得できた有効値を採用する。
* 後順位の値で先順位の値を上書きしない。
* `None` または空文字列を空欄とみなす。
* 取得元ごとのRawデータを保持する。
* 取得元一覧の順序を維持する。
* 入力ISBNを統合結果のISBNとして使用する。
* 不一致値を自動的に混合しない。

---

## 15.3 統合対象項目

空欄補完方式で統合する項目は次のとおりである。

* 書籍名
* 著者名
* 出版社
* 出版日
* 出版形態
* 内容紹介
* 表紙画像URL

次の項目は個別の統合規則を使用する。

* ISBN
* 取得元
* Rawデータ

---

## 15.4 空欄判定

次の値は空欄として扱う。

```python id="b45517"
None
""
" "
"\t"
"\n"
```

文字列の場合は、前後空白を除去して判定する。

共通関数の概念例を次に示す。

```python id="8dyyuq"
def has_meaningful_value(
    value: object,
) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    return True
```

第1段階では、統合対象の主要項目は文字列または `None` である。

---

## 15.5 統合順序

初期の統合順序は次のとおりである。

```text id="03ev9e"
1. Google Books
2. openBD
```

ServiceへClientを追加する順序が統合優先順位となる。

```python id="43nzb9"
clients = [
    google_books_client,
    openbd_client,
]
```

優先順位をClientクラス内部へハードコードしない。

---

## 15.6 項目単位の統合

統合は結果オブジェクト単位ではなく、項目単位で行う。

例を次に示す。

| 項目    | Google Books | openBD  | 統合結果  |
| :---- | :----------- | :------ | :---- |
| 書籍名   | 書籍A          | 書籍A 改訂版 | 書籍A   |
| 著者名   | 著者A          | 著者A     | 著者A   |
| 出版社   | 未取得          | 出版社B    | 出版社B  |
| 内容紹介  | 紹介A          | 紹介B     | 紹介A   |
| 表紙URL | 未取得          | URL-B   | URL-B |

Google Booksの結果全体を採用し、openBDの結果全体を破棄する方式にはしない。

---

## 15.7 書籍名の統合

書籍名は、先順位で有効な値を取得できた場合、その値を維持する。

後順位の書籍名が長い、詳しい、または副題を含む場合でも、自動上書きしない。

第1段階では、品質比較による自動選択を行わない。

---

## 15.8 著者名の統合

著者名も空欄補完方式とする。

先順位で取得した著者名に生没年がなく、後順位に生没年が含まれる場合でも、自動的に混合しない。

次のような結合は行わない。

```text id="y0ps3a"
Google Books:
松本清張

openBD:
松本,清張,1909-1992

不適切な統合:
松本清張、松本,清張,1909-1992
```

将来の著者マスタ正規化で、表記差を扱う。

---

## 15.9 出版社の統合

出版社は、先順位が空欄の場合だけ後順位で補完する。

会社種別の表記差を自動的に統一しない。

例を次に示す。

```text id="6mz7oc"
株式会社文藝春秋
文藝春秋
```

第1段階では、これらの同一性判定は行わない。

---

## 15.10 出版日の統合

出版日も先順位優先とする。

先順位が年だけで、後順位が年月日まで取得できた場合でも、第1段階では後順位で上書きしない。

例を次に示す。

```text id="tm114l"
Google Books:
2023

openBD:
20231027

統合結果:
2023
```

より高精度な日付を優先する設計は合理性があるが、空欄補完方針と異なるため、第1段階では採用しない。

将来、項目別の品質比較規則として検討する。

---

## 15.11 出版形態の統合

出版形態は、先順位で確実な値が取得できた場合に維持する。

先順位が `None` で、後順位が既存GUIの許容値へ明確に変換できる場合だけ補完する。

不明確な値を使用しない。

---

## 15.12 内容紹介の統合

内容紹介は、先順位で有効な値を取得できた場合、その値を維持する。

文字数が多いことだけを理由に、後順位の内容紹介で上書きしない。

また、二つの内容紹介を連結しない。

---

## 15.13 表紙画像URLの統合

表紙画像URLは、先順位で有効な値を取得できた場合、そのURLを維持する。

画像解像度の比較、URL到達確認または画像サイズ比較は、第1段階では行わない。

---

## 15.14 ISBNの統合

統合結果のISBNには、Serviceで正規化した利用者入力ISBNを使用する。

各Clientが返したISBNは、検索候補の照合には使用するが、最終表示値として優先しない。

```python id="pgnlyv"
merged.isbn = normalized_input_isbn
```

---

## 15.15 取得元の統合

`sources` は、Client優先順位を維持して結合する。

同じ値を重複させない。

概念例を次に示す。

```python id="kqgrke"
sources: list[str] = []

for result in results:
    for source in result.sources:
        if source not in sources:
            sources.append(source)
```

最終的にはタプルへ変換する。

```python id="nqfzru"
merged_sources = tuple(sources)
```

---

## 15.16 Rawデータの統合

`raw_data` は取得元名をキーとして結合する。

```python id="mj719m"
merged_raw_data: dict[str, Any] = {}

for result in results:
    merged_raw_data.update(
        result.raw_data,
    )
```

同じ取得元名が重複した場合は設計異常である。

必要に応じて上書きではなく例外または警告ログとする。

---

## 15.17 統合メソッド

概念的な統合メソッドを次に示す。

```python id="oa0355"
def _merge_results(
    self,
    input_isbn: str,
    results: list[FetchedBookData],
) -> FetchedBookData:
    return FetchedBookData(
        isbn=input_isbn,
        title=self._first_value(
            result.title
            for result in results
        ),
        authors=self._first_value(
            result.authors
            for result in results
        ),
        publisher=self._first_value(
            result.publisher
            for result in results
        ),
        publication_date=self._first_value(
            result.publication_date
            for result in results
        ),
        publication_format=self._first_value(
            result.publication_format
            for result in results
        ),
        description=self._first_value(
            result.description
            for result in results
        ),
        cover_image_url=self._first_value(
            result.cover_image_url
            for result in results
        ),
        sources=self._merge_sources(results),
        raw_data=self._merge_raw_data(results),
    )
```

実装時は、可読性を優先して補助メソッドへ分割する。

---

## 15.18 最初の有効値

最初の有効値を取得する補助メソッドの概念例を次に示す。

```python id="g2d6va"
def _first_value(
    self,
    values: Iterable[str | None],
) -> str | None:
    for value in values:
        if value is None:
            continue

        normalized = value.strip()

        if normalized:
            return normalized

    return None
```

文字列以外の項目を将来追加する場合は、型に応じて別メソッドを用意する。

---

## 15.19 有効結果の判定

統合後、少なくとも一つの有効な書誌項目があるか確認する。

```python id="lt7hn7"
def _has_useful_metadata(
    self,
    data: FetchedBookData,
) -> bool:
    return any(
        (
            data.title,
            data.authors,
            data.publisher,
            data.publication_date,
            data.publication_format,
            data.description,
            data.cover_image_url,
        )
    )
```

実装では、空白文字列を除外する共通判定を使用する。

ISBN、取得元およびRawデータだけでは、有効な書誌情報とはみなさない。

---

## 15.20 部分失敗時の統合

一部Clientが失敗した場合でも、成功したClientの結果だけで統合する。

例を次に示す。

```text id="75lxnv"
Google Books:
BookMetadataConnectionError

openBD:
タイトル、出版社を取得

結果:
openBDの値を返す。
```

失敗したClientの空の `FetchedBookData` を作って統合しない。

---

## 15.21 すべて空欄の場合

Clientが `FetchedBookData` を返しても、すべての書誌項目が空欄の場合は、有効結果とみなさない。

この場合、他のClient結果も有効でなければ、最終的に対象なしまたは取得エラーを送出する。

Rawデータが存在するだけでは成功としない。

---

## 15.22 値の競合

取得元間で値が異なる場合、第1段階では競合通知を行わない。

先順位の値を採用する。

ただし、将来のデバッグやレビュー用として、競合情報をログへ記録する拡張は検討できる。

例を次に示す。

```text id="9qt8io"
title conflict:
Google Books = 書籍A
openBD = 書籍A 新装版
```

第1段階では、通常ログを過度に増やさない。

---

## 15.23 将来の統合拡張

将来、次の統合方式を検討できる。

* 項目ごとの取得元優先順位
* 出版日の精度比較
* 表紙画像の解像度比較
* 内容紹介の品質判定
* 著者名正規化
* 出版社マスタ照合
* 信頼度スコア
* 利用者による候補選択
* 競合項目の確認ダイアログ

これらは第1段階の対象外とする。

---

## 15.24 データ統合のテスト観点

少なくとも次を確認する。

* Google Booksの値が優先される。
* openBDが空欄だけを補完する。
* 空文字列が有効値として採用されない。
* 空白だけの値が採用されない。
* 著者名が連結されない。
* 内容紹介が連結されない。
* 入力ISBNが維持される。
* 取得元が順序を維持して結合される。
* 取得元が重複しない。
* Rawデータが取得元別に結合される。
* 一部Client失敗時も統合できる。
* 全項目空欄の場合は成功としない。

---

## 15.25 データ統合上の禁止事項

次の実装は禁止する。

* 後順位で先順位を無条件上書きする。
* 長い文字列を自動的に優先する。
* 著者名を取得元間で連結する。
* 内容紹介を取得元間で連結する。
* ISBNを外部API値へ自動変更する。
* RawデータをDBへ保存する。
* 値の競合を推測で解決する。
* Clientごとに異なる統合規則を持たせる。

---

# 16. エラー設計

## 16.1 目的

エラー設計では、外部書誌情報取得中に発生する異常を分類し、各層で一貫した方法で処理する。

利用者が次に取るべき行動を判断できること、開発者が原因を追跡できること、および既存機能へ影響を波及させないことを目的とする。

---

## 16.2 エラー分類

本機能で扱うエラーは、次の分類とする。

| 分類    | 例                       |
| :---- | :---------------------- |
| 入力エラー | ISBN未入力、形式不正、チェックデジット不正 |
| 対象なし  | 外部サービスに該当書籍がない          |
| 接続エラー | 通信失敗、DNS、timeout、TLS    |
| 利用制限  | HTTP 429、明確なクォータ超過      |
| 応答エラー | HTTP異常、JSON不正、構造不正      |
| 設定エラー | APIキー未設定、設定値不正          |
| 内部エラー | 想定外のプログラム例外             |

---

## 16.3 層ごとの責務

| 層       | エラー処理の責務                        |
| :------ | :------------------------------ |
| Client  | HTTP・JSON・API固有異常をアプリケーション例外へ変換 |
| Service | 複数Clientの結果と例外を集約し、最終結果を決定      |
| GUI     | 例外を利用者向け表示へ変換                   |
| ログ      | 開発者向けの技術情報を記録                   |

Clientが利用者向けダイアログを表示してはならない。

GUIがHTTPステータスやJSON構造を直接解析してはならない。

---

## 16.4 入力エラー

入力エラーは、外部Clientを呼び出す前に検出する。

想定例は次のとおりである。

* ISBNが空
* ISBNが10桁または13桁でない
* 使用できない文字を含む
* ISBN-10のチェックデジット不正
* ISBN-13のチェックデジット不正
* ISBN-13の接頭辞不正

入力エラーは、通信エラーや応答エラーへ変換しない。

---

## 16.5 対象なし

外部APIから正常応答を受け取ったが、対象ISBNの書誌情報が存在しない状態を「対象なし」とする。

対象なしは、システム障害ではない。

次の状態を対象なしとして扱う。

* Google Booksの検索件数が0
* Google BooksにISBN一致候補がない
* openBDの要素が `null`
* openBDにISBN一致要素がない
* 正常レスポンスだが有効書誌項目がない

すべてのClientが対象なしの場合に、Serviceが `BookMetadataNotFoundError` を送出する。

---

## 16.6 接続エラー

次を接続エラーとして扱う。

* DNS解決失敗
* 接続拒否
* 接続timeout
* 読み取りtimeout
* TLSハンドシェイク失敗
* プロキシ接続失敗
* ネットワーク切断

Clientは、`requests.RequestException` 系の例外を適切に変換する。

接続エラー時に、対象なしとして `None` を返してはならない。

---

## 16.7 利用制限

HTTP 429は、専用の利用制限エラーとする。

APIレスポンスがHTTP 403であっても、内容から明確にクォータ超過と判定できる場合は、利用制限として扱うことができる。

利用制限では、自動再試行を行わない。

利用者には、時間をおいて再試行するよう案内する。

---

## 16.8 応答エラー

次を応答エラーとして扱う。

* HTTP 400番台の異常
* HTTP 500番台の異常
* JSON解析失敗
* HTMLなどJSON以外の応答
* トップレベル型の不一致
* 必須構造の破損
* APIエラーオブジェクト
* 想定外のレスポンス仕様変更

個別項目が欠落しているだけの場合は、応答エラーとしない。

その項目を `None` として部分成功を許容する。

---

## 16.9 設定エラー

設定エラーの候補は次のとおりである。

* APIキーが必須なのに未設定
* timeout値が不正
* Clientが一つも登録されていない
* エンドポイント設定が空
* 環境変数の形式が不正

設定エラーは、利用者操作による通常エラーとは性質が異なる。

アプリケーション起動時に検出できるものは、早期に検出する。

---

## 16.10 内部エラー

次を内部エラーとして扱う。

* `AttributeError`
* `TypeError`
* 想定外の `KeyError`
* 統合処理の不具合
* 型契約違反
* 未処理のプログラム例外

内部エラーをすべて外部サービスの接続エラーへ変換してはならない。

開発者向けログへスタックトレースを記録し、利用者には一般的なメッセージを表示する。

---

## 16.11 エラー処理フロー

```text id="6w3ccr"
外部APIまたは入力
        │
        ▼
Client / ISBN処理
        │
        │ 例外変換
        ▼
BookMetadataService
        │
        │ 集約・最終判定
        ▼
GUI
        │
        │ 利用者向け表示
        ▼
利用者
```

技術的な詳細は、例外チェーンとログによって保持する。

---

## 16.12 例外チェーン

Clientが外部ライブラリ例外をアプリケーション例外へ変換する場合は、`raise ... from exc` を使用する。

```python id="8bb0ku"
except requests.Timeout as exc:
    raise BookMetadataConnectionError(
        "Google Booksへの接続が"
        "タイムアウトしました。"
    ) from exc
```

これにより、利用者向け例外を抽象化しつつ、原因追跡を可能にする。

---

## 16.13 例外の握りつぶし禁止

次のような実装は禁止する。

```python id="to3tqi"
try:
    ...
except Exception:
    return None
```

すべての異常が対象なしとして扱われ、障害原因を特定できなくなるためである。

`None` は正常応答における対象なしだけに使用する。

---

## 16.14 Clientエラーの集約

Serviceは、一つのClient例外だけで処理を終了しない。

他のClientから有効な結果を取得できる可能性があるためである。

ただし、入力エラーは全Clientに共通するため、Client呼び出し前に処理を終了する。

---

## 16.15 部分成功時の扱い

次の場合は、成功として扱う。

```text id="yh7tyq"
Google Books:
接続失敗

openBD:
有効な書誌情報を取得
```

有効結果がある場合は、その結果をGUIへ返す。

失敗したClientのエラーを利用者へ重ねて表示しない。

必要に応じて警告ログへ記録する。

---

## 16.16 全Client失敗時

すべてのClientが失敗し、有効結果がない場合は、Serviceが最終例外を選択する。

優先順位は次のとおりとする。

```text id="gg80yv"
1. 利用制限
2. 接続エラー
3. 応答エラー
4. 基底エラー
```

この優先順位は、利用者が再試行方法を判断しやすくするためである。

---

## 16.17 対象なしとエラーの混在

次のように対象なしとエラーが混在し、有効結果がない場合がある。

```text id="96bg76"
Google Books:
対象なし

openBD:
接続エラー
```

この場合は、対象なしと断定できないため、接続エラーを最終結果とする。

すべてのClientが正常に対象なしを返した場合だけ、`BookMetadataNotFoundError` とする。

---

## 16.18 GUI表示との対応

| 例外または状態                     | GUI表示       |
| :-------------------------- | :---------- |
| ISBN未入力                     | 警告          |
| ISBN形式不正                    | 警告          |
| BookMetadataNotFoundError   | 情報          |
| BookMetadataRateLimitError  | 警告          |
| BookMetadataConnectionError | エラー         |
| BookMetadataResponseError   | エラー         |
| 設定エラー                       | エラーまたは起動時通知 |
| 想定外例外                       | 一般エラー       |

---

## 16.19 利用者向けメッセージ

利用者向けメッセージには、次を含める。

* 何が起きたか
* 必要に応じて次に行うこと

例を次に示す。

```text id="hybr2y"
書籍情報サービスへ接続できませんでした。
インターネット接続を確認してから再試行してください。
```

次は含めない。

* Python例外クラス名
* スタックトレース
* APIキー
* リクエストURL全文
* JSONレスポンス全文
* 内部ファイルパス

---

## 16.20 開発者向けログ

開発者向けログには、必要に応じて次を記録する。

* 取得元
* ISBN
* 例外クラス
* HTTPステータス
* timeout種別
* 処理時間
* 例外チェーン
* スタックトレース
* 最終的に選択した例外

秘密情報は記録しない。

---

## 16.21 エラー設計のテスト観点

少なくとも次を確認する。

* 対象なしと通信失敗を区別する。
* HTTP 429が専用例外になる。
* timeoutが接続例外になる。
* JSON解析失敗が応答例外になる。
* 一部Client失敗時に成功できる。
* 全Client対象なしでNotFoundになる。
* 対象なしと接続失敗の混在で接続例外になる。
* 例外チェーンが保持される。
* APIキーが例外文やログへ出ない。
* 想定外例外が握りつぶされない。

---

## 16.22 エラー設計上の禁止事項

次の実装は禁止する。

* すべてのエラーを `None` で返す。
* すべてのエラーを同じ例外に変換する。
* HTTP 429を対象なしとして扱う。
* Client内でダイアログを表示する。
* 利用者へスタックトレースを表示する。
* 例外の原因を失う再送出
* 一部成功を全体失敗とする。
* 想定外例外を無条件に握りつぶす。
* APIキーをエラー情報へ含める。

---

# 17. 例外設計

## 17.1 目的

例外設計では、外部書誌情報取得機能が送出する例外クラス、保持する情報、および各層での使用方法を定義する。

外部ライブラリ固有の例外をGUIまで伝播させず、アプリケーション内部で意味のある例外へ変換する。

---

## 17.2 例外階層

例外階層は次のとおりとする。

```text id="ioobsv"
BookMetadataError
├─ BookMetadataConnectionError
├─ BookMetadataResponseError
├─ BookMetadataRateLimitError
├─ BookMetadataNotFoundError
└─ BookMetadataConfigurationError
```

ISBN入力不正については、既存の入力検証方針に合わせて次のいずれかを採用する。

* `ValueError`
* 既存のValidationError
* 新しい `InvalidIsbnError`

第1段階では、プロジェクト全体の例外設計との整合性を優先する。

---

## 17.3 基底例外

`BookMetadataError` は、外部書誌情報取得に関する例外の基底クラスとする。

```python id="cld3mp"
class BookMetadataError(Exception):
    """外部書誌情報取得に関する基底例外。"""
```

GUIでは、個別例外を処理した後の最終フォールバックとして使用できる。

---

## 17.4 接続例外

`BookMetadataConnectionError` は、外部サービスへの通信が成立しなかった場合に使用する。

```python id="a1q0w1"
class BookMetadataConnectionError(
    BookMetadataError
):
    """外部サービスへの接続失敗。"""
```

対象例は次のとおりである。

* 接続timeout
* 読み取りtimeout
* DNS失敗
* 接続拒否
* TLS失敗
* ネットワーク切断

---

## 17.5 応答例外

`BookMetadataResponseError` は、外部サービスから応答を受け取ったが、正常に処理できない場合に使用する。

```python id="azpxbc"
class BookMetadataResponseError(
    BookMetadataError
):
    """外部サービスからの応答不正。"""
```

対象例は次のとおりである。

* HTTP 400番台
* HTTP 500番台
* JSON解析失敗
* レスポンス構造不正
* APIエラーオブジェクト
* 想定外のトップレベル型

HTTP 429は、専用の利用制限例外を使用する。

---

## 17.6 利用制限例外

`BookMetadataRateLimitError` は、API利用制限に達した場合に使用する。

```python id="ihtg61"
class BookMetadataRateLimitError(
    BookMetadataError
):
    """外部サービスの利用制限。"""
```

対象例は次のとおりである。

* HTTP 429
* 明確なクォータ超過
* APIレスポンスで利用上限到達が明示された場合

---

## 17.7 対象なし例外

`BookMetadataNotFoundError` は、すべての取得元で対象ISBNの書誌情報が見つからなかった場合にServiceが送出する。

```python id="grx6b6"
class BookMetadataNotFoundError(
    BookMetadataError
):
    """対象書籍情報が見つからない。"""
```

Client単体では、対象なしを `None` で返す。

Serviceが複数Clientの結果を集約した後に、この例外へ変換する。

---

## 17.8 設定例外

`BookMetadataConfigurationError` は、外部取得機能の設定不備を表す。

```python id="b5kpu5"
class BookMetadataConfigurationError(
    BookMetadataError
):
    """外部書誌情報取得の設定不備。"""
```

対象例は次のとおりである。

* 必須APIキーが未設定
* Client設定が不正
* timeout値が不正
* 利用可能なClientがない
* エンドポイント設定が不正

---

## 17.9 例外属性

必要に応じて、例外へ次の属性を持たせることを検討する。

| 属性                | 説明           |
| :---------------- | :----------- |
| source_name       | エラーが発生した取得元  |
| status_code       | HTTPステータス    |
| retry_after       | 再試行可能時刻または秒数 |
| technical_message | ログ用の技術情報     |
| user_message      | 利用者向け候補文     |
| isbn              | 問い合わせISBN    |

第1段階では、過度に複雑な例外クラスを作らず、必要最小限の属性に限定する。

---

## 17.10 推奨する例外実装

概念例を次に示す。

```python id="yduwt6"
class BookMetadataError(Exception):
    def __init__(
        self,
        message: str,
        *,
        source_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.source_name = source_name
```

HTTP応答例外の例を次に示す。

```python id="0hh26r"
class BookMetadataResponseError(
    BookMetadataError
):
    def __init__(
        self,
        message: str,
        *,
        source_name: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            message,
            source_name=source_name,
        )
        self.status_code = status_code
```

実装量と利用価値を比較し、必要な属性だけを採用する。

---

## 17.11 利用者向け文言と例外本文

例外本文を、そのまま利用者向けダイアログへ表示する設計は避ける。

例外本文は、開発者向けまたはログ向けの情報を含む可能性がある。

GUIは、例外クラスに応じて固定または整形済みの利用者向けメッセージを表示する。

例を次に示す。

```python id="r1c0v3"
except BookMetadataConnectionError:
    messagebox.showerror(
        "接続エラー",
        (
            "書籍情報サービスへ"
            "接続できませんでした。\n"
            "インターネット接続を確認して"
            "再試行してください。"
        ),
    )
```

---

## 17.12 Clientからの送出

Clientは、次の例外を送出できる。

* `BookMetadataConnectionError`
* `BookMetadataResponseError`
* `BookMetadataRateLimitError`
* `BookMetadataConfigurationError`

Clientは、通常の対象なしでは例外を送出せず `None` を返す。

`BookMetadataNotFoundError` はServiceが送出する。

---

## 17.13 Serviceからの送出

Serviceは、次の例外を送出できる。

* ISBN入力不正に関する例外
* `BookMetadataNotFoundError`
* `BookMetadataConnectionError`
* `BookMetadataResponseError`
* `BookMetadataRateLimitError`
* `BookMetadataConfigurationError`
* `BookMetadataError`

一つ以上の有効な取得結果がある場合は、他Clientの例外を原則として送出しない。

---

## 17.14 GUIでの捕捉順序

GUIでは、より具体的な例外から順に捕捉する。

```python id="ftihwg"
try:
    metadata = (
        self._metadata_service.fetch_by_isbn(
            isbn,
        )
    )
except BookMetadataNotFoundError:
    ...
except BookMetadataRateLimitError:
    ...
except BookMetadataConnectionError:
    ...
except BookMetadataResponseError:
    ...
except BookMetadataConfigurationError:
    ...
except BookMetadataError:
    ...
```

基底例外を先に捕捉してはならない。

---

## 17.15 外部ライブラリ例外の境界

次の例外をGUIへ直接伝播させない。

* `requests.Timeout`
* `requests.ConnectionError`
* `requests.HTTPError`
* JSONデコード例外
* `urllib3` 固有例外
* API固有エラー型

これらはClient境界で、アプリケーション例外へ変換する。

---

## 17.16 `ValueError` の扱い

JSON解析で発生する `ValueError` と、ISBN入力不正で使用する `ValueError` を混同しない。

JSON解析の `ValueError` はClient内で `BookMetadataResponseError` へ変換する。

GUIへ到達する `ValueError` は、原則として入力検証に限定する。

より明確にするため、将来 `InvalidIsbnError` の導入を検討できる。

---

## 17.17 専用ISBN例外の候補

専用例外を導入する場合は、次の構造とする。

```python id="z2uqqh"
class InvalidIsbnError(ValueError):
    """ISBNの形式またはチェックデジット不正。"""
```

外部書誌情報取得例外の配下には置かず、入力検証例外として扱う。

理由は、ISBN検証が外部API以外の機能でも再利用される可能性があるためである。

---

## 17.18 例外チェーンの保持

例外変換時は、元の原因を保持する。

```python id="b9x9j6"
except requests.RequestException as exc:
    raise BookMetadataConnectionError(
        "openBDへの接続に失敗しました。",
        source_name=self.source_name,
    ) from exc
```

`from None` によって原因を隠す実装は、利用者向け表示以外では原則として行わない。

---

## 17.19 例外の再利用

同じ意味の例外をClientごとに個別定義しない。

次のような例外は作らない。

```text id="gkw6xc"
GoogleBooksConnectionError
OpenBdConnectionError
GoogleBooksRateLimitError
OpenBdRateLimitError
```

取得元の違いは、共通例外の `source_name` 属性やメッセージで表現する。

これにより、GUIの捕捉処理を共通化できる。

---

## 17.20 最終例外選択

Serviceが複数Clientの例外から最終例外を選ぶ場合、元の例外オブジェクトを可能な限り再送出する。

これにより、`source_name`、`status_code` および例外チェーンを維持できる。

新しい例外へまとめ直す場合は、代表例外を `from` で原因として保持する。

---

## 17.21 例外メッセージの方針

内部例外メッセージは、次を満たす。

* どの取得元で発生したか判断できる。
* エラー種別が分かる。
* APIキーを含まない。
* URLの秘密パラメータを含まない。
* 長大なレスポンス本文を含まない。
* ログで原因追跡できる情報量を持つ。

例を次に示す。

```text id="w7of41"
Google BooksからJSONレスポンスを解析できませんでした。
```

---

## 17.22 例外クラスの配置

推奨配置は次のとおりである。

```text id="kdhdww"
src/
└── book_manager/
    └── metadata/
        ├── exceptions.py
        ├── service.py
        └── clients/
```

既存の例外管理方針がある場合は、それに合わせて配置してよい。

ただし、Clientファイルごとに同じ例外を重複定義しない。

---

## 17.23 例外のテスト

少なくとも次を検証する。

* timeoutが接続例外へ変換される。
* HTTP 429が利用制限例外になる。
* HTTP 500が応答例外になる。
* JSON解析失敗が応答例外になる。
* 対象なしではClientが `None` を返す。
* 全Client対象なしでServiceがNotFoundを送出する。
* 例外チェーンが保持される。
* `source_name` が保持される。
* HTTPステータスが必要に応じて保持される。
* GUIが具体例外を正しい順序で捕捉する。
* APIキーが例外文に含まれない。

---

## 17.24 例外設計上の禁止事項

次の実装は禁止する。

* Clientごとに同義の例外を乱立させる。
* 外部ライブラリ例外をGUIへ直接伝播させる。
* 例外本文を無条件に利用者へ表示する。
* 例外原因を失う再送出
* すべての異常を基底例外だけで表す。
* 対象なしを接続例外として扱う。
* 一部成功時に不要な例外を送出する。
* APIキーやレスポンス全文を例外へ含める。
* 基底例外を具体例外より先に捕捉する。

---
# 18. HTTP通信設計

## 18.1 目的

HTTP通信設計では、外部書誌情報サービスとの通信方法、timeout、Session、ステータス判定および通信例外の扱いを定義する。

通信処理は各API Clientへ閉じ込め、GUIおよびServiceからHTTPライブラリの詳細を隠蔽する。

---

## 18.2 使用ライブラリ

HTTP通信には `requests` を使用する。

基本的な依存関係は次のとおりである。

```text
GoogleBooksClient
        │
        ▼
requests.Session
        │
        ▼
Google Books API
```

```text
OpenBdClient
        │
        ▼
requests.Session
        │
        ▼
openBD API
```

標準ライブラリの `urllib` と `requests` を混在させない。

---

## 18.3 Sessionの利用

各Clientは、`requests.get()` を直接呼び出さず、注入された `requests.Session` を使用する。

```python
response = self._session.get(
    self.BASE_URL,
    params=params,
    timeout=self._timeout,
)
```

Sessionを利用する目的は次のとおりである。

* TCP接続を再利用する。
* 共通ヘッダーを設定する。
* 通信設定を集約する。
* テスト時にFake Sessionへ差し替える。
* Client内部で通信オブジェクトを固定しない。
* 将来のリトライ設定やプロキシ設定に対応しやすくする。

---

## 18.4 Sessionの生成箇所

Sessionは、アプリケーション起動時の依存関係組み立て箇所で生成する。

```python
session = requests.Session()

google_books_client = GoogleBooksClient(
    session=session,
    api_key=google_books_api_key,
)

openbd_client = OpenBdClient(
    session=session,
)
```

GUIイベント処理内で毎回Sessionを生成しない。

Clientのコンストラクタ内で無条件にSessionを生成する設計も採用しない。

---

## 18.5 Session共有方針

第1段階では、Google BooksとopenBDで同一のSessionを共有してよい。

```python
session = requests.Session()

clients = [
    GoogleBooksClient(
        session=session,
        api_key=api_key,
    ),
    OpenBdClient(
        session=session,
    ),
]
```

同一Sessionを共有する利点は次のとおりである。

* 構成が単純になる。
* 共通ヘッダーを一か所で設定できる。
* Sessionのライフサイクルを管理しやすい。
* テスト時の差し替えが容易になる。

ただし、将来、取得元ごとにプロキシ、認証、リトライまたはヘッダーを分ける必要が生じた場合は、別Sessionを注入できる構造を維持する。

---

## 18.6 Sessionの終了

アプリケーション終了時には、可能であればSessionを閉じる。

```python
session.close()
```

GUIアプリケーションの終了処理にSessionの破棄を組み込む場合は、SQLite接続など他のリソースと合わせて管理する。

Sessionを閉じた後にClientを再利用しない。

---

## 18.7 timeout

すべてのHTTP通信でtimeoutを必須とする。

第1段階のDesign Freeze値は次のとおりである。

```python
DEFAULT_TIMEOUT = (5, 10)
```

各値の意味は次のとおりである。

| 値   | 意味          |
| :-- | :---------- |
| 5秒  | 接続timeout   |
| 10秒 | 読み取りtimeout |

---

## 18.8 接続timeout

接続timeoutは、外部サービスとのTCP接続が成立するまでの待機時間を制限する。

対象となる状態は次のとおりである。

* 接続先が応答しない。
* ネットワーク経路に問題がある。
* プロキシへ接続できない。
* TLS接続の開始に時間がかかる。

接続timeoutは5秒とする。

---

## 18.9 読み取りtimeout

読み取りtimeoutは、接続後にサーバーからデータを受信するまでの待機時間を制限する。

読み取りtimeoutは10秒とする。

これは処理全体の総時間が必ず10秒以内になることを意味しない。

複数Clientを順次呼び出すため、全体の待機時間はClient数と障害状態によって増える可能性がある。

---

## 18.10 timeout値の注入

Clientはtimeoutをコンストラクタで受け取れるようにする。

```python
class GoogleBooksClient:
    def __init__(
        self,
        session: requests.Session,
        api_key: str | None = None,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._timeout = timeout
```

テストでは短いtimeout値を注入できる。

ただし、自動テストでは原則として実通信を行わないため、timeout動作はFakeまたはMockで再現する。

---

## 18.11 timeout値の検証

timeoutは、正の数値からなる2要素タプルを前提とする。

不正な値の例は次のとおりである。

```python
(0, 10)
(-1, 10)
(5,)
"5,10"
None
```

必要に応じて、アプリケーション構成時またはClientコンストラクタで検証する。

過度な防御コードを各Clientへ重複させず、共通設定オブジェクトで検証する方式も将来検討できる。

---

## 18.12 リクエストメソッド

第1段階では、Google BooksおよびopenBDの取得にHTTP GETを使用する。

リクエストパラメータは `params` 引数で指定する。

```python
params = {
    "isbn": isbn,
}

response = self._session.get(
    self.BASE_URL,
    params=params,
    timeout=self._timeout,
)
```

クエリ文字列を手作業で連結しない。

---

## 18.13 HTTPS

外部サービスへの接続にはHTTPSを使用する。

HTTPエンドポイントへ自動的にフォールバックしない。

表紙画像URLなど、外部レスポンス内のURLは別のデータとして扱い、API通信のHTTPS要件とは分離する。

---

## 18.14 TLS検証

`requests` の既定の証明書検証を有効のまま使用する。

次のような設定は行わない。

```python
verify=False
```

証明書エラーを回避するために検証を無効化してはならない。

TLS関連エラーは接続エラーとして扱い、利用者へ一般的な接続失敗を通知する。

---

## 18.15 HTTPヘッダー

必要に応じて、Sessionへ共通ヘッダーを設定する。

候補例を次に示す。

```python
session.headers.update(
    {
        "Accept": "application/json",
        "User-Agent": (
            "book_manager/"
            f"{application_version}"
        ),
    }
)
```

User-Agentへ次を含めない。

* 利用者名
* PC名
* OSアカウント名
* APIキー
* 個人を特定する情報

---

## 18.16 Content-Type

GETレスポンスがJSONである場合でも、Content-Typeヘッダーだけを根拠に正常判定しない。

最終的には `response.json()` の結果とトップレベル型を検証する。

Content-Typeが明らかにHTMLである場合は、ログ上の補助情報として使用できる。

---

## 18.17 HTTPステータス判定順序

HTTPステータスは次の順序で判定する。

1. HTTP 429
2. API固有の既知エラー
3. その他の400番台
4. 500番台
5. 正常系

概念例を次に示す。

```python
if response.status_code == 429:
    raise BookMetadataRateLimitError(
        "APIの利用制限に達しました。",
        source_name=self.source_name,
    )

try:
    response.raise_for_status()
except requests.HTTPError as exc:
    raise BookMetadataResponseError(
        "外部サービスから正常な応答を"
        "取得できませんでした。",
        source_name=self.source_name,
        status_code=response.status_code,
    ) from exc
```

---

## 18.18 リダイレクト

`requests` の既定のリダイレクト処理を使用する。

異常に多いリダイレクトや不正なリダイレクトは、`requests` の例外を通じて接続または応答エラーへ変換する。

外部APIのベースURLを、レスポンスの指示だけで永続的に変更しない。

---

## 18.19 プロキシ

第1段階では、アプリケーション独自のプロキシ設定画面を実装しない。

`requests` が利用する環境設定やOS環境に従う。

将来プロキシ設定を追加する場合は、ClientごとではなくSession構成として管理する。

---

## 18.20 自動リトライ

第1段階では、自動リトライを行わない。

次の理由による。

* 同期GUIの待機時間が長くなる。
* HTTP 429に対して不適切な再試行を行う可能性がある。
* 外部APIへ不要な負荷を与える。
* エラー再現とテストが複雑になる。
* 利用者による再試行で十分な初期要件である。

将来リトライを導入する場合は、次を明示的に設計する。

* 最大試行回数
* 対象例外
* 対象HTTPステータス
* 待機時間
* 指数バックオフ
* Retry-After
* GUIの応答性
* 操作キャンセル

---

## 18.21 通信処理の共通化

Google BooksとopenBDで共通する通信処理を、過度に重複させない。

共通化候補は次のとおりである。

* GET実行
* timeout設定
* HTTP 429判定
* `raise_for_status()` 処理
* JSON解析
* `requests` 例外変換

ただし、初期段階から複雑な基底Clientクラスを作成しない。

重複が小さい間は、各Clientで明示的に実装してもよい。

重複が増え、共通処理が安定した時点で、補助関数または共通HTTP Clientを検討する。

---

## 18.22 基底Clientクラスを採用しない理由

第1段階では、Google BooksとopenBDの共通基底クラスを必須としない。

理由は次のとおりである。

* レスポンス構造が大きく異なる。
* 対象なしの判定方法が異なる。
* API固有処理が多い。
* 継承関係が実装を複雑にする可能性がある。
* 共通化すべき範囲が実装前には確定していない。

共通契約には `Protocol` を使用し、実装共有は必要になった時点で判断する。

---

## 18.23 通信ログ

通信ログでは、必要に応じて次を記録する。

* 取得元
* HTTPメソッド
* ベースURL
* HTTPステータス
* 処理時間
* timeout種別
* 例外種別
* 問い合わせISBN

次は記録しない。

* APIキー
* Authorizationヘッダー
* Cookie
* セッショントークン
* クエリ全文に含まれる秘密情報
* 不要なレスポンス全文

---

## 18.24 HTTP通信のテスト

HTTP通信テストでは、次を検証する。

* Sessionの `get()` が使用される。
* 正しいURLが指定される。
* `params` が正しく渡される。
* timeoutが必ず指定される。
* HTTP 429が専用例外になる。
* HTTP 500が応答例外になる。
* timeoutが接続例外になる。
* ConnectionErrorが接続例外になる。
* JSON解析失敗が応答例外になる。
* APIキーがRawデータへ含まれない。
* APIキーが例外文へ含まれない。

---

## 18.25 HTTP通信上の禁止事項

次の実装は禁止する。

* timeoutを省略する。
* `verify=False` を指定する。
* APIキーをURL文字列へ直接連結する。
* GUIからHTTP通信を行う。
* ServiceからHTTP通信を行う。
* 自動リトライを暗黙に有効化する。
* 通信例外を対象なしとして扱う。
* Sessionを取得操作ごとに生成する。
* APIキーや認証情報をログへ出力する。
* HTTPエラー本文をそのまま利用者へ表示する。

---

# 19. ログ設計

## 19.1 目的

ログは、外部書誌情報取得機能の障害調査、動作確認および保守を支援するために使用する。

利用者向けメッセージと開発者向けログは分離する。

GUIには簡潔な案内を表示し、技術的な詳細はログへ記録する。

---

## 19.2 使用ライブラリ

ログ出力には、Python標準ライブラリの `logging` を使用する。

各モジュールで次の形式によりLoggerを取得する。

```python
import logging


logger = logging.getLogger(__name__)
```

`print()` を恒常的なログ出力として使用しない。

---

## 19.3 ログレベル

使用する主なログレベルは次のとおりである。

| レベル      | 用途                 |
| :------- | :----------------- |
| DEBUG    | 開発時の詳細情報           |
| INFO     | 正常な主要処理            |
| WARNING  | 部分失敗、利用制限、再試行可能な問題 |
| ERROR    | 取得処理を完了できない異常      |
| CRITICAL | アプリケーション継続が困難な重大障害 |

外部書誌情報取得の通常障害で `CRITICAL` を多用しない。

---

## 19.4 INFOログ

INFOログの候補は次のとおりである。

* 外部取得処理の開始
* 外部取得処理の成功
* 使用した取得元
* 対象書籍なし
* Clientの初期化
* 外部取得機能の有効化または無効化

例を次に示す。

```python
logger.info(
    "書誌情報取得に成功しました。"
    " isbn=%s sources=%s",
    isbn,
    metadata.sources,
)
```

---

## 19.5 DEBUGログ

DEBUGログの候補は次のとおりである。

* Client呼び出し順序
* 正規化済みISBN
* 問い合わせ用ISBN-13
* HTTPステータス
* 候補件数
* ISBN照合結果
* 統合前の取得項目有無
* 統合後の取得項目有無
* 処理時間
* 使用した補完元

Rawレスポンス全文は、DEBUGであっても原則として出力しない。

---

## 19.6 WARNINGログ

WARNINGログの候補は次のとおりである。

* 一部Clientの失敗
* HTTP 429
* 対象なしとエラーの混在
* 未知のレスポンス項目
* ISBN不一致候補
* 未知の出版形態
* 統合時の取得元名重複
* 設定値の一部不足

一部Clientが失敗しても最終結果が成功した場合は、WARNINGとして記録できる。

---

## 19.7 ERRORログ

ERRORログの候補は次のとおりである。

* すべてのClientが失敗
* JSON解析不能
* 想定外のレスポンス構造
* 設定不備により取得機能を使用できない。
* Service内の想定外例外
* GUIへ一般エラーを表示した障害

例外情報を記録する場合は、`logger.exception()` を使用できる。

```python
logger.exception(
    "書誌情報取得中に想定外の"
    "エラーが発生しました。"
)
```

---

## 19.8 ログへ含める情報

必要に応じて次を含める。

* 処理名
* 取得元
* 正規化済みISBN
* HTTPステータス
* 例外クラス
* 処理結果
* 取得項目
* 処理時間
* Client呼び出し順序
* 最終例外の選択結果

ログは、後から検索しやすい形式で統一する。

---

## 19.9 ログへ含めない情報

次をログへ記録しない。

* Google Books APIキー
* Authorizationヘッダー
* Cookie
* セッショントークン
* OSアカウント名
* 利用者の個人的な備考
* 内容紹介全文
* Rawレスポンス全文
* 不要な外部サービス内部情報

ISBNは書籍識別子であり、通常は秘密情報ではないが、ログ量と利用目的を考慮して必要な範囲だけ記録する。

---

## 19.10 APIキーのマスキング

設定確認などでAPIキーの存在をログへ記録する場合は、値そのものを出力しない。

```python
logger.info(
    "Google Books APIキー設定=%s",
    bool(api_key),
)
```

次のような出力は禁止する。

```python
logger.debug(
    "api_key=%s",
    api_key,
)
```

一部だけをマスキングして出力する方式も、第1段階では必要としない。

---

## 19.11 Rawレスポンスの扱い

Rawレスポンスは、`FetchedBookData.raw_data` に一時保持できるが、通常ログへ自動出力しない。

障害調査でRawレスポンスが必要な場合は、開発用の明示的なデバッグ機能として扱う。

本番利用時に常時保存する設計にはしない。

---

## 19.12 例外ログ

例外ログでは、例外チェーンを保持する。

```python
logger.warning(
    "Google Booksからの取得に"
    "失敗しました。 isbn=%s",
    isbn,
    exc_info=True,
)
```

一部成功の場合に、すべての失敗をERRORとして記録するとログが過剰になるため、結果に応じてWARNINGとERRORを使い分ける。

---

## 19.13 部分成功ログ

部分成功の例を次に示す。

```text
Google Books:
BookMetadataConnectionError

openBD:
取得成功
```

この場合、全体結果は成功であるため、次のように扱う。

* Google Books失敗: WARNING
* 外部取得全体: INFO
* GUI: 成功表示

---

## 19.14 対象なしログ

すべてのClientで対象なしの場合は、通常の利用状況としてINFOまたはDEBUGで記録する。

対象なしをERRORにしない。

```python
logger.info(
    "書誌情報が見つかりませんでした。"
    " isbn=%s",
    isbn,
)
```

---

## 19.15 処理時間

外部取得処理の応答性を確認するため、処理時間をログへ記録できる。

```python
from time import perf_counter


started_at = perf_counter()

try:
    ...
finally:
    elapsed = perf_counter() - started_at
    logger.debug(
        "書誌情報取得処理時間"
        " elapsed=%.3f",
        elapsed,
    )
```

時刻計測には、経過時間測定に適した `perf_counter()` を使用する。

---

## 19.16 ログ出力先

第1段階では、プロジェクト全体のログ方針に従う。

候補は次のとおりである。

* コンソール
* アプリケーション用ログファイル
* 開発時のみコンソール
* ローテーション付きログファイル

外部書誌情報取得機能だけで独自のログ保存方式を導入しない。

---

## 19.17 ログファイルのローテーション

ファイルログを採用する場合は、無制限にファイルを増加させない。

候補として、`RotatingFileHandler` または `TimedRotatingFileHandler` を使用する。

保持世代数、最大サイズおよび保存場所は、アプリケーション全体のログ設計で定義する。

---

## 19.18 ログと利用者通知の分離

次の役割を分離する。

```text
GUIメッセージ:
利用者が理解し、次の操作を判断するための情報

ログ:
開発者が原因を分析するための技術情報
```

利用者向けメッセージを詳細ログの代わりにしてはならない。

ログの技術情報をそのままGUIへ表示してはならない。

---

## 19.19 ログのテスト

少なくとも次を確認する。

* APIキーがログへ出力されない。
* 部分成功が全体ERRORにならない。
* 全Client失敗時にERRORログが記録される。
* 対象なしがERRORにならない。
* 取得元とISBNを必要に応じて記録できる。
* 例外チェーンを記録できる。
* Rawレスポンス全文を通常ログへ出力しない。
* 処理時間を記録できる。

---

## 19.20 ログ設計上の禁止事項

次の実装は禁止する。

* `print()` による恒常的な障害記録
* APIキーのログ出力
* Rawレスポンスの常時全文出力
* 内容紹介全文のログ出力
* 対象なしをERRORとして扱う。
* 一部Client失敗を必ず全体ERRORとする。
* GUIメッセージだけで障害情報を完結させる。
* スタックトレースを利用者へ表示する。
* ログファイルを無制限に増加させる。

---

# 20. セキュリティ設計

## 20.1 目的

セキュリティ設計では、APIキー、外部通信、外部データおよびログの安全な取り扱いを定義する。

本機能は個人向けデスクトップアプリケーションであるが、外部サービスと通信するため、認証情報漏えいと不正データの取り込みを防ぐ必要がある。

---

## 20.2 APIキーの管理

Google Books APIキーは、環境変数から取得する。

想定する環境変数名は次のとおりである。

```text
GOOGLE_BOOKS_API_KEY
```

ソースコード内へ直接記述しない。

```python
import os


api_key = os.getenv(
    "GOOGLE_BOOKS_API_KEY"
)
```

---

## 20.3 Git管理対象からの除外

APIキーを含む可能性があるローカル設定ファイルを作成する場合は、`.gitignore` へ追加する。

候補例は次のとおりである。

```text
.env
.env.local
config.local.toml
secrets.toml
```

ただし、第1段階では `.env` ファイルの導入を必須としない。

環境変数を基本方式とする。

---

## 20.4 `.env` の扱い

将来 `.env` を採用する場合は、実値を含むファイルをGitへ登録しない。

代わりに、キー名だけを示すサンプルファイルを登録できる。

```text
GOOGLE_BOOKS_API_KEY=
```

サンプルへ実際のAPIキーを記述しない。

---

## 20.5 APIキーのコード内固定禁止

次の実装は禁止する。

```python
API_KEY = "実際のAPIキー"
```

テストコード、Fixture、ドキュメントおよびコメントにも実値を記述しない。

---

## 20.6 APIキーのURL露出

APIキーは `params` を使用してリクエストへ付加する。

ただし、HTTPクライアントやプロキシログに完全なURLが記録される可能性を考慮する。

アプリケーションログでは、クエリ文字列付きURLを記録しない。

```python
logger.debug(
    "request_url=%s",
    response.url,
)
```

上記は、APIキーが含まれる可能性があるため禁止する。

---

## 20.7 HTTPS通信

すべてのAPI通信でHTTPSを使用する。

証明書検証を無効化しない。

中間者攻撃の危険があるため、HTTPへのフォールバックを行わない。

---

## 20.8 外部データの信頼境界

Google BooksおよびopenBDから取得したデータは、信頼済みデータとして扱わない。

外部データには次の問題が含まれる可能性がある。

* 不正な型
* 想定外の文字列
* 過度に長い文章
* HTMLタグ
* 制御文字
* 欠損値
* 誤った書誌情報
* 外部URL
* 文字コード上の問題

Client境界で型と構造を確認し、GUIへ渡す値を限定する。

---

## 20.9 HTMLの扱い

内容紹介にHTMLが含まれていても、HTMLとして実行しない。

Tkinterのテキストウィジェットへプレーンテキストとして表示する。

将来HTML表示機能を導入する場合は、スクリプト、外部リソースおよびリンク処理を含めて別途設計する。

---

## 20.10 スクリプト実行禁止

外部データ内に、JavaScript、Pythonコードまたはコマンド文字列が含まれていても実行しない。

外部レスポンスを `eval()`、`exec()` またはシェルコマンドへ渡してはならない。

```python
eval(external_value)
exec(external_value)
```

上記は禁止する。

---

## 20.11 SQLインジェクション

外部取得結果を保存する場合も、Repositoryではパラメータ化SQLを使用する。

外部取得データをSQL文字列へ直接連結しない。

```python
cursor.execute(
    """
    INSERT INTO book_items (
        title,
        publisher
    )
    VALUES (?, ?)
    """,
    (
        book.title,
        book.publisher,
    ),
)
```

外部データだから特別に安全であるとは仮定しない。

---

## 20.12 文字列長

外部サービスが極端に長い文字列を返す可能性を考慮する。

第1段階では、既存GUIおよびDBの制約に従う。

必要に応じて、次の項目へ最大長を設定することを検討する。

* 書籍名
* 著者名
* 出版社
* 内容紹介
* 表紙画像URL

ただし、Clientが独自判断で内容を途中切断する場合は、情報欠損が発生するため、Serviceまたは入力検証層で統一する。

---

## 20.13 制御文字

表示や保存に不要な制御文字が含まれる場合は除去を検討する。

ただし、改行、タブなど、内容紹介に必要な文字まで無条件に削除しない。

文字列正規化規則を共通化する。

---

## 20.14 表紙画像URL

表紙画像URLは外部入力として扱う。

第1段階ではURLへアクセスしないため、URL起因の追加リスクは限定される。

将来画像を取得する場合は、次を別途検討する。

* 許可するスキーム
* リダイレクト
* ファイルサイズ上限
* Content-Type
* timeout
* ローカルネットワークへのアクセス防止
* キャッシュ保存場所
* 不正画像ファイル
* 画像処理ライブラリの脆弱性

---

## 20.15 Rawデータ

Rawレスポンスはメモリ上の一時データとして扱う。

第1段階では次を行わない。

* SQLiteへの保存
* ログファイルへの常時保存
* 利用者への表示
* 外部ファイルへの自動書き出し
* クラウドへの送信

RawデータにAPIキーや認証ヘッダーを含めない。

---

## 20.16 ログの安全性

ログへ秘密情報を含めない。

特に次を禁止する。

* APIキー
* Authorizationヘッダー
* Cookie
* セッショントークン
* クエリ文字列付き完全URL
* Rawレスポンス全文
* OSユーザー情報

ログファイルへアクセス権を設定できる環境では、利用者本人だけが読み取れる範囲を推奨する。

---

## 20.17 エラーメッセージ

利用者向けエラーメッセージへ、内部情報を含めない。

表示しない情報は次のとおりである。

* APIキー
* ローカルファイルパス
* Pythonモジュール名
* スタックトレース
* HTTPレスポンス本文
* 内部URLパラメータ
* 環境変数の値

---

## 20.18 環境変数の確認

環境変数が設定されているか確認する場合は、存在だけを判定する。

```python
if api_key:
    logger.info(
        "Google Books APIキーを"
        "使用します。"
    )
```

値の長さ、先頭文字または末尾文字も、必要がなければログへ出力しない。

---

## 20.19 依存ライブラリ

`requests` などの依存ライブラリは、プロジェクトの依存管理ファイルでバージョン範囲を管理する。

既知の脆弱性があるバージョンを長期間使用しない。

依存関係更新は、外部書誌情報取得機能だけでなくプロジェクト全体の保守方針に従う。

---

## 20.20 最小権限

Google Books APIキーに制限を設定できる場合は、必要なAPIおよび利用範囲だけに限定することを推奨する。

不要なGoogle APIへのアクセス権を持つキーを流用しない。

APIキーの発行および制限方法は、運用ドキュメントで管理する。

---

## 20.21 機密情報が漏えいした場合

APIキーがGit履歴、ログ、スクリーンショットまたは共有ファイルへ漏えいした場合は、次を行う。

1. 該当キーを無効化する。
2. 新しいキーを発行する。
3. 新しいキーへ必要な制限を設定する。
4. ローカル環境変数を更新する。
5. 漏えい経路を修正する。
6. 必要に応じてGit履歴や公開物を確認する。

文字列を削除しただけで、漏えい済みキーを継続使用しない。

---

## 20.22 セキュリティテスト

少なくとも次を確認する。

* APIキーがソースコードに存在しない。
* APIキーがログへ出力されない。
* APIキーがRawデータへ含まれない。
* HTTPSを使用する。
* TLS検証を無効化していない。
* 外部HTMLを実行しない。
* 外部文字列を `eval()` しない。
* Repositoryがパラメータ化SQLを使用する。
* 不正なJSON型で異常終了しない。
* 極端な文字列に対してGUIが破損しない。
* 利用者向けエラーに内部情報が含まれない。

---

## 20.23 セキュリティ設計上の禁止事項

次の実装は禁止する。

* APIキーのハードコード
* APIキーをGitへ登録する。
* APIキーをログへ出力する。
* `verify=False` を使用する。
* HTTPへ自動フォールバックする。
* 外部HTMLやスクリプトを実行する。
* 外部文字列を `eval()` または `exec()` へ渡す。
* SQL文字列へ外部データを直接連結する。
* Rawレスポンスを恒常的に保存する。
* 外部URLへ無制限にアクセスする。
* 内部例外情報をそのまま利用者へ表示する。

---

# 21. 設定管理

## 21.1 目的

設定管理では、外部書誌情報取得機能が使用する環境依存値、秘密情報および変更可能な設定値の管理方法を定義する。

設定をコードへ分散させず、アプリケーション起動時に読み込み、各構成要素へ注入する。

---

## 21.2 設定項目

第1段階で想定する設定項目は次のとおりである。

| 設定項目               |      必須     | 管理方法       |
| :----------------- | :---------: | :--------- |
| Google Books APIキー |   運用条件による   | 環境変数       |
| 接続timeout          |      必須     | コード定数      |
| 読み取りtimeout        |      必須     | コード定数      |
| Client優先順位         |      必須     | 起動時の登録順    |
| Google Books使用有無   |     将来対応    | Client登録有無 |
| openBD使用有無         |     将来対応    | Client登録有無 |
| User-Agent         |      任意     | Session構成  |
| ログレベル              | プロジェクト方針による | 既存ログ設定     |

---

## 21.3 環境変数

Google Books APIキーは環境変数から取得する。

```python
GOOGLE_BOOKS_API_KEY
```

読み込み例を次に示す。

```python
import os


google_books_api_key = os.getenv(
    "GOOGLE_BOOKS_API_KEY"
)
```

環境変数の読み込み処理を、Google Books Client内へ直接埋め込まない。

---

## 21.4 環境変数をClient内で読まない理由

Clientが自ら環境変数を読むと、次の問題が発生する。

* テストで値を差し替えにくい。
* 設定の取得場所が分散する。
* Client生成時の依存関係が見えにくい。
* 別の設定方式へ変更しにくい。
* 実行環境に暗黙依存する。

そのため、起動処理で設定値を取得し、コンストラクタへ渡す。

```python
client = GoogleBooksClient(
    session=session,
    api_key=google_books_api_key,
)
```

---

## 21.5 timeout定数

timeoutのDesign Freeze値は、共通定数として管理する。

```python
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 10

DEFAULT_HTTP_TIMEOUT = (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
)
```

各Clientへ同じ数値を重複記述しないことを推奨する。

---

## 21.6 設定モジュール

小規模な第1段階では、設定用モジュールを一つ用意できる。

推奨配置例を次に示す。

```text
src/
└── book_manager/
    └── config.py
```

概念例を次に示す。

```python
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppConfig:
    google_books_api_key: str | None
    http_timeout: tuple[int, int]


def load_config() -> AppConfig:
    return AppConfig(
        google_books_api_key=os.getenv(
            "GOOGLE_BOOKS_API_KEY"
        ),
        http_timeout=(5, 10),
    )
```

プロジェクト全体の設定設計が別に存在する場合は、それへ統合する。

---

## 21.7 `AppConfig`

設定値が増えた場合は、`AppConfig` のような不変データクラスへまとめる。

利点は次のとおりである。

* 必要な設定が一覧化される。
* 型ヒントを付けられる。
* テスト用設定を生成しやすい。
* 依存関係が明確になる。
* 実行途中で設定が変更されにくい。

第1段階で設定数が少ない場合は、過度な設定クラス化を避けてもよい。

---

## 21.8 設定読み込みのタイミング

設定は、原則としてアプリケーション起動時に一度読み込む。

取得ボタンを押すたびに環境変数を読み直さない。

```text
アプリケーション起動
        │
        ▼
設定読み込み
        │
        ▼
SessionとClient生成
        │
        ▼
Service生成
        │
        ▼
GUI生成
```

---

## 21.9 設定値の検証

設定読み込み後、必要な値を検証する。

検証候補は次のとおりである。

* timeoutが正の数値である。
* timeoutが2要素である。
* APIキーが必要な運用で未設定ではない。
* Client一覧が空ではない。
* エンドポイントがHTTPSである。
* Client優先順位に重複がない。

不正な設定は、処理開始後ではなく可能な限り起動時に検出する。

---

## 21.10 APIキー未設定時の方針

Google Books APIキーが未設定の場合の動作は、実装時の利用条件に応じて次のいずれかへ固定する。

### 方針A: キーなし通信を許可する

```text
APIキー未設定
    ↓
Google Booksをキーなしで呼び出す。
```

### 方針B: Google Books Clientを無効化する

```text
APIキー未設定
    ↓
Google Books Clientを登録しない。
    ↓
openBDだけを使用する。
```

### 方針C: 設定エラーとする

```text
APIキー未設定
    ↓
BookMetadataConfigurationError
```

第1段階では、Google Booksの実際の利用条件と取得テストを確認し、いずれかをDesign Freezeする。

キー未設定時の動作をClientごとに暗黙判断させない。

---

## 21.11 Client優先順位

Client優先順位は、Serviceへ渡す順序で表現する。

```python
clients = [
    google_books_client,
    openbd_client,
]
```

設定ファイルへ文字列として優先順位を記述する方式は、第1段階では採用しない。

Client数が増え、利用者または運用環境ごとに順序を変更する必要が生じた場合に検討する。

---

## 21.12 Client有効・無効

第1段階では、Clientの有効・無効を、Serviceへ登録するかどうかで表現する。

```python
clients: list[BookMetadataClient] = []

if use_google_books:
    clients.append(
        GoogleBooksClient(...)
    )

if use_openbd:
    clients.append(
        OpenBdClient(...)
    )
```

設定画面やチェックボックスによる切り替えは、第1段階の対象外とする。

---

## 21.13 エンドポイント設定

外部APIのエンドポイントは、原則として各Clientのクラス定数で管理する。

```python
BASE_URL = (
    "https://api.openbd.jp/v1/get"
)
```

一般利用者が変更する設定とはしない。

テストでは、Session Mockにより通信先を差し替えるため、実エンドポイントを変更する必要はない。

開発用サーバーや互換APIを使用する要件が生じた場合は、コンストラクタ注入を検討する。

---

## 21.14 User-Agent設定

User-Agentを設定する場合は、Session生成時に行う。

```python
session.headers.update(
    {
        "User-Agent": (
            f"book_manager/{version}"
        ),
    }
)
```

バージョン情報の取得方法は、プロジェクト全体のパッケージ設計へ合わせる。

Clientごとに異なるUser-Agentを設定する必要はない。

---

## 21.15 ログレベル設定

外部書誌情報取得機能だけでログレベルを管理しない。

アプリケーション全体のログ設定に従う。

開発時はDEBUG、本番利用時はINFO以上とするなど、運用方針で切り替える。

---

## 21.16 設定ファイルの導入判断

第1段階では、秘密情報以外の設定値が少ないため、専用設定ファイルを必須としない。

設定ファイル導入を検討する条件は次のとおりである。

* Client有効・無効を利用者が変更する。
* Client優先順位を変更する。
* timeoutをGUIから変更する。
* プロキシ設定を追加する。
* キャッシュ設定を追加する。
* 複数環境の設定を切り替える。
* ログ出力先を変更する。

---

## 21.17 設定の既定値

秘密情報以外には、安全で合理的な既定値を用意する。

```python
DEFAULT_HTTP_TIMEOUT = (5, 10)
```

APIキーには既定値を用意しない。

ダミーキーをソースコードへ記述しない。

---

## 21.18 テスト用設定

テストでは、実環境変数へ依存せず、設定値を直接注入する。

```python
client = GoogleBooksClient(
    session=fake_session,
    api_key="test-key",
    timeout=(1, 1),
)
```

テスト用キーは、外部通信へ使用しない無効な固定文字列とする。

実際のAPIキーをテストへ使用しない。

---

## 21.19 設定の表示

将来、設定確認画面を追加する場合でも、APIキーの実値を表示しない。

表示候補は次のとおりである。

```text
Google Books APIキー: 設定済み
Google Books APIキー: 未設定
```

キーの全文または一部を表示しない方針を基本とする。

---

## 21.20 設定エラー時の起動

外部取得機能の設定だけが不正な場合でも、可能であればbook_manager本体を起動する。

例えばGoogle Books APIキーが必須なのに未設定の場合は、次の構成を検討する。

```text
Google Books Client:
無効

openBD Client:
有効

既存CRUD:
利用可能
```

すべての外部Clientを使用できない場合でも、外部取得ボタンを無効化し、既存書籍管理機能は利用可能とする設計が望ましい。

---

## 21.21 設定エラーの通知

設定不備を利用者へ通知する場合は、秘密情報を含めず、必要な対応を示す。

例を次に示す。

```text
Google Books APIの設定が見つかりません。
環境変数を確認してください。
```

通常利用者が設定を変更できない運用では、ログだけへ記録し、外部取得機能を無効化する方式も検討する。

---

## 21.22 設定管理のテスト

少なくとも次を確認する。

* 環境変数からAPIキーを読み込める。
* 未設定時に `None` となる。
* APIキーがClientへ注入される。
* timeoutの既定値が `(5, 10)` である。
* 不正timeoutを検出できる。
* Client登録順が優先順位になる。
* Client一覧が空の場合に検出できる。
* 設定不備でも既存CRUDへ影響しない。
* テストが実環境変数へ依存しない。
* APIキーの実値を画面やログへ出さない。

---

## 21.23 設定管理上の禁止事項

次の実装は禁止する。

* APIキーのハードコード
* Client内で環境変数を直接読む。
* 取得操作ごとに設定を読み直す。
* 各Clientへtimeout値を重複記述する。
* 設定値をグローバル変数として自由に変更する。
* APIキーの実値を設定画面へ表示する。
* 実APIキーをテストへ使用する。
* 設定不備だけで既存CRUD機能を停止する。
* エンドポイントを利用者入力へ無条件に委ねる。
* 秘密情報をGit管理対象へ保存する。

---
# 22. テスト設計

## 22.1 目的

テストでは、外部サービスの提供状況に依存せず、外部書誌情報取得機能の正常系、異常系および境界条件を再現可能な形で検証する。

自動テストから実際のGoogle Books APIおよびopenBD APIへ接続しない。

外部通信、レスポンス、例外および取得結果は、Fake、MockまたはFixtureを使用して再現する。

---

## 22.2 テスト方針

本機能のテスト方針は次のとおりである。

* 層ごとに責務を分離してテストする。
* 外部APIへの実通信を行わない。
* 正常系だけでなく異常系を重視する。
* APIレスポンスの項目欠損を再現する。
* Clientの優先順位と統合規則を固定する。
* GUIテストではServiceをFakeへ差し替える。
* RepositoryおよびSQLiteを外部取得テストへ持ち込まない。
* 外部APIの一時的な状態によってテスト結果が変化しないようにする。
* Fixtureは必要最小限のデータとする。
* APIキーや秘密情報をFixtureへ含めない。

---

## 22.3 テスト対象

主なテスト対象は次のとおりである。

| 対象                  | 主な検証内容                |
| :------------------ | :-------------------- |
| ISBN正規化             | 空白、ハイフン、小文字xの処理       |
| ISBN検証              | 桁数、文字種、チェックデジット       |
| ISBN変換              | ISBN-10からISBN-13への変換  |
| GoogleBooksClient   | 通信、候補選択、レスポンス変換       |
| OpenBdClient        | 対象なし判定、summary・ONIX解析 |
| BookMetadataService | Client制御、部分成功、統合、最終例外 |
| FetchedBookData     | 既定値、型、データ保持           |
| GUI連携               | 確認、ボタン状態、フォーム反映、通知    |
| 設定管理                | 環境変数、timeout、Client登録 |
| ログ                  | 秘密情報非出力、エラーレベル        |

---

## 22.4 テストの種類

第1段階では、次のテストを実施する。

### 単体テスト

一つの関数またはクラスを、外部依存から切り離して検証する。

対象例は次のとおりである。

* ISBN関数
* Clientのレスポンス変換
* Serviceの統合
* 例外選択
* GUI反映用補助メソッド

### 結合テスト

複数の内部構成要素を組み合わせて検証する。

対象例は次のとおりである。

* Fake SessionとClient
* Fake ClientとService
* Fake ServiceとGUI
* 設定読み込みとClient生成

### 手動確認

実際のAPIおよびGUI操作が必要な項目を確認する。

対象例は次のとおりである。

* 実APIからの取得
* 実際のレスポンス傾向
* GUI応答性
* ダイアログ文言
* 外部サービス障害時の操作感

---

## 22.5 自動テストで実APIを使用しない理由

自動テストから実APIを呼び出すと、次の問題が発生する。

* ネットワーク環境によって失敗する。
* API停止によって失敗する。
* レスポンス内容が変化する。
* API仕様変更によって突然失敗する。
* 利用制限へ到達する。
* APIキーが必要になる。
* テスト速度が低下する。
* 同じ条件を再現できない。
* CI環境で外部接続できない可能性がある。

そのため、通常の自動テストでは実通信を禁止する。

---

## 22.6 テストディレクトリ構成

推奨構成例を次に示す。

```text id="ooz7mb"
tests/
├── unit/
│   ├── isbn/
│   │   ├── test_normalizer.py
│   │   ├── test_validator.py
│   │   └── test_converter.py
│   ├── metadata/
│   │   ├── test_google_books_client.py
│   │   ├── test_openbd_client.py
│   │   ├── test_metadata_service.py
│   │   └── test_fetched_book_data.py
│   └── gui/
│       └── test_metadata_integration.py
├── integration/
│   └── test_metadata_workflow.py
└── fixtures/
    └── metadata/
        ├── google_books/
        └── openbd/
```

既存のテスト構成がある場合は、それに合わせる。

---

## 22.7 Fake Session

Clientテストでは、`requests.Session` と同じ必要最小限の振る舞いを持つFake Sessionを使用できる。

概念例を次に示す。

```python id="n5du4y"
class FakeSession:
    def __init__(
        self,
        response: FakeResponse,
    ) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, object],
        timeout: tuple[int, int],
    ) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )
        return self._response
```

Fake Sessionでは、URL、パラメータおよびtimeoutが正しく渡されたか確認する。

---

## 22.8 Fake Response

HTTPレスポンスを再現するFake Responseの概念例を次に示す。

```python id="5mt9fj"
class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: object = None,
        json_error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self) -> object:
        if self._json_error is not None:
            raise self._json_error

        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}"
            )
```

実装ではMockライブラリを使用してもよい。

---

## 22.9 MockとFakeの使い分け

Fakeは、単純で再利用可能な振る舞いを定義する場合に使用する。

Mockは、次のような呼び出し検証を行う場合に使用する。

* メソッドが呼ばれたか
* 呼び出し回数
* 引数
* 呼び出し順序
* 例外送出

テストがMockの内部設定に過度に依存しないようにする。

---

## 22.10 Fixture JSON

APIレスポンスの例は、JSON Fixtureとして保存する。

Fixtureは、対象となる条件を明確に表す名前とする。

Google Booksの例を次に示す。

```text id="em3lt9"
full_metadata.json
missing_authors.json
missing_description.json
multiple_items.json
first_item_isbn_mismatch.json
not_found.json
invalid_top_level.json
```

openBDの例を次に示す。

```text id="stptlq"
summary_full.json
summary_missing_author.json
null_item.json
empty_array.json
onix_description.json
invalid_top_level.json
```

---

## 22.11 Fixtureの最小化

Fixtureには、テストに必要な項目だけを含める。

実レスポンス全体をそのまま保存すると、次の問題が生じる。

* ファイルが大きくなる。
* テスト意図が分かりにくくなる。
* 不要な仕様変更の影響を受ける。
* 秘密情報や不要データが混入する可能性がある。
* レビューが困難になる。

Fixtureは一つのテスト条件を明確に表す最小構成とする。

---

## 22.12 ISBN正規化テスト

少なくとも次を検証する。

```text id="pwsrzh"
入力:
978-4-16-391773-3

期待値:
9784163917733
```

```text id="nw4h8g"
入力:
  4101109184

期待値:
4101109184
```

```text id="9l63nb"
入力:
097522980x

期待値:
097522980X
```

半角空白、全角空白および許容するハイフン文字を個別に検証する。

---

## 22.13 ISBN-10検証テスト

少なくとも次を検証する。

* 有効な数字末尾ISBN-10
* 有効な末尾X
* 小文字xを正規化した後の有効性
* 9桁
* 11桁
* 途中に英字
* 末尾以外のX
* 不正チェックデジット
* 空文字列

---

## 22.14 ISBN-13検証テスト

少なくとも次を検証する。

* 有効な978 ISBN
* 有効な979 ISBN
* 12桁
* 14桁
* 英字を含む
* 不正チェックデジット
* 不正接頭辞
* 空文字列

---

## 22.15 ISBN変換テスト

ISBN-10からISBN-13への変換では、既知の対応を固定値で検証する。

例を次に示す。

```text id="yucnkg"
ISBN-10:
4101109184

ISBN-13:
9784101109180
```

変換後のISBN-13が、ISBN-13検証にも合格することを確認する。

---

## 22.16 Google Books Client正常系

少なくとも次を検証する。

* 書籍名を取得できる。
* 複数著者を全角読点で結合する。
* 出版社を取得できる。
* 出版日を文字列として保持する。
* 内容紹介を取得できる。
* 表紙画像URLを取得できる。
* `sources` にGoogle Booksが設定される。
* Rawデータが取得元別に保持される。
* timeoutが `(5, 10)` で渡される。
* APIキーが `params` に含まれる。

---

## 22.17 Google Books Client候補選択

少なくとも次を検証する。

* 先頭候補のISBNが不一致でも、後続の一致候補を採用する。
* ISBN-13完全一致を採用する。
* ISBN-10を変換すると一致する候補を採用する。
* ISBN一致候補がなければ `None` を返す。
* タイトルが同じでもISBN不一致なら採用しない。
* `industryIdentifiers` が欠落している候補を無条件に採用しない。

---

## 22.18 Google Books Client欠損項目

少なくとも次を検証する。

* `authors` がない場合に `None`
* `publisher` がない場合に `None`
* `publishedDate` がない場合に `None`
* `description` がない場合に `None`
* `imageLinks` がない場合に `None`
* `title` 以外が欠落しても取得成功
* 一部の値が空文字列の場合に `None`

個別項目欠損で `BookMetadataResponseError` を送出しない。

---

## 22.19 Google Books Client異常系

少なくとも次を検証する。

* HTTP 429
* HTTP 403
* HTTP 404
* HTTP 500
* 接続timeout
* 読み取りtimeout
* ConnectionError
* JSON解析失敗
* トップレベルが配列
* `items` が辞書
* APIエラーオブジェクト

---

## 22.20 openBD Client正常系

少なくとも次を検証する。

* `summary.title` を取得できる。
* `summary.author` を取得できる。
* `summary.publisher` を取得できる。
* `summary.pubdate` を文字列として保持する。
* `summary.cover` を取得できる。
* 内容紹介候補を取得できる。
* `sources` にopenBDが設定される。
* Rawデータが取得元別に保持される。
* ISBNパラメータが正しく渡される。
* timeoutが指定される。

---

## 22.21 openBD Client対象なし

少なくとも次を検証する。

* `[null]` で `None`
* 空配列で `None`
* ISBN一致要素なしで `None`
* 有効な書誌項目なしで `None`
* HTTP 200の対象なしを例外にしない。

---

## 22.22 openBD Client欠損項目

少なくとも次を検証する。

* `summary` がない。
* 著者がない。
* 出版社がない。
* 出版日がない。
* 表紙画像URLがない。
* 内容紹介がない。
* `onix` がない。
* `hanmoto` がない。

欠損項目があっても、取得できた項目を返す。

---

## 22.23 openBD Client異常系

少なくとも次を検証する。

* HTTP 429
* HTTP 404
* HTTP 500
* timeout
* ConnectionError
* JSON解析失敗
* トップレベルが辞書
* 配列内が文字列
* 想定外の構造
* ISBN形式不正なレスポンス

---

## 22.24 Fake Client

Serviceテストでは、HTTP通信を再現せず、`BookMetadataClient` Protocolへ適合するFake Clientを使用する。

概念例を次に示す。

```python id="oc4t3e"
class FakeBookMetadataClient:
    def __init__(
        self,
        source_name: str,
        *,
        result: FetchedBookData | None = None,
        error: BookMetadataError | None = None,
    ) -> None:
        self._source_name = source_name
        self._result = result
        self._error = error
        self.called_with: list[str] = []

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        self.called_with.append(isbn)

        if self._error is not None:
            raise self._error

        return self._result
```

---

## 22.25 Service正常系テスト

少なくとも次を検証する。

* ISBN-13が全Clientへ渡される。
* ISBN-10がISBN-13へ変換される。
* Clientが登録順に呼ばれる。
* Google Booksの値が優先される。
* openBDが空欄だけを補完する。
* 統合結果のISBNが入力ISBNになる。
* `sources` が順序を維持する。
* Rawデータが結合される。
* 一部項目だけでも成功する。

---

## 22.26 Service部分成功テスト

少なくとも次を検証する。

```text id="15frza"
Google Books:
接続エラー

openBD:
取得成功

期待結果:
openBDの取得結果を返す。
```

```text id="ytarbt"
Google Books:
取得成功

openBD:
利用制限

期待結果:
Google Booksの取得結果を返す。
```

```text id="wl3uwi"
Google Books:
対象なし

openBD:
取得成功

期待結果:
openBDの取得結果を返す。
```

---

## 22.27 Service失敗テスト

少なくとも次を検証する。

* 全Clientが対象なしの場合にNotFound
* 対象なしと接続失敗の混在で接続例外
* 全Clientが接続失敗
* 利用制限と接続失敗の混在で利用制限
* 応答エラーだけの場合に応答例外
* Client未登録時の設定エラーまたは `ValueError`
* すべての結果が空欄の場合に成功しない。
* 想定外例外を無条件に握りつぶさない。

---

## 22.28 統合テスト

統合処理では、各項目について次を確認する。

| 先順位  | 後順位  | 期待値  |
| :--- | :--- | :--- |
| 値あり  | 値あり  | 先順位  |
| 値あり  | None | 先順位  |
| None | 値あり  | 後順位  |
| 空文字列 | 値あり  | 後順位  |
| 空白のみ | 値あり  | 後順位  |
| None | None | None |

書籍名、著者名、出版社、出版日、出版形態、内容紹介および表紙画像URLで同様に検証する。

---

## 22.29 取得元統合テスト

少なくとも次を検証する。

* 一つの取得元
* 二つの取得元
* 同一取得元の重複除去
* 優先順位の維持
* 空の `sources`
* Client結果順と取得元順の一致

---

## 22.30 Rawデータ統合テスト

少なくとも次を検証する。

* Google BooksとopenBDのRawデータが共存する。
* 取得元名をキーとして保持する。
* APIキーを含まない。
* 元のFixtureを予期せず書き換えない。
* 同じ取得元名が重複した場合の動作が固定される。

---

## 22.31 GUIテスト方針

GUIテストでは、実Clientおよび実HTTP通信を使用しない。

`BookMetadataService` のFakeをGUIへ注入する。

GUIの主な検証対象は次のとおりである。

* 利用者入力の取得
* 上書き確認
* Service呼び出し
* フォーム反映
* ボタン状態
* ダイアログ
* ステータス表示
* 非対象項目の維持
* 自動保存されないこと

---

## 22.32 GUI上書き確認テスト

少なくとも次を検証する。

* 対象欄がすべて空なら確認しない。
* 書籍名だけ入力済みなら確認する。
* 著者名だけ入力済みなら確認する。
* 内容紹介だけ入力済みなら確認する。
* 空白だけなら入力済みとみなさない。
* 利用者が拒否した場合にServiceを呼ばない。
* 利用者が承認した場合にServiceを呼ぶ。

---

## 22.33 GUI反映テスト

少なくとも次を検証する。

* 取得した書籍名を反映する。
* 取得した著者名を反映する。
* 取得した出版社を反映する。
* 許容された出版形態だけを反映する。
* 内容紹介を反映する。
* `None` の項目で既存値を消さない。
* 雑誌コードを変更しない。
* 読了年月を変更しない。
* 備考を変更しない。
* 取得結果を自動保存しない。

---

## 22.34 GUIボタン状態テスト

少なくとも次を検証する。

* 取得開始時にボタンが無効になる。
* 成功後に有効へ戻る。
* 入力エラー後に有効へ戻る。
* 対象なし後に有効へ戻る。
* 通信エラー後に有効へ戻る。
* 想定外例外後にも有効へ戻る。
* 二重実行されない。

---

## 22.35 GUI通知テスト

少なくとも次を検証する。

* 成功時はステータス表示
* 対象なしは情報ダイアログ
* ISBN不正は警告
* 利用制限は警告
* 接続失敗はエラー
* 応答不正はエラー
* 想定外例外は一般エラー
* 内部例外文をそのまま表示しない。
* APIキーを表示しない。

---

## 22.36 設定テスト

少なくとも次を検証する。

* 環境変数設定時にAPIキーを取得する。
* 未設定時に `None`
* timeoutの既定値
* Client登録順
* Client未登録
* APIキー未設定時のDesign Freeze動作
* テストが実環境変数に依存しない。
* 設定値をClientへ正しく注入する。

環境変数テストでは、pytestの `monkeypatch` などを使用する。

---

## 22.37 ログテスト

ログテストでは、pytestの `caplog` などを利用できる。

少なくとも次を検証する。

* APIキーがログに含まれない。
* 対象なしがERRORではない。
* 部分成功が全体ERRORではない。
* 全失敗時にERRORが記録される。
* 取得元が必要に応じて記録される。
* ISBNが想定形式で記録される。
* Rawレスポンス全文が記録されない。
* 例外チェーンを記録できる。

---

## 22.38 テストデータの独立性

各テストは、他のテストの実行結果に依存しない。

次の状態を共有しない。

* 前回のClient結果
* グローバルMock
* 変更されたFixture辞書
* 環境変数
* Session呼び出し履歴
* GUIウィジェット状態

必要な状態は、各テストまたはFixtureで毎回作成する。

---

## 22.39 パラメータ化テスト

同じ規則を複数入力で検証する場合は、pytestのパラメータ化を使用する。

例を次に示す。

```python id="qppodf"
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "978-4-16-391773-3",
            "9784163917733",
        ),
        (
            " 4101109184 ",
            "4101109184",
        ),
        (
            "097522980x",
            "097522980X",
        ),
    ],
)
def test_normalize_isbn(
    raw: str,
    expected: str,
) -> None:
    assert normalize_isbn(raw) == expected
```

---

## 22.40 カバレッジ

数値上のカバレッジだけを目的としない。

特に次の分岐を必ずテストする。

* Client成功
* Client対象なし
* Client接続失敗
* Client利用制限
* Client応答不正
* Service部分成功
* Service全失敗
* 統合の空欄補完
* GUIのキャンセル
* GUIの `finally`
* APIキー非出力

---

## 22.41 実API手動テスト

実APIを使用するテストは、自動テストとは分離する。

手動確認時は、少なくとも次を記録する。

* 実施日
* ISBN
* 取得元
* 取得項目
* 欠損項目
* 応答時間
* 発生したエラー
* API仕様上の気付き

実APIテスト結果は、API仕様が変化する可能性を考慮して参考情報として扱う。

---

## 22.42 回帰テスト

APIレスポンス解析の不具合を修正した場合は、その不具合を再現するFixtureとテストを追加する。

例を次に示す。

```text id="68sywm"
不具合:
著者名が文字列の場合に1文字ずつ結合された。

対応:
著者名が配列か確認するテストを追加する。
```

修正だけで終わらせず、同じ不具合の再発を防ぐ。

---

## 22.43 テスト設計上の禁止事項

次のテストは禁止する。

* 通常の自動テストから実APIへ接続する。
* 実APIキーをテストへ記述する。
* テスト順序へ依存する。
* Fixtureをテスト内で共有変更する。
* HTTPエラーを対象なしとして期待する。
* 外部APIの現在のレスポンス値を固定的に期待する。
* GUIテストで実通信を行う。
* RepositoryテストとHTTPテストを不必要に混在させる。
* カバレッジ数値だけを目的とする。
* 例外が起きないことだけを検証し、結果内容を確認しない。

---

# 23. 手動確認項目

## 23.1 目的

手動確認では、自動テストだけでは判断しにくいGUI操作、実API連携、表示内容および利用者体験を確認する。

手動確認は、自動テストの代替ではなく補完として実施する。

---

## 23.2 実施前提

手動確認前に、次を満たす。

* 自動テストがすべて成功している。
* APIキーが必要な場合は環境変数へ設定されている。
* テスト用ではない通常のデータベースをバックアップしている。
* 外部取得結果が自動保存されないことを理解している。
* ログ出力先を確認している。
* ネットワークへ接続できる。

---

## 23.3 起動確認

次を確認する。

* アプリケーションが正常に起動する。
* 外部取得機能の追加によって既存画面が崩れていない。
* 取得ボタンがISBN欄の近くに表示される。
* APIキー未設定時の動作が設計どおりである。
* 外部取得機能が利用できなくても既存CRUDが動作する。
* 起動時に秘密情報が画面やログへ表示されない。

---

## 23.4 ISBN未入力

手順は次のとおりである。

1. ISBN欄を空にする。
2. 取得ボタンを押す。

確認内容は次のとおりである。

* 外部通信が行われない。
* ISBN入力を促す警告が表示される。
* 取得ボタンが有効状態のままである。
* 他の入力欄が変更されない。

---

## 23.5 有効なISBN-13

手順は次のとおりである。

1. 有効なISBN-13を入力する。
2. 取得ボタンを押す。
3. 取得結果を確認する。

確認内容は次のとおりである。

* 書籍名が取得される。
* 取得可能な著者名が表示される。
* 取得可能な出版社が表示される。
* 内容紹介が取得できる場合は表示される。
* 成功内容がステータスバーへ表示される。
* 自動保存されない。
* 取得後もフォームを編集できる。

---

## 23.6 ハイフン付きISBN-13

手順は次のとおりである。

1. ハイフン付きISBN-13を入力する。
2. 取得ボタンを押す。

確認内容は次のとおりである。

* 正しく正規化される。
* 書誌情報を取得できる。
* ISBN欄の表示が無断で変更されない。
* 保存時の既存仕様と矛盾しない。

---

## 23.7 有効なISBN-10

手順は次のとおりである。

1. 有効なISBN-10を入力する。
2. 取得ボタンを押す。

確認内容は次のとおりである。

* 問い合わせ時にISBN-13へ変換される。
* 書誌情報を取得できる。
* ISBN欄は利用者入力のISBN-10を維持する。
* 取得結果のISBNによって自動上書きされない。

---

## 23.8 不正なISBN

次の入力を確認する。

* 桁数不足
* 桁数超過
* 不正文字
* 不正チェックデジット
* 途中のX
* ISBN以外の数字列

確認内容は次のとおりである。

* 外部通信が行われない。
* 分かりやすい警告が表示される。
* アプリケーションが異常終了しない。
* 入力済みフォームが変更されない。
* 取得ボタンが有効状態へ戻る。

---

## 23.9 上書き確認

手順は次のとおりである。

1. 書籍名などを手入力する。
2. ISBNを入力する。
3. 取得ボタンを押す。

確認内容は次のとおりである。

* 上書き確認が表示される。
* 「いいえ」で通信しない。
* 「いいえ」で入力内容が維持される。
* 「はい」で取得処理が開始される。
* 確認対象外項目は変更されない。

---

## 23.10 空欄補完

Google Booksで一部項目が欠落し、openBDで補完できるISBNを用意して確認する。

確認内容は次のとおりである。

* Google Booksで取得できた値が維持される。
* Google Booksの空欄だけがopenBDで補完される。
* 後順位の値で先順位の値が上書きされない。
* 成功表示に取得元が正しく表示される。

---

## 23.11 既存値の保持

取得元から特定項目を取得できないISBNを使用する。

確認内容は次のとおりである。

* 取得できない項目の既存入力値が消えない。
* `None` が空文字列として反映されない。
* 内容紹介が取得できない場合でも既存内容を維持する。
* 出版形態が不明な場合でも現在の選択を維持する。

---

## 23.12 非対象項目

取得前に次の項目を入力する。

* 雑誌コード
* 読了年月
* 備考

取得後に値が変化していないことを確認する。

---

## 23.13 対象書籍なし

外部サービスに登録されていない有効形式のISBNを使用する。

確認内容は次のとおりである。

* 対象なしメッセージが表示される。
* 重大エラーとして表示されない。
* 既存入力値が変更されない。
* 取得ボタンが有効へ戻る。
* 既存CRUD操作を継続できる。

---

## 23.14 ネットワーク切断

ネットワークを切断した状態で取得する。

確認内容は次のとおりである。

* 接続エラーが表示される。
* 長時間無制限に待機しない。
* アプリケーションが異常終了しない。
* 取得ボタンが有効へ戻る。
* 既存データの閲覧や編集を継続できる。

---

## 23.15 timeout

可能であれば、テスト用Fakeまたは開発用設定によりtimeoutを再現する。

確認内容は次のとおりである。

* timeoutが接続エラーとして扱われる。
* 利用者向けに技術的すぎない文言が表示される。
* ボタン状態が復旧する。
* スタックトレースが画面へ表示されない。

---

## 23.16 利用制限

HTTP 429をFake Clientまたは開発用Mockで再現する。

確認内容は次のとおりである。

* 利用制限専用メッセージが表示される。
* 対象なしとして表示されない。
* 自動再試行しない。
* ボタン状態が復旧する。

---

## 23.17 一部Client失敗

次の状態をFake Clientで再現する。

```text id="1f3ysx"
Google Books:
接続失敗

openBD:
取得成功
```

確認内容は次のとおりである。

* 取得処理全体は成功する。
* openBDの値がフォームへ反映される。
* 不要なエラーダイアログが表示されない。
* ログには部分失敗が記録される。
* ステータスバーには成功が表示される。

---

## 23.18 全Client失敗

すべてのClientが失敗する状態をFake Clientで再現する。

確認内容は次のとおりである。

* 適切な最終エラーが表示される。
* 例外優先順位が設計どおりである。
* フォームが変更されない。
* ボタンが有効へ戻る。
* 既存CRUDが利用できる。

---

## 23.19 連続取得

異なるISBNで連続して取得する。

確認内容は次のとおりである。

* 前回の検索結果が混入しない。
* 前回の取得元が残らない。
* 前回のエラー状態が残らない。
* ボタン状態が正常である。
* Sessionが再利用されても結果が混在しない。

---

## 23.20 二重操作

取得処理中に取得ボタンを再度押そうとする。

確認内容は次のとおりである。

* ボタンが無効になっている。
* 同じ処理が二重実行されない。
* ダイアログが重複しない。
* 結果反映が二重に行われない。

---

## 23.21 GUI応答性

同期処理であることを踏まえ、次を確認する。

* 通常通信時の待機が許容範囲である。
* 接続失敗時の待機が過度に長くない。
* Google BooksとopenBDの両方がtimeoutした場合の操作感
* 待機中であることを利用者が認識できる。
* GUIが完全に操作不能に見えない。

操作性に問題がある場合は、将来の非同期化を検討する。

---

## 23.22 長い内容紹介

長い内容紹介を返すFixtureまたは実ISBNで確認する。

確認内容は次のとおりである。

* GUIが崩れない。
* スクロールできる。
* 文字列が途中で不自然に欠落しない。
* 保存時の既存制約に適合する。
* ログへ全文が出力されない。

---

## 23.23 特殊文字

次を含む書誌情報を確認する。

* 絵文字
* アクセント記号
* 異体字
* 全角記号
* 改行
* HTMLタグ
* アンパサンド
* 引用符

確認内容は次のとおりである。

* 文字化けしない。
* HTMLが実行されない。
* GUI表示が破損しない。
* SQLite保存時にSQLエラーにならない。

---

## 23.24 APIキー未設定

Design Freezeした方針に応じて確認する。

### キーなし通信を許可する場合

* Google Booksへキーなしで問い合わせる。
* 失敗時に適切なエラーとなる。
* openBDへフォールバックできる。

### Google Booksを無効化する場合

* openBDだけで取得する。
* 既存CRUDが利用できる。
* 必要に応じて設定不足をログへ記録する。

### 設定エラーとする場合

* 利用者へ設定不足を通知する。
* APIキーの実値を表示しない。
* 既存CRUDは利用できる。

---

## 23.25 APIキーの安全確認

次を確認する。

* 画面へAPIキーが表示されない。
* ログへAPIキーが出力されない。
* エラーダイアログへAPIキーが表示されない。
* RawデータにAPIキーが含まれない。
* Git差分にAPIキーが含まれない。
* FixtureにAPIキーが含まれない。

---

## 23.26 保存操作

取得後に利用者が登録する。

確認内容は次のとおりである。

* 既存の登録処理を使用する。
* 重複確認が既存どおり動作する。
* 取得対象外項目もフォーム値から保存される。
* 外部取得時点では保存されていない。
* 保存後のデータを再表示できる。
* Rawデータや取得元がDBへ保存されない。
* 出版日や表紙画像URLがDBへ追加されていない。

---

## 23.27 更新操作

既存書籍を表示し、外部情報を取得してから更新する。

確認内容は次のとおりである。

* 上書き確認が表示される。
* 利用者が内容を確認できる。
* 更新ボタンを押すまでDBへ反映されない。
* 備考や読了年月が維持される。
* キャンセルすればDBが変更されない。

---

## 23.28 ログ確認

各主要ケースでログを確認する。

* 正常取得
* 対象なし
* 部分成功
* 全Client失敗
* timeout
* HTTP 429
* 想定外例外

秘密情報、Rawレスポンス全文および内容紹介全文が出力されていないことを確認する。

---

## 23.29 macOS確認

本アプリケーションをmacOSで利用する場合は、次も確認する。

* Tkinterのダイアログ表示
* ボタン無効化
* フォーカス移動
* 環境変数の反映方法
* 証明書エラーの有無
* 日本語入力
* 長文テキスト表示
* アプリケーション終了時のSession解放

---

## 23.30 Windows確認

Windowsで利用する場合は、次も確認する。

* 環境変数の反映
* プロキシ環境での動作
* 証明書検証
* ログファイルの保存先
* 日本語パス
* 高DPI表示
* ダイアログの改行
* アプリケーション終了時のリソース解放

---

## 23.31 手動確認記録

手動確認結果は、必要に応じて次の形式で記録する。

| 項目   | 内容                  |
| :--- | :------------------ |
| 確認日  | YYYY-MM-DD          |
| 確認環境 | OS、Python、アプリ版      |
| ISBN | 確認に使用したISBN         |
| 取得元  | Google Books、openBD |
| 結果   | 成功、失敗、部分成功          |
| 確認者  | 確認者名またはGitHub名      |
| 備考   | 取得項目、問題、判断          |

---

## 23.32 完了条件

手動確認は、少なくとも次を満たした場合に完了とする。

* 有効なISBN-10とISBN-13で取得できる。
* 不正ISBNを拒否できる。
* Google BooksとopenBDの補完が動作する。
* 一部障害で取得を継続できる。
* 全障害時に異常終了しない。
* 既存値を誤って消去しない。
* 自動保存されない。
* 既存CRUDへ影響しない。
* APIキーが漏えいしない。
* GUI文言が理解可能である。

---

# 24. 受入れ基準

## 24.1 目的

受入れ基準は、外部書誌情報取得機能の第1段階を完了と判断するための条件を定義する。

すべての外部書誌情報を完全に取得できることではなく、設計した範囲で安全かつ予測可能に動作することを完了条件とする。

---

## 24.2 機能受入れ基準

### AC-001 ISBN入力

利用者がISBN-10またはISBN-13を入力し、取得操作を開始できる。

### AC-002 ISBN正規化

ハイフンおよび空白を含むISBNを正規化できる。

### AC-003 ISBN検証

不正な形式またはチェックデジットを持つISBNを、外部通信前に拒否できる。

### AC-004 ISBN-10変換

有効なISBN-10を、問い合わせ用ISBN-13へ正しく変換できる。

### AC-005 Google Books取得

Google Booksから、取得可能な書誌情報を `FetchedBookData` へ変換できる。

### AC-006 openBD取得

openBDから、取得可能な書誌情報を `FetchedBookData` へ変換できる。

### AC-007 優先順位

Google Booksを第1取得元、openBDを第2取得元として処理できる。

### AC-008 空欄補完

openBDの値は、Google Booksで取得できなかった項目だけを補完する。

### AC-009 部分成功

一つのClientが失敗しても、別のClientから有効結果を取得できれば成功として扱う。

### AC-010 対象なし

すべてのClientで対象書籍が見つからない場合、対象なしとして通知できる。

### AC-011 取得結果反映

取得結果をGUIの対象入力欄へ反映できる。

### AC-012 既存値保持

取得値がない項目で、GUIの既存入力値を消去しない。

### AC-013 非対象項目保持

雑誌コード、読了年月および備考を変更しない。

### AC-014 上書き確認

対象入力欄に値がある場合、通信開始前に上書き確認を行う。

### AC-015 取得キャンセル

利用者が上書きを拒否した場合、外部通信を行わない。

### AC-016 自動保存禁止

外部情報取得後も、利用者が登録または更新操作を行うまでDBへ保存しない。

### AC-017 ボタン制御

取得中は取得ボタンを無効化し、処理終了後に有効へ戻す。

### AC-018 エラー通知

入力不正、対象なし、利用制限、接続失敗および応答不正を区別して通知できる。

---

## 24.3 データ受入れ基準

### AC-019 共通モデル

各ClientはAPI固有JSONではなく、`FetchedBookData` を返す。

### AC-020 `BookItem` との分離

外部取得結果に既存の `BookItem` を直接流用しない。

### AC-021 ISBN保持

統合結果のISBNは、正規化済みの利用者入力値を保持する。

### AC-022 取得元保持

有効な結果を提供した取得元を `sources` に保持する。

### AC-023 Rawデータ

Rawレスポンスを一時的に保持できるが、SQLiteへ保存しない。

### AC-024 出版日

出版日は文字列として取得可能であるが、第1段階ではDBへ保存しない。

### AC-025 表紙画像URL

表紙画像URLを取得可能であるが、第1段階では表示および保存を行わない。

---

## 24.4 アーキテクチャ受入れ基準

### AC-026 GUIとHTTPの分離

GUI内にHTTP通信処理が存在しない。

### AC-027 ServiceとHTTPの分離

`BookMetadataService` 内に `requests` を使用した通信処理が存在しない。

### AC-028 ClientとDBの分離

Client内にRepositoryまたはSQLite処理が存在しない。

### AC-029 ServiceとDBの分離

`BookMetadataService` はRepositoryを呼び出さない。

### AC-030 Protocol

Serviceは具象Clientではなく `BookMetadataClient` Protocolに依存する。

### AC-031 Client注入

Client一覧をServiceの外部から注入できる。

### AC-032 Session注入

`requests.Session` をClientの外部から注入できる。

### AC-033 既存CRUD分離

外部取得機能が利用できない場合でも、既存CRUD機能を利用できる。

---

## 24.5 HTTP受入れ基準

### AC-034 timeout

すべての外部HTTP通信で `(5, 10)` のtimeoutを指定する。

### AC-035 HTTPS

Google BooksおよびopenBDへHTTPSで接続する。

### AC-036 TLS検証

TLS証明書検証を無効化しない。

### AC-037 HTTP 429

HTTP 429を専用例外として扱う。

### AC-038 接続例外

timeoutおよび接続失敗を、アプリケーション接続例外へ変換する。

### AC-039 JSON不正

JSON解析失敗を応答例外へ変換する。

### AC-040 対象なしとの区別

接続失敗または応答異常を対象なしとして扱わない。

---

## 24.6 セキュリティ受入れ基準

### AC-041 APIキー管理

Google Books APIキーを環境変数から取得する。

### AC-042 ハードコード禁止

実APIキーがソースコード、テスト、Fixtureおよびドキュメントに存在しない。

### AC-043 ログ非出力

APIキーがログへ出力されない。

### AC-044 Rawデータ非混入

APIキーがRawデータへ含まれない。

### AC-045 GUI非表示

APIキー、スタックトレースおよびレスポンス全文をGUIへ表示しない。

### AC-046 外部HTML

外部サービスから取得したHTMLまたはスクリプトを実行しない。

### AC-047 SQL安全性

外部取得結果の保存時も、パラメータ化SQLを使用する。

---

## 24.7 テスト受入れ基準

### AC-048 実通信非依存

通常の自動テストが実外部APIへ接続しない。

### AC-049 ISBNテスト

ISBN正規化、検証および変換の正常系・異常系テストが存在する。

### AC-050 Clientテスト

Google Books ClientとopenBD Clientの正常系、対象なしおよび異常系テストが存在する。

### AC-051 Serviceテスト

優先順位、空欄補完、部分成功および全失敗のテストが存在する。

### AC-052 GUIテスト

上書き確認、フォーム反映、ボタン復旧および自動保存禁止を検証できる。

### AC-053 秘密情報テスト

APIキーがログ、例外およびRawデータに含まれないことを検証する。

### AC-054 回帰テスト

実装中に発見した不具合には、再現テストを追加する。

---

## 24.8 GUI受入れ基準

### AC-055 取得ボタン

ISBN欄の近くに取得ボタンが配置されている。

### AC-056 成功表示

正常取得時にステータスバーへ成功内容を表示する。

### AC-057 対象なし表示

対象書籍がない場合に、情報ダイアログで手入力を案内する。

### AC-058 入力不正表示

ISBN不正時に、利用者が理解できる警告を表示する。

### AC-059 接続エラー表示

接続失敗時に、ネットワーク確認を案内する。

### AC-060 利用制限表示

利用制限時に、時間をおいた再試行を案内する。

### AC-061 応答エラー表示

応答不正時に、一般的な再試行案内を表示する。

### AC-062 編集可能性

取得結果を反映した後も、利用者が各項目を修正できる。

---

## 24.9 ログ受入れ基準

### AC-063 正常ログ

正常取得を必要に応じてINFOで記録できる。

### AC-064 部分成功ログ

一部Client失敗をWARNINGとして記録し、全体成功をINFOとして記録できる。

### AC-065 全失敗ログ

全Client失敗時にERRORまたは例外ログを記録できる。

### AC-066 対象なしログ

対象なしを通常のINFOまたはDEBUGとして記録し、ERRORにしない。

### AC-067 秘密情報

APIキー、認証情報およびRawレスポンス全文を記録しない。

---

## 24.10 性能および操作性の受入れ基準

第1段階では同期処理を採用する。

次を満たすことを確認する。

* timeoutにより無制限待機しない。
* 通常時の取得時間が実用上許容できる。
* 二重実行を防止できる。
* エラー後にGUI操作を継続できる。
* 外部取得失敗後も既存CRUDを利用できる。

具体的な秒数を厳密な性能保証とはしない。

---

## 24.11 ドキュメント受入れ基準

次の情報が設計書または関連ドキュメントへ記録されている。

* 採用したアーキテクチャ
* Client優先順位
* 空欄補完規則
* timeout値
* APIキー管理
* 例外方針
* 自動保存禁止
* テスト方針
* 対象外項目
* 将来課題
* 設計判断の理由

---

## 24.12 第1段階の完了判定

第1段階は、次の条件をすべて満たした時点で完了とする。

1. 必須の受入れ基準を満たす。
2. 自動テストが成功する。
3. 主要な手動確認が完了する。
4. 既存CRUDの回帰テストが成功する。
5. APIキーがリポジトリへ含まれていない。
6. 設計書と実装が矛盾していない。
7. 未対応項目が明示されている。
8. コードレビューで重大な責務混在が指摘されていない。
9. 外部API障害時にアプリが継続利用できる。
10. 利用者が取得結果を確認してから保存できる。

---

## 24.13 受入れ対象外

次は第1段階の受入れ対象外とする。

* 書籍名による外部検索
* 著者名による外部検索
* 雑誌コードによる取得
* 表紙画像表示
* 表紙画像保存
* 出版日のDB保存
* RawレスポンスのDB保存
* 外部取得結果のキャッシュ
* 非同期通信
* 自動リトライ
* 著者名の完全正規化
* 出版社マスタとの自動照合
* 取得候補選択画面
* 項目ごとの取得元選択
* ISBN以外の識別子対応
* バルク取得
* オフライン同期

---

# 25. 実装順序

## 25.1 目的

実装順序は、依存関係の下位から上位へ進め、各段階でテスト可能な状態を維持するよう定める。

GUIから先に実装せず、データモデル、ISBN処理、例外、Client、Service、GUIの順に進める。

---

## 25.2 基本方針

実装は次の方針で進める。

* 一度に全機能を作らない。
* 1コミット1テーマを守る。
* 各段階でテストを追加する。
* 実API確認と自動テストを分離する。
* 既存CRUDを変更しすぎない。
* 設計書との差異が生じた場合は設計書を更新する。
* Google Books Clientを先に完成させる。
* openBD Clientを後から追加する。
* GUI連携はService完成後に行う。
* 最後に回帰テストと文書更新を行う。

---

## 25.3 第1段階：既存構成の確認

実装開始前に、次を確認する。

* 現在のディレクトリ構成
* `BookItem` の定義
* `BookService` の公開メソッド
* Repositoryの構造
* GUIクラスの依存注入方法
* ISBN欄の変数名
* 各入力欄のウィジェット
* ステータスバーの実装
* 既存例外クラス
* ログ設定
* テスト構成
* pyprojectの依存関係

この段階では、機能コードを変更しない。

---

## 25.4 第2段階：ディレクトリ設計

外部書誌情報取得機能の配置を確定する。

推奨構成例を次に示す。

```text id="xfntpm"
src/
└── book_manager/
    ├── config.py
    ├── isbn/
    │   ├── __init__.py
    │   ├── normalizer.py
    │   ├── validator.py
    │   └── converter.py
    ├── metadata/
    │   ├── __init__.py
    │   ├── exceptions.py
    │   ├── protocols.py
    │   ├── service.py
    │   └── clients/
    │       ├── __init__.py
    │       ├── google_books.py
    │       └── openbd.py
    └── models/
        └── fetched_book_data.py
```

既存プロジェクト構成に合わせて調整する。

---

## 25.5 第3段階：`FetchedBookData`

最初に共通データモデルを実装する。

作業内容は次のとおりである。

1. `fetched_book_data.py` を作成する。
2. `FetchedBookData` を定義する。
3. 型ヒントとDocstringを追加する。
4. 既定値を定義する。
5. モデル単体テストを追加する。

この段階ではClientを実装しない。

---

## 25.6 第4段階：例外クラス

次に外部取得用例外を実装する。

実装候補は次のとおりである。

```text id="i6u8nj"
BookMetadataError
BookMetadataConnectionError
BookMetadataResponseError
BookMetadataRateLimitError
BookMetadataNotFoundError
BookMetadataConfigurationError
```

必要な属性は最小限から開始する。

例外クラスの単体テストも追加する。

---

## 25.7 第5段階：ISBN正規化

ISBN正規化処理を実装する。

対象は次のとおりである。

* 前後空白
* 半角空白
* 全角空白
* 許容ハイフン
* 小文字xから大文字X

正規化テストを先にまたは同時に追加する。

---

## 25.8 第6段階：ISBN検証

ISBN-10とISBN-13の検証を実装する。

順序は次のとおりである。

1. ISBN-10形式判定
2. ISBN-10チェックデジット
3. ISBN-13形式判定
4. ISBN-13チェックデジット
5. 共通検証関数

正常系と異常系をパラメータ化テストで固定する。

---

## 25.9 第7段階：ISBN変換

ISBN-10からISBN-13への変換を実装する。

次を確認する。

* 変換前ISBN-10が有効である。
* `978` を付加する。
* ISBN-13チェックデジットを再計算する。
* 既知の変換結果と一致する。
* 変換後ISBN-13が検証に合格する。

---

## 25.10 第8段階：Protocol

`BookMetadataClient` Protocolを定義する。

必要な契約は次のとおりである。

```python id="ceq6sj"
@property
def source_name(self) -> str:
    ...

def fetch_by_isbn(
    self,
    isbn: str,
) -> FetchedBookData | None:
    ...
```

この段階でFake Clientを作成し、Serviceテスト準備に利用できる。

---

## 25.11 第9段階：文字列補助関数

外部レスポンスの文字列を安全に処理する共通補助関数を実装する。

候補は次のとおりである。

```text id="7gwezn"
normalize_optional_text
join_authors
has_meaningful_value
```

共通化が小さすぎる場合は、各Client内の非公開関数として開始してもよい。

Client間で同じ処理が増えた時点で共通モジュールへ移動する。

---

## 25.12 第10段階：Google Books Clientの通信部分

Google Books Clientの最初の実装では、通信境界を作る。

作業内容は次のとおりである。

1. コンストラクタ
2. Session注入
3. APIキー注入
4. timeout注入
5. リクエストパラメータ生成
6. HTTP GET
7. HTTP 429判定
8. HTTP異常処理
9. JSON解析
10. 通信単体テスト

この段階では、詳細な書誌変換を分けて実装してよい。

---

## 25.13 第11段階：Google Books Clientの候補選択

次にISBN一致候補の選択を実装する。

作業内容は次のとおりである。

* `items` の型確認
* `volumeInfo` の型確認
* `industryIdentifiers` の解析
* ISBN正規化
* ISBN-10変換比較
* 一致候補の選択
* 一致候補なしの `None`

複数候補Fixtureを使用してテストする。

---

## 25.14 第12段階：Google Books Clientの変換

Google Booksレスポンスから次を取得する。

* 書籍名
* 著者名
* 出版社
* 出版日
* 内容紹介
* 表紙画像URL
* 取得元
* Rawデータ

出版形態は、明確な規則がない限り `None` とする。

欠損項目のFixtureテストを追加する。

---

## 25.15 第13段階：Google Books単体確認

Google Books Client完成後に、Fake Sessionによる自動テストをすべて成功させる。

その後、限定的に実APIで手動確認する。

確認するISBNは、次の種類を含める。

* 国内書籍
* ISBN-10を持つ書籍
* 内容紹介あり
* 内容紹介なし
* 複数著者
* 古い書籍
* Google Booksで対象なし

実API確認結果を基に、レスポンス変換を調整する。

---

## 25.16 第14段階：Serviceの基本実装

Google Books Clientだけを使用して、`BookMetadataService` の基本処理を実装する。

作業内容は次のとおりである。

* Client一覧の注入
* ISBN正規化
* ISBN検証
* 問い合わせISBN生成
* Client呼び出し
* 対象なしのNotFound変換
* 例外伝播
* 統合結果のISBN置換

Fake Clientで単体テストする。

---

## 25.17 第15段階：Serviceの複数Client対応

次に複数Clientの制御を実装する。

作業内容は次のとおりである。

* Client登録順の維持
* 全Client呼び出し
* 結果一覧
* エラー一覧
* 部分成功
* 全失敗
* 最終例外選択

この時点ではFake Clientだけで検証できる。

---

## 25.18 第16段階：統合処理

空欄補完方式の統合を実装する。

対象項目は次のとおりである。

* 書籍名
* 著者名
* 出版社
* 出版日
* 出版形態
* 内容紹介
* 表紙画像URL
* 取得元
* Rawデータ

後順位で先順位を上書きしないテストを重点的に追加する。

---

## 25.19 第17段階：openBD Clientの通信部分

Google Books ClientとServiceの基本動作が安定した後に、openBD Clientを実装する。

最初に次を実装する。

* Session注入
* timeout
* ISBNパラメータ
* HTTP GET
* HTTP 429
* HTTP異常
* JSON解析
* トップレベル配列判定
* `[null]` の対象なし判定

---

## 25.20 第18段階：openBDのsummary変換

次に `summary` から基本項目を取得する。

対象は次のとおりである。

* ISBN
* 書籍名
* 著者名
* 出版社
* 出版日
* 表紙画像URL

最初は `summary` だけでClientを完成させてもよい。

ONIXとhanmotoは、必要性と取得テストを確認して段階的に追加する。

---

## 25.21 第19段階：openBDの内容紹介

内容紹介が必要な場合は、Fixtureと実レスポンスを確認しながら追加する。

作業順序は次のとおりである。

1. 内容紹介候補項目を調査する。
2. 各項目の意味を文書化する。
3. 優先順位を定義する。
4. HTML処理方針を決定する。
5. Fixtureを作成する。
6. 変換処理を実装する。
7. 単体テストを追加する。

項目の意味が不明なまま推測実装しない。

---

## 25.22 第20段階：ServiceへのopenBD登録

openBD ClientをServiceへ第2取得元として登録する。

```python id="0gde40"
metadata_service = BookMetadataService(
    clients=[
        google_books_client,
        openbd_client,
    ],
)
```

次を確認する。

* Google Booksが先順位
* openBDが後順位
* 空欄補完
* Google Books失敗時のopenBD成功
* openBD失敗時のGoogle Books成功
* 両方対象なし
* 両方失敗

---

## 25.23 第21段階：設定読み込み

Google Books APIキーおよびtimeout設定を起動処理へ組み込む。

作業内容は次のとおりである。

* 環境変数名を確定する。
* APIキー未設定時の動作をDesign Freezeする。
* timeout定数を定義する。
* Sessionを生成する。
* User-Agentを必要に応じて設定する。
* Clientを生成する。
* Serviceを生成する。
* GUIへ注入する。

---

## 25.24 第22段階：GUIへのService注入

GUIクラスが `BookMetadataService` を受け取れるようにする。

概念例を次に示す。

```python id="cl5bhs"
class BookManagerApplication:
    def __init__(
        self,
        ...,
        metadata_service: BookMetadataService,
    ) -> None:
        self._metadata_service = (
            metadata_service
        )
```

GUI内部でServiceやClientを生成しない。

---

## 25.25 第23段階：取得ボタン

ISBN欄の近くへ取得ボタンを追加する。

最初に確認する内容は次のとおりである。

* 画面レイアウト
* ボタン文言
* フォーカス順序
* 既存ボタンとの整合性
* macOSとWindowsでの表示
* ボタン状態切り替え方法

まだAPI呼び出しを接続せず、イベントメソッドの枠だけ作成してもよい。

---

## 25.26 第24段階：上書き確認

GUIへ上書き確認処理を追加する。

確認対象は次のとおりである。

* 書籍名
* 著者名
* 出版社
* 出版形態
* 内容紹介

利用者が拒否した場合、Serviceを呼ばないことをテストする。

---

## 25.27 第25段階：取得イベント

取得ボタンとServiceを接続する。

処理順序は次のとおりである。

1. ISBN取得
2. 未入力確認
3. 上書き確認
4. ボタン無効化
5. Service呼び出し
6. 結果反映
7. 成功表示
8. 例外表示
9. `finally` でボタン復旧

イベントハンドラを過度に長くしない。

---

## 25.28 第26段階：フォーム反映

`_apply_fetched_metadata()` のような専用メソッドを実装する。

次を確認する。

* 対象項目だけ更新
* `None` は反映しない。
* 空白だけの値は反映しない。
* 未知の出版形態は反映しない。
* 非対象項目を維持する。
* 自動保存しない。

---

## 25.29 第27段階：GUI例外表示

例外クラスごとの表示を実装する。

捕捉順序は具体例外から基底例外とする。

次を用意する。

* ISBN不正
* 対象なし
* 利用制限
* 接続失敗
* 応答不正
* 設定不備
* 基底例外
* 想定外例外

ログとGUIメッセージを分離する。

---

## 25.30 第28段階：ログ追加

主要処理へログを追加する。

対象は次のとおりである。

* 取得開始
* Client呼び出し
* Client成功
* Client失敗
* 部分成功
* 対象なし
* 全失敗
* 統合成功
* 想定外例外

APIキー、Rawレスポンス全文および内容紹介全文を出力しない。

---

## 25.31 第29段階：GUI手動確認

次の順に手動確認する。

1. ISBN未入力
2. 不正ISBN
3. 有効ISBN-13
4. ハイフン付きISBN
5. ISBN-10
6. 上書きキャンセル
7. 上書き承認
8. 対象なし
9. ネットワーク切断
10. 部分成功
11. 全失敗
12. 連続取得
13. 保存
14. 更新

---

## 25.32 第30段階：既存CRUD回帰テスト

外部取得機能の追加後に、既存機能を確認する。

* 新規登録
* 更新
* 削除
* 検索
* 一覧表示
* 重複ISBN
* 読了年月
* 備考
* 雑誌コード
* CSV機能がある場合は入出力
* アプリケーション終了
* DBバックアップ

外部取得機能の追加によって既存動作を変更しない。

---

## 25.33 第31段階：セキュリティ確認

実装完了前に、次を確認する。

* APIキーがGit差分にない。
* APIキーがログにない。
* APIキーがFixtureにない。
* APIキーがRawデータにない。
* `verify=False` がない。
* クエリ付き完全URLをログへ出していない。
* 外部HTMLを実行していない。
* SQL文字列へ外部データを連結していない。

---

## 25.34 第32段階：ドキュメント更新

実装に合わせて、次を更新する。

* `external_book_metadata_design.md`
* README
* 環境変数設定手順
* テスト実行手順
* 利用者向け操作説明
* 必要に応じてADR
* Revision history
* 実装済み範囲
* 将来課題

設計書と実装の差異を残さない。

---

## 25.35 第33段階：ADRの作成

実装中に重要な設計判断を変更した場合は、ADRを作成する。

候補例は次のとおりである。

* Google Books APIキー未設定時の動作
* openBDを補完元とする判断
* 同期処理を採用する判断
* Rawデータを保存しない判断
* ISBN-10入力を維持する判断
* 出版日をDBへ保存しない判断
* 表紙画像を第1段階で扱わない判断

単なる実装詳細ではなく、将来の変更判断に影響する決定を記録する。

---

## 25.36 コミット単位

推奨コミット例を次に示す。

```text id="xcb5td"
feat: 外部書誌情報モデルを追加する
```

```text id="4lp8sy"
feat: ISBNの正規化と検証を追加する
```

```text id="gxsivp"
feat: ISBN-10からISBN-13への変換を追加する
```

```text id="52rs69"
feat: Google Books Clientを追加する
```

```text id="k5y3vw"
test: Google Books Clientのテストを追加する
```

```text id="oyb70r"
feat: 外部書誌情報Serviceを追加する
```

```text id="fuv85o"
feat: openBD Clientを追加する
```

```text id="v3mp68"
feat: ISBNからの書誌情報取得をGUIへ追加する
```

```text id="1xy3ru"
docs: 外部書誌情報取得の設計を更新する
```

一つのコミットへClient、Service、GUIおよびドキュメント変更をすべて混在させない。

---

## 25.37 実装中の設計変更

実装中に設計どおりに進められない場合は、次の順序で判断する。

1. 実装上の一時的な問題か確認する。
2. 設計意図を再確認する。
3. 代替案を比較する。
4. 既存責務分離を壊さないか確認する。
5. テスト可能性を確認する。
6. 設計変更が必要なら文書を更新する。
7. 重要な判断ならADRを作成する。
8. 変更理由をコミット本文へ記録する。

コードだけを設計書と異なる状態へ変更しない。

---

## 25.38 最終レビュー

実装完了時に、次をレビューする。

* GUIがHTTPを認識していない。
* ServiceがAPI固有JSONを認識していない。
* ClientがDBを認識していない。
* Repositoryが外部APIを認識していない。
* `FetchedBookData` と `BookItem` が分離されている。
* 後順位が先順位を上書きしていない。
* `None` で既存GUI値を消していない。
* 自動保存していない。
* timeoutが指定されている。
* APIキーが安全に管理されている。
* 自動テストが実APIに依存していない。
* 設計書と実装が一致している。

---

## 25.39 実装完了条件

実装作業は、次をすべて満たした時点で完了とする。

1. 第24章の受入れ基準を満たす。
2. 自動テストがすべて成功する。
3. 手動確認が完了する。
4. 既存CRUDの回帰確認が完了する。
5. セキュリティ確認が完了する。
6. 設計書が更新されている。
7. 未対応事項が明示されている。
8. コミット履歴が機能単位に整理されている。
9. APIキーがGit履歴へ含まれていない。
10. 外部サービス障害時にもアプリケーションを継続利用できる。

---
# 26. ファイル構成

## 26.1 目的

ファイル構成では、外部書誌情報取得機能を既存のbook_managerへ追加する際の推奨配置を定義する。

責務ごとにモジュールを分離し、GUI、Service、Client、モデル、例外、ISBN処理および設定が一つのファイルへ集中しない構成とする。

---

## 26.2 推奨構成

推奨する全体構成例を次に示す。

```text
book_manager/
├── pyproject.toml
├── README.md
├── docs/
│   ├── README.md
│   ├── external_book_metadata_design.md
│   └── adr/
├── src/
│   └── book_manager/
│       ├── __init__.py
│       ├── config.py
│       ├── main.py
│       ├── gui/
│       │   ├── __init__.py
│       │   └── application.py
│       ├── isbn/
│       │   ├── __init__.py
│       │   ├── normalizer.py
│       │   ├── validator.py
│       │   └── converter.py
│       ├── metadata/
│       │   ├── __init__.py
│       │   ├── exceptions.py
│       │   ├── protocols.py
│       │   ├── service.py
│       │   ├── text_utils.py
│       │   └── clients/
│       │       ├── __init__.py
│       │       ├── google_books.py
│       │       └── openbd.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── book_item.py
│       │   └── fetched_book_data.py
│       ├── repositories/
│       │   ├── __init__.py
│       │   └── book_repository.py
│       └── services/
│           ├── __init__.py
│           └── book_service.py
└── tests/
    ├── unit/
    │   ├── isbn/
    │   ├── metadata/
    │   └── gui/
    ├── integration/
    └── fixtures/
        └── metadata/
            ├── google_books/
            └── openbd/
```

既存プロジェクトの構成と異なる場合は、命名と配置を調整してよい。

ただし、責務分離の方針は維持する。

---

## 26.3 `config.py`

`config.py` は、アプリケーション設定の読み込みと型定義を担当する。

想定する内容は次のとおりである。

* Google Books APIキーの読み込み
* HTTP timeout定数
* 設定データクラス
* 設定値の検証
* 将来のClient有効・無効設定

外部API通信処理を記述しない。

---

## 26.4 `isbn` パッケージ

`isbn` パッケージは、ISBNに関する純粋な処理を担当する。

### `normalizer.py`

* 空白除去
* ハイフン除去
* 小文字xの大文字化

### `validator.py`

* ISBN-10検証
* ISBN-13検証
* チェックデジット検証
* 共通検証

### `converter.py`

* ISBN-10からISBN-13への変換
* 問い合わせ用ISBN-13生成
* ISBN比較用変換

HTTP通信やGUI操作を含めない。

---

## 26.5 `metadata` パッケージ

`metadata` パッケージは、外部書誌情報取得機能の中心となる。

### `exceptions.py`

外部書誌情報取得用の共通例外を定義する。

### `protocols.py`

`BookMetadataClient` Protocolを定義する。

### `service.py`

Client制御、ISBN処理の呼び出し、結果統合および最終例外選択を担当する。

### `text_utils.py`

外部レスポンス文字列の共通補助処理を配置できる。

例は次のとおりである。

* `normalize_optional_text`
* `has_meaningful_value`
* 著者文字列結合
* 必要最小限のHTMLテキスト化

重複が少ない段階では、無理に作成しなくてもよい。

---

## 26.6 `metadata/clients` パッケージ

`clients` パッケージには、取得元ごとの具象Clientを配置する。

### `google_books.py`

* Google Books API通信
* Google Booksレスポンス解析
* ISBN一致候補選択
* `FetchedBookData` 生成

### `openbd.py`

* openBD API通信
* openBDレスポンス解析
* 対象なし判定
* `FetchedBookData` 生成

Client間で互いをimportしない。

---

## 26.7 `models/fetched_book_data.py`

`FetchedBookData` は、外部取得結果専用モデルとして配置する。

既存の `BookItem` とは別ファイルとする。

```text
models/
├── book_item.py
└── fetched_book_data.py
```

両モデルの違いがファイル構成上も分かるようにする。

---

## 26.8 GUIファイル

GUIへの追加内容は、既存GUI構成へ合わせる。

一つのGUIクラスが大きくなりすぎる場合は、次の分離を検討する。

```text
gui/
├── application.py
├── book_form.py
└── metadata_controller.py
```

ただし、第1段階で外部取得処理だけのために過度なController階層を追加しない。

GUIイベントとフォーム反映処理を専用メソッドへ分けるだけでもよい。

---

## 26.9 テスト構成

テストは、本体コードの責務に対応する形で配置する。

```text
tests/
├── unit/
│   ├── isbn/
│   │   ├── test_normalizer.py
│   │   ├── test_validator.py
│   │   └── test_converter.py
│   ├── metadata/
│   │   ├── test_google_books_client.py
│   │   ├── test_openbd_client.py
│   │   ├── test_metadata_service.py
│   │   └── test_exceptions.py
│   └── gui/
│       └── test_metadata_integration.py
├── integration/
│   └── test_metadata_workflow.py
└── fixtures/
    └── metadata/
```

本体ファイルとテストファイルの対応関係が分かる命名とする。

---

## 26.10 Fixture配置

APIごとにFixtureを分離する。

```text
tests/
└── fixtures/
    └── metadata/
        ├── google_books/
        │   ├── full_metadata.json
        │   ├── missing_description.json
        │   ├── multiple_items.json
        │   └── not_found.json
        └── openbd/
            ├── summary_full.json
            ├── null_item.json
            ├── onix_description.json
            └── empty_array.json
```

取得元が増えた場合も、同じ階層へ追加する。

---

## 26.11 `__init__.py`

各パッケージの `__init__.py` では、必要な公開要素だけを再公開する。

例を次に示す。

```python
from .exceptions import (
    BookMetadataConnectionError,
    BookMetadataError,
    BookMetadataNotFoundError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
)
from .service import BookMetadataService

__all__ = [
    "BookMetadataConnectionError",
    "BookMetadataError",
    "BookMetadataNotFoundError",
    "BookMetadataRateLimitError",
    "BookMetadataResponseError",
    "BookMetadataService",
]
```

すべての内部補助関数を公開しない。

---

## 26.12 import方向

推奨する依存方向を次に示す。

```text
GUI
 ├─ metadata.service
 ├─ metadata.exceptions
 └─ models.fetched_book_data

metadata.service
 ├─ metadata.protocols
 ├─ metadata.exceptions
 ├─ models.fetched_book_data
 └─ isbn

metadata.clients
 ├─ metadata.exceptions
 ├─ models.fetched_book_data
 └─ isbn

Repository
 └─ models.book_item
```

Repositoryからmetadataパッケージをimportしない。

---

## 26.13 循環importの防止

次のような循環依存を作らない。

```text
service.py
  ↓
google_books.py
  ↓
service.py
```

ServiceはProtocolへ依存し、ClientはServiceへ依存しない。

共通モデルと例外は、両者から参照可能な独立モジュールへ配置する。

---

## 26.14 型チェック時のimport

GUI型ヒントなどで循環importが発生する場合は、次を利用できる。

```python
from __future__ import annotations
```

必要に応じて `TYPE_CHECKING` を使用する。

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from book_manager.metadata.service import (
        BookMetadataService,
    )
```

ただし、循環依存そのものを隠す目的で乱用しない。

---

## 26.15 ファイル名の命名規則

Pythonファイル名は、原則として小文字のsnake_caseとする。

```text
google_books.py
fetched_book_data.py
book_metadata_service.py
```

クラス名はPascalCaseとする。

```text
GoogleBooksClient
FetchedBookData
BookMetadataService
```

既存プロジェクトの命名規則と統一する。

---

## 26.16 将来のClient追加

将来、別の取得元を追加する場合は、次のようにClientファイルを追加する。

```text
metadata/
└── clients/
    ├── google_books.py
    ├── openbd.py
    └── new_provider.py
```

Service本体は、原則として変更せず、起動時のClient登録を追加する。

```python
clients = [
    GoogleBooksClient(...),
    OpenBdClient(...),
    NewProviderClient(...),
]
```

Protocolに適合する限り、Serviceの統合処理を再利用する。

---

## 26.17 ファイル構成上の禁止事項

次の構成は禁止する。

* GUIファイル内にClientクラスを定義する。
* Repositoryファイル内に外部API処理を記述する。
* 一つのファイルへモデル、Service、Client、GUIを集約する。
* Clientごとに例外クラスを重複定義する。
* ISBN処理を各Clientへコピーする。
* Fixtureを本番コード配下へ置く。
* RawレスポンスをGit管理対象の実行時データとして保存する。
* Client間で相互importする。
* Serviceから具象Clientモジュールを直接生成目的でimportする。

---

# 27. 依存関係管理

## 27.1 目的

依存関係管理では、外部書誌情報取得機能で追加するPythonパッケージと、バージョン管理方針を定義する。

不要な依存ライブラリを増やさず、標準ライブラリと既存依存関係を優先する。

---

## 27.2 追加依存

第1段階で必要となる主要な外部依存は `requests` である。

```toml
dependencies = [
    "requests",
]
```

既にプロジェクト依存へ登録されている場合は、重複追加しない。

---

## 27.3 開発依存

テストにpytestを使用する場合の候補を次に示す。

```toml
[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
]
```

既存の開発依存管理方式へ合わせる。

Mock機能は、原則としてPython標準の `unittest.mock` を使用できる。

---

## 27.4 HTML処理ライブラリ

内容紹介のHTMLをプレーンテキスト化するためだけに、大きな依存ライブラリを直ちに追加しない。

まずは次の選択肢を比較する。

* HTMLをそのままプレーン文字列として表示する。
* 標準ライブラリで必要最小限に処理する。
* 既存依存ライブラリを利用する。
* 専用ライブラリを追加する。

外部ライブラリ追加は、実レスポンス上の必要性を確認してから行う。

---

## 27.5 `.env` ライブラリ

環境変数読み込みだけのために、`python-dotenv` を必須依存へ追加しない。

第1段階では `os.getenv()` を使用できる。

開発環境で `.env` の利便性が必要になった場合は、開発依存または明確な運用要件として導入を検討する。

---

## 27.6 バージョン範囲

依存ライブラリのバージョン指定は、プロジェクト全体の方針へ合わせる。

候補例を次に示す。

```toml
dependencies = [
    "requests>=2.32,<3",
]
```

厳密な固定が必要な場合は、ロックファイルまたは運用環境の依存固定方式を使用する。

---

## 27.7 Pythonバージョン

型ヒントでは、プロジェクトが対象とするPythonバージョンを前提とする。

次の記法を使用する場合は、対応Pythonバージョンを確認する。

```python
str | None
list[str]
tuple[int, int]
```

Python 3.10以降を前提とする構成であれば使用できる。

---

## 27.8 依存の注入

外部ライブラリそのものを直接差し替えるのではなく、SessionやClientを注入可能にする。

```text
requests
   ↓
Session
   ↓
GoogleBooksClient
   ↓
BookMetadataClient Protocol
   ↓
BookMetadataService
```

これにより、テストで実通信を避けられる。

---

## 27.9 依存更新

依存ライブラリ更新時は、少なくとも次を確認する。

* Clientテスト
* timeout例外
* HTTPError処理
* JSON解析
* Session動作
* TLS接続
* 既存CRUD
* macOSとWindowsでの起動

`requests` のメジャーバージョン更新時は、変更点を確認する。

---

## 27.10 脆弱性確認

依存ライブラリに既知の脆弱性が報告された場合は、影響範囲を確認し、必要に応じて更新する。

APIキーやHTTPS通信を扱うため、HTTP関連ライブラリの更新を長期間放置しない。

---

## 27.11 依存関係管理上の禁止事項

次を禁止する。

* 同じ目的のHTTPライブラリを複数導入する。
* 実装前に不要なライブラリを追加する。
* APIキー管理のためだけに重い設定フレームワークを追加する。
* テストだけで必要な依存を本番必須へ混在させる。
* 依存バージョンを確認せずメジャー更新する。
* Git管理されない手作業インストールだけに依存する。

---

# 28. 将来拡張

## 28.1 目的

将来拡張では、第1段階の対象外とした機能と、拡張時に維持すべき設計原則を整理する。

将来の可能性を考慮するが、現時点で必要のない抽象化や実装を先行して追加しない。

---

## 28.2 書籍名検索

将来、ISBNが不明な場合に書籍名から候補検索する機能を追加できる。

想定フローは次のとおりである。

```text
書籍名入力
    ↓
外部候補検索
    ↓
候補一覧表示
    ↓
利用者が選択
    ↓
フォームへ反映
```

複数候補を返すため、現在の `fetch_by_isbn()` とは別のインターフェースが必要となる。

```python
def search_by_title(
    self,
    title: str,
) -> list[FetchedBookData]:
    ...
```

---

## 28.3 著者名検索

著者名による検索も将来候補とする。

同名著者、表記ゆれ、複数著者および大量候補への対応が必要となる。

ISBN検索より曖昧性が高いため、利用者による候補選択を必須とする。

---

## 28.4 雑誌コード検索

雑誌コードから書誌情報を取得する機能は、第1段階の対象外とする。

対応する場合は、次を調査する。

* 利用可能な外部サービス
* 雑誌コードの形式
* 定期刊行物と増刊号の識別
* JANコードとの関係
* 号数および発売日の扱い
* 書籍ISBNとのモデル分離

---

## 28.5 表紙画像表示

将来、取得した表紙画像URLから画像を取得し、GUIへ表示できる。

追加設計が必要な項目は次のとおりである。

* 画像Client
* timeout
* ファイルサイズ上限
* Content-Type確認
* Pillowなど画像ライブラリ
* Tkinter画像参照の保持
* プレースホルダー
* 画像取得失敗時の処理
* 画像キャッシュ
* セキュリティ

書誌情報取得Clientと画像取得処理を同一責務にしない。

---

## 28.6 表紙画像保存

表紙画像を保存する場合は、次の方式を比較する。

* SQLite BLOB
* ローカルファイル
* URLだけを保存
* サムネイルだけを保存
* キャッシュとして保存

バックアップ、容量、リンク切れ、画像更新および削除時処理を設計する必要がある。

---

## 28.7 出版日のDB保存

将来、出版日を正式項目として保存する場合は、日付精度を保持できる設計が必要となる。

外部APIは次のような値を返す可能性がある。

```text
2026
2026-07
2026-07-24
20260724
```

単純な日付型へ変換すると、存在しない月日を補完する問題が生じる。

候補設計は次のとおりである。

* 原文文字列を保存する。
* 年、月、日を別カラムで保存する。
* 日付精度カラムを持つ。
* 正規化値とRaw値を分ける。

---

## 28.8 外部取得キャッシュ

同じISBNへの繰り返し通信を減らすため、キャッシュを導入できる。

設計項目は次のとおりである。

* キャッシュキー
* 有効期限
* 取得元別キャッシュ
* 失敗結果のキャッシュ
* 手動更新
* キャッシュ無効化
* SQLiteまたはファイル保存
* API仕様変更時の扱い

正式な書籍データとキャッシュを同じテーブルへ保存しない。

---

## 28.9 非同期処理

GUI応答性を改善するため、将来は外部取得をバックグラウンドスレッドで実行できる。

追加設計が必要な項目は次のとおりである。

* Tkinterのメインスレッド制約
* `after()` による画面更新
* キャンセル
* 二重実行防止
* 終了時の処理
* Sessionのスレッド安全性
* 例外のメインスレッドへの伝達
* 進捗表示

第1段階では同期処理とし、必要性を実測して判断する。

---

## 28.10 自動リトライ

一時的な通信障害への自動リトライを将来追加できる。

検討項目は次のとおりである。

* 対象例外
* 最大回数
* 待機時間
* 指数バックオフ
* Retry-After
* HTTP 429の扱い
* GUI待機時間
* キャンセル
* ログ

利用者の操作感と外部サービスへの負荷を考慮する。

---

## 28.11 項目別取得元優先順位

将来、項目ごとに優先取得元を変更できる。

例を次に示す。

| 項目   | 第1優先         | 第2優先         |
| :--- | :----------- | :----------- |
| 書籍名  | Google Books | openBD       |
| 著者名  | Google Books | openBD       |
| 出版社  | openBD       | Google Books |
| 内容紹介 | openBD       | Google Books |
| 表紙画像 | Google Books | openBD       |

ただし、設定とテストが複雑になるため、第1段階ではClient順による統一優先順位を使用する。

---

## 28.12 競合確認画面

取得元間で値が異なる場合に、利用者が選択できる画面を追加できる。

想定例を次に示す。

```text
書籍名

Google Books:
〇〇入門

openBD:
〇〇入門 改訂版
```

この場合、項目ごとの候補保持モデルが必要になる。

現在の統合済み `FetchedBookData` だけでは、競合候補を完全には保持できない。

---

## 28.13 著者マスタ連携

将来の著者マスタでは、外部取得著者名を正規化候補として扱える。

検討項目は次のとおりである。

* 姓名分離
* 表記順
* 生没年
* ペンネーム
* 翻訳者
* 編集者
* 監修者
* 同姓同名
* 外部識別子
* 利用者確認

Client内で著者マスタ登録を行わない。

---

## 28.14 出版社マスタ連携

出版社名の表記ゆれを正規化するため、出版社マスタとの照合を追加できる。

例を次に示す。

```text
株式会社文藝春秋
文藝春秋
（株）文藝春秋
```

自動確定ではなく、候補提示や別名管理を検討する。

---

## 28.15 取得履歴

将来、外部取得履歴を記録できる。

候補項目は次のとおりである。

* ISBN
* 取得日時
* 取得元
* 成功または失敗
* 取得項目
* HTTPステータス
* アプリケーションバージョン

ただし、RawレスポンスやAPIキーを履歴へ保存しない。

---

## 28.16 バルク取得

複数ISBNを一括取得する機能は、第1段階の対象外とする。

追加設計が必要な項目は次のとおりである。

* API利用制限
* 進捗表示
* キャンセル
* 並列数
* エラー一覧
* 部分成功
* キャッシュ
* 保存前確認
* 重複ISBN
* バックグラウンド処理

---

## 28.17 オフライン利用

キャッシュまたは事前取得データを使用したオフライン補完を将来検討できる。

既存CRUDはもともとローカルSQLiteで利用できるため、外部取得機能がオフライン時に無効でも本体利用を継続できる設計を維持する。

---

## 28.18 取得元追加

将来の取得元追加では、次を満たすClientを実装する。

* `BookMetadataClient` Protocolへ適合する。
* API固有JSONを内部モデルへ変換する。
* 共通例外を使用する。
* timeoutを指定する。
* Sessionまたは通信依存を注入可能にする。
* 対象なしと障害を区別する。
* 自動テストを実APIへ依存させない。

Serviceの既存統合規則を利用できる。

---

## 28.19 将来拡張時に維持する原則

将来機能を追加する場合も、次を維持する。

* GUIはHTTP通信を行わない。
* ServiceはAPI固有JSONを扱わない。
* ClientはDBへ保存しない。
* Repositoryは外部APIへ接続しない。
* 保存前に利用者が確認できる。
* APIキーを安全に管理する。
* 外部障害で既存CRUDを停止しない。
* 自動テストは実APIへ依存しない。
* モデルの責務を分離する。
* 重要な設計変更を文書化する。

---

# 29. リスクと対策

## 29.1 目的

本章では、外部書誌情報取得機能に関する主要な技術的・運用上のリスクと、その対策を整理する。

外部サービスを利用する以上、すべての書籍情報を常に正しく取得できることは保証しない。

---

## 29.2 API仕様変更

### リスク

外部APIのレスポンス項目、構造、認証方式またはエンドポイントが変更される可能性がある。

### 影響

* JSON解析失敗
* 項目欠損
* 全取得失敗
* 誤った値の反映

### 対策

* API固有処理をClientへ隔離する。
* レスポンス型を防御的に確認する。
* Fixtureテストを用意する。
* 想定外構造を応答例外として扱う。
* API変更時はClientだけを修正する。
* 回帰テストを追加する。

---

## 29.3 外部サービス停止

### リスク

Google BooksまたはopenBDが一時的または恒久的に停止する可能性がある。

### 影響

書誌情報の自動取得ができない。

### 対策

* 複数取得元を使用する。
* 一部Client失敗時も処理を継続する。
* 手入力を可能にする。
* 外部取得と既存CRUDを分離する。
* timeoutを設定する。
* 利用者へ再試行または手入力を案内する。

---

## 29.4 利用制限

### リスク

APIのクォータまたはレート制限へ到達する可能性がある。

### 影響

一時的に取得できなくなる。

### 対策

* HTTP 429を専用例外とする。
* 自動連続再試行を行わない。
* 利用者へ時間をおくよう案内する。
* APIキーへ適切な制限を設定する。
* 将来必要ならキャッシュを導入する。
* バルク取得時は別途制御する。

---

## 29.5 APIキー漏えい

### リスク

APIキーがGit、ログ、Fixtureまたは画面へ露出する可能性がある。

### 影響

* 不正利用
* クォータ消費
* 課金
* キー停止
* セキュリティ上の信用低下

### 対策

* 環境変数を使用する。
* ソースコードへ記述しない。
* ログへ出力しない。
* Rawデータへ含めない。
* `.gitignore` を設定する。
* 漏えい時は直ちに無効化する。
* API制限を設定する。

---

## 29.6 誤った書誌情報

### リスク

外部APIの書誌情報自体が誤っている可能性がある。

### 影響

誤ったタイトル、著者、出版社または内容紹介が登録される。

### 対策

* 自動保存しない。
* 利用者確認後に保存する。
* 既存入力がある場合は上書き確認する。
* ISBN一致候補だけを採用する。
* 後順位で先順位を自動上書きしない。
* フォーム反映後も編集可能とする。

---

## 29.7 ISBN一致誤判定

### リスク

検索結果の先頭候補や類似書籍を誤採用する可能性がある。

### 対策

* `industryIdentifiers` を確認する。
* ISBN-10とISBN-13を正規化して比較する。
* 一致候補がなければ対象なしとする。
* タイトル類似だけで採用しない。
* 複数候補Fixtureをテストする。

---

## 29.8 著者名表記ゆれ

### リスク

取得元により、著者名の区切り、生没年、役割、姓名順が異なる。

### 影響

* 重複著者
* 検索精度低下
* マスタ照合困難
* 表示不統一

### 対策

* 第1段階では過度な正規化をしない。
* 取得元間で著者名を連結しない。
* 原文を利用者が修正可能にする。
* 将来の著者マスタで正規化する。
* Rawデータを一時的に参照可能とする。

---

## 29.9 出版形態の誤判定

### リスク

API分類を文庫、単行本、電子書籍へ誤変換する可能性がある。

### 対策

* 確実な規則がある場合だけ設定する。
* `printType` だけで判定しない。
* 判型だけで文庫と判断しない。
* 不明な場合は `None` とする。
* GUIの現在値を維持する。
* 利用者が手動選択できる。

---

## 29.10 GUI停止

### リスク

同期HTTP通信中にGUIが一時的に応答しにくくなる。

### 影響

利用者がフリーズと誤認する可能性がある。

### 対策

* timeoutを設定する。
* 取得ボタンを無効化する。
* 待機状態を表示する。
* Client数を必要最小限とする。
* 自動リトライを行わない。
* 実測で問題があれば非同期化する。

---

## 29.11 二重実行

### リスク

取得ボタンの連打により、同じ処理が複数回実行される。

### 影響

* 複数通信
* 結果競合
* ダイアログ重複
* 利用制限消費

### 対策

* 取得開始時にボタンを無効化する。
* `finally` で必ず復旧する。
* 将来の非同期化時は処理中フラグも検討する。

---

## 29.12 既存値の消失

### リスク

取得できなかった項目を空文字列で反映し、利用者入力を消去する可能性がある。

### 対策

* 空文字列を `None` へ正規化する。
* `None` はGUIへ反映しない。
* 対象項目だけ個別更新する。
* フォーム全体を初期化しない。
* GUI反映テストを追加する。

---

## 29.13 既存CRUDへの影響

### リスク

外部機能の初期化や設定エラーにより、既存の登録、検索、更新または削除が利用できなくなる。

### 対策

* 外部取得と `BookService` を分離する。
* Client設定失敗を局所化する。
* 取得ボタンだけを無効化できる構成にする。
* 外部API障害時もアプリを起動する。
* 既存CRUDの回帰テストを行う。

---

## 29.14 ログ肥大化

### リスク

Rawレスポンスや内容紹介全文をログへ記録し、ファイル容量が増加する。

### 対策

* Rawレスポンス全文を通常ログへ出力しない。
* 内容紹介全文を記録しない。
* ローテーションを使用する。
* DEBUGログを本番で常時有効にしない。
* 必要な項目だけを構造化して記録する。

---

## 29.15 テストの不安定化

### リスク

実APIへ依存するテストが、外部要因で失敗する。

### 対策

* 自動テストではFakeとFixtureを使用する。
* 実API確認を手動テストへ分離する。
* Fixtureを最小化する。
* 環境変数に依存しないテストを作る。
* 時刻やネットワークへ依存しない。

---

## 29.16 過剰設計

### リスク

将来拡張を想定しすぎて、初期実装が複雑になる。

### 影響

* 実装遅延
* テスト増大
* 理解困難
* 不要な抽象化
* 変更しにくい構造

### 対策

* 第1段階の要件を固定する。
* Protocolと依存注入に限定する。
* 基底Clientクラスを先行導入しない。
* キャッシュや非同期化を実装しない。
* 実際の重複を確認してから共通化する。
* YAGNIを意識する。

---

## 29.17 設計書と実装の乖離

### リスク

実装変更が文書へ反映されず、将来の保守判断を誤る。

### 対策

* 実装変更時に設計書を更新する。
* 重要な変更はADRへ記録する。
* コードレビューで設計書との差異を確認する。
* Revision historyを更新する。
* 完了条件へ文書整合性を含める。

---

# 30. 設計判断記録

## 30.1 目的

本章では、本機能で採用した主要な設計判断と、その理由を一覧化する。

詳細な検討が必要な判断は、必要に応じてADRへ分離する。

---

## 30.2 `requests` の採用

### 判断

HTTP通信には `requests` を使用する。

### 理由

* 可読性が高い。
* Session注入が容易である。
* timeoutを明示できる。
* 例外体系が分かりやすい。
* FakeまたはMockによるテストが容易である。
* プロジェクト規模に適している。

---

## 30.3 Session注入

### 判断

各Clientは、外部から `requests.Session` を受け取る。

### 理由

* テストで差し替えられる。
* 接続を再利用できる。
* Client内の暗黙依存を減らせる。
* 共通ヘッダーを管理できる。
* 将来の通信設定変更に対応しやすい。

---

## 30.4 timeout `(5, 10)`

### 判断

HTTP timeoutは、接続5秒、読み取り10秒とする。

### 理由

* 無制限待機を防止できる。
* デスクトップGUIとして極端に長い待機を避けられる。
* 接続と読み取りを分けて制御できる。
* 初期値として理解しやすい。
* 将来必要に応じて注入値を変更できる。

---

## 30.5 Protocolの採用

### 判断

Client共通契約には継承基底クラスではなく `Protocol` を使用する。

### 理由

* 実装継承を強制しない。
* APIごとの差異を維持できる。
* Fake Clientを作りやすい。
* Serviceが具象Clientに依存しない。
* 構造的部分型を利用できる。
* 過剰な共通基底実装を避けられる。

---

## 30.6 Google Books優先

### 判断

Google Booksを第1取得元とする。

### 理由

* 当初の主要取得元として想定している。
* 書籍名、著者名、内容紹介、表紙画像などを取得できる。
* APIキーを利用した管理が可能である。
* 複数候補検索とISBN照合ができる。
* 既存の取得試験で利用実績がある。

---

## 30.7 openBDを補完元とする

### 判断

openBDを第2取得元とし、空欄補完に使用する。

### 理由

* 国内書籍情報を取得できる。
* Google Booksで不足する出版社や出版日などを補完できる可能性がある。
* 複数取得元によって可用性を高められる。
* openBD固有形式をClientへ隔離できる。

---

## 30.8 後順位による上書き禁止

### 判断

後順位Clientは、先順位の空欄だけを補完する。

### 理由

* 統合結果が予測可能になる。
* 取得元間の競合を推測で解決しなくてよい。
* テスト規則が単純になる。
* 優先順位が明確になる。
* 利用者が最終的に修正できる。

---

## 30.9 `FetchedBookData` の採用

### 判断

外部取得結果専用モデルとして `FetchedBookData` を使用する。

### 理由

* `BookItem` と一時取得データの責務が異なる。
* DB非保存項目を扱える。
* Rawデータと取得元を保持できる。
* API固有JSONを上位層へ渡さずに済む。
* 保存前データであることを明確にできる。

---

## 30.10 Rawレスポンス非保存

### 判断

Rawレスポンスは一時保持できるが、SQLiteへ保存しない。

### 理由

* データ量が増える。
* API仕様へDBが依存する。
* 秘密情報混入リスクがある。
* 通常利用では不要である。
* 必要時はFixtureやログ設計で調査できる。
* 正式な書籍データと目的が異なる。

---

## 30.11 出版日非保存

### 判断

出版日は外部取得モデルへ保持するが、第1段階ではDBへ保存しない。

### 理由

* 既存DB項目に含まれていない。
* APIごとに日付精度と形式が異なる。
* 正規化規則が確定していない。
* DB変更とMigrationが必要になる。
* 第1段階の主要要件ではない。

---

## 30.12 表紙画像非表示・非保存

### 判断

表紙画像URLは取得できるが、第1段階ではGUI表示およびDB保存を行わない。

### 理由

* 画像通信と書誌通信の責務が異なる。
* Pillowなど追加依存が必要になる可能性がある。
* キャッシュ、サイズ制限、画像エラーの設計が必要である。
* 初期要件を超える。
* URLだけは将来調査用として保持できる。

---

## 30.13 同期処理

### 判断

第1段階ではHTTP通信を同期処理とする。

### 理由

* 実装が単純である。
* 例外処理が分かりやすい。
* Tkinterのスレッド制約を避けられる。
* 初期要件とClient数では許容可能と想定する。
* timeoutで無制限待機を防止できる。
* 必要性を確認してから非同期化できる。

---

## 30.14 自動リトライ非採用

### 判断

第1段階では自動リトライを行わない。

### 理由

* GUI待機時間が増える。
* HTTP 429への不適切な再試行を避けられる。
* API負荷を抑えられる。
* テストと挙動が単純になる。
* 利用者による再実行で対応できる。

---

## 30.15 APIキーの環境変数管理

### 判断

Google Books APIキーは環境変数から受け取る。

### 理由

* Gitへの誤登録を防ぎやすい。
* 実行環境ごとに変更できる。
* Clientへ注入できる。
* テストで無効な値を使用できる。
* ソースコードと秘密情報を分離できる。

---

## 30.16 自動保存禁止

### 判断

外部取得成功後も、DBへ自動保存しない。

### 理由

* 外部情報が誤っている可能性がある。
* 利用者管理項目を補う必要がある。
* 取得結果を修正できる。
* 既存登録・更新フローを再利用できる。
* 外部取得を入力補助として位置づけられる。

---

## 30.17 ISBN-10入力の維持

### 判断

ISBN-10を入力した場合、外部問い合わせではISBN-13へ変換するが、最終的な入力値はISBN-10を維持する。

### 理由

* 利用者の入力意図を維持できる。
* 問い合わせ用識別子と保存候補を分離できる。
* 取得操作だけでフォーム値を無断変更しない。
* 既存のISBN管理方針への影響を抑えられる。

---

## 30.18 Client全件呼び出し

### 判断

第1段階では、Google Booksで値を取得できてもopenBDを呼び出す。

### 理由

* 空欄補完を確実に行える。
* 項目不足判定を複雑化しない。
* 動作が一貫する。
* Serviceテストが単純になる。
* 初期Client数が少ない。

将来、通信量や応答時間が問題になった場合は最適化を検討する。

---

# 31. 未決事項

## 31.1 目的

本章では、実装開始前または実装中に最終決定が必要な事項を整理する。

未決事項は、曖昧なままコードへ埋め込まず、取得試験、既存実装および運用条件を確認して決定する。

---

## 31.2 Google Books APIキー未設定時

次のいずれかを決定する必要がある。

* キーなしでGoogle Booksを利用する。
* Google Books Clientを登録しない。
* 設定エラーとして取得機能を停止する。

推奨判断は、実APIの利用条件とキーなし取得試験を確認して行う。

既存CRUDは停止しない。

---

## 31.3 Google Booksの副題

`volumeInfo.subtitle` を書籍名へ結合するかを決定する必要がある。

候補は次のとおりである。

```text
titleのみ
```

```text
title: subtitle
```

既存データの書籍名表記との整合性と、実レスポンスの重複傾向を確認する。

---

## 31.4 openBDの内容紹介取得元

openBD内のどの項目を内容紹介として採用するか、実レスポンスと仕様を確認して決定する。

確認対象は次のとおりである。

* `hanmoto`
* ONIXのCollateralDetail
* TextContent
* TextType
* ContentAudience
* HTML含有
* 複数候補の優先順位

意味が不明な項目は採用しない。

---

## 31.5 HTML除去方法

内容紹介にHTMLが含まれる場合の処理を決定する。

候補は次のとおりである。

* タグをそのままプレーン文字として表示する。
* 標準ライブラリで除去する。
* 専用ライブラリを追加する。
* 主要タグだけ改行へ変換する。

実レスポンス上の頻度と内容を確認してから決定する。

---

## 31.6 出版形態の取得

Google BooksおよびopenBDから、既存出版形態へ確実に変換できるかを確認する。

確実な規則を定義できない場合は、すべて `None` とする。

推測による自動設定は行わない。

---

## 31.7 例外属性

例外クラスに次の属性を持たせるかを実装時に決定する。

* `source_name`
* `status_code`
* `retry_after`
* `isbn`

初期実装で利用しない属性を先行追加しない。

---

## 31.8 GUIボタン文言

次の候補から、既存GUI文言に合うものを選択する。

```text
ISBNから取得
書籍情報取得
書誌情報取得
```

利用者が機能を理解しやすいことを優先する。

---

## 31.9 成功時の取得元表示

成功時に取得元を常時ステータスバーへ表示するかを決定する。

候補は次のとおりである。

```text
書籍情報を取得しました。
```

```text
書籍情報を取得しました。取得元: Google Books、openBD
```

通常利用者に必要な情報量と画面幅を考慮する。

---

## 31.10 Sessionの終了管理

Sessionをどのクラスまたは起動処理が所有し、終了時に閉じるかを既存アプリケーションのライフサイクルに合わせて決定する。

候補は次のとおりである。

* `main.py`
* アプリケーションコンテナ
* GUI終了ハンドラ
* Context管理クラス

Client自身が共有Sessionを勝手に閉じない。

---

## 31.11 想定外例外のGUI捕捉

GUIで最終的な `Exception` を捕捉する範囲を決定する。

利用者向けアプリとして異常終了を防ぐ必要がある一方、開発時に不具合を隠さない設計とする。

候補は次のとおりである。

* ログへ `logger.exception()` を記録して一般エラーを表示する。
* 開発モードでは再送出する。
* 本番モードだけ一般エラーへ変換する。

---

## 31.12 `FetchedBookData.raw_data` の保持

Rawデータを常に保持するか、開発時だけ保持するかを決定する。

常時保持する場合でもDBへ保存しない。

レスポンスサイズとデバッグ価値を実測して判断する。

---

## 31.13 未決事項の解消手順

未決事項は次の手順で解消する。

1. 実APIまたは既存コードを確認する。
2. 選択肢を整理する。
3. 既存設計方針との整合性を確認する。
4. テスト可能性を確認する。
5. Design Freezeする。
6. 本設計書を更新する。
7. 必要に応じてADRを作成する。
8. 実装とテストへ反映する。

---

# 32. 完了後の保守方針

## 32.1 目的

外部書誌情報取得機能の実装完了後も、API仕様、依存ライブラリおよび利用環境の変化に対応できる保守方針を定める。

---

## 32.2 障害発生時

取得障害が報告された場合は、次の順序で確認する。

1. 入力ISBNが有効か。
2. 一方または両方の取得元で再現するか。
3. HTTPステータスは何か。
4. JSON解析に失敗しているか。
5. ISBN一致候補が存在するか。
6. API仕様が変更されていないか。
7. APIキーまたは利用制限に問題がないか。
8. 同じ条件をFixtureで再現できるか。

---

## 32.3 不具合修正

不具合を修正する場合は、原則として次を行う。

1. 再現条件を特定する。
2. 最小Fixtureを作成する。
3. 失敗するテストを追加する。
4. 責務を壊さない範囲で修正する。
5. 全テストを実行する。
6. 既存CRUDを回帰確認する。
7. 必要に応じて設計書を更新する。
8. 1テーマのコミットとして記録する。

---

## 32.4 API仕様確認

外部APIの仕様は定期的または障害時に確認する。

確認対象は次のとおりである。

* エンドポイント
* 認証方式
* 利用制限
* レスポンス構造
* 利用規約
* 廃止予定
* HTTPS要件
* APIキー制限
* エラー形式

仕様確認日をドキュメントへ残すことを検討する。

---

## 32.5 Fixture更新

API仕様変更に対応してFixtureを更新する場合は、既存ケースを無条件に置き換えない。

旧形式を引き続き受け入れる必要がある場合は、旧Fixtureと新Fixtureを両方残す。

Fixture名から形式差が分かるようにする。

---

## 32.6 依存ライブラリ更新

`requests`、pytestまたはPythonを更新する場合は、外部取得機能の全テストを実行する。

特に次を確認する。

* Session Mock
* timeout例外
* HTTPError
* JSON解析例外
* 型ヒント
* macOS
* Windows

---

## 32.7 ログの確認

運用中に次の傾向を確認できる。

* 特定Clientの失敗増加
* HTTP 429増加
* 対象なし増加
* レスポンス解析失敗
* 平均処理時間の増加
* 特定ISBN形式の問題

ただし、個人利用アプリで過度な監視基盤を導入しない。

---

## 32.8 Client追加時

新しい取得元を追加する場合は、次を実施する。

1. API仕様と利用条件を確認する。
2. Client責務を定義する。
3. Protocolへ適合させる。
4. 共通例外へ変換する。
5. Fixtureを作成する。
6. Client単体テストを追加する。
7. Service統合テストを追加する。
8. 優先順位を決定する。
9. 設計書を更新する。
10. 必要ならADRを作成する。

---

## 32.9 機能削除時

外部取得元が廃止された場合は、Client登録から除外する。

Service、GUI、RepositoryおよびDBを大幅変更せずに削除できることが望ましい。

不要になったClient、Fixture、設定およびドキュメントを同じ変更内で整理する。

---

## 32.10 ドキュメント更新

次の場合は、本設計書を更新する。

* API追加または削除
* 優先順位変更
* 統合規則変更
* DB保存項目追加
* 非同期化
* キャッシュ導入
* APIキー管理変更
* 例外体系変更
* GUI操作変更
* 対象範囲変更

---

# 33. まとめ

## 33.1 設計の要点

外部書誌情報取得機能は、ISBNを基にGoogle BooksとopenBDから書誌情報を取得し、利用者の入力作業を支援する。

本設計の中心となる方針は次のとおりである。

* Google Booksを第1取得元とする。
* openBDを第2取得元とする。
* 後順位は空欄だけを補完する。
* Client共通契約にはProtocolを使用する。
* HTTP通信には `requests.Session` を使用する。
* timeoutは `(5, 10)` とする。
* ClientはAPI固有レスポンスを `FetchedBookData` へ変換する。
* `FetchedBookData` と `BookItem` を分離する。
* Serviceは複数Clientの制御と統合を担当する。
* GUIは取得結果の確認とフォーム反映を担当する。
* Repositoryは外部APIを認識しない。
* 外部取得後に自動保存しない。
* APIキーは環境変数から注入する。
* HTTP 429は専用例外とする。
* 自動テストでは実APIへ接続しない。

---

## 33.2 責務分離

最終的な依存関係は次のとおりである。

```text
GUI
 │
 ▼
BookMetadataService
 │
 ▼
BookMetadataClient Protocol
 ├─ GoogleBooksClient
 └─ OpenBdClient
 │
 ▼
FetchedBookData
```

保存処理は、外部取得経路から分離する。

```text
GUI
 │
 ▼
BookService
 │
 ▼
Repository
 │
 ▼
SQLite
```

二つのServiceは、異なるユースケースを担当する。

---

## 33.3 第1段階の範囲

第1段階で実装する範囲は次のとおりである。

* ISBN-10およびISBN-13の正規化と検証
* ISBN-10からISBN-13への問い合わせ用変換
* Google Booksからの取得
* openBDからの取得
* 空欄補完による統合
* GUIフォームへの反映
* 上書き確認
* エラー通知
* Session注入
* APIキー環境変数管理
* FakeとFixtureによる自動テスト

---

## 33.4 第1段階の対象外

次は将来拡張とする。

* 書籍名検索
* 著者名検索
* 雑誌コード検索
* 表紙画像表示
* 表紙画像保存
* 出版日のDB保存
* 外部取得キャッシュ
* 非同期処理
* 自動リトライ
* バルク取得
* 著者名の完全正規化
* 取得元間の候補選択画面

---

## 33.5 完了後の状態

本設計どおりに実装した場合、利用者は次の操作を行える。

1. ISBNを入力する。
2. 取得ボタンを押す。
3. Google BooksとopenBDから書誌情報を取得する。
4. Google Booksの不足項目をopenBDで補完する。
5. 取得結果をフォーム上で確認する。
6. 必要な内容を修正する。
7. 読了年月や備考を入力する。
8. 既存の登録または更新操作で保存する。

外部サービスが利用できない場合でも、従来どおり手入力と既存CRUDを利用できる。

---

## 33.6 最終方針

外部書誌情報は、正解を保証するデータではなく、利用者の入力を支援する候補情報として扱う。

取得の自動化よりも、次を優先する。

* データの安全性
* 利用者による確認
* 既存機能の継続利用
* 責務の明確さ
* テスト可能性
* 将来の変更容易性

この方針を維持し、必要な機能を段階的に追加する。

---

# 付録A. 主要インターフェース一覧

## A.1 `BookMetadataClient`

```python
from typing import Protocol

from book_manager.models.fetched_book_data import (
    FetchedBookData,
)


class BookMetadataClient(Protocol):
    @property
    def source_name(self) -> str:
        ...

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        ...
```

---

## A.2 `BookMetadataService`

```python
class BookMetadataService:
    def __init__(
        self,
        clients: list[BookMetadataClient],
    ) -> None:
        ...

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData:
        ...
```

---

## A.3 `GoogleBooksClient`

```python
class GoogleBooksClient:
    def __init__(
        self,
        session: requests.Session,
        api_key: str | None = None,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        ...

    @property
    def source_name(self) -> str:
        ...

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        ...
```

---

## A.4 `OpenBdClient`

```python
class OpenBdClient:
    def __init__(
        self,
        session: requests.Session,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        ...

    @property
    def source_name(self) -> str:
        ...

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        ...
```

---

## A.5 `FetchedBookData`

```python
@dataclass(slots=True)
class FetchedBookData:
    isbn: str
    title: str | None = None
    authors: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    publication_format: str | None = None
    description: str | None = None
    cover_image_url: str | None = None
    sources: tuple[str, ...] = ()
    raw_data: dict[str, Any] = field(
        default_factory=dict,
    )
```

---

# 付録B. 主要設定値

| 設定            | 値                    |
| :------------ | :------------------- |
| 第1取得元         | Google Books         |
| 第2取得元         | openBD               |
| 統合方式          | 先順位優先、空欄補完           |
| HTTPライブラリ     | requests             |
| 接続timeout     | 5秒                   |
| 読み取りtimeout   | 10秒                  |
| 自動リトライ        | 行わない                 |
| HTTP 429      | 専用例外                 |
| APIキー管理       | 環境変数                 |
| 環境変数名         | GOOGLE_BOOKS_API_KEY |
| 外部取得後の自動保存    | 行わない                 |
| RawレスポンスのDB保存 | 行わない                 |
| 出版日のDB保存      | 行わない                 |
| 表紙画像表示        | 行わない                 |
| 表紙画像保存        | 行わない                 |
| 通信方式          | 第1段階では同期処理           |
| 自動テストの実API通信  | 行わない                 |

---

# 付録C. 例外一覧

| 例外                             | 用途               |
| :----------------------------- | :--------------- |
| BookMetadataError              | 外部書誌情報取得例外の基底    |
| BookMetadataConnectionError    | 接続失敗、timeout     |
| BookMetadataResponseError      | HTTP異常、JSON・構造不正 |
| BookMetadataRateLimitError     | HTTP 429、利用制限    |
| BookMetadataNotFoundError      | 全取得元で対象なし        |
| BookMetadataConfigurationError | 設定不備             |
| InvalidIsbnErrorまたはValueError  | ISBN入力不正         |

---

# 付録D. Revision History

| 版     | 日付         | 変更内容               |
| :---- | :--------- | :----------------- |
| 0.1.0 | YYYY-MM-DD | 外部書誌情報取得機能の初版設計を作成 |
