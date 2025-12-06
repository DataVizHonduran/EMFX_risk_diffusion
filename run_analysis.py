import os
import time
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.signal import savgol_filter

# --- 1. FETCH DATA (Alpha Vantage) ---
# We retrieve the key from the environment variable for security
api_key = os.environ.get("ALPHA_VANTAGE_KEY")

if not api_key:
    raise ValueError("API Key not found. Make sure ALPHA_VANTAGE_KEY is set in GitHub Secrets.")

nsize = "full"
symbols = [
    "EUR", "AUD", "CAD", "GBP", "JPY", "SEK", "NOK", "NZD", "CHF",
    "MXN", "CLP", "BRL", "COP", "PEN",
    "KRW", "IDR", "INR", "THB", "PHP", "SGD",
    "PLN", "HUF", "CZK", "ZAR", "TRY"
]

data_dict = {}

print("Starting API Fetch loop...")

for symbol in symbols:
    print(f"Fetching USD/{symbol}...")
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "FX_DAILY",
        "from_symbol": "USD",
        "to_symbol": symbol,
        "outputsize": nsize,
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "Time Series FX (Daily)" in data:
            ts = data['Time Series FX (Daily)']
            df_temp = pd.DataFrame.from_dict(ts, orient='index')
            df_temp.index = pd.to_datetime(df_temp.index)
            df_temp.columns = ['open', 'high', 'low', 'close']
            df_temp = df_temp.astype(float)
            
            # Store in dict
            for col in df_temp.columns:
                data_dict[(symbol, col)] = df_temp[col]
        else:
            print(f"Error fetching {symbol}: {data.get('Note') or data.get('Error Message')}")
            
    except Exception as e:
        print(f"Exception for {symbol}: {e}")
    
    # Respect API rate limits (Standard free tier is 5 calls/min)
    time.sleep(15)

# Combine into MultiIndex DataFrame
combined_df = pd.DataFrame(data_dict)
combined_df.columns = pd.MultiIndex.from_tuples(combined_df.columns)
combined_df.sort_index(inplace=True)

# Extract only 'close' prices for the analysis to keep math simple
# This creates a DataFrame where columns are just the tickers (MXN, BRL, etc.)
df_close = combined_df.xs('close', axis=1, level=1)

# Save raw FX close prices to CSV (USDXXX quotes)
df_close.to_csv('fx_data_raw.csv')
print(f"Saved raw FX data to fx_data_raw.csv ({df_close.shape[0]} rows, {df_close.shape[1]} currencies)")

print("Data fetch complete. Running analysis...")

# --- 2. RUN ANALYSIS ---

emfx = ['MXN','CLP', 'BRL', 'COP', 'PEN',
        'KRW', 'IDR', 'INR', 'THB', 'PHP', 'SGD',
        'PLN', 'HUF', 'CZK', 'ZAR', 'TRY']

# Filter and inverse quote (Assuming underlying data is USDXXX, we want XXXUSD strength context)
# We use df_close here
df_em = 1 / df_close[emfx].bfill().ffill().loc["2014-11-01":]

# Save processed EM FX data to CSV (inverted quotes, XXXUSD, from 2014-11-01)
df_em.to_csv('fx_data_emfx.csv')
print(f"Saved processed EM FX data to fx_data_emfx.csv ({df_em.shape[0]} rows, {df_em.shape[1]} currencies)")

window = 252
threshold = 0.05
diffusion_data = []

for i in range(window, len(df_em)):
    slice_df = df_em.iloc[:i+1]
    highs = slice_df.rolling(window).max()
    lows = slice_df.rolling(window).min()
    latest_prices = slice_df.iloc[-1]
    latest_highs = highs.iloc[-1]
    latest_lows = lows.iloc[-1]
    
    near_high = (latest_highs - latest_prices) / latest_highs <= threshold
    near_low = (latest_prices - latest_lows) / latest_lows <= threshold
    
    count_high = near_high.sum()
    count_low = near_low.sum()
    total = df_em.shape[1]
    
    diffusion_index = (count_high - count_low) / total
    diffusion_data.append((slice_df.index[-1], diffusion_index))

diffusion_df = pd.DataFrame(diffusion_data, columns=["Date", "Diffusion"]).set_index("Date")
diffusion_df["Smoothed"] = savgol_filter(diffusion_df["Diffusion"], 11, 3)

# Calculate Trend
em_fx = df_em.mean(axis=1)
em_fx = em_fx / em_fx.iloc[0] * 100
trend = em_fx - em_fx.rolling(100).mean()

# Signal Logic
signal = pd.Series(index=diffusion_df.index, dtype='float64')
for date in diffusion_df.index:
    if date not in trend: continue
    trend_val = trend.loc[date]
    diffusion_val = diffusion_df.loc[date, "Diffusion"]
    if trend_val > 0 and diffusion_val > 0.2: signal.loc[date] = 1
    elif trend_val < 0 and diffusion_val < -.2: signal.loc[date] = -1
    else: signal.loc[date] = 0

# --- Figure Generation (Contrarian Model) ---
q10_c = diffusion_df["Diffusion"].quantile(0.06)
q90_c = diffusion_df["Diffusion"].quantile(0.94)
contrarian_signal = pd.Series(index=diffusion_df.index, dtype='float64')
last_signal_day = None
cooldown = pd.Timedelta(days=5)

for date in diffusion_df.index:
    val = diffusion_df.loc[date, "Diffusion"]
    if last_signal_day is not None and (date - last_signal_day) < cooldown:
        contrarian_signal.loc[date] = 0
        continue
    if val >= q90_c:
        contrarian_signal.loc[date] = -1
        last_signal_day = date
    elif val <= q10_c:
        contrarian_signal.loc[date] = 1
        last_signal_day = date
    else:
        contrarian_signal.loc[date] = 0

fig2 = go.Figure()

cs = contrarian_signal.copy()
cs = cs[cs != cs.shift(1)]
cs = cs.to_frame(name='signal')
cs['start'] = cs.index
cs['end'] = cs['start'].shift(-1)
cs = cs.dropna()

for _, row in cs.iterrows():
    if row['signal'] == 1: color = "rgba(0,200,0,0.8)"
    elif row['signal'] == -1: color = "rgba(255,0,0,0.8)"
    else: continue
    fig2.add_vrect(x0=row['start'], x1=row['end'], fillcolor=color, layer="below", line_width=0)

fig2.add_trace(go.Scatter(x=diffusion_df.index, y=diffusion_df["Smoothed"], mode='lines', name='EM Diffusion', line=dict(color='#008080', width=2)))

fx_change = em_fx.pct_change(window)
fig2.add_trace(go.Scatter(x=fx_change.index, y=fx_change, mode='lines', name=f'EM FX Index ({window}d)', yaxis='y2', line=dict(color='#FF8C00', dash='solid', width=1.5)))

fig2.update_layout(title="Contrarian Signal: EM FX Diffusion vs. Index", yaxis=dict(title="Diffusion", range=[-1, 1]), yaxis2=dict(overlaying='y', side='right', showgrid=False), template="plotly_white", height=600)

# --- 3. SAVE HTML ---
with open('index.html', 'w') as f:
    f.write('<html><head><title>EM FX Z-Scores</title></head><body>')
    f.write('<h1 style="font-family:sans-serif; text-align:center;">EM FX Diffusion & Contrarian Signals</h1>')
    f.write(fig2.to_html(full_html=False, include_plotlyjs='cdn'))
    f.write(f'<p style="text-align:center; font-family:sans-serif;">Last updated: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')
    f.write('</body></html>')
