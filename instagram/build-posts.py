#!/usr/bin/env python3
"""Instagram 投稿バッチを検証し、目視チェック用シートと予約投稿用CSVを書き出す。

    python3 instagram/build-posts.py                      # posts/*.json を全部処理
    python3 instagram/build-posts.py posts/2026-09-01-brand-ritz.json
    python3 instagram/build-posts.py --strict              # 警告もエラー扱い（PR前の確認用）
    python3 instagram/build-posts.py --prompt brand-ritz --count 4 --start 2026-09-01

Web版 Claude で生成した投稿案（JSON）を instagram/posts/ に置いて実行すると、
instagram/out/ に次を書き出す。

  <batch>-review.md        目視チェックシート（承認者はこれだけ見れば足りる）
  <batch>-schedule.csv     予約投稿ツールへの取り込み用（1投稿1行）
  <batch>-captions/NN.txt  キャプション全文（手貼り用・コピペするだけ）

検証は instagram/accounts.json の共通ルールとアカウント別ルールで行う。
掲載品目の線引きは競合デイリー紙面リポジトリ Lear0511/Riuz-newspoper の CLAUDE.md
「ブランドリッツの取扱品目」と同じものを共有する。
"""
import argparse, csv, json, pathlib, re, sys
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9), 'JST')
ERROR, WARN = 'ERROR', 'WARN'
TYPES = ('carousel', 'single', 'reel')
PLACEMENTS = ('caption', 'first_comment')

# 予約投稿ツール。Meta Business Suite は1件目のコメントを自動投稿できないため、
# ハッシュタグはキャプション本文に入れるのを既定にする（手作業の入れ忘れ事故を防ぐ）。
POSTING_TOOL = 'Meta Business Suite'
HASHTAG_PLACEMENT_DEFAULT = 'caption'

# 記号を除いた実質の本文でNG語を見るための正規化
def norm(s):
    return re.sub(r'[\s　]+', '', s or '')


def load_accounts():
    accounts = json.loads((ROOT / 'accounts.json').read_text(encoding='utf-8'))
    # 既定値の正本は accounts.json 側。未設定ならスクリプトの定数で補う。
    global POSTING_TOOL, HASHTAG_PLACEMENT_DEFAULT
    POSTING_TOOL = accounts['common'].get('posting_tool', POSTING_TOOL)
    HASHTAG_PLACEMENT_DEFAULT = accounts['common']['limits'].get(
        'hashtag_placement_default', HASHTAG_PLACEMENT_DEFAULT)
    return accounts


def parse_at(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=JST)
    except (TypeError, ValueError):
        return None


def hashtags_of(post):
    return [h for h in post.get('hashtags', []) if h.strip()]


def placement_of(post):
    """ハッシュタグの置き場所。省略時は HASHTAG_PLACEMENT_DEFAULT（caption）。"""
    return post.get('hashtag_placement') or HASHTAG_PLACEMENT_DEFAULT


def caption_filename(post):
    return f'{str(post.get("id", "00")).zfill(2)}-{post.get("slug", "post")}.txt'


def caption_full(post):
    """キャプション欄に実際に入る文字列。ハッシュタグの置き場所で変わる。"""
    body = post.get('caption', '')
    if placement_of(post) == 'caption':
        tags = ' '.join(hashtags_of(post))
        return f'{body}\n\n{tags}' if tags else body
    return body


def first_comment_full(post):
    parts = [post.get('first_comment', '').strip()]
    if placement_of(post) == 'first_comment':
        parts.append(' '.join(hashtags_of(post)))
    return '\n\n'.join(p for p in parts if p)


