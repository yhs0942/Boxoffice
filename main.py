import json
import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import streamlit.components.v1 as components


# --------------------------------------------------
# 1. 기본 화면 설정
# --------------------------------------------------
st.set_page_config(
    page_title="일별 박스오피스",
    page_icon="🎬",
    layout="wide",
)

# 전체 화면에 영화관을 떠올리게 하는 어두운 그라데이션 배경과 카드 스타일을 적용합니다.
st.markdown("""
<style>
.stApp {
  background: radial-gradient(ellipse at 12% 0%, rgba(70, 92, 145, .28), transparent 36%),
              radial-gradient(ellipse at 92% 18%, rgba(139, 67, 91, .22), transparent 32%),
              linear-gradient(145deg, #10131d 0%, #171b29 48%, #10141e 100%);
  color: #f3f4f8;
}
[data-testid="stHeader"] { background: rgba(16, 19, 29, .65); }
[data-testid="stAppViewContainer"] .main .block-container {
  padding-top: 2.1rem; padding-bottom: 3rem; max-width: 1250px;
}
h1, h2, h3 { color: #f7f8fc !important; letter-spacing: -.025em; }
p, label, [data-testid="stCaptionContainer"] { color: #c5cada; }
[data-testid="stMetric"] {
  background: linear-gradient(135deg, rgba(39, 46, 67, .92), rgba(25, 30, 45, .92));
  border: 1px solid rgba(160, 177, 220, .2); border-radius: 16px;
  padding: 16px 18px; box-shadow: 0 8px 24px rgba(0,0,0,.16);
}
[data-testid="stMetricLabel"] { color: #b9c6e5 !important; }
[data-testid="stMetricValue"] { color: #ffffff !important; }
[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: rgba(160, 177, 220, .18) !important; border-radius: 16px;
}
[data-baseweb="select"] > div, [data-testid="stDateInput"] input {
  background: rgba(28, 34, 51, .9); color: #f7f8fc; border-color: #414b67;
}
hr { border-color: rgba(160, 177, 220, .2); }
[data-testid="stDataFrame"] {
  border: 1px solid rgba(160, 177, 220, .2); border-radius: 12px; overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

st.title("🎬 일별 박스오피스")
st.caption("영화진흥위원회(KOBIS) API로 날짜별 영화 순위를 확인합니다.")


# --------------------------------------------------
# 2. 한국 시간 기준 날짜 계산 및 달력 선택
# --------------------------------------------------
korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = korea_now.date() - timedelta(days=1)

st.subheader("📅 조회 날짜 선택")
selected_date = st.date_input(
    "박스오피스를 확인할 날짜",
    value=yesterday,
    max_value=yesterday,
    format="YYYY-MM-DD",
)
target_date = selected_date.strftime("%Y%m%d")
st.caption(f"선택한 날짜: {selected_date.strftime('%Y년 %m월 %d일')}")


# --------------------------------------------------
# 3. 공통 함수
# --------------------------------------------------
def to_number(value):
    """API에서 받은 문자열 숫자를 정수로 변환합니다."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def format_number(value):
    """숫자에 천 단위 쉼표를 붙입니다."""
    return f"{value:,}"


def format_rank_change(value):
    """순위 변화량을 화살표와 숫자로 표시합니다."""
    if value > 0:
        return f"↑ {value}"
    if value < 0:
        return f"↓ {abs(value)}"
    return "—"


def get_secret(name):
    """Secrets에 값이 있으면 반환하고, 없으면 빈 문자열을 반환합니다."""
    try:
        return str(st.secrets[name]).strip()
    except (KeyError, FileNotFoundError):
        return ""


# --------------------------------------------------
# 4. KOBIS 인증키 확인
# --------------------------------------------------
api_key = get_secret("KOBIS_KEY")
if not api_key:
    st.error("🔑 KOBIS API 인증키를 찾을 수 없습니다.")
    st.info(
        "Streamlit Cloud의 앱 설정 → Secrets에 "
        '`KOBIS_KEY = "발급받은_인증키"`를 등록해 주세요.'
    )
    st.stop()


# --------------------------------------------------
# 5. KOBIS 일별 박스오피스 API 요청
# --------------------------------------------------
api_url = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)
params = {"key": api_key, "targetDt": target_date}

