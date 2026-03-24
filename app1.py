import re
from collections import Counter

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from kiwipiepy import Kiwi
from wordcloud import WordCloud
from sklearn.feature_extraction.text import TfidfVectorizer


st.set_page_config(page_title="뉴스 키워드 분석 앱", layout="wide")

st.title("📰 뉴스 키워드 분석 앱")
st.write("주제를 선택하면 해당 주제 뉴스의 핵심 키워드를 워드클라우드와 TOP 10 표로 보여줍니다.")


# ---------------------------
# 1. 데이터 로드
# ---------------------------
@st.cache_data
def load_data(path: str):
    df = pd.read_csv(path)
    return df


# ---------------------------
# 2. 컬럼 자동 찾기 (수정됨 ✅)
# ---------------------------
def detect_columns(df: pd.DataFrame):
    possible_topic_cols = [
        "query", "topic", "category", "subject", "주제", "분류"
    ]
    possible_text_cols = [
        "content", "text", "article", "news", "body",
        "본문", "기사", "processed",
        "description",   # ✅ 추가
        "title",         # ✅ 추가 (본문이 없을 때 제목 사용)
        "summary",       # ✅ 추가
    ]

    topic_col = None
    text_col = None

    for col in possible_topic_cols:
        if col in df.columns:
            topic_col = col
            break

    for col in possible_text_cols:
        if col in df.columns:
            text_col = col
            break

    return topic_col, text_col


# ---------------------------
# 3. 텍스트 전처리
# ---------------------------
kiwi = Kiwi()

stopwords = {
    "기자", "뉴스", "오늘", "지난", "이번", "관련", "통해", "위해", "대한", "정도",
    "경우", "이후", "현재", "지난해", "올해", "정부", "한국", "국내", "오전", "오후",
    "때문", "모습", "해당", "정말", "진짜", "그냥", "이것", "저것", "부분", "사람",
    "우리", "여기", "저기", "때문", "니다", "있다", "했다", "한다고", "있습니다"
}

allowed_pos = {"NNG", "NNP", "SL"}


def clean_text(text: str) -> str:
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def preprocess_text(text: str) -> str:
    text = clean_text(text)
    tokens = []
    for token in kiwi.tokenize(text):
        if token.tag in allowed_pos:
            word = token.form.strip().lower()
            if len(word) >= 2 and word not in stopwords and not word.isdigit():
                tokens.append(word)
    return " ".join(tokens)


@st.cache_data
def preprocess_dataframe(df: pd.DataFrame, text_col: str):
    df = df.copy()
    df["processed"] = df[text_col].fillna("").astype(str).apply(preprocess_text)
    return df


# ---------------------------
# 4. TF-IDF 계산
# ---------------------------
@st.cache_data
def build_tfidf(processed_series: pd.Series):
    vectorizer = TfidfVectorizer(
        max_features=1000,
        min_df=2,
        max_df=0.8
    )
    tfidf_matrix = vectorizer.fit_transform(processed_series)
    return vectorizer, tfidf_matrix


# ---------------------------
# 5. 키워드 추출
# ---------------------------
def get_top_keywords_by_topic(selected_topic, df, topic_col, tfidf_matrix, vectorizer, top_n=30):
    indices = df[df[topic_col] == selected_topic].index.tolist()
    if not indices:
        return pd.DataFrame(columns=["keyword", "score"])

    mean_tfidf = tfidf_matrix[indices].mean(axis=0)
    mean_tfidf = np.asarray(mean_tfidf).flatten()

    feature_names = vectorizer.get_feature_names_out()
    top_indices = mean_tfidf.argsort()[::-1][:top_n]

    rows = []
    for i in top_indices:
        score = float(mean_tfidf[i])
        if score > 0:
            rows.append((feature_names[i], score))

    keyword_df = pd.DataFrame(rows, columns=["keyword", "score"])
    return keyword_df


