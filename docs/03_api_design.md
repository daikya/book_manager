# 03 API設計

## 取得順序
1. ローカルキャッシュ
2. openBD
3. Google Books
4. 出版社公式サイト
5. 将来追加する取得元

## 原則
- 取得元ごとに独立モジュール化
- GUIから直接APIを呼ばない
- 共通形式へ変換して統合
- 一つの取得元が失敗しても継続
- Rawデータ、取得日時、HTTP状態を保存
- HTTP 429、タイムアウトを処理
- ユーザー確定値を保護

## 項目別優先例
| 項目 | 優先候補 |
|---|---|
| 書名 | openBD、出版社 |
| 著者 | openBD、出版社 |
| 発売日 | 出版社、openBD |
| 内容紹介 | 出版社、Google Books、openBD |
| ページ数 | 出版社、Google Books |
| 表紙 | 出版社、Google Books、openBD |
