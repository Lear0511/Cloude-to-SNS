# Cloude-to-SNS

株式会社Ritz Solution Partner の **SNS投稿を Claude でつくって予約投稿する運用**の置き場です。

投稿案は Web版 Claude で生成し、リポジトリ内のスクリプトで機械チェックしてから、**Meta Business Suite** で予約投稿します。
**各SNSの API 連携は持ちません。**アカウント停止のリスクを避けられること、公開前に必ず人の目が1回入ることが狙いです。

予約投稿ツールは Meta Business Suite に一本化しました（2026-08-28 オーナー判断）。Meta 公式の管理画面で追加費用が発生せず、Instagram の予約投稿に必要な機能がそろうためです。Buffer / Later / Hootsuite は採用していません（将来乗り換える可能性は残します）。

第1弾は Instagram（[`instagram/`](instagram/)）。今後 X・LINE公式 などを増やす想定なので、**SNSごとにディレクトリを並べる**構成にしています。

対象は3ブランドです。

| ブランド | 種別 | Instagram |
|---|---|---|
| ブランドリッツ | BtoC 買取・販売 | `@brand_ritz` / `@brandritzbuy` / `@brandritzrokko` |
| ネクストプラチナム | BtoB 貴金属卸・買取 | **未確認**（推測で埋めない） |
| 色石マーケット | BtoB 色石の業者間卸・仕入 | **未確認**（推測で埋めない） |

---

## ワークフローの流れ

**この表を丸ごとターミナルに貼らないでください。**実際に打つコマンドは「コマンド」欄のある2行だけで、残りは手作業です。

| # | やること | コマンド | 手作業 |
|---|---|---|---|
| 1 | 生成プロンプトを出す | `python3 instagram/build-posts.py --prompt brand-ritz --count 4` | 出力をコピーする |
| 2 | 投稿案を生成する | ― | Web版 Claude にプロンプトを貼り、返ってきた JSON を `instagram/posts/` に保存する |
| 3 | 機械チェックする | `python3 instagram/build-posts.py` | 指摘が出たら投稿案を直して再実行する |
| 4 | 目視チェックする | ― | `instagram/out/review.md` を開き、事実・トーン・法定表記を人が確認する |
| 5 | 画像をつくる | ― | ブランドの配色で画像を用意する |
| 6 | 予約投稿する | ― | `instagram/out/schedule.csv` と `captions/` をもとに、**Meta Business Suite** で予約する |

ステップ2・4・6は人の判断が要る工程です。ここを飛ばさないことが、この運用の前提になっています。

---

## クイックスタート

```shell
# 1. 生成プロンプトを出す（Web版 Claude に貼る）
python3 instagram/build-posts.py --prompt brand-ritz --count 4

# 2. instagram/posts/ に保存した投稿バッチを検証し、out/ に変換する
python3 instagram/build-posts.py
```

`--prompt` に渡すブランド名は `brand-ritz` / `next-platinum` / `iroishi-market` の3つです。

- Instagram運用の詳しい手順 → **[`instagram/README.md`](instagram/README.md)**（正本）
- 環境の準備・Meta Business Suite 側の初期設定 → **[`SETUP.md`](SETUP.md)**
- ブランドの前提条件・守るルール（Claude が作業前に読む） → **[`CLAUDE.md`](CLAUDE.md)**

---

## ディレクトリ構成

```
.
├── README.md                     ← このファイル（入口）
├── SETUP.md                      ← 環境・ツールの初期設定
├── CLAUDE.md                     ← Claude 向けの前提条件
└── instagram/
    ├── README.md                 ← Instagram運用フローの正本
    ├── accounts.json             ← 3ブランドの前提条件の台帳
    ├── build-posts.py            ← プロンプト出力 / 検証 / 変換
    ├── prompt-template.md        ← 生成プロンプトの雛形
    ├── posts/                    ← 投稿バッチ JSON
    └── out/                      ← 生成物（review.md / schedule.csv / captions/）
```

| ファイル | 役割 |
|---|---|
| `instagram/accounts.json` | トーン・取扱品目・投稿の型・ハッシュタグ・法定表記・NG表現・ブランドカラーの台帳。**前提条件はここ1本に集約**し、別ファイルへ二重管理しない |
| `instagram/build-posts.py` | 生成プロンプトの出力、投稿バッチの検証、目視チェックシート・CSV・キャプションへの変換 |
| `instagram/prompt-template.md` | 生成プロンプトの雛形。**正本は `build-posts.py` の `PROMPT` 定数** |
| `instagram/posts/` `instagram/out/` | 「いつ何を出したか」の記録なので**コミットして残す**（`.gitignore` しない） |

---

## 守るルール

- **事実は brand-kit のみを出典にする。** 住所・数値・人名・許可番号・実績は [`Lear0511/Riuz-base`](https://github.com/Lear0511/Riuz-base) の brand-kit を唯一の出典とし、投稿で創作しない
- **ブランドをまたいで配色・トーンを混ぜない。** BtoC（ブランドリッツ）は親しみやすく安心感、BtoB（ネクストプラチナム・色石マーケット）は専門家同士の対等な語り口。配色も `accounts.json` のブランド別の値を使う
- **取扱外の品目に触れない。** 対象品目の線引きは `accounts.json` の `common.out_of_scope_items` が正。この線引きは競合紙面 [`Lear0511/Riuz-newspoper`](https://github.com/Lear0511/Riuz-newspoper) と共有しているので、**対象外品目を足すときは両リポジトリに反映する**
- **未確認のアカウント名を推測で埋めない。** ネクストプラチナムと色石マーケットの Instagram は brand-kit に記載がなく、`accounts.json` では `null` のまま。実アカウントを確認してから `handle` / `url` に入れる
- **ハッシュタグは既定でキャプション本文に入れる。** Meta Business Suite には1件目のコメントを自動投稿する機能が無いため、投稿バッチの `hashtag_placement` の既定は `caption`。`first_comment` を指定した投稿は検証で WARN が出て、公開後に人が手でコメントを入れる運用になる
- **Instagram Graph API は使わない。** 予約投稿は Meta Business Suite 側で行う

---

## 関連リポジトリ

| リポジトリ | 役割 |
|---|---|
| [`Lear0511/Riuz-base`](https://github.com/Lear0511/Riuz-base) | ブランドキット。事実データの唯一の出典 |
| [`Lear0511/Riuz-newspoper`](https://github.com/Lear0511/Riuz-newspoper) | 競合デイリー紙面。取扱外品目の線引きを共有 |