# ---------------------------
# 6. 워드클라우드 생성
# ---------------------------
def get_font_path():
    candidate_fonts = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",    # Colab / Linux
        "/usr/share/fonts/nanum/NanumGothic.ttf",              # Ubuntu 변형
        "C:/Windows/Fonts/malgun.ttf",                         # Windows
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",  # macOS
    ]
    for path in candidate_fonts:
        try:
            with open(path, "rb"):
                return path
        except Exception:
            continue
    return None


def make_wordcloud(keyword_df: pd.DataFrame):
    freq_dict = dict(zip(keyword_df["keyword"], keyword_df["score"]))
    font_path = get_font_path()

    wc = WordCloud(
        font_path=font_path,
        width=900,
        height=450,
        background_color="white",
        colormap="viridis",
        max_words=50
    ).generate_from_frequencies(freq_dict)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    return fig


# ---------------------------
# 7. 앱 실행
# ---------------------------
try:
    df_news = load_data("news_data.csv")
except FileNotFoundError:
    st.error("`news_data.csv` 파일을 찾을 수 없습니다. app.py와 같은 폴더에 넣어주세요.")
    st.stop()

# 컬럼 자동 감지
topic_col, text_col = detect_columns(df_news)

# ✅ 자동 감지 실패 시 — 사이드바에서 직접 선택 가능
if topic_col is None or text_col is None:
    st.warning(
        f"컬럼을 자동으로 찾지 못했습니다. 아래에서 직접 선택해주세요.\n\n"
        f"현재 컬럼: {list(df_news.columns)}"
    )
    all_cols = list(df_news.columns)
    topic_col = st.selectbox("주제 컬럼 선택", all_cols, index=0)
    text_col  = st.selectbox("본문 컬럼 선택", all_cols, index=min(1, len(all_cols)-1))

# ✅ 사이드바에서 컬럼 수동 변경 가능
with st.sidebar:
    st.header("⚙️ 설정")
    st.write(f"**자동 감지된 컬럼**")
    st.write(f"- 주제: `{topic_col}`")
    st.write(f"- 본문: `{text_col}`")
    st.markdown("---")
    override = st.checkbox("컬럼 직접 선택하기")
    if override:
        all_cols = list(df_news.columns)
        topic_col = st.selectbox("주제 컬럼", all_cols,
                                  index=all_cols.index(topic_col) if topic_col in all_cols else 0)
        text_col  = st.selectbox("본문 컬럼", all_cols,
                                  index=all_cols.index(text_col) if text_col in all_cols else 0)
    st.markdown("---")
    top_n = st.slider("추출 키워드 수", min_value=10, max_value=50, value=30, step=5)

with st.spinner("텍스트 전처리 중입니다..."):
    df_news = preprocess_dataframe(df_news, text_col)

with st.spinner("TF-IDF 계산 중입니다..."):
    vectorizer, tfidf_matrix = build_tfidf(df_news["processed"])

topics = sorted(df_news[topic_col].dropna().astype(str).unique().tolist())

selected_topic = st.selectbox("주제를 선택하세요", topics)

keyword_df = get_top_keywords_by_topic(
    selected_topic=selected_topic,
    df=df_news,
    topic_col=topic_col,
    tfidf_matrix=tfidf_matrix,
    vectorizer=vectorizer,
    top_n=top_n
)

if keyword_df.empty:
    st.warning("선택한 주제에서 추출할 키워드가 없습니다.")
    st.stop()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"'{selected_topic}' 워드클라우드")
    fig = make_wordcloud(keyword_df)
    st.pyplot(fig)

with col2:
    st.subheader("키워드 TOP 10")
    top10_df = keyword_df.head(10).copy()
    top10_df["score"] = top10_df["score"].round(4)
    top10_df.index = np.arange(1, len(top10_df) + 1)
    st.dataframe(top10_df, use_container_width=True)

st.markdown("---")
st.caption(f"사용 컬럼 → 주제: `{topic_col}`, 본문: `{text_col}`")