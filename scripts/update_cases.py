#!/usr/bin/env python3
"""네이버 블로그 RSS를 읽어 홈페이지 '최신 정비 사례' 목록(latest.json)을 만든다.
GitHub Actions에서 하루 한 번 실행된다. 표준 라이브러리만 사용."""
import json, re, sys, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

BLOG_ID = "gk8192"
RSS = f"https://rss.blog.naver.com/{BLOG_ID}.xml"
OUT = "latest.json"
STATS = "stats.json"
ARCHIVE = "cases_all.json"   # 전체 사례 페이지용, 지금까지 본 글을 계속 쌓아 둔다
# 2일차·3일차처럼 같은 현장 이어지는 글은 현장 수에 다시 세지 않음
SERIES = re.compile(r"([2-9]|1\d)\s*일차|[2-9]\s*편|\(\s*[2-9]\s*\)")
LIMIT = 8
# 정비 사례로 보이는 글만: 분류명이나 제목에 아래 단어가 있으면 포함, 스터디 글은 제외
INCLUDE = re.compile(r"수리|소모품|유지보수|오버홀|교체|정비|점검")
EXCLUDE = re.compile(r"스터디")

def clean_link(link):
    m = re.search(r"/(\d{9,})", link)
    return f"https://blog.naver.com/{BLOG_ID}/{m.group(1)}" if m else link.split("?")[0]

def update_stats(found):
    """기준일(since) 이후 올라온 현장 글마다 누적 현장 수를 1씩 올린다."""
    try:
        st = json.load(open(STATS, encoding="utf-8"))
    except FileNotFoundError:
        st = {"base": 500, "since": "2026-11-22", "counted": [], "total": 500}
    since = st.get("since", "2026-11-22").replace("-", ".")
    seen = set(st.get("counted", []))
    for link, date, title in found:
        if not date or date < since or link in seen or SERIES.search(title):
            continue
        seen.add(link)
    st["counted"] = sorted(seen)
    st["total"] = st.get("base", 500) + len(seen)
    json.dump(st, open(STATS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"누적 현장 수: {st['total']}")

def update_archive(found):
    """RSS에 보이는 글을 기존 목록과 합쳐 최신순으로 저장 (오래된 글도 지우지 않음)."""
    try:
        arch = json.load(open(ARCHIVE, encoding="utf-8"))
    except FileNotFoundError:
        arch = []
    by = {a["link"]: a for a in arch}
    for rec in found:
        old = by.get(rec["link"], {})
        by[rec["link"]] = {**old, **{k: v for k, v in rec.items() if v}}
    out = sorted(by.values(), key=lambda a: (a.get("date", "") != "", a.get("date", ""), a["link"]), reverse=True)
    json.dump(out, open(ARCHIVE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"전체 사례 {len(out)}건")

def main():
    req = urllib.request.Request(RSS, headers={"User-Agent": "Mozilla/5.0 (enginedoctor site updater)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    items = []
    counted_new = []
    all_items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        cat = (it.findtext("category") or "").strip()
        if not title or EXCLUDE.search(cat) or not (INCLUDE.search(cat) or INCLUDE.search(title)):
            continue
        try:
            date = parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y.%m.%d")
        except Exception:
            date = ""
        # 제목 앞 '[수리]' 같은 말머리와 '000아파트' 같은 가림 표기는 정리
        t = re.sub(r"\s*0{2,}\s*(아파트|빌딩|건물)?", " ", title)
        t = re.sub(r"\s{2,}", " ", t).strip()
        link = clean_link(it.findtext("link") or "")
        counted_new.append((link, date, title))
        rec = {"title": t, "category": cat, "date": date, "link": link}
        all_items.append(rec)
        if len(items) < LIMIT:
            items.append(rec)
    update_stats(counted_new)
    update_archive(all_items)
    if not items:
        print("RSS에서 사례를 찾지 못해 기존 목록을 유지합니다.")
        return 0
    new = json.dumps(items, ensure_ascii=False, indent=1)
    try:
        old = open(OUT, encoding="utf-8").read()
    except FileNotFoundError:
        old = ""
    if new != old:
        open(OUT, "w", encoding="utf-8").write(new)
        print(f"{len(items)}건으로 갱신했습니다.")
    else:
        print("변경 없음")
    return 0

if __name__ == "__main__":
    sys.exit(main())