def validate(batch, accounts):
    """(level, post_id, message) のリストを返す。"""
    out = []
    common, lim = accounts['common'], accounts['common']['limits']
    key = batch.get('account')
    acc = accounts['accounts'].get(key)

    def add(level, pid, msg):
        out.append((level, pid, msg))

    if acc is None:
        add(ERROR, '-', f'account "{key}" が accounts.json に無い（{"/".join(accounts["accounts"])}）')
        return out
    if not acc.get('handle'):
        add(WARN, '-', f'{acc["brand"]} の Instagram handle が accounts.json 未設定。'
                       '運用開始前に実アカウントを確認して埋めること')

    posts = batch.get('posts') or []
    if not posts:
        add(ERROR, '-', 'posts が空')

    ng = [w for w in common['ng_words'] if w not in acc.get('ng_allow', [])]
    seen_ids, seen_at = set(), {}

    for post in posts:
        pid = str(post.get('id', '?'))
        if pid in seen_ids:
            add(ERROR, pid, 'id が重複している')
        seen_ids.add(pid)

        if not post.get('slug'):
            add(ERROR, pid, 'slug が無い（ファイル名に使う）')
        if post.get('type') not in TYPES:
            add(ERROR, pid, f'type は {"/".join(TYPES)} のいずれか（今: {post.get("type")!r}）')
        if not post.get('theme'):
            add(ERROR, pid, 'theme が無い')

        at = parse_at(post.get('publish_at'))
        if at is None:
            add(ERROR, pid, f'publish_at は "YYYY-MM-DD HH:MM"(JST) 形式（今: {post.get("publish_at")!r}）')
        else:
            if at <= datetime.now(JST):
                add(WARN, pid, f'publish_at {post["publish_at"]} が過去。予約投稿できない')
            if post['publish_at'] in seen_at:
                add(WARN, pid, f'publish_at が #{seen_at[post["publish_at"]]} と同時刻')
            seen_at[post['publish_at']] = pid

        # 本文
        cap = caption_full(post)
        if not post.get('caption', '').strip():
            add(ERROR, pid, 'caption が空')
        if len(cap) > lim['caption_max']:
            add(ERROR, pid, f'キャプションが {len(cap)}字。上限 {lim["caption_max"]}字を超えている')

        # ハッシュタグ
        tags = hashtags_of(post)
        bad = [t for t in tags if not t.startswith('#')]
        if bad:
            add(ERROR, pid, f'# で始まらないハッシュタグ: {", ".join(bad)}')
        if len(tags) != len(set(tags)):
            dup = sorted({t for t in tags if tags.count(t) > 1})
            add(ERROR, pid, f'ハッシュタグが重複: {", ".join(dup)}')
        if len(tags) > lim['hashtag_max']:
            add(ERROR, pid, f'ハッシュタグ {len(tags)}個。上限 {lim["hashtag_max"]}個を超えている')
        if not tags:
            add(WARN, pid, 'ハッシュタグが1つも無い')
        missing = [t for t in acc['hashtags']['fixed'] if t not in tags]
        if missing:
            add(WARN, pid, f'固定ハッシュタグが入っていない: {", ".join(missing)}')

        placement = placement_of(post)
        if placement not in PLACEMENTS:
            add(ERROR, pid, f'hashtag_placement は {"/".join(PLACEMENTS)} のいずれか'
                            f'（今: {post.get("hashtag_placement")!r}）')
        elif placement == 'first_comment':
            add(WARN, pid, f'hashtag_placement が first_comment。{POSTING_TOOL} は1件目のコメントを'
                           '自動投稿できないため、公開後に手で入れる運用になる'
                           f'（既定は {HASHTAG_PLACEMENT_DEFAULT}）')

        # スライド
        slides = post.get('slides') or []
        if post.get('type') == 'carousel':
            if not (lim['carousel_min'] <= len(slides) <= lim['carousel_max']):
                add(ERROR, pid, f'カルーセルは {lim["carousel_min"]}〜{lim["carousel_max"]}枚。'
                                f'今 {len(slides)}枚')
        elif post.get('type') == 'single' and len(slides) != 1:
            add(ERROR, pid, f'single は1枚。今 {len(slides)}枚')

        for i, sl in enumerate(slides, 1):
            head = sl.get('headline', '')
            if not head.strip():
                add(ERROR, pid, f'{i}枚目の headline が空')
            elif len(head) > lim['headline_soft_max']:
                add(WARN, pid, f'{i}枚目の見出しが {len(head)}字。'
                               f'{lim["headline_soft_max"]}字までに収めると1枚目で読ませやすい')
            alt = sl.get('alt', '')
            if not alt.strip():
                add(ERROR, pid, f'{i}枚目の alt（代替テキスト）が空')
            elif len(alt) > lim['alt_max']:
                add(WARN, pid, f'{i}枚目の alt が {len(alt)}字。{lim["alt_max"]}字までが読みやすい')

        # 表現・品目のチェック
        allow = post.get('allow', [])
        haystack = norm(' '.join([cap, first_comment_full(post),
                                  ' '.join(sl.get('headline', '') + sl.get('body', '') + sl.get('alt', '')
                                           for sl in slides)]))
        for w in ng:
            if w in allow:
                continue
            if norm(w) in haystack:
                add(ERROR, pid, f'NG表現「{w}」が入っている（優良誤認・断定表現）')
        for w in common['out_of_scope_items']:
            if w in allow:
                continue
            if norm(w) in haystack:
                add(ERROR, pid, f'取扱対象外の品目「{w}」に触れている。当社が扱う品目だけを書く')

    return out


