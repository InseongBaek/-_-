# ✅ 모의투자 웹앱 - 최신 통합 버전 (UI 정상 출력 보장)

import streamlit as st
import pandas as pd
import hashlib
import datetime
import time
import json
import os
from streamlit_autorefresh import st_autorefresh
import matplotlib.pyplot as plt

USERS_FILE = 'users_db.json'
PORTFOLIO_FILE = 'portfolios.json'

# ----------------- 사용자 및 포트폴리오 저장/불러오기 -----------------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {
        "admin": {"password": hashlib.sha256("admin123".encode()).hexdigest(), "is_admin": True, "initial_balance": 10000, "balance": 10000},
        "user1": {"password": hashlib.sha256("test123".encode()).hexdigest(), "is_admin": False, "initial_balance": 10000, "balance": 10000}
    }

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def load_portfolios():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_portfolios(portfolios):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolios, f)

def save_all():
    save_users(st.session_state.users_db)
    save_portfolios(st.session_state.portfolios)

# ----------------- 초기 설정 -----------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ''
    st.session_state.is_admin = False

if 'users_db' not in st.session_state:
    st.session_state.users_db = load_users()

if 'portfolios' not in st.session_state:
    st.session_state.portfolios = load_portfolios()

if 'market_time' not in st.session_state:
    st.session_state.market_time = datetime.datetime(2018, 1, 3, 9, 30)

if 'last_auto_update' not in st.session_state:
    st.session_state.last_auto_update = time.time()

if 'price_log' not in st.session_state:
    st.session_state.price_log = {'AAPL': []}

if 'previous_day' not in st.session_state:
    st.session_state.previous_day = st.session_state.market_time.date()

if 'view' not in st.session_state:
    st.session_state.view = 'home'

# ----------------- 데이터 로딩 -----------------
@st.cache_data
def load_data():
    df = pd.read_csv('aapl_2018_q1_5min.csv', parse_dates=['Datetime'])
    return df.sort_values('Datetime')

aapl_df = load_data()

# ----------------- 로그인 UI -----------------
def login_ui():
    st.title("📥 로그인 또는 회원가입")
    tab1, tab2 = st.tabs(["🔐 로그인", "🧾 회원가입"])

    with tab1:
        username = st.text_input("사용자 이름")
        password = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            hashed = hashlib.sha256(password.encode()).hexdigest()
            user = st.session_state.users_db.get(username)
            if user and user['password'] == hashed:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.is_admin = user['is_admin']
                st.rerun()
            else:
                st.error("❌ 로그인 실패. 사용자명 또는 비밀번호를 확인하세요.")

    with tab2:
        new_username = st.text_input("새 사용자 이름")
        new_password = st.text_input("새 비밀번호", type="password")
        if st.button("회원가입"):
            if new_username in st.session_state.users_db:
                st.warning("이미 존재하는 사용자입니다.")
            else:
                st.session_state.users_db[new_username] = {
                    "password": hashlib.sha256(new_password.encode()).hexdigest(),
                    "is_admin": False,
                    "initial_balance": 10000,
                    "balance": 10000
                }
                save_users(st.session_state.users_db)
                st.success("회원가입 성공! 로그인 해주세요.")

    st.markdown("""
    ---
    🛠️ **관리자 계정 정보 (테스트용)**  
    - ID: `admin`  
    - PW: `admin123`
    """)

# ----------------- 유틸 함수 -----------------
def get_current_price(current_time):
    closest = (aapl_df['Datetime'] - current_time).abs().idxmin()
    return float(aapl_df.loc[closest, 'Close'])

def get_previous_close(current_time):
    prev_day = current_time.date() - datetime.timedelta(days=1)
    prev_data = aapl_df[aapl_df['Datetime'].dt.date == prev_day]
    return float(prev_data['Close'].iloc[-1]) if not prev_data.empty else None

def get_current_user_data():
    username = st.session_state.username
    return username, st.session_state.users_db[username]

