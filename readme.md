# 📰 뉴스 키워드 분석 앱

> 매일 주요 뉴스를 자동 수집하고, TF-IDF 기반으로 핵심 키워드를 시각화하는 Streamlit 앱입니다.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app.streamlit.app)

---

## 📌 주요 기능

| 기능 | 설명 |
|---|---|
| 뉴스 자동 수집 | 8개 주제별 RSS 피드에서 매일 뉴스 수집 |
| 한국어 형태소 분석 | KiwiPiepy로 명사 추출 및 불용어 제거 |
| TF-IDF 키워드 추출 | 주제별 핵심 키워드 자동 추출 |
| 워드클라우드 | 키워드 빈도를 시각적으로 표현 |
| 막대 차트 | TOP 10 키워드 TF-IDF 점수 비교 |
| 기사 링크 연결 | 제목 클릭 시 원본 기사로 이동 |
| 자동 배포 | GitHub Actions + Streamlit Cloud 연동 |

---

## 🗂 프로젝트 구조

```
NLP_App/
├── app.py                          # Streamlit 메인 앱
├── collect_news.py                 # 뉴스 수집 스크립트
├── news_data.csv                   # 수집된 뉴스 데이터 (자동 생성)
├── requirements.txt                # Python 패키지 목록
├── packages.txt                    # 시스템 패키지 (한글 폰트)
└── .github/
    └── workflows/
        └── collect_news.yml        # GitHub Actions 자동 수집
```

---

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone https://github.com/아이디/NLP_App.git
cd NLP_App
```

### 2. 가상환경 생성 및 패키지 설치
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Mac/Linux

pip install -r requirements.txt
```

### 3. 뉴스 수집
```bash
python collect_news.py
```

### 4. 앱 실행
```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## 📊 수집 주제

| 주제 | RSS 출처 |
|---|---|
| 정치 | 경향신문, 전자신문 |
| 경제 | 경향신문, 전자신문 |
| 사회 | 경향신문, 중앙일보 |
| IT/과학 | 전자신문, ZDNet |
| AI/인공지능 | 전자신문, AI타임스 |
| 스포츠 | 경향신문 |
| 문화/연예 | 경향신문 |
| 국제 | 경향신문 |

---

## 🗃 데이터 구조

`news_data.csv` 컬럼 설명:

| 컬럼 | 설명 |
|---|---|
| `date` | 수집 날짜 (YYYY-MM-DD) |
| `query` | 뉴스 주제 |
| `title` | 기사 제목 |
| `description` | 기사 요약 |
| `link` | 원본 기사 URL |
| `published` | 기사 발행 시각 |
| `source` | 언론사 이름 |

> 매일 수집 시 **최근 30일치**만 유지되며 중복 기사는 자동 제거됩니다.

---

## ⚙️ GitHub Actions 자동 수집

매일 **오전 8시(KST)** 에 자동으로 뉴스를 수집합니다.

```
매일 오전 8시
    ↓ GitHub Actions 실행
    ↓ collect_news.py 실행
    ↓ news_data.csv 업데이트
    ↓ GitHub 자동 커밋
    ↓ Streamlit Cloud 자동 재배포
```

수동 실행은 GitHub → Actions → `매일 뉴스 자동 수집` → `Run workflow`

---

## ☁️ Streamlit Cloud 배포

### 배포 순서
1. GitHub에 저장소 Public으로 생성
2. 모든 파일 push
3. [share.streamlit.io](https://share.streamlit.io) 접속
4. `New app` → 저장소 선택 → `app.py` 선택 → `Deploy`

### 비용
| 서비스 | 무료 한도 | 실제 사용 |
|---|---|---|
| GitHub | 무제한 (Public) | - |
| GitHub Actions | 월 2,000분 | 약 30분/월 |
| Streamlit Cloud | 무제한 (Public) | - |

**총 비용: 0원**

---

## 🔧 기술 스택

| 분류 | 기술 |
|---|---|
| 앱 프레임워크 | Streamlit |
| 한국어 NLP | KiwiPiepy (형태소 분석) |
| 키워드 추출 | TF-IDF (scikit-learn) |
| 시각화 | WordCloud, Matplotlib |
| 뉴스 수집 | feedparser, BeautifulSoup4 |
| 자동화 | GitHub Actions |
| 배포 | Streamlit Cloud |

---

## 📖 NLP 핵심 개념

이 앱은 다음 NLP 개념을 활용합니다:

**토큰화 (Tokenization)**
```
"삼성전자가 신제품을 발표했다"
→ ['삼성전자', '신제품', '발표']  (명사만 추출)
```

**TF-IDF**
```
TF  = 이 문서에서 단어가 얼마나 자주 나오나
IDF = 전체 문서에서 얼마나 희귀한 단어인가

점수가 높을수록 = 이 주제를 대표하는 핵심 단어
```

---

## 🔄 뉴스 수동 업데이트

로컬에서 수집 후 GitHub에 반영:
```bash
python collect_news.py
git add news_data.csv
git commit -m "뉴스 업데이트 $(date +%Y-%m-%d)"
git push
```

---

## 📝 라이선스

MIT License

---

## 🙋 문의

이슈는 [GitHub Issues](https://github.com/아이디/NLP_App/issues) 로 남겨주세요.
