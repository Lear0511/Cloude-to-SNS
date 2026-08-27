# セットアップ手順（macOS）

株式会社Ritz Solution Partner の Instagram 投稿ワークフローを、Mac で動かせるようにするまでの手順です。
上から順にそのまま進めれば動きます。

---

## この手順の読み方（最初に必ず読む）

**打ち込むのは「灰色の枠（コードブロック）の中身だけ」です。**

- 見出し・番号（`1.` `2.`）・矢印（`→`）・表・この地の文は **コマンドではありません**。ターミナルに貼らないでください
- コードブロックは1行につき1コマンドです。**1行コピー → ⌘V で貼る → `return`（Enter）**、を1行ずつ繰り返します
- 行末の `#` から後ろは説明用のコメントです。一緒に貼っても無害ですが、無くても構いません

説明文まで貼ると `zsh: command not found: 1.` のようなエラーになります（下の「困ったときは」参照）。

ターミナルは Finder の「アプリケーション」→「ユーティリティ」→「ターミナル.app」で開きます。

---

## 1. 前提を確認する

必要なのは **Python 3** と **git** の2つだけです。追加のライブラリのインストールは不要で、Python の標準ライブラリだけで動きます（`pip install` は要りません）。

まず Python 3 が入っているか確認します。

```
python3 -V
```

`Python 3.x.x` のようにバージョンが表示されれば OK です。

次に git を確認します。

```
git --version
```

`git version 2.x.x` のように表示されれば OK です。

どちらかが `command not found` になった場合、または「コマンドライン・デベロッパツールが必要です」というダイアログが出た場合は、macOS の Xcode Command Line Tools を入れます。

```
xcode-select --install
```

画面にインストーラのダイアログが出るので、「インストール」を押して完了するまで待ちます（数分〜十数分）。
完了したら、上の `python3 -V` と `git --version` をもう一度実行して確認してください。

---

## 2. リポジトリを取得する

作業場所（ここではホーム直下）へ移動します。

```
cd ~
```

リポジトリを取得します。

```
git clone https://github.com/Lear0511/Cloude-to-SNS.git
```

取得したフォルダの中へ入ります。

```
cd Cloude-to-SNS
```

**以降のコマンドは、すべてこのフォルダの中で実行します。** 今どこにいるかは次で確認できます。

```
pwd
```

`/Users/<あなたのユーザ名>/Cloude-to-SNS` と出れば正しい場所です。
`/Users/<あなたのユーザ名>` のようにホームのままだと、この後のコマンドはすべて失敗します。

### すでに clone 済みの場合（2回目以降）

clone はやり直さず、フォルダへ入って最新を取り込むだけです。

```
cd ~/Cloude-to-SNS
```

```
git pull
```

---

## 3. 動作確認（同梱のサンプルで試す）

サンプルの投稿バッチが `instagram/posts/` に同梱されています。まず引数なしで実行して、何が起きるか見てください。

```
python3 instagram/build-posts.py
```

### 期待する出力

3つのバッチが処理され、いずれも **ERROR 0** で `instagram/out/` にファイルが出れば成功です。

```
── 2026-09-01-brand-ritz.json  投稿 4本 / ERROR 0 / WARN 0
   → 2026-09-01-brand-ritz-review.md / 2026-09-01-brand-ritz-schedule.csv / 2026-09-01-brand-ritz-captions/
── 2026-09-02-iroishi-market.json  投稿 2本 / ERROR 0 / WARN 1
   [WARN] #- 色石マーケット の Instagram handle が accounts.json 未設定。運用開始前に実アカウントを確認して埋めること
   → 2026-09-02-iroishi-market-review.md / 2026-09-02-iroishi-market-schedule.csv / 2026-09-02-iroishi-market-captions/
── 2026-09-02-next-platinum.json  投稿 2本 / ERROR 0 / WARN 1
   [WARN] #- ネクストプラチナム の Instagram handle が accounts.json 未設定。運用開始前に実アカウントを確認して埋めること
   → 2026-09-02-next-platinum-review.md / 2026-09-02-next-platinum-schedule.csv / 2026-09-02-next-platinum-captions/
```

**ネクストプラチナムと色石マーケットに WARN が1件ずつ出るのは正常です。** この2ブランドは Instagram の実アカウントが未確認のため、`instagram/accounts.json` の `handle` を空にしてあります。推測で埋めず、実アカウントを確認できてから入れてください。WARN は出力を止めません（ファイルは生成されます）。

出力されるファイルは1バッチにつき3種類です。

| ファイル | 用途 |
|---|---|
| `<バッチ名>-review.md` | 目視チェックシート。承認者はこれだけ見れば足りる |
| `<バッチ名>-schedule.csv` | SNS管理ツールへの取り込み用（1投稿1行） |
| `<バッチ名>-captions/NN-*.txt` | キャプション全文。手貼り用にコピペするだけ |

参考: `--strict` を付けると WARN もエラー扱いになり、そのバッチは出力されません（PR前の厳格チェック用）。現状は上記の handle 未設定 WARN があるため、`--strict` は途中で止まります。日常の実行では付けないでください。