def render_review(batch, accounts, issues, name):
    acc = accounts['accounts'][batch['account']]
    lim = accounts['common']['limits']
    handle = acc.get('handle') or '（アカウント未設定）'
    L = []
    L.append(f'# 目視チェックシート ── {acc["brand"]} {handle}')
    L.append('')
    L.append(f'- バッチ: `{batch.get("batch", "-")}`')
    L.append(f'- 投稿数: {len(batch.get("posts", []))}本')
    L.append(f'- 生成: {batch.get("author", "-")}')
    L.append(f'- 適用した前提条件: brand-kit / {acc["brand"]}（{acc["type"]}）'
             f' ── トーン「{acc["tone"]}」')
    L.append('')
    L.append('公開前に、各投稿の3つのチェックを人の目で通してから予約する。')
    L.append('')

    by_post = {}
    for level, pid, msg in issues:
        by_post.setdefault(pid, []).append((level, msg))
    if issues:
        L.append('## 自動チェックの指摘')
        L.append('')
        L.append('| 投稿 | 種別 | 内容 |')
        L.append('|---|---|---|')
        for level, pid, msg in issues:
            L.append(f'| {pid} | {level} | {msg} |')
        L.append('')
    else:
        L.append('## 自動チェックの指摘')
        L.append('')
        L.append('指摘なし。')
        L.append('')

    for post in batch.get('posts', []):
        pid = str(post.get('id', '?'))
        L.append('---')
        L.append('')
        L.append(f'## #{pid} {post.get("theme", "")}')
        L.append('')
        L.append(f'- 予約日時（JST）: **{post.get("publish_at", "-")}**')
        L.append(f'- 形式: {post.get("type", "-")}／{len(post.get("slides") or [])}枚')
        L.append(f'- ハッシュタグ: {len(hashtags_of(post))}個（{placement_of(post)} に置く）')
        cap = caption_full(post)
        L.append(f'- キャプション: {len(cap)}字 / {lim["caption_max"]}字')
        L.append('')
        L.append('- [ ] 事実（店舗名・品目・条件・許可番号）が brand-kit と一致している')
        L.append('- [ ] 断定・煽り表現が無い／当社の取扱品目だけを書いている')
        L.append('- [ ] 画像とキャプションの組み合わせが正しい（別投稿の取り違えが無い）')
        L.append('')
        for level, msg in by_post.get(pid, []):
            L.append(f'> **{level}** {msg}')
        if by_post.get(pid):
            L.append('')

        slides = post.get('slides') or []
        n = len(slides)
        placement = placement_of(post)
        upload = (f'画像をカルーセルの順（1枚目→{n}枚目）どおりにアップロードする'
                  if n >= 2 else '画像をアップロードする（1枚）')
        if placement == 'first_comment':
            last = ('この投稿は hashtag_placement が first_comment。'
                    '公開後に下の「1件目のコメント」を手で入れる（自動投稿されない）')
        elif post.get('first_comment', '').strip():
            last = ('ハッシュタグはキャプションに入っている。'
                    '下の「1件目のコメント」の注記だけ、公開後に手で入れる')
        else:
            last = ('ハッシュタグはキャプションに入っているので、'
                    '公開後に手で入れるコメントは無い')
        L.append(f'### {POSTING_TOOL} への入れ方')
        L.append('')
        L.append(f'1. プランナー →「投稿を作成」→ {handle} を選ぶ')
        L.append(f'2. {upload}')
        L.append(f'3. `out/{name}-captions/{caption_filename(post)}` の本文をキャプション欄に貼る')
        L.append('4. 画像ごとに下の「画像の指示」表の alt を代替テキストに入れる')
        L.append(f'5. 予約日時に **{post.get("publish_at", "-")}（JST）** を設定する')
        L.append(f'6. {last}')
        L.append('')

        if slides:
            L.append('### 画像の指示')
            L.append('')
            L.append('| 枚 | 見出し | 本文 | alt |')
            L.append('|---|---|---|---|')
            for i, sl in enumerate(slides, 1):
                cell = lambda s: (s or '').replace('|', '\\|').replace('\n', '<br>')
                L.append(f'| {i} | {cell(sl.get("headline"))} | {cell(sl.get("body"))} | {cell(sl.get("alt"))} |')
            L.append('')

        L.append('### キャプション')
        L.append('')
        L.append('```text')
        L.append(cap)
        L.append('```')
        L.append('')
        fc = first_comment_full(post)
        if fc:
            L.append('### 1件目のコメント')
            L.append('')
            L.append('```text')
            L.append(fc)
            L.append('```')
            L.append('')
        if acc.get('legal'):
            L.append('<details><summary>法定表記・注記（必要な投稿に入れる）</summary>')
            L.append('')
            for x in acc['legal']:
                L.append(f'- {x}')
            L.append('')
            L.append('</details>')
            L.append('')
    return '\n'.join(L) + '\n'


