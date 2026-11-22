#!/usr/bin/env python3
"""네이버 블로그 RSS를 읽어 홈페이지 '최신 정비 사례' 목록(latest.json)을 만든다.
GitHub Actions에서 하루 한 번 실행된다. 표준 라이브러리만 사용."""
import json, re, sys, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

BLOG_ID = "gk8192"
RSS = f"https://rss.blog.naver.com/{BLOG_ID}.xml"
OUT = "latest.json"
LIMIT = 8
# 정비 사례로 보이는 글만: 분류명이나 제목에 아래 단어가 있으면 포함, 스터디 글은 제외
INCLUDE = re.compile(r"수리|소모품|유지보수|오버홀|교체|정비|점검")
EXCLUDE = re.compile(r"스터디")

def clean_link(link):
    m = re.search(r"/(\d{9,})", link)
    return f"https://blog.naver.com/{BLOG_ID}/{m.group(1)}" if m else link.split("?")[0]

def main():
    req = urllib.request.Request(RSS, headers={"User-Agent": "Mozilla/5.0 (enginedoctor site updater)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    items = []
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
        items.append({"title": t, "category": cat, "date": date, "link": clean_link(it.findtext("link") or "")})
        if len(items) >= LIMIT:
            break
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
