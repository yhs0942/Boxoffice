
import streamlit as st
import pandas as pd
import requests
import plotly.express as px

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------------
# 1. 기본 화면 설정
# --------------------------------------------------
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 일별 박스오피스")
st.caption("영화진흥위원회(KOBIS) API로 날짜별 영화 순위를 확인합니다.")


# --------------------------------------------------
# 2. 한국 시간 기준 날짜 계산
# --------------------------------------------------
# 배포 서버의 시간대와 관계없이 한국 날짜를 사용합니다.
korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = korea_now.date() - timedelta(days=1)


# --------------------------------------------------
# 3. 달력에서 조회 날짜 선택
# --------------------------------------------------
st.subheader("📅 조회 날짜 선택")

selected_date = st.date_input(
    "박스오피스를 확인할 날짜",
    value=yesterday,
    max_value=yesterday,
    format="YYYY-MM-DD"
)

# KOBIS API가 요구하는 YYYYMMDD 형식으로 변환합니다.
target_date = selected_date.strftime("%Y%m%d")

st.caption(
    f"선택한 날짜: {selected_date.strftime('%Y년 %m월 %d일')}"
)


# --------------------------------------------------
# 4. 숫자 변환 및 표시 함수
# --------------------------------------------------
def to_number(value):
    """API에서 받은 문자열 숫자를 정수로 바꿉니다."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def format_number(value):
    """숫자에 천 단위 쉼표를 붙입니다."""
    return f"{value:,}"


def format_rank_change(value):
    """순위 변화에 따라 화살표와 변화량을 표시합니다."""
    if value > 0:
        return f"↑ {value}"
    elif value < 0:
        return f"↓ {abs(value)}"
    else:
        return "—"


# --------------------------------------------------
# 5. 비밀 금고에서 API 인증키 불러오기
# --------------------------------------------------
try:
    api_key = st.secrets["KOBIS_KEY"]

except (KeyError, FileNotFoundError):
    st.error("🔑 KOBIS API 인증키를 찾을 수 없습니다.")
    st.info(
        "Streamlit Cloud의 앱 설정에서 Secrets를 열고 "
        "KOBIS_KEY를 등록했는지 확인해 주세요."
    )
    st.code('KOBIS_KEY = "본인의_API_인증키"')
    st.stop()


# --------------------------------------------------
# 6. KOBIS API 요청
# --------------------------------------------------
api_url = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

params = {
    "key": api_key,
    "targetDt": target_date
}

try:
    with st.spinner("선택한 날짜의 박스오피스를 불러오는 중입니다..."):
        response = requests.get(
            api_url,
            params=params,
            timeout=20
        )

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


# --------------------------------------------------
# 7. API 응답 오류 확인
# --------------------------------------------------
if not isinstance(data, dict):
    st.error("API 응답 형식이 올바르지 않습니다.")
    st.info("KOBIS API 응답 내용을 확인해 주세요.")
    st.stop()

# 인증키가 틀려도 HTTP 상태코드가 200일 수 있습니다.
# 따라서 응답 안의 faultInfo를 별도로 확인합니다.
if "faultInfo" in data:
    fault = data["faultInfo"]

    if isinstance(fault, dict):
        error_code = fault.get("errorCode", "확인 불가")
        error_message = fault.get(
            "message",
            "오류 메시지가 없습니다."
        )
    else:
        error_code = "확인 불가"
        error_message = str(fault)

    st.error("🚨 KOBIS API에서 오류를 반환했습니다.")
    st.write(f"오류 코드: {error_code}")
    st.write(f"오류 메시지: {error_message}")
    st.info(
        "Secrets에 등록한 KOBIS_KEY가 정확한지, "
        "인증키가 유효한지 확인해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 8. 영화 목록 확인
# --------------------------------------------------
box_office_result = data.get("boxOfficeResult")

if not isinstance(box_office_result, dict):
    st.error("박스오피스 결과를 찾을 수 없습니다.")
    st.info("API 응답에 boxOfficeResult가 있는지 확인해 주세요.")
    st.stop()

movie_list = box_office_result.get("dailyBoxOfficeList")

# 선택한 날짜에 영화 목록이 없으면 안내 메시지를 표시합니다.
if not isinstance(movie_list, list) or len(movie_list) == 0:
    st.warning("📭 그날은 아직 집계 전입니다")
    st.info(
        "선택한 날짜의 박스오피스 자료가 아직 제공되지 않았거나 "
        "해당 날짜에 조회할 자료가 없을 수 있습니다. "
        "날짜를 다시 선택하거나 잠시 후 확인해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 9. 영화 목록 정리
# --------------------------------------------------
rows = []

for movie in movie_list:
    # 숫자로 제공되는 값은 문자열이므로 정수로 변환합니다.
    rank = to_number(movie.get("rank"))
    rank_change = to_number(movie.get("rankInten"))
    audience = to_number(movie.get("audiCnt"))
    total_audience = to_number(movie.get("audiAcc"))
    screens = to_number(movie.get("scrnCnt"))

    # 누적 관객수가 100만 명을 초과하면 트로피를 붙입니다.
    movie_name = movie.get("movieNm", "영화명 없음")

    if total_audience > 1_000_000:
        movie_name = f"{movie_name} 🏆"

    rows.append({
        "순위": rank,
        "영화명": movie_name,
        "개봉일": movie.get("openDt", ""),
        "관객수": audience,
        "누적관객": total_audience,
        "스크린수": screens,
        "상영횟수": to_number(movie.get("showCnt")),
        "순위변동값": rank_change
    })

df = pd.DataFrame(rows)
df = df.sort_values("순위").reset_index(drop=True)

# 1위 영화 정보를 가져옵니다.
first_movie = df.iloc[0]


# --------------------------------------------------
# 10. 1위 영화 지표 카드 3개
# --------------------------------------------------
st.divider()
st.header(f"🏆 1위 영화: {first_movie['영화명']}")

st.caption(
    f"{selected_date.strftime('%Y년 %m월 %d일')} 집계 기준"
)

card1, card2, card3 = st.columns(3)

with card1:
    st.metric(
        label="🎟️ 관객수",
        value=f"{format_number(first_movie['관객수'])}명"
    )

with card2:
    st.metric(
        label="👥 누적 관객수",
        value=f"{format_number(first_movie['누적관객'])}명"
    )

with card3:
    st.metric(
        label="🖥️ 스크린수",
        value=f"{format_number(first_movie['스크린수'])}개"
    )


# --------------------------------------------------
# 11. 관객수 상위 5편 막대그래프
# --------------------------------------------------
st.divider()
st.header("📊 관객수 상위 5편")

top5 = df.nlargest(5, "관객수").copy()

# 막대그래프에서 관객수가 많은 영화가 위에 표시되도록 정렬합니다.
top5 = top5.sort_values("관객수", ascending=True)

fig = px.bar(
    top5,
    x="관객수",
    y="영화명",
    orientation="h",
    text="관객수",
    labels={
        "관객수": "관객수(명)",
        "영화명": "영화명"
    },
    title="선택한 날짜의 관객수 TOP 5"
)

fig.update_traces(
    texttemplate="%{text:,}명",
    textposition="outside",
    cliponaxis=False
)

fig.update_layout(
    yaxis_title="",
    xaxis_title="관객수(명)",
    showlegend=False,
    margin=dict(l=10, r=65, t=60, b=20)
)

st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# 12. 전체 박스오피스 표
# --------------------------------------------------
st.divider()
st.header("🎞️ 전체 일별 박스오피스")

table_df = df[
    [
        "순위",
        "영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수",
        "순위변동값"
    ]
].copy()

# 순위 변화 값을 화살표와 숫자로 바꿉니다.
table_df["순위 변동"] = table_df["순위변동값"].map(
    format_rank_change
)

# 원래 숫자형 순위 변화 열은 화면에서 제외합니다.
table_df = table_df.drop(columns=["순위변동값"])

# 관객수와 스크린수에 천 단위 쉼표를 적용합니다.
for column in ["관객수", "누적관객", "스크린수"]:
    table_df[column] = table_df[column].map(format_number)


# 화살표 색상을 지정합니다.
# 양수는 빨간색, 음수는 파란색, 변동 없음은 회색입니다.
def color_rank_change(value):
    if value.startswith("↑"):
        return "color: red; font-weight: bold"
    elif value.startswith("↓"):
        return "color: blue; font-weight: bold"
    return "color: gray"


styled_table = table_df.style.map(
    color_rank_change,
    subset=["순위 변동"]
)

st.dataframe(
    styled_table,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 13. 추가 정보
# --------------------------------------------------
with st.expander("추가 정보: 상영횟수와 순위 변동"):
    extra_df = df[
        ["순위", "영화명", "상영횟수", "순위변동값"]
    ].copy()

    extra_df["순위 변동"] = extra_df["순위변동값"].map(
        format_rank_change
    )

    extra_df = extra_df.drop(columns=["순위변동값"])
    extra_df["상영횟수"] = extra_df["상영횟수"].map(format_number)

    st.dataframe(
        extra_df,
        use_container_width=True,
        hide_index=True
    )

st.caption(
    "자료 출처: 영화진흥위원회(KOBIS) 일별 박스오피스 API"
)