CSV_COLUMNS = ['publish_at_jst', 'account', 'handle', 'type', 'theme',
               'caption', 'first_comment', 'media', 'alt_texts', 'slide_count']


def render_csv(batch, accounts, path):
    acc = accounts['accounts'][batch['account']]
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for post in batch.get('posts', []):
            slides = post.get('slides') or []
            w.writerow([
                post.get('publish_at', ''),
                batch['account'],
                acc.get('handle') or '',
                post.get('type', ''),
                post.get('theme', ''),
                caption_full(post),
                first_comment_full(post),
                ' | '.join(post.get('media') or []),
                ' | '.join(sl.get('alt', '') for sl in slides),
                len(slides),
            ])


def render_captions(batch, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob('*.txt'):
        old.unlink()
    for post in batch.get('posts', []):
        name = caption_filename(post)
        text = caption_full(post)
        fc = first_comment_full(post)
        if fc:
            text += '\n\n----- 1件目のコメント -----\n' + fc
        (outdir / name).write_text(text + '\n', encoding='utf-8')


PROMPT = '''あなたは株式会社Ritz Solution Partner の {brand}（{type_}）の
Instagram 運用担当です。次の前提条件だけを使って、投稿案を {count} 本つくってください。

【前提条件（この範囲の事実しか使わない。住所・数値・人名・実績を創作しない）】
{account_block}

【禁止】
- 断定・優良誤認の表現を使わない: {ng}
- 当社の取扱外の品目に触れない: {oos}
- 前提条件に無い事実（店舗名・数値・キャンペーン・許可番号）を書かない
- ハッシュタグは合計 {hashtag_max} 個まで。キャプションは {caption_max} 字まで
- ハッシュタグはキャプション末尾にまとめて置く（予約投稿に使う {posting_tool} は1件目のコメントを自動投稿できないため）

【投稿の型（ここから選ぶ。同じ型を続けない）】
{pillars}

【日程】
{schedule}

【出力形式】
説明文を付けず、次の JSON だけを ```json コードブロックで出力する。

```json
{{
  "account": "{key}",
  "batch": "{batch}",
  "author": "Claude (Web) / 目視チェック: ",
  "posts": [
    {{
      "id": "01",
      "slug": "半角英数とハイフンの短い識別子",
      "type": "carousel",
      "publish_at": "YYYY-MM-DD HH:MM",
      "theme": "この投稿で言い切ること（1行）",
      "slides": [
        {{ "headline": "1枚目の見出し（20字まで）",
           "body": "画像に載せる補足（無ければ空文字）",
           "alt": "画像の代替テキスト（100字まで・何が写っているかを説明）" }}
      ],
      "caption": "本文。1文ずつ改行して読みやすくする。最後に CTA を置く",
      "hashtag_placement": "caption",
      "hashtags": ["#..."],
      "first_comment": "補足があれば。無ければ空文字",
      "media": [],
      "cta": "{cta}"
    }}
  ]
}}
```

出力した JSON を instagram/posts/{batch}-{key}.json として保存し、
`python3 instagram/build-posts.py` で検証すること。'''


def build_prompt(accounts, key, count, start):
    acc = accounts['accounts'][key]
    common = accounts['common']
    block = {k: v for k, v in acc.items() if not k.startswith('_') and k not in ('pillars', 'hashtags')}
    block['hashtags_fixed'] = acc['hashtags']['fixed']
    block['hashtags_rotating'] = acc['hashtags']['rotating']
    ng = [w for w in common['ng_words'] if w not in acc.get('ng_allow', [])]

    d0 = datetime.strptime(start, '%Y-%m-%d')
    days = [(d0 + timedelta(days=i * 2)).strftime('%Y-%m-%d') for i in range(count)]
    hhmm = '19:00' if acc['type'] == 'BtoC' else '12:00'
    schedule = '\n'.join(f'- {i + 1}本目: {d} {hhmm}（JST）' for i, d in enumerate(days))
    schedule += f'\n（目安の頻度: {acc["cadence"]}。曜日は運用側で調整してよい）'

    return PROMPT.format(
        brand=acc['brand'], type_=acc['type'], count=count, key=key,
        batch=start,
        account_block=json.dumps(block, ensure_ascii=False, indent=2),
        ng='／'.join(ng),
        oos='／'.join(common['out_of_scope_items']),
        hashtag_max=common['limits']['hashtag_max'],
        posting_tool=POSTING_TOOL,
        caption_max=common['limits']['caption_max'],
        pillars='\n'.join(f'- {p}' for p in acc['pillars']),
        schedule=schedule,
        cta=acc['cta'],
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*', help='投稿バッチJSON。省略時は instagram/posts/*.json')
    ap.add_argument('--out', default=str(ROOT / 'out'), help='出力先ディレクトリ')
    ap.add_argument('--strict', action='store_true', help='WARN もエラー扱いにする')
    ap.add_argument('--prompt', metavar='ACCOUNT', help='Web版Claudeに貼る生成プロンプトを表示して終了')
    ap.add_argument('--count', type=int, default=4, help='--prompt で何本つくらせるか')
    ap.add_argument('--start', default=None, help='--prompt の初回投稿日 YYYY-MM-DD')
    args = ap.parse_args()

    accounts = load_accounts()

    if args.prompt:
        if args.prompt not in accounts['accounts']:
            sys.exit(f'account "{args.prompt}" が無い（{"/".join(accounts["accounts"])}）')
        start = args.start or (datetime.now(JST) + timedelta(days=1)).strftime('%Y-%m-%d')
        print(build_prompt(accounts, args.prompt, args.count, start))
        return 0

    files = [pathlib.Path(f) for f in args.files] or sorted((ROOT / 'posts').glob('*.json'))
    if not files:
        sys.exit('処理する投稿バッチが無い（instagram/posts/*.json）')

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    failed = False

    for path in files:
        batch = json.loads(path.read_text(encoding='utf-8'))
        issues = validate(batch, accounts)
        errs = [i for i in issues if i[0] == ERROR]
        warns = [i for i in issues if i[0] == WARN]
        name = path.stem

        print(f'── {path.name}  投稿 {len(batch.get("posts", []))}本 / '
              f'ERROR {len(errs)} / WARN {len(warns)}')
        for level, pid, msg in issues:
            print(f'   [{level}] #{pid} {msg}')

        if errs:
            failed = True
            print(f'   → ERROR があるため出力しない: {path.name}')
            continue
        if warns and args.strict:
            failed = True
            print(f'   → --strict のため出力しない: {path.name}')
            continue

        (outdir / f'{name}-review.md').write_text(render_review(batch, accounts, issues, name), encoding='utf-8')
        render_csv(batch, accounts, outdir / f'{name}-schedule.csv')
        render_captions(batch, outdir / f'{name}-captions')
        print(f'   → {name}-review.md / {name}-schedule.csv / {name}-captions/')

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
