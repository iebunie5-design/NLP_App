"""
뉴스 키워드 분석 앱 (자동 수집 연동 버전)
collect_news.py 로 수집한 news_data.csv를 실시간으로 분석합니다.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from kiwipiepy import Kiwi
from wordcloud import WordCloud
from sklearn.feature_extraction.text import TfidfVectorizer

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ── 한글 폰트 설정 ──────────────────────────────────────────
def set_korean_font():
    font_candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux/Colab
        "/usr/share/fonts/nanum/NanumGothic.ttf",
        "C:/Windows/Fonts/malgun.ttf",                       # Windows
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf" # macOS
    ]
    for path in font_candidates:
        try:
            fm.fontManager.addfont(path)
            font_name = fm.FontProperties(fname=path).get_name()
            plt.rcParams["font.family"] = font_name
            plt.rcParams["axes.unicode_minus"] = False
            return
        except Exception:
            continue
    # 없으면 나눔고딕 설치 시도
    try:
        import subprocess
        subprocess.run(["apt-get", "install", "-y", "fonts-nanum"],
                       capture_output=True)
        fm._load_fontmanager(try_read_cache=False)
        plt.rcParams["font.family"] = "NanumGothic"
        plt.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass

set_korean_font()
st.set_page_config(
    page_title="뉴스 키워드 분석",
    page_icon="📰",
    layout="wide",
)

# ── 헤더 ──────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("📰 뉴스 키워드 분석 앱")
    st.caption("매일 주요 뉴스를 수집해서 핵심 키워드를 시각화합니다.")
with col_h2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 뉴스 새로 수집", use_container_width=True):
        with st.spinner("뉴스 수집 중... (30초~1분 소요)"):
            try:
                result = subprocess.run(
                    ["python", "collect_news.py"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    st.success("수집 완료! 페이지를 새로고침해주세요.")
                    st.cache_data.clear()
                else:
                    st.error(f"수집 오류: {result.stderr[:200]}")
            except Exception as e:
                st.error(f"실행 오류: {e}")


# ── 데이터 로드 ────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data(path: str):
    df = pd.read_csv(path)
    return df


# ── 컬럼 감지 ──────────────────────────────────────────────
def detect_columns(df: pd.DataFrame):
    topic_candidates = ["query", "topic", "category", "subject", "주제", "분류"]
    text_candidates  = [
        "content", "text", "article", "news", "body",
        "description", "summary", "본문", "기사", "processed", "title",
    ]
    topic_col = next((c for c in topic_candidates if c in df.columns), None)
    text_col  = next((c for c in text_candidates  if c in df.columns), None)
    return topic_col, text_col


# ── 전처리 ─────────────────────────────────────────────────
@st.cache_resource
def get_kiwi():
    return Kiwi()

STOPWORDS = {
    "기자", "뉴스", "오늘", "지난", "이번", "관련", "통해", "위해", "대한", "정도",
    "경우", "이후", "현재", "지난해", "올해", "정부", "한국", "국내", "오전", "오후",
    "때문", "모습", "해당", "정말", "진짜", "그냥", "이것", "저것", "부분", "사람",
    "우리", "여기", "저기", "때문", "니다", "있다", "했다", "한다고", "있습니다",
}
ALLOWED_POS = {"NNG", "NNP", "SL"}


def clean_text(text: str) -> str:
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def preprocess_text(text: str) -> str:
    kiwi = get_kiwi()
    text = clean_text(text)
    tokens = [
        token.form.strip().lower()
        for token in kiwi.tokenize(text)
        if token.tag in ALLOWED_POS
    ]
    return " ".join(
        w for w in tokens
        if len(w) >= 2 and w not in STOPWORDS and not w.isdigit()
    )


@st.cache_data(show_spinner=False)
def preprocess_dataframe(df: pd.DataFrame, text_col: str):
    df = df.copy()
    df["processed"] = df[text_col].fillna("").astype(str).apply(preprocess_text)
    return df


# ── TF-IDF ─────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def build_tfidf(processed_series: pd.Series):
    vec = TfidfVectorizer(max_features=1000, min_df=2, max_df=0.8)
    mat = vec.fit_transform(processed_series)
    return vec, mat


# ── 키워드 추출 ────────────────────────────────────────────
def get_top_keywords(topic, df, topic_col, mat, vec, top_n=30):
    idx = df[df[topic_col] == topic].index.tolist()
    if not idx:
        return pd.DataFrame(columns=["keyword", "score"])
    mean_vec = np.asarray(mat[idx].mean(axis=0)).flatten()
    top_idx  = mean_vec.argsort()[::-1][:top_n]
    names    = vec.get_feature_names_out()
    rows     = [(names[i], float(mean_vec[i])) for i in top_idx if mean_vec[i] > 0]
    return pd.DataFrame(rows, columns=["keyword", "score"])


# ── 워드클라우드 ───────────────────────────────────────────
def get_font_path():
    for p in [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/nanum/NanumGothic.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    ]:
        try:
            open(p, "rb").close()
            return p
        except Exception:
            continue
    return None


def make_wordcloud(kw_df: pd.DataFrame):
    freq = dict(zip(kw_df["keyword"], kw_df["score"]))
    wc   = WordCloud(
        font_path=get_font_path(),
        width=900, height=420,
        background_color="white",
        colormap="viridis",
        max_words=50,
    ).generate_from_frequencies(freq)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    return fig


def make_bar_chart(kw_df: pd.DataFrame, top_n: int = 10):
    df10 = kw_df.head(top_n)
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(df10["keyword"][::-1], df10["score"][::-1], color="#1D9E75")
    ax.set_xlabel("TF-IDF 점수")
    ax.set_title(f"상위 {top_n} 키워드")
    for bar in bars:
        ax.text(bar.get_width() + 0.0005, bar.get_y() + bar.get_height()/2,
                f"{bar.get_width():.4f}", va="center", fontsize=8)
    plt.tight_layout()
    return fig


# ── 사이드바 ───────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")
    top_n   = st.slider("추출 키워드 수", 10, 50, 30, 5)
    show_df = st.checkbox("원본 데이터 보기", value=False)
    st.markdown("---")
    st.subheader("🕐 자동 수집 설정")
    st.info(
        "매일 자동 수집하려면 cron에 등록하세요.\n\n"
        "**Linux/Mac:**\n"
        "`crontab -e` 후 아래 추가\n\n"
        "`0 8 * * * python /path/to/collect_news.py`\n\n"
        "**Windows:**\n"
        "작업 스케줄러에서 매일 오전 8시 실행 등록"
    )
    st.markdown("---")
    override = st.checkbox("컬럼 직접 선택")


# ── 데이터 로드 & 실행 ─────────────────────────────────────
DATA_FILE = "news_data.csv"

if not Path(DATA_FILE).exists():
    st.warning("📂 `news_data.csv` 파일이 없습니다.")
    st.info(
        "**첫 뉴스 수집 방법:**\n\n"
        "```bash\n"
        "pip install feedparser beautifulsoup4 requests\n"
        "python collect_news.py\n"
        "```\n\n"
        "또는 위의 **🔄 뉴스 새로 수집** 버튼을 클릭하세요."
    )
    st.stop()

df_news = load_data(DATA_FILE)

# 수집 현황 표시
if "date" in df_news.columns:
    dates     = pd.to_datetime(df_news["date"], errors="coerce")
    last_date = dates.max()
    topic_col_temp, _ = detect_columns(df_news)
    n_topics = df_news[topic_col_temp].nunique() if topic_col_temp else "-"
    m1, m2, m3 = st.columns(3)
    m1.metric("총 기사 수",  f"{len(df_news):,}건")
    m2.metric("주제 수",     f"{n_topics}개")
    m3.metric("최근 수집일", last_date.strftime("%Y-%m-%d") if pd.notna(last_date) else "-")

st.markdown("---")

# 컬럼 감지
topic_col, text_col = detect_columns(df_news)

if override or topic_col is None or text_col is None:
    cols      = list(df_news.columns)
    topic_col = st.sidebar.selectbox(
        "주제 컬럼", cols,
        index=cols.index(topic_col) if topic_col in cols else 0
    )
    text_col = st.sidebar.selectbox(
        "본문 컬럼", cols,
        index=cols.index(text_col) if text_col in cols else 0
    )

if topic_col is None or text_col is None:
    st.error(f"컬럼을 찾지 못했습니다. 현재 컬럼: {list(df_news.columns)}")
    st.stop()

# 전처리 & TF-IDF
with st.spinner("전처리 중..."):
    df_news = preprocess_dataframe(df_news, text_col)
with st.spinner("TF-IDF 계산 중..."):
    vectorizer, tfidf_mat = build_tfidf(df_news["processed"])

# 주제 선택
topics   = sorted(df_news[topic_col].dropna().astype(str).unique())
selected = st.selectbox("📌 주제를 선택하세요", topics)

n_articles = len(df_news[df_news[topic_col] == selected])
st.caption(f"'{selected}' 관련 기사: {n_articles}건")

# 키워드 추출
kw_df = get_top_keywords(selected, df_news, topic_col, tfidf_mat, vectorizer, top_n)

if kw_df.empty:
    st.warning("키워드를 추출할 수 없습니다.")
    st.stop()

# ── 시각화 탭 ──────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["☁️ 워드클라우드", "📊 막대 차트", "📋 키워드 표"])

with tab1:
    st.subheader(f"'{selected}' 워드클라우드")
    st.pyplot(make_wordcloud(kw_df))

with tab2:
    st.subheader(f"'{selected}' TOP {min(top_n, 10)} 키워드")
    st.pyplot(make_bar_chart(kw_df, top_n=min(top_n, 10)))

with tab3:
    st.subheader("키워드 전체 목록")
    display_df       = kw_df.copy()
    display_df.index = np.arange(1, len(display_df) + 1)
    display_df["score"] = display_df["score"].round(4)
    st.dataframe(display_df, use_container_width=True)

# ── 원본 기사 목록 ──────────────────────────────────────────
if show_df:
    st.markdown("---")
    st.subheader(f"'{selected}' 원본 기사 (최근 20건)")

    preview = df_news[df_news[topic_col] == selected].head(20)

    for _, row in preview.iterrows():
        title = row.get("title", "제목 없음")
        desc  = row.get("description", "")[:100]
        link  = row.get("link", "")
        date  = row.get("date", "")
        source = row.get("source", "")

        # 제목을 클릭 가능한 링크로 표시
        if link:
            st.markdown(
                f"**[{title}]({link})**  \n"
                f"<span style='color:gray;font-size:12px'>{date} · {source}</span>  \n"
                f"{desc}...",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"**{title}**  \n{desc}...")

        st.divider()

st.markdown("---")
st.caption(
    f"컬럼 → 주제: `{topic_col}` · 본문: `{text_col}` · "
    f"마지막 업데이트: {datetime.now().strftime('%H:%M')}"
)
