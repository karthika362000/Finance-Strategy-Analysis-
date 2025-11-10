"""
Stock Breakout Strategy Analyzer
--------------------------------
This Streamlit application analyzes breakout trading opportunities for user-specified stocks.
It uses Yahoo Finance for data retrieval, Plotly for visualizations, and pandas for analysis.

Features:
- Fetches stock data for given tickers and date range
- Detects breakout points using volume and price thresholds
- Displays detailed trade statistics and summary metrics
- Visualizes stock prices, volume, and returns distribution
- Allows download of results as a CSV file
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Streamlit page setup
st.set_page_config(page_title="Stock Breakout Analysis", layout="wide")
st.title('📈 Stock Breakout Strategy Analyzer')

# ✅ Compatible version of download button (no @st.fragment)
def download_button_no_refresh(label, data, file_name, mime):
    st.download_button(label=label, data=data, file_name=file_name, mime=mime)

# ---------------------- DATA FETCH FUNCTION ----------------------
def get_stock_data(ticker, start_date, end_date):
    """
    Fetch historical stock data using Yahoo Finance.
    """
    adjusted_start = (pd.to_datetime(start_date) - timedelta(days=30)).strftime('%Y-%m-%d')
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=adjusted_start, end=end_date)
        return df
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {str(e)}")
        return None

# ---------------------- ANALYSIS FUNCTION ----------------------
def analyze_breakouts(df, volume_threshold, price_threshold, holding_period):
    """
    Identify breakout days and compute returns based on thresholds.
    """
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
    df['Daily_Return'] = df['Close'].pct_change()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA20']

    breakout_condition = (df['Volume_Ratio'] > volume_threshold / 100) & \
                         (df['Daily_Return'] > price_threshold / 100)

    breakout_results = []
    breakout_days = df[breakout_condition].index

    for breakout_day in breakout_days:
        try:
            entry_price = df.loc[breakout_day, 'Close']
            entry_date = breakout_day
            exit_date_idx = min(df.index.get_loc(breakout_day) + holding_period, len(df) - 1)
            exit_date = df.index[exit_date_idx]
            exit_price = df.iloc[exit_date_idx]['Close']
            trade_return = (exit_price - entry_price) / entry_price * 100

            breakout_results.append({
                'Entry_Date': entry_date.strftime('%Y-%m-%d'),
                'Entry_Price': round(entry_price, 2),
                'Exit_Date': exit_date.strftime('%Y-%m-%d'),
                'Exit_Price': round(exit_price, 2),
                'Return_Pct': round(trade_return, 2),
                'Volume_Ratio': round(df.loc[breakout_day, 'Volume_Ratio'], 2)
            })
        except Exception as e:
            st.warning(f"Could not calculate returns for breakout on {breakout_day}: {str(e)}")
            continue

    return pd.DataFrame(breakout_results)

# ---------------------- SUMMARY STATISTICS FUNCTION ----------------------
def create_summary_stats(results_df):
    """
    Compute key performance statistics from breakout results.
    """
    if len(results_df) == 0:
        return pd.Series({
            'Total_Trades': 0,
            'Win_Rate': 0,
            'Average_Return': 0,
            'Max_Return': 0,
            'Min_Return': 0,
            'Std_Dev': 0
        })

    summary = {
        'Total_Trades': len(results_df),
        'Win_Rate': (results_df['Return_Pct'] > 0).mean() * 100,
        'Average_Return': results_df['Return_Pct'].mean(),
        'Max_Return': results_df['Return_Pct'].max(),
        'Min_Return': results_df['Return_Pct'].min(),
        'Std_Dev': results_df['Return_Pct'].std()
    }
    return pd.Series(summary).round(2)

# ---------------------- SIDEBAR INPUTS ----------------------
st.sidebar.header('🔧 Input Parameters')

ticker_input = st.sidebar.text_input('Stock Ticker(s)', value='', placeholder='e.g., AAPL, TSLA, TCS.NS')
tickers = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]

start_date = st.sidebar.date_input('Start Date', value=datetime.now() - timedelta(days=365))
end_date = st.sidebar.date_input('End Date', value=datetime.now())
volume_threshold = st.sidebar.number_input('Volume Breakout Threshold (%)', value=200, min_value=50)
price_threshold = st.sidebar.number_input('Daily Change Threshold (%)', value=2.0, min_value=0.1)
holding_period = st.sidebar.number_input('Holding Period (Days)', value=10, min_value=1)

# ---------------------- VALIDATIONS ----------------------
if start_date >= end_date:
    st.sidebar.error("Start date must be earlier than the end date.")
if end_date > datetime.now().date():
    st.sidebar.error("End date cannot be in the future.")
if not tickers:
    st.sidebar.warning('Enter at least one stock ticker to proceed.')

# ---------------------- MAIN ANALYSIS SECTION ----------------------
if st.sidebar.button('🚀 Generate Report'):
    if tickers:
        tabs = st.tabs(tickers)
        for idx, ticker in enumerate(tickers):
            with tabs[idx]:
                df = get_stock_data(ticker, start_date, end_date)
                if df is None or df.empty:
                    st.error(f"No data found for {ticker}. Please check the symbol.")
                else:
                    results_df = analyze_breakouts(df, volume_threshold, price_threshold, holding_period)
                    if not results_df.empty:
                        st.header(f'📊 Analysis for {ticker}')

                        # Summary stats
                        st.subheader('Summary Statistics')
                        summary_stats = create_summary_stats(results_df)
                        cols = st.columns(3)
                        for i, (label, value) in enumerate(summary_stats.items()):
                            cols[i % 3].metric(label=label, value=value)

                        # Detailed results
                        st.subheader('Detailed Trade Results')
                        st.dataframe(results_df)

                        # Visualizations
                        st.subheader('Stock Price Candlestick')
                        fig_price = go.Figure(data=[go.Candlestick(
                            x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close']
                        )])
                        fig_price.update_layout(title=f'{ticker} Stock Price Over Time', xaxis_title='Date', yaxis_title='Price')
                        st.plotly_chart(fig_price)

                        st.subheader('Volume Over Time')
                        fig_vol = go.Figure(data=[go.Bar(x=df.index, y=df['Volume'])])
                        fig_vol.update_layout(title=f'{ticker} Volume Over Time', xaxis_title='Date', yaxis_title='Volume')
                        st.plotly_chart(fig_vol)

                        st.subheader('Distribution of Returns')
                        fig_returns = go.Figure(data=[go.Histogram(x=results_df['Return_Pct'], nbinsx=20)])
                        fig_returns.update_layout(xaxis_title='Return (%)', yaxis_title='Frequency')
                        st.plotly_chart(fig_returns)

                        # Download results
                        csv_data = results_df.to_csv(index=False).encode('utf-8')
                        download_button_no_refresh(
                            label="📥 Download Results CSV",
                            data=csv_data,
                            file_name=f"{ticker}_breakout_analysis.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning(f'No breakout conditions found for {ticker}.')
    else:
        st.error('Please enter a valid stock ticker.')