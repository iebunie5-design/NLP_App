"""
뉴스 자동 수집 스크립트
매일 주요 뉴스를 RSS로 수집해서 news_data.csv에 저장합니다.

실행 방법:
    python collect_news.py          # 수동 실행
    python collect_news.py --reset  # 기존 데이터 초기화 후 수집

자동 실행 (cron):
    0 8 * * * /usr/bin/python3 /path/to/collect_news.py
"""

import csv
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

import feedparser
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ── 로깅 설정 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── 수집할 RSS 피드 ────────────────────────────────────────
RSS_FEEDS = {
    "정치": [
        "https://rss.etnews.com/Section901.xml",
        "https://www.khan.co.kr/rss/rssdata/politic_news.xml",
    ],
    "경제": [
        "https://rss.etnews.com/Section902.xml",
        "https://www.khan.co.kr/rss/rssdata/economy_news.xml",
    ],
    "사회": [
        "https://www.khan.co.kr/rss/rssdata/society_news.xml",
        "https://rss.joins.com/joins_news_list.xml",
    ],
    "IT/과학": [
        "https://rss.etnews.com/Section903.xml",
        "https://www.zdnet.co.kr/rss/index.xml",
    ],
    "AI/인공지능": [
        "https://rss.etnews.com/Section904.xml",
        "https://www.aitimes.com/rss/allArticle.xml",
    ],
    "스포츠": [
        "https://www.khan.co.kr/rss/rssdata/sports_news.xml",
    ],
    "문화/연예": [
        "https://www.khan.co.kr/rss/rssdata/art_news.xml",
    ],
    "국제": [
        "https://www.khan.co.kr/rss/rssdata/world_news.xml",
    ],
}

# ── 설정 ──────────────────────────────────────────────────
OUTPUT_FILE = "news_data.csv"
MAX_PER_FEED = 20        # 피드당 최대 기사 수
REQUEST_DELAY = 0.5      # 요청 간격 (초)
REQUEST_TIMEOUT = 10     # 요청 타임아웃 (초)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}


# ── 본문 가져오기 ──────────────────────────────────────────
def fetch_article_body(url: str) -> str:
    """기사 URL에서 본문 텍스트 추출 (실패 시 빈 문자열 반환)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 본문 영역 후보 선택자 (언론사마다 다름)
        selectors = [
            "div#article-view-content-div",   # 아이뉴스24, 전자신문
            "div.article_body",
            "div#articleBodyContents",         # 네이버뉴스
            "div.article-body",
            "div#newsct_article",
            "div.news_body",
            "article",
        ]
        for sel in selectors:
            tag = soup.select_one(sel)
            if tag and len(tag.get_text(strip=True)) > 100:
                return tag.get_text(separator=" ", strip=True)

        # 선택자 없으면 <p> 태그 합치기
        paragraphs = soup.find_all("p")
        body = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20)
        return body[:2000] if body else ""
    except Exception:
        return ""


# ── RSS 파싱 ───────────────────────────────────────────────
def parse_feed(topic: str, url: str) -> list[dict]:
    """RSS 피드 하나를 파싱해서 기사 목록 반환"""
    records = []
    try:
        feed = feedparser.parse(url)
        entries = feed.entries[:MAX_PER_FEED]
        log.info(f"  [{topic}] {url} → {len(entries)}건")

        for entry in entries:
            title       = entry.get("title", "").strip()
            link        = entry.get("link", "").strip()
            description = BeautifulSoup(
                entry.get("summary", entry.get("description", "")), "html.parser"
            ).get_text(separator=" ", strip=True)
            published   = entry.get("published", entry.get("updated", ""))

            if not title or not link:
                continue

            records.append({
                "date":        datetime.now().strftime("%Y-%m-%d"),
                "query":       topic,
                "title":       title,
                "description": description,
                "link":        link,
                "published":   published,
                "source":      feed.feed.get("title", url),
            })
            time.sleep(REQUEST_DELAY)

    except Exception as e:
        log.warning(f"  [{topic}] 피드 오류: {e}")
    return records


# ── 본문 보완 ──────────────────────────────────────────────
def enrich_with_body(records: list[dict], fetch_body: bool = False) -> list[dict]:
    """description이 짧을 때 본문 크롤링으로 보완"""
    if not fetch_body:
        return records
    for r in records:
        if len(r["description"]) < 100 and r["link"]:
            log.info(f"    본문 크롤링: {r['title'][:30]}...")
            body = fetch_article_body(r["link"])
            if body:
                r["description"] = body
            time.sleep(REQUEST_DELAY)
    return records


# ── CSV 저장 ───────────────────────────────────────────────
def save_to_csv(records: list[dict], path: str, reset: bool = False):
    """기존 CSV에 추가 저장 (reset=True면 덮어쓰기)"""
    new_df = pd.DataFrame(records)

    if not reset and Path(path).exists():
        old_df = pd.read_csv(path)
        # 중복 제거 (link 기준)
        combined = pd.concat([old_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["link"], keep="last")
        # 최신 30일치만 유지
        if "date" in combined.columns:
            combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
            combined = combined[combined["date"] >= cutoff]
            combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")
        combined.to_csv(path, index=False, encoding="utf-8-sig")
        log.info(f"✅ 저장 완료: {len(combined)}건 → {path}")
    else:
        new_df.to_csv(path, index=False, encoding="utf-8-sig")
        log.info(f"✅ 신규 저장: {len(new_df)}건 → {path}")


# ── 메인 ──────────────────────────────────────────────────
def main(reset: bool = False, fetch_body: bool = False):
    log.info("=" * 50)
    log.info(f"뉴스 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 50)

    all_records = []

    for topic, urls in RSS_FEEDS.items():
        log.info(f"\n[주제: {topic}]")
        topic_records = []
        for url in urls:
            records = parse_feed(topic, url)
            records = enrich_with_body(records, fetch_body)
            topic_records.extend(records)
        log.info(f"  → {topic}: 총 {len(topic_records)}건 수집")
        all_records.extend(topic_records)

    log.info(f"\n전체 수집: {len(all_records)}건")
    save_to_csv(all_records, OUTPUT_FILE, reset=reset)
    log.info("\n수집 완료!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="뉴스 자동 수집")
    parser.add_argument("--reset",      action="store_true", help="기존 데이터 초기화 후 수집")
    parser.add_argument("--fetch-body", action="store_true", help="기사 본문 크롤링 (느림)")
    args = parser.parse_args()
    main(reset=args.reset, fetch_body=args.fetch_body)