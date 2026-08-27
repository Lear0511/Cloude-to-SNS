# Instagram 投稿ワークフロー ── ブランドリッツ／ネクストプラチナム／色石マーケット

Instagram Graph API を使わず、**Web版 Claude で投稿案をつくり、SNS管理ツール（または Meta Business Suite）へ流し込んで予約投稿する**運用の実装。

API 連携を持たないぶんアカウント停止のリスクが小さく、公開前に人の目を必ず1回通せる。
そのかわり「生成した案が前提条件どおりか」を人が全部読むのは現実的でないので、
**機械でチェックできるところは `build-posts.py` が落とす**という分担にしている。

適用した前提条件: brand-kit ── Brand Ritz(BtoC)／Next Platinum(BtoB)／色石マーケット(BtoB)

## 対象アカウント

| ブランド | 種別 | アカウント | 投稿頻度の目安 |
|---|---|---|---|
| ブランドリッツ | BtoC | [@brand_ritz](https://www.instagram.com/brand_ritz/)（本体）／[@brandritzbuy](https://www.instagram.com/brandritzbuy/)（買取）／[@brandritzrokko](https://www.instagram.com/brandritzrokko/)（六甲道店） | 週4本 19:00 |
| ネクストプラチナム | BtoB | **未設定** | 週2本 12:00 |
| 色石マーケット | BtoB | **未設定** | 週2本 12:00 |

ネクストプラチナムと色石マーケットの Instagram は brand-kit に記載が無い。
**実アカウントを確認して `accounts.json` の `handle` / `url` を埋めるまで、この2ブランドは検証時に WARN が出続ける**（推測で埋めないこと）。

## 全体の流れ

| # | やること | 手 |
|---|---|---|
| 1 | プロンプトを出す（`accounts.json` の前提条件が埋まった本文が出る） | コマンド |
| 2 | Web版 Claude に貼り、返ってきた JSON を `posts/` に保存 | 手作業 |
| 3 | 検証して変換（`out/` に チェックシート・CSV・キャプション） | コマンド |
| 4 | `out/*-review.md` のチェックボックスを人が通す | 手作業 |
| 5 | 「画像の指示」どおりに画像を作り、`media` 欄に記入 | 手作業 |
| 6 | Meta Business Suite / Buffer / Later / Hootsuite へ流し込む | 手作業 |

**ターミナルで打つのは 1 と 3 の2つだけ。** 残りは人の作業なので貼り付けても動かない。

```shell
python3 instagram/build-posts.py --prompt brand-ritz --count 4   # 手順1
python3 instagram/build-posts.py                                  # 手順3
```

## 1. プロンプトを出す

```shell
python3 instagram/build-posts.py --prompt brand-ritz --count 4 --start 2026-09-01
python3 instagram/build-posts.py --prompt next-platinum --count 2
python3 instagram/build-posts.py --prompt iroishi-market --count 2
```

`accounts.json` の該当ブランドの前提条件（トーン・取扱品目・投稿の型・ハッシュタグ・法定表記・NG表現）を
そのまま埋め込んだ本文が標準出力に出る。**これをコピーして Web版 Claude に貼る。**

`--start` を省略すると翌日始まり。日付は隔日で振られるので、曜日は運用側で調整してよい。

プロンプトの雛形そのものを直したいときは `build-posts.py` の `PROMPT` を編集する。
中身を読むだけなら [prompt-template.md](prompt-template.md) に同じものを置いてある。

## 2. Web版 Claude で生成する

返ってきた JSON を `instagram/posts/<日付>-<account>.json` として保存する。
形式は [posts/2026-09-01-brand-ritz.json](posts/2026-09-01-brand-ritz.json) を見本にする。

| キー | 内容 |
|---|---|
| `account` | `brand-ritz` / `next-platinum` / `iroishi-market` |
| `posts[].type` | `carousel` / `single` / `reel` |
| `posts[].publish_at` | `YYYY-MM-DD HH:MM`（**JST**） |
| `posts[].slides[]` | 1枚ごとの `headline` / `body` / `alt`。画像制作の指示書になる |
| `posts[].caption` | キャプション本文。1文ずつ改行する |
| `posts[].hashtag_placement` | `first_comment`（既定）または `caption` |
| `posts[].hashtags` | `#` 始まりの配列 |
| `posts[].media` | 画像ができたらファイル名やURLを入れる（CSVに出る） |
| `posts[].allow` | どうしても必要な語だけ、NG判定を個別に解除する逃げ道 |

## 3. 検証する

```shell
python3 instagram/build-posts.py            # posts/*.json を全部
python3 instagram/build-posts.py --strict   # WARN もエラー扱い（PR前）
```

**ERROR が1件でもあるバッチは出力しない。** 直してから再実行する。

| チェック | 種別 |
|---|---|
| キャプション 2,200字以内 | ERROR |
| ハッシュタグ 30個以内・`#`始まり・重複なし | ERROR |
| カルーセル 2〜20枚 / single は1枚 | ERROR |
| 各スライドに見出しと alt（代替テキスト）がある | ERROR |
| `publish_at` が `YYYY-MM-DD HH:MM` で読める | ERROR |
| NG表現（断定・優良誤認）が無い | ERROR |
| 当社の取扱外品目に触れていない | ERROR |
| `publish_at` が未来 / 同時刻の重複が無い | WARN |
| 固定ハッシュタグが入っている | WARN |
| 見出しが20字以内・alt が100字以内 | WARN |
| アカウントの handle が設定済み | WARN |

NG表現と取扱外品目のリストは `accounts.json` の `common` にある。
**取扱外品目は競合デイリー紙面リポジトリ [Lear0511/Riuz-newspoper](https://github.com/Lear0511/Riuz-newspoper) の `CLAUDE.md`「掲載範囲 ── ブランドリッツの取扱品目に関わる動きだけ」と同じ判定**にしてあり、紙面と投稿で線引きが揃う。新しい品目が出たら、本リポジトリの `accounts.json` と紙面リポジトリ側（`CLAUDE.md` および `riuz-daily/rebuild-log.py` の `NG`）の両方に足す。

ブランド公式のキャッチコピーが NG語に当たる場合は `accounts.json` の `ng_allow` で解除する
（例: ネクストプラチナムの「どこよりも高くお買取致します」）。

### 出力されるもの

| ファイル | 用途 |
|---|---|
| `out/<batch>-review.md` | **目視チェックシート。** 承認者はこれだけ見れば足りる |
| `out/<batch>-schedule.csv` | 予約投稿ツールへの取り込み用。1投稿1行 |
| `out/<batch>-captions/NN-slug.txt` | キャプション全文。手貼りするときはこれをコピー |

## 4. 目視チェック

`out/<batch>-review.md` を開き、投稿ごとに3つのチェックを人が通す。

- 事実（店舗名・品目・条件・許可番号）が brand-kit と一致している
- 断定・煽り表現が無い／当社の取扱品目だけを書いている
- 画像とキャプションの組み合わせが正しい（別投稿の取り違えが無い）

3つ目は機械では見られない。**このワークフローで誤投稿が起きるとしたらここ**なので、
画像を作ったあとにもう一度見る。

## 5. 画像をつくる

`review.md` の「画像の指示」表がそのまま制作指示になる（枚数・見出し・本文・alt）。
配色はブランドごとに `accounts.json` の `colors` を使い、**混ぜない**。

| ブランド | プライマリ | 併用 |
|---|---|---|
| ブランドリッツ | `#E96081` | `#F5B32D` / `#3B82C5` / 背景 `#DFEFF8` |
| ネクストプラチナム | `#CB3B08` | `#2BB5B5` / `#9B833C` |
| 色石マーケット | `#B14242` | `#E5E551` |

できた画像は `posts/*.json` の `media` に記入して `build-posts.py` を再実行すると、CSVに載る。

## 6. 予約投稿ツールへ流し込む

### 共通の注意

`out/<batch>-schedule.csv` の列はこの順。

```
publish_at_jst, account, handle, type, theme, caption, first_comment, media, alt_texts, slide_count
```

**一括取り込みのCSV仕様はツールとプランで変わる。** 各ツールのヘルプは外部から参照できなかったため、ここでは列名を検証していない。
初回だけ、使うツールの取り込み画面から**テンプレートCSVをダウンロードして列名と日時書式を突き合わせ**、
必要なら列を並べ替えてから読み込むこと。2回目以降は同じ変換を使い回せる。

一括取り込みが使えない（プラン外・Instagram非対応・画像がURLで渡せない等）ときは、
**`out/<batch>-captions/*.txt` を手貼りする**。この経路は確実に動くので、迷ったらこちらでよい。

### Meta Business Suite（推奨・追加費用なし）

1. プランナー → 投稿を作成 → Instagram アカウントを選ぶ
2. 画像をカルーセルの順どおりにアップロードする
3. `captions/NN-slug.txt` の本文をキャプション欄に貼る
4. 画像ごとに `review.md` の alt を代替テキストに入れる
5. `publish_at_jst` の日時で予約する
6. 1件目のコメント（ハッシュタグ）は自動投稿できないため、**公開後に手で入れる**か `hashtag_placement` を `caption` に変えておく

### Buffer / Later / Hootsuite

1. Instagram ビジネスアカウントを接続する（Facebookページとの紐付けが要る）
2. `schedule.csv` を各ツールのテンプレートに合わせて並べ替え、一括取り込みする
3. 取り込み後、**必ずプレビューで日時・画像・本文の対応を目視する**（ここでの取り違えが誤投稿になる）
4. ハッシュタグを1件目のコメントに入れる機能があるツールでは `first_comment` 列をそこへ入れる

## 運用ルール

- **事実は brand-kit だけを出典にする。** 住所・数値・人名・実績・許可番号を創作しない。新しい事実が要るときは brand-kit 側を更新してから使う
- **ブランドをまたいで配色・トーンを混ぜない。** BtoC（ブランドリッツ）は親しみやすく安心感、BtoB（ネクストプラチナム・色石マーケット）は専門家同士の対等な語り口
- **取扱外の品目に触れない。** 衣類・古着・PC・スマホ・ゲーム・トレカ・家電・楽器など（全リストは `accounts.json`）
- **投稿の型を続けて同じにしない。** `accounts.json` の `pillars` から回す
- 生成済みバッチと出力は `posts/` `out/` にコミットして残す。何をいつ出したかの記録になる

## ファイル構成

```
instagram/
├── README.md            この運用フロー
├── accounts.json        3ブランドの前提条件・NG表現・取扱外品目（台帳）
├── prompt-template.md   Web版 Claude に貼るプロンプトの雛形（読む用）
├── build-posts.py       プロンプト生成 / 検証 / 変換
├── posts/               投稿バッチ JSON（Web版 Claude の出力を保存する場所）
└── out/                 生成物（review.md / schedule.csv / captions/）
```