---

## 4. 初回の生成を試す

投稿案そのものは Web版 Claude で作ります。このスクリプトは、そのための**プロンプトを組み立てて表示する**役割です（Instagram Graph API は使いません）。

ブランドリッツ向けに4本ぶんのプロンプトを表示します。

```
python3 instagram/build-posts.py --prompt brand-ritz --count 4
```

長いプロンプトが画面に出ます。Mac なら `| pbcopy` を付けると**画面に出さずクリップボードへ入る**ので、Web版 Claude の入力欄に ⌘V でそのまま貼れます。

```
python3 instagram/build-posts.py --prompt brand-ritz --count 4 | pbcopy
```

`--prompt` に指定できるアカウント名は次の3つです。

| 指定する名前 | ブランド |
|---|---|
| `brand-ritz` | ブランドリッツ（BtoC） |
| `next-platinum` | ネクストプラチナム（BtoB） |
| `iroishi-market` | 色石マーケット（BtoB） |

本数や初回投稿日を変えたいときのオプションです。

| オプション | 意味 |
|---|---|
| `--count 4` | 何本つくらせるか（既定 4本） |
| `--start 2026-09-01` | 初回投稿日 `YYYY-MM-DD`（既定は翌日） |

Web版 Claude から返ってきた JSON は `instagram/posts/` に `YYYY-MM-DD-<アカウント名>.json` という名前で保存し、もう一度 手順3 のコマンドを実行すると検証・変換されます。

```
python3 instagram/build-posts.py
```

特定の1バッチだけ処理したいときは、ファイルを直接指定します。

```
python3 instagram/build-posts.py instagram/posts/2026-09-01-brand-ritz.json
```

---

## 5. 出力を開く

出力フォルダを Finder で開きます。

```
open instagram/out/
```

目視チェックシートを開きます（`open` は拡張子に応じた既定のアプリに渡します）。

```
open instagram/out/2026-09-01-brand-ritz-review.md
```

予約投稿用の CSV を表計算アプリ（Numbers / Excel）で開きます。

```
open instagram/out/2026-09-01-brand-ritz-schedule.csv
```

キャプション全文のフォルダを開きます。1投稿1ファイルなので、開いて全選択・コピーするだけで貼れます。

```
open instagram/out/2026-09-01-brand-ritz-captions/
```

ターミナル上で中身をそのまま見たいときは `cat` を使います。

```
cat instagram/out/2026-09-01-brand-ritz-review.md
```

出力ファイルの一覧だけ確認したいときはこちらです。

```
ls instagram/out/
```

公開前に必ず `-review.md` を目視で確認してから、SNS管理ツールで予約投稿してください。

---

## 6. 困ったときは

| 出たメッセージ | 原因 | 対処 |
|---|---|---|
| `zsh: command not found: 1.` / `zsh: command not found: →` | 手順の番号や説明文まで一緒に貼っている。`1.` や `→` はコマンドではない | コードブロックの中身の行だけを、1行ずつ貼り直す |
| `can't open file '.../build-posts.py': No such file or directory` | リポジトリの外（ホームなど）で実行している | `cd ~/Cloude-to-SNS` で移動してから実行する。今どこにいるかは `pwd` で確認できる |
| `zsh: command not found: python3` | Python 3 が入っていない | `xcode-select --install` で Xcode Command Line Tools を入れる |
| `zsh: command not found: git` | git が入っていない | 同じく `xcode-select --install` を実行する |
| `ERROR` が出て、そのバッチのファイルが生成されない | 仕様。検証に落ちたバッチは出力しない（不完全な投稿をそのまま流さないため） | 画面に出た `[ERROR] #<投稿番号> <内容>` を読み、`instagram/posts/` の該当 JSON を直してから再実行する |
| `WARN` が出るがファイルは生成される | 仕様。WARN は出力を止めない | 内容を確認する。ネクストプラチナム／色石マーケットの handle 未設定 WARN は現時点では正常 |
| `--strict` を付けたら `→ --strict のため出力しない` で止まる | `--strict` は WARN もエラー扱いにする | 日常の実行では `--strict` を付けない |
| `処理する投稿バッチが無い（instagram/posts/*.json）` | `instagram/posts/` に JSON が1つも無い | Web版 Claude から返ってきた JSON を `instagram/posts/` に保存してから実行する |
| `account "..." が無い` | `--prompt` に渡した名前が違う | `brand-ritz` / `next-platinum` / `iroishi-market` のいずれかを指定する |

### 迷ったら最初に確認する2つ

今いる場所を確認します。

```
pwd
```

このフォルダに `instagram/` があるかを確認します。

```
ls instagram/
```

`build-posts.py` や `accounts.json` が並んで見えれば、正しい場所にいます。

---

## 参考

- 運用手順の詳細は `instagram/README.md` を参照してください
- スクリプトのオプション一覧は次で確認できます

```
python3 instagram/build-posts.py --help
```
