import pyupbit
import time
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter


# 기본 설정
TICKER = "KRW-BTC"
TRADE_AMOUNT = 10000  # 매수 금액 (KRW)
SHORT_WINDOW = 5
LONG_WINDOW = 20
FEE_RATE = 0.0005  # 거래 수수료

# 가상 계좌 설정
virtual_balance_krw = 100000000  # 초기 가상 자금 1억 (100,000,000 KRW)
virtual_balance_coin = 0  # 초기 코인 잔고
trade_log = []  # 거래 내역 로그
position = False  # 초기 포지션 상태 (매수/매도 상태 추적)
running = False  # 매매 진행 여부
buy_price = 0  # 매수 가격 추적

# 실시간 가격을 저장할 리스트
price_history = []

# 금액 표시 함수 (천 단위 구분 기호 추가)
def format_currency(value):
    return f"{int(value):,}"

# 이동평균선 계산
def get_moving_average(ticker, window, interval="minute1", count=20):
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
    return df['close'].rolling(window=window).mean().iloc[-1], df['close'].rolling(window=window).mean().iloc[-2]

# RSI 계산
def calculate_rsi(ticker, period=14):
    df = pyupbit.get_ohlcv(ticker, interval="minute1", count=period + 1)  # 최소 period+1개의 데이터 필요
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# 실시간 가격 업데이트 및 그래프 갱신
def update_trade_status():
    global virtual_balance_krw, virtual_balance_coin, trade_log, position, running, buy_price, price_history

    if not running:
        return  # running이 False일 때 매매 진행하지 않음

    current_price = pyupbit.get_current_price(TICKER)
    short_ma, prev_short_ma = get_moving_average(TICKER, SHORT_WINDOW)
    long_ma, prev_long_ma = get_moving_average(TICKER, LONG_WINDOW)
    rsi = calculate_rsi(TICKER)

    # 가격 기록 갱신
    price_history.append(current_price)
    if len(price_history) > 50:  # 최대 50개 가격을 저장 (그래프에 표시할 최대 길이)
        price_history = price_history[-50:]

    # 그래프 갱신
    ax.clear()
    ax.plot(price_history, label="Price", color="blue")
    ax.set_title(f"Real-time Price of {TICKER}")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Price (KRW)")
    ax.legend()

    # y축 가격 레이블 형식 설정
    def currency_format(x, pos):
        return f"{int(x):,}"  # 천 단위 구분 기호 추가

    ax.yaxis.set_major_formatter(FuncFormatter(currency_format))  # y축 포맷 변경

    canvas.draw()

    # 매수 조건: 단기 MA > 장기 MA & 단기 MA 상승 추세 & RSI < 30
    if short_ma > long_ma and short_ma > prev_short_ma and rsi < 30 and not position:
        trade_krw = virtual_balance_krw * (1 - FEE_RATE)
        virtual_balance_coin = trade_krw / current_price
        virtual_balance_krw = 0
        buy_price = current_price  # 매수 가격 저장
        trade_log.append({
            "type": "BUY", "price": current_price,
            "balance_coin": virtual_balance_coin, "time": time.time()
        })
        position = True
        current_status = "매수"  # 매수 상태로 변경
        buy_price_label.config(text=f"매수 가격: {format_currency(current_price)} KRW")  # 매수 가격 GUI에 표시

    # 매도 조건: 단기 MA < 장기 MA & 단기 MA 하락 추세 & 포지션 있음
    # 수익률 3% 이상일 때 강제 매도
    elif short_ma < long_ma and short_ma < prev_short_ma and position:
        profit_loss = (current_price - buy_price) * virtual_balance_coin
        profit_loss_percent = (profit_loss / (buy_price * virtual_balance_coin)) * 100

        # 3% 이상 수익이면 강제 매도
        if profit_loss_percent >= 3:
            trade_krw = virtual_balance_coin * current_price * (1 - FEE_RATE)
            virtual_balance_krw = trade_krw
            virtual_balance_coin = 0
            trade_log.append({
                "type": "SELL", "price": current_price,
                "balance_krw": virtual_balance_krw, "time": time.time()
            })
            position = False
            current_status = "매도"  # 매도 상태로 변경
            sell_price_label.config(text=f"매도 가격: {format_currency(current_price)} KRW")  # 매도 가격 GUI에 표시

        # 수익이 없거나 손실이면 hold
        else:
            current_status = "Hold"

    # Hold 상태: 매수나 매도 조건이 맞지 않으면 hold
    else:
        current_status = "Hold"

        trade_log.append({
            "type": "HOLD", "price": current_price,
            "balance_krw": virtual_balance_krw, "balance_coin": virtual_balance_coin, "time": time.time()
        })

    # 수익률 계산
    if position:  # 포지션이 있을 때만 수익률 계산
        profit_loss = (current_price - buy_price) * virtual_balance_coin
        profit_loss_percent = (profit_loss / (buy_price * virtual_balance_coin)) * 100
    else:
        profit_loss = 0
        profit_loss_percent = 0

    # GUI에 상태 업데이트
    price_label.config(text=f"현재가: {format_currency(current_price)} KRW")
    short_ma_label.config(text=f"단기 MA: {short_ma}")
    long_ma_label.config(text=f"장기 MA: {long_ma}")
    rsi_label.config(text=f"RSI: {rsi:.2f}")
    balance_label.config(text=f"현금 잔고: {format_currency(virtual_balance_krw)} KRW\n코인 잔고: {virtual_balance_coin} BTC")
    status_label.config(text=f"현재 상태: {current_status}")
    profit_label.config(text=f"수익률: {profit_loss_percent:.2f}% (₩{format_currency(profit_loss)})")

    # 최신 30개 매매 내역 갱신 (왼쪽 내역창)
    trade_text.delete(1.0, tk.END)  # 기존 내역 지우기
    for log in trade_log[-30:]:  # 최신 30개 내역만 표시
        if log["type"] == "BUY":
            trade_text.insert("1.0", f"{log['type']} - 가격: {format_currency(log['price'])} KRW\n", "green")
        else:
            trade_text.insert("1.0", f"{log['type']} - 가격: {format_currency(log['price'])} KRW\n")

    # 매수, 매도 내역만 갱신 (오른쪽 내역창)
    all_trade_text.delete(1.0, tk.END)  # 기존 내역 지우기
    for log in trade_log:
        if log['type'] in ["BUY", "SELL"]:
            all_trade_text.insert("1.0", f"{log['type']} - 가격: {format_currency(log['price'])} KRW\n", "green" if log['type'] == "BUY" else "")

    # 1초마다 업데이트
    window.after(100, update_trade_status)  # 1000ms = 1초


