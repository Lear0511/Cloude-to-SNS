# Cloude-to-SNS — プロジェクト前提条件

株式会社Ritz Solution Partner の SNS 投稿を、Claude で生成して予約投稿するためのリポジトリ。
第1弾は Instagram（`instagram/`）。SNS が増えたらディレクトリを並べて足す。

## 構成

- `instagram/` — 3ブランドの Instagram 投稿ワークフロー（生成プロンプト・検証・予約投稿用の変換）。手順の正本は [`instagram/README.md`](instagram/README.md)
- `SETUP.md` — macOS でのセットアップ手順（clone から初回実行まで）
- `README.md` — リポジトリの入口

## 対象ブランド

事実データは **[Lear0511/Riuz-base](https://github.com/Lear0511/Riuz-base) の brand-kit のみ**を出典にする。
作業前に `/brand-kit` スキルを呼び、対象ブランドの前提条件をロードすること。

| ブランド | 種別 | プライマリカラー | トーン |
|---|---|---|---|
| ブランドリッツ | BtoC 買取・販売 | `#E96081`（ローズ） | 誠実で親しみやすい。価値・信頼・利便性 |
| ネクストプラチナム | BtoB 貴金属卸・買取 | `#CB3B08`（バーミリオン） | 専門的・革新志向。専門家同士の対等な語り口 |
| 色石マーケット | BtoB 色石の業者間卸・仕入 | `#B14242`（ディープレッド） | 専門的・安心感重視。数字と根拠で語る |

コーポレート共通のタグラインは「人から人へ渡る喜びを」。

## ルール

### 事実を創作しない

住所・数値・人名・許可番号・実績・アカウント名は brand-kit に載っているものだけを使う。
新しい事実が要るときは **brand-kit 側を更新してから**使う。投稿の中で作らない。

**ネクストプラチナムと色石マーケットの Instagram アカウントは brand-kit に記載が無い。**
`instagram/accounts.json` の `handle` / `url` は `null` のままにしてあり、検証で WARN が出る。
実アカウントを確認するまで**推測で埋めない**（WARN が出続けるのは意図した挙動）。

### 前提条件の台帳は1本だけ

`instagram/accounts.json` がトーン・取扱品目・投稿の型・ハッシュタグ・法定表記・NG表現・配色の正本。
生成プロンプトはここから組み立てるので、**同じ情報を別ファイルに書き写さない**。
プロンプトの雛形を直すときは `instagram/build-posts.py` の `PROMPT` を編集する
（`instagram/prompt-template.md` は読む用の写しなので、直したら同じコマンドで貼り直す）。

### 取扱外品目のリストは紙面リポジトリと共有する

`accounts.json` の `common.out_of_scope_items` は、競合デイリー紙面リポジトリ
[Lear0511/Riuz-newspoper](https://github.com/Lear0511/Riuz-newspoper) の `CLAUDE.md`「掲載範囲」および
`riuz-daily/rebuild-log.py` の `NG` と同じ線引き。**新しい対象外品目が出たら両方に足す。**

対象外: 衣類・古着・アパレル／PC・スマホ・タブレット・携帯電話／ゲーム・ホビー・フィギュア／
トレカ・古本／家電・家具／車・バイク用品／楽器（和楽器を含む）。

### ブランドをまたいで混ぜない

配色もトーンも、対象ブランドを特定してから選ぶ。BtoC（ブランドリッツ）は親しみやすく安心感、
BtoB（ネクストプラチナム・色石マーケット）は専門家同士の対等な語り口。

### Instagram Graph API は使わない

アカウント停止リスクを避け、公開前に必ず目視を挟むため。
**予約投稿は Meta Business Suite で行う**（2026-08-28 オーナー判断・無料。Buffer / Later / Hootsuite は不採用。
将来の乗り換えの可能性は残す）。

**Meta Business Suite には1件目のコメントを自動投稿する機能が無い。**
そのため `hashtag_placement` の既定は `first_comment` から **`caption`**（キャプション本文）へ変更した。
`first_comment` を指定した投稿は検証で WARN が出て、公開後に人が手でコメントを入れる運用になる。

Meta Business Suite で扱うには、Instagram がプロアカウント（ビジネス／クリエイター）で、
Facebook ページと連携されている必要がある。ネクストプラチナムと色石マーケットは実アカウントが未確認のため、
**運用開始前にアカウントの特定とプロアカウント化・ページ連携の確認が要る**（手順は `SETUP.md`）。
管理画面の細かい仕様（予約できる期間・件数の上限、カルーセルの最大枚数、alt の設定場所など）は
**未確認なので推測で書かない。** 必要なら実機で確認してから書く。

### 生成物をコミットして残す

`instagram/posts/` の投稿バッチと `instagram/out/` の生成物は、いつ何を出したかの記録になる。
`.gitignore` に入れない。

## 発行の手順

```shell
python3 instagram/build-posts.py --prompt brand-ritz --count 4   # 生成プロンプトを出す
python3 instagram/build-posts.py                                  # 全バッチを検証して変換
python3 instagram/build-posts.py --strict                         # WARN もエラー扱い（PR前）
```

**ERROR があるバッチは出力されない。** 直してから再実行する。
**`hashtag_placement` に `first_comment` を指定すると WARN が出る**（Meta Business Suite が1件目のコメントを自動投稿できないため。既定は `caption`）。
検証で落とすもの: キャプション2,200字／ハッシュタグ30個・重複・`#`始まり／カルーセル2〜20枚／
alt必須／`publish_at` の書式・過去日／断定・優良誤認のNG表現／取扱外品目への言及。

ブランド公式のキャッチコピーがNG語に当たる場合は `accounts.json` の `ng_allow` で個別解除する
（例: ネクストプラチナムの「どこよりも高くお買取致します」）。

## ドキュメントの書き方

**手順の説明文とコマンドを同じコードブロックに入れない。** 番号付きの流れをコードブロックで書いたところ、
利用者が全行をターミナルに貼って `zsh: command not found: 1.` になった実例がある。
流れは表で書き、**実際に打つ行だけ**を `shell` のコードブロックに入れること。

## 関連リポジトリ

| リポジトリ | 用途 |
|---|---|
| [Lear0511/Riuz-base](https://github.com/Lear0511/Riuz-base) | ブランドキット。事実データの唯一の出典 |
| [Lear0511/Riuz-newspoper](https://github.com/Lear0511/Riuz-newspoper) | 競合デイリー紙面。取扱外品目の線引きを共有 |
