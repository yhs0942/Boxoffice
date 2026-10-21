
# 필요한 라이브러리 불러오기
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

st.title("🎬 어제의 박스오피스")
st.caption("영화진흥위원회(KOBIS) 일별 박스오피스 API를 이용합니다.")


# --------------------------------------------------
# 2. 한국 시간 기준으로 어제 날짜 계산하기
# --------------------------------------------------
# 서버가 어느 나라 시간을 사용하든 한국 시간으로 날짜를 계산합니다.
korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = (korea_now.date() - timedelta(days=1))

# API에서 요구하는 날짜 형식: YYYYMMDD
target_date = yesterday.strftime("%Y%m%d")

st.subheader(f"📅 조회 날짜: {yesterday.strftime('%Y년 %m월 %d일')}")


# --------------------------------------------------
# 3. 숫자 표시를 위한 함수
# --------------------------------------------------
def to_number(value):
    """API에서 받은 문자열 숫자를 정수로 변환합니다."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def format_number(value):
    """숫자에 천 단위 쉼표를 넣어 보기 쉽게 표시합니다."""
    return f"{value:,}"


# --------------------------------------------------
# 4. KOBIS API 요청하기
# --------------------------------------------------
# 인증키는 코드에 직접 입력하지 않고 Streamlit 비밀 금고에서 읽습니다.
try:
    api_key = st.secrets["KOBIS_KEY"]
except (KeyError, FileNotFoundError):
    st.error(
        "🔑 인증키를 찾을 수 없습니다.\n\n"
        "Streamlit Cloud의 앱 설정에서 Secrets를 열고 "
        "아래 내용을 등록했는지 확인해 주세요."
    )
    st.code('KOBIS_KEY = "발급받은_인증키"')
    st.info(
        "인증키는 main.py에 입력하지 마세요. "
        "Streamlit Cloud의 Secrets에만 등록해야 합니다."
    )
    st.stop()


# 공식 일별 박스오피스 API 주소
api_url = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

# 인증키와 조회 날짜를 요청 변수로 전달합니다.
params = {
    "key": api_key,
    "targetDt": target_date
}

# API 응답을 저장할 변수를 준비합니다.
data = None

try:
    with st.spinner("어제의 영화 관객 정보를 불러오는 중입니다..."):
        response = requests.get(
            api_url,
            params=params,
            timeout=20
        )

        # HTTP 오류가 발생하면 예외를 발생시킵니다.
        response.raise_for_status()

        # JSON 형식으로 응답을 읽습니다.
        data = response.json()

except requests.exceptions.Timeout:
    st.error("⏱️ API 응답 시간이 초과되었습니다.")
    st.warning(
        "인터넷 연결 상태를 확인하거나 잠시 후 다시 실행해 주세요."
    )
    st.stop()

except requests.exceptions.HTTPError as error:
    st.error("🌐 API 서버에서 HTTP 오류가 발생했습니다.")
    st.write(f"오류 내용: {error}")
    st.info(
        "KOBIS API 서버의 상태와 요청 주소를 확인해 주세요."
    )
    st.stop()

except requests.exceptions.RequestException as error:
    st.error("🌐 API 요청에 실패했습니다.")
    st.write(f"오류 내용: {error}")
    st.info(
        "인터넷 연결, API 서버 상태, 요청 주소를 확인해 주세요."
    )
    st.stop()

except ValueError:
    st.error("📄 API 응답을 JSON으로 읽을 수 없습니다.")
    st.info(
        "KOBIS API 서버가 정상적으로 응답하는지 확인해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 5. API 응답에 오류 상자가 있는지 확인하기
# --------------------------------------------------
# 인증키가 잘못되어도 HTTP 상태코드가 200일 수 있으므로
# 응답 안에 faultInfo가 있는지 별도로 검사합니다.
if not isinstance(data, dict):
    st.error("API 응답의 형식이 올바르지 않습니다.")
    st.info("KOBIS API 응답 형식을 확인해 주세요.")
    st.stop()

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
    st.warning(
        "Secrets의 KOBIS_KEY가 정확한지, 인증키가 유효한지 "
        "확인해 주세요. API 요청 변수와 이용 권한도 확인해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 6. 영화 목록 가져오기
# --------------------------------------------------
box_office_result = data.get("boxOfficeResult")

if not isinstance(box_office_result, dict):
    st.error("박스오피스 결과를 찾을 수 없습니다.")
    st.info(
        "API 응답에 boxOfficeResult가 있는지 확인해 주세요."
    )
    st.stop()

movie_list = box_office_result.get("dailyBoxOfficeList")

if not isinstance(movie_list, list) or len(movie_list) == 0:
    st.warning("해당 날짜의 영화 목록이 비어 있습니다.")
    st.info(
        "조회 날짜에 집계된 자료가 있는지, "
        "KOBIS API가 정상적으로 데이터를 제공하는지 확인해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 7. 영화 데이터를 표에 맞게 정리하기
# --------------------------------------------------
rows = []

for movie in movie_list:
    # API의 숫자 값은 문자열이므로 정수로 변환합니다.
    rows.append({
        "순위": to_number(movie.get("rank")),
        "영화명": movie.get("movieNm", "영화명 없음"),
        "개봉일": movie.get("openDt", ""),
        "관객수": to_number(movie.get("audiCnt")),
        "누적관객": to_number(movie.get("audiAcc")),
        "스크린수": to_number(movie.get("scrnCnt")),
        "상영횟수": to_number(movie.get("showCnt")),
        "전일 대비 순위": to_number(movie.get("rankInten"))
    })

df = pd.DataFrame(rows)

# 순위를 기준으로 오름차순 정렬합니다.
df = df.sort_values("순위").reset_index(drop=True)

# 1위 영화 정보를 가져옵니다.
first_movie = df.iloc[0]


# --------------------------------------------------
# 8. 1위 영화 지표 카드 3개
# --------------------------------------------------
st.divider()
st.header(f"🏆 오늘의 주인공: {first_movie['영화명']}")

st.caption("아래 지표는 조회 날짜인 어제의 집계 결과입니다.")

card1, card2, card3 = st.columns(3)

with card1:
    st.metric(
        label="🎟️ 어제 관객수",
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
# 9. 관객수 상위 5편 막대그래프
# --------------------------------------------------
st.divider()
st.header("📊 관객수 상위 5편")

# 순위와 관계없이 관객수가 많은 영화부터 5편을 선택합니다.
top5 = df.sort_values(
    "관객수", ascending=False
).head(5).copy()

# 그래프에서 위쪽에 관객수가 많은 영화가 보이도록 정렬합니다.
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
    title="어제 관객수 기준 TOP 5"
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
    margin=dict(l=10, r=60, t=60, b=20)
)

st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# 10. 전체 박스오피스 표
# --------------------------------------------------
st.divider()
st.header("🎞️ 전체 일별 박스오피스 순위")

# 표에 표시할 열을 선택합니다.
table_df = df[
    ["순위", "영화명", "개봉일", "관객수",
     "누적관객", "스크린수"]
].copy()

# 숫자에 천 단위 쉼표를 적용해 읽기 쉽게 만듭니다.
for column in ["관객수", "누적관객", "스크린수"]:
    table_df[column] = table_df[column].map(format_number)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True
)

# 상영횟수 등 추가 정보는 표 아래에서 확인할 수 있습니다.
with st.expander("추가 정보: 상영횟수와 전일 대비 순위"):
    extra_df = df[
        ["순위", "영화명", "상영횟수", "전일 대비 순위"]
    ].copy()

    extra_df["상영횟수"] = extra_df["상영횟수"].map(format_number)

    st.dataframe(
        extra_df,
        use_container_width=True,
        hide_index=True
    )

st.caption(
    "자료 출처: 영화진흥위원회(KOBIS) 일별 박스오피스 API"
)