# 매매 시작 버튼 클릭 시 매매 시작
def start_trading():
    global running
    running = True
    update_trade_status()

# 매매 멈추기 버튼 클릭 시 매매 멈춤
def stop_trading():
    global running
    running = False


# Tkinter GUI 설정
window = tk.Tk()
window.title("Crypto Trading Bot")

# 화면 크기 조정
window.geometry("800x600")

# 가격 및 상태 표시
price_label = tk.Label(window, text="현재가: -- KRW")
price_label.pack()

short_ma_label = tk.Label(window, text="단기 MA: --")
short_ma_label.pack()

long_ma_label = tk.Label(window, text="장기 MA: --")
long_ma_label.pack()

rsi_label = tk.Label(window, text="RSI: --")
rsi_label.pack()

balance_label = tk.Label(window, text="현금 잔고: --\n코인 잔고: --")
balance_label.pack()

status_label = tk.Label(window, text="현재 상태: --")
status_label.pack()

profit_label = tk.Label(window, text="수익률: --%")
profit_label.pack()

# 거래 내역
trade_text = tk.Text(window, height=15, width=40)
trade_text.pack(side=tk.LEFT)

# 매수/매도 내역
all_trade_text = tk.Text(window, height=15, width=40)
all_trade_text.pack(side=tk.LEFT)

# 매수/매도 가격 표시
buy_price_label = tk.Label(window, text="매수 가격: -- KRW")
buy_price_label.pack()

sell_price_label = tk.Label(window, text="매도 가격: -- KRW")
sell_price_label.pack()

# 매매 버튼
start_button = tk.Button(window, text="매매 시작", command=start_trading)
start_button.pack()

stop_button = tk.Button(window, text="매매 멈추기", command=stop_trading)
stop_button.pack()

# 실시간 가격 그래프
fig = Figure(figsize=(8, 4), dpi=100)
ax = fig.add_subplot(111)
ax.set_title("Real-time Price")
ax.set_xlabel("Time")
ax.set_ylabel("Price (KRW)") 
canvas = FigureCanvasTkAgg(fig, master=window)
canvas.get_tk_widget().pack()

# GUI 실행
window.mainloop()