# ----------------- 포트폴리오 기능 -----------------
def portfolio_view():
    st.subheader("📁 나의 자산 포트폴리오")
    username, user_data = get_current_user_data()
    portfolios = st.session_state.portfolios.get(username, [])
    df = pd.DataFrame(portfolios)

    if df.empty:
        st.info("보유 종목이 없습니다.")
        return

    current_price = get_current_price(st.session_state.market_time)
    data = []
    for ticker in df['ticker'].unique():
        buy_df = df[(df['ticker'] == ticker) & (df['type'] == '매수')]
        sell_df = df[(df['ticker'] == ticker) & (df['type'] == '매도')]
        buy_qty = buy_df['shares'].sum()
        sell_qty = sell_df['shares'].sum()
        net_qty = buy_qty - sell_qty
        if net_qty <= 0:
            continue
        avg_price = (buy_df['shares'] * buy_df['price']).sum() / buy_qty
        market_value = net_qty * current_price
        data.append([ticker, net_qty, round(avg_price, 2), round(current_price, 2), round(market_value, 2)])

    result = pd.DataFrame(data, columns=['종목', '보유수량', '평균단가', '현재가', '평가금액'])
    st.dataframe(result, use_container_width=True)

    import matplotlib
    matplotlib.rc('font', family='Malgun Gothic')
    matplotlib.rcParams['axes.unicode_minus'] = False

    pie_labels = list(result['종목']) + ['현금']
    pie_values = list(result['평가금액']) + [user_data['balance']]

    fig, ax = plt.subplots()
    ax.pie(pie_values, labels=pie_labels, autopct='%1.1f%%')
    ax.set_title("보유 자산 비율")
    st.pyplot(fig)

    total_value = result['평가금액'].sum()
    cash = user_data['balance']
    total_assets = total_value + cash

    st.markdown(f"💰 **총 자산**: ${total_assets:,.2f} (주식 평가금액: ${total_value:.2f}, 현금: ${cash:.2f})")


# ----------------- 거래 기능 -----------------
def trade_view():
    st.subheader("💼 매수/매도 시뮬레이션")
    username, user_data = get_current_user_data()
    portfolios = st.session_state.portfolios
    current_price = get_current_price(st.session_state.market_time)
    if current_price is None:
        st.warning("현재가 데이터를 불러올 수 없습니다.")
        return

    ticker = st.selectbox("종목 선택", ["AAPL"])
    action = st.radio("동작 선택", ["매수", "매도"], horizontal=True)
    trades = portfolios.get(username, [])
    owned = sum(r['shares'] for r in trades if r['ticker'] == ticker and r['type'] == '매수') - \
            sum(r['shares'] for r in trades if r['ticker'] == ticker and r['type'] == '매도')
    st.markdown(f"📦 현재 보유 수량: {owned}주")

    quantity = st.number_input("수량", min_value=1, step=1)
    st.markdown(f"💰 현재 잔고: ${user_data['balance']:.2f}")
    potential_cost = current_price * quantity
    st.markdown(f"💸 예상 거래 금액: ${potential_cost:.2f}")

    if st.button("거래 실행"):
        trades = portfolios.get(username, [])

        if action == "매수":
            cost = current_price * quantity
            if user_data['balance'] >= cost:
                trade = {
                    "ticker": ticker,
                    "shares": quantity,
                    "price": current_price,
                    "type": "매수",
                    "date": st.session_state.market_time.strftime('%Y-%m-%d %H:%M')
                }
                trades.append(trade)
                portfolios[username] = trades
                user_data['balance'] -= cost
                save_all()
                st.success(f"✅ {quantity}주 매수 완료. 잔고: ${user_data['balance']:.2f}")
            else:
                st.error("❌ 잔고 부족")

        elif action == "매도":
            if owned >= quantity:
                trade = {
                    "ticker": ticker,
                    "shares": quantity,
                    "price": current_price,
                    "type": "매도",
                    "date": st.session_state.market_time.strftime('%Y-%m-%d %H:%M')
                }
                trades.append(trade)
                portfolios[username] = trades
                user_data['balance'] += current_price * quantity
                save_all()
                st.success(f"✅ {quantity}주 매도 완료. 잔고: ${user_data['balance']:.2f}")
            else:
                st.error(f"❌ 보유 수량 부족. 현재 보유: {owned}주")

# ----------------- 메인 -----------------
def main():
    st_autorefresh(interval=30000, key="refresh")

    st.sidebar.title("📌 메뉴")
    st.sidebar.button("📊 종목 시세 요약", on_click=lambda: st.session_state.update({'view': 'home'}))
    st.sidebar.button("💼 거래", on_click=lambda: st.session_state.update({'view': 'trade'}))
    st.sidebar.button("📁 포트폴리오", on_click=lambda: st.session_state.update({'view': 'portfolio'}))

    view = st.session_state.view
    if view == 'home':
        st.subheader("📊 종목 시세 요약")
        current_time = st.session_state.market_time
        current_price = get_current_price(current_time)
        st.write(f"🕒 현재 시각: {current_time.strftime('%Y-%m-%d %H:%M')}")
        st.write(f"📈 AAPL 현재가: ${current_price:.2f}")
    elif view == 'trade':
        trade_view()
    elif view == 'portfolio':
        portfolio_view()

# ----------------- 실행 -----------------
if not st.session_state.authenticated:
    login_ui()
else:
    main()