try:
    with st.spinner("선택한 날짜의 박스오피스를 불러오는 중입니다..."):
        response = requests.get(api_url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
except requests.exceptions.Timeout:
    st.error("⏱️ API 응답 시간이 초과되었습니다.")
    st.info("인터넷 연결을 확인하거나 잠시 후 다시 시도해 주세요.")
    st.stop()
except requests.exceptions.HTTPError as error:
    st.error("🌐 API 서버에서 HTTP 오류가 발생했습니다.")
    st.write(f"오류 내용: {error}")
    st.info("KOBIS API 서버 상태와 요청 주소를 확인해 주세요.")
    st.stop()
except requests.exceptions.RequestException as error:
    st.error("🌐 API 요청에 실패했습니다.")
    st.write(f"오류 내용: {error}")
    st.info("인터넷 연결과 KOBIS API 서버 상태를 확인해 주세요.")
    st.stop()
except ValueError:
    st.error("📄 API 응답을 JSON 형식으로 읽을 수 없습니다.")
    st.info("KOBIS API 서버가 정상적으로 응답하는지 확인해 주세요.")
    st.stop()

if not isinstance(data, dict):
    st.error("API 응답 형식이 올바르지 않습니다.")
    st.info("KOBIS API 응답 내용을 확인해 주세요.")
    st.stop()

# 인증키가 잘못되어도 HTTP 상태코드가 200일 수 있어 faultInfo를 검사합니다.
if "faultInfo" in data:
    fault = data["faultInfo"]
    if isinstance(fault, dict):
        error_code = fault.get("errorCode", "확인 불가")
        error_message = fault.get("message", "오류 메시지가 없습니다.")
    else:
        error_code = "확인 불가"
        error_message = str(fault)
    st.error("🚨 KOBIS API에서 오류를 반환했습니다.")
    st.write(f"오류 코드: {error_code}")
    st.write(f"오류 메시지: {error_message}")
    st.info("Secrets에 등록한 KOBIS_KEY가 정확하고 유효한지 확인해 주세요.")
    st.stop()

box_office_result = data.get("boxOfficeResult")
if not isinstance(box_office_result, dict):
    st.error("박스오피스 결과를 찾을 수 없습니다.")
    st.info("API 응답에 boxOfficeResult가 있는지 확인해 주세요.")
    st.stop()

movie_list = box_office_result.get("dailyBoxOfficeList")
if not isinstance(movie_list, list) or not movie_list:
    st.warning("📭 그날은 아직 집계 전입니다")
    st.info(
        "선택한 날짜의 자료가 아직 제공되지 않았거나 해당 날짜에 "
        "조회할 자료가 없을 수 있습니다. 날짜를 다시 선택하거나 "
        "잠시 후 확인해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 6. 영화 목록 정리
# --------------------------------------------------
rows = []
for movie in movie_list:
    rank = to_number(movie.get("rank"))
    rank_change = to_number(movie.get("rankInten"))
    audience = to_number(movie.get("audiCnt"))
    total_audience = to_number(movie.get("audiAcc"))
    screens = to_number(movie.get("scrnCnt"))
    original_name = movie.get("movieNm", "영화명 없음")
    display_name = f"{original_name} 🏆" if total_audience > 1_000_000 else original_name

    rows.append({
        "순위": rank,
        "영화명": display_name,
        "원본영화명": original_name,
        "개봉일": movie.get("openDt", ""),
        "관객수": audience,
        "누적관객": total_audience,
        "스크린수": screens,
        "상영횟수": to_number(movie.get("showCnt")),
        "순위변동값": rank_change,
    })

df = pd.DataFrame(rows).sort_values("순위").reset_index(drop=True)
first_movie = df.iloc[0]


# --------------------------------------------------
# 7. 1위 영화 지표 카드 3개
# --------------------------------------------------
st.divider()
st.header(f"🏆 1위 영화: {first_movie['영화명']}")
st.caption(f"{selected_date.strftime('%Y년 %m월 %d일')} 집계 기준")

card1, card2, card3 = st.columns(3)
with card1:
    st.metric("🎟️ 관객수", f"{format_number(first_movie['관객수'])}명")
with card2:
    st.metric("👥 누적 관객수", f"{format_number(first_movie['누적관객'])}명")
with card3:
    st.metric("🖥️ 스크린수", f"{format_number(first_movie['스크린수'])}개")


# --------------------------------------------------
# 8. 영화 포스터 조회 함수 (TMDB)
# --------------------------------------------------
# 포스터는 TMDB에서 가져오며, 감상평 조회 기능은 사용하지 않습니다.
@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_movie_poster(movie_name, release_date, tmdb_key):
    """TMDB에서 영화 포스터와 영화 정보 링크만 가져옵니다."""
    result = {"poster": "", "source_url": "https://www.themoviedb.org/"}
    if not tmdb_key:
        return result

    search_url = "https://api.themoviedb.org/3/search/movie"
    search_params = {
        "api_key": tmdb_key,
        "query": movie_name,
        "language": "ko-KR",
        "include_adult": "false",
    }
    if release_date:
        try:
            search_params["year"] = int(release_date[:4])
        except (ValueError, TypeError):
            pass

    try:
        response = requests.get(search_url, params=search_params, timeout=8)
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            search_params.pop("language", None)
            response = requests.get(search_url, params=search_params, timeout=8)
            response.raise_for_status()
            results = response.json().get("results", [])
        if results:
            movie = results[0]
            if movie.get("poster_path"):
                result["poster"] = "https://image.tmdb.org/t/p/w500" + movie["poster_path"]
            if movie.get("id"):
                result["source_url"] = f"https://www.themoviedb.org/movie/{movie['id']}"
    except (requests.exceptions.RequestException, ValueError, TypeError, KeyError):
        pass
    return result


# --------------------------------------------------
# 9. 관객수 상위 5편 그래프와 마우스 오버 포스터
# --------------------------------------------------
st.divider()
st.header("📊 관객수 상위 5편")
st.caption("막대에 마우스를 올리면 영화 포스터를 확인할 수 있습니다.")

top5 = df.nlargest(5, "관객수").copy().sort_values("관객수", ascending=True)
tmdb_key = get_secret("TMDB_KEY")
movie_extras = {}

if not tmdb_key:
    st.info("영화 포스터를 표시하려면 Streamlit Cloud의 Secrets에 TMDB_KEY를 등록해 주세요.")

with st.spinner("상위 5편의 포스터를 확인하는 중입니다..."):
    for _, movie in top5.iterrows():
        name = str(movie["원본영화명"])
        movie_extras[name] = get_movie_poster(name, str(movie["개봉일"]), tmdb_key)

hover_details = []
for _, movie in top5.iterrows():
    name = str(movie["원본영화명"])
    extra = movie_extras.get(name, {})
    hover_details.append({
        "name": name,
        "audience": int(movie["관객수"]),
        "poster": extra.get("poster", ""),
        "source_url": extra.get("source_url", "https://www.themoviedb.org/"),
    })

chart_payload = json.dumps(hover_details, ensure_ascii=False).replace("</", "<\\/")
chart_html = r"""
<div id="chart-wrap" style="font-family:Arial,sans-serif;position:relative;width:100%;">
  <div id="audience-chart" style="width:100%;height:430px;"></div>
  <div id="movie-card" style="
      display:none; position:absolute; z-index:20; top:12px; right:12px;
      width:min(280px, 44%); max-height:350px; overflow:auto;
      background:#202638; color:#f5f6fb; border:1px solid #46516f; border-radius:14px;
      box-shadow:0 8px 28px rgba(0,0,0,.35); padding:13px; box-sizing:border-box;">
    <div id="movie-title" style="font-size:16px;font-weight:700;margin-bottom:10px;"></div>
    <img id="movie-poster" alt="영화 포스터" style="
      display:none; width:auto; max-width:100%; max-height:245px;
      object-fit:contain; border-radius:7px; margin:0 auto 10px;">
    <div id="movie-poster-note" style="font-size:12px;color:#c5cada;margin-top:4px;">포스터 제공: TMDB</div>
    <a id="movie-source-link" href="#" target="_blank" rel="noopener noreferrer"
       style="display:none;font-size:12px;margin-top:8px;color:#a9c9ff;">TMDB 영화 정보 보기 ↗</a>
  </div>
</div>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
const details = __DETAILS__;
const names = details.map(d => d.name);
const counts = details.map(d => d.audience);
const trace = {
  type: "bar", orientation: "h", x: counts, y: names,
  marker: {color: "#8ca8f5", line: {color: "#c0ceff", width: 1}},
  text: counts.map(n => n.toLocaleString("ko-KR") + "명"),
  textposition: "outside", cliponaxis: false,
  hovertemplate: "<b>%{y}</b><br>관객수: %{x:,}명<extra></extra>"
};
const layout = {
  margin: {l: 12, r: 65, t: 20, b: 55},
  xaxis: {title: "관객수(명)", rangemode: "tozero", separatethousands: true,
          gridcolor: "rgba(190,200,230,.14)", zerolinecolor: "rgba(190,200,230,.2)", color: "#dce2f4"},
  yaxis: {title: "", automargin: true, color: "#e5e9f6"},
  showlegend: false, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  font: {family: "Arial, sans-serif", size: 12, color: "#e5e9f6"}
};
Plotly.newPlot("audience-chart", [trace], layout, {responsive:true, displayModeBar:false}).then(gd => {
  const card = document.getElementById("movie-card");
  const title = document.getElementById("movie-title");
  const poster = document.getElementById("movie-poster");
  const link = document.getElementById("movie-source-link");
  gd.on("plotly_hover", eventData => {
    if (!eventData || !eventData.points || !eventData.points.length) return;
    const item = details.find(d => d.name === eventData.points[0].y);
    if (!item) return;
    title.textContent = item.name + " · " + item.audience.toLocaleString("ko-KR") + "명";
    poster.style.display = "none"; poster.removeAttribute("src");
    if (item.poster) {
      poster.src = item.poster;
      poster.onload = () => { poster.style.display = "block"; };
      poster.onerror = () => { poster.style.display = "none"; };
    }
    link.href = item.source_url || "https://www.themoviedb.org/";
    link.style.display = "inline-block";
    card.style.display = "block";
  });
});
</script>
"""
chart_html = chart_html.replace("__DETAILS__", chart_payload)
components.html(chart_html, height=455, scrolling=False)


# --------------------------------------------------
# 10. 전체 박스오피스 표
# --------------------------------------------------
st.divider()
st.header("🎞️ 전체 일별 박스오피스")

table_df = df[
    ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수", "순위변동값"]
].copy()

table_df["순위 변동"] = table_df["순위변동값"].map(format_rank_change)
table_df = table_df.drop(columns=["순위변동값"])

for column in ["관객수", "누적관객", "스크린수"]:
    table_df[column] = table_df[column].map(format_number)


def color_rank_change(value):
    """순위 상승은 빨간색, 하락은 파란색으로 표시합니다."""
    if value.startswith("↑"):
        return "color: red; font-weight: bold"
    if value.startswith("↓"):
        return "color: blue; font-weight: bold"
    return "color: gray"


styled_table = table_df.style.map(
    color_rank_change,
    subset=["순위 변동"],
)
st.dataframe(styled_table, use_container_width=True, hide_index=True)


# --------------------------------------------------
# 11. 추가 정보
# --------------------------------------------------
with st.expander("추가 정보: 상영횟수와 순위 변동"):
    extra_df = df[["순위", "영화명", "상영횟수", "순위변동값"]].copy()
    extra_df["순위 변동"] = extra_df["순위변동값"].map(format_rank_change)
    extra_df = extra_df.drop(columns=["순위변동값"])
    extra_df["상영횟수"] = extra_df["상영횟수"].map(format_number)
    st.dataframe(extra_df, use_container_width=True, hide_index=True)

st.caption("박스오피스 자료: 영화진흥위원회(KOBIS) · 포스터: TMDB")
