"""
Stock Portfolio Tracker - Streamlit Dashboard
A professional dashboard for tracking stock portfolios with real-time data.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import init_db, get_engine, Portfolio, PortfolioSnapshot
from portfolio_manager import (
    create_portfolio,
    add_transaction,
    get_portfolio_holdings,
    get_portfolio_performance,
    save_portfolio_snapshot
)
from stock_fetcher import get_historical_prices, update_prices_in_db


# Page configuration
st.set_page_config(
    page_title="Stock Portfolio Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme and professional styling
st.markdown("""
    <style>
    .big-metric {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .positive {
        color: #00ff00;
    }
    .negative {
        color: #ff4444;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize database
@st.cache_resource
def initialize_database():
    """Initialize database connection and create tables."""
    return init_db()

engine = initialize_database()


def load_portfolios():
    """Load all portfolios from database."""
    with Session(engine) as session:
        portfolios = session.query(Portfolio).all()
        return [(p.id, p.name) for p in portfolios]


def format_currency(value):
    """Format value as currency."""
    return f"${value:,.2f}"


def format_percent(value):
    """Format value as percentage."""
    return f"{value:.2f}%"


# ============================================================================
# SIDEBAR
# ============================================================================
st.sidebar.title("📈 Stock Portfolio Tracker")
st.sidebar.markdown("---")

# Create new portfolio section
st.sidebar.subheader("Create New Portfolio")
new_portfolio_name = st.sidebar.text_input("Portfolio Name", key="new_portfolio_name")
if st.sidebar.button("Create Portfolio", type="primary"):
    if new_portfolio_name:
        portfolio_id = create_portfolio(engine, new_portfolio_name)
        if portfolio_id:
            st.sidebar.success(f"Portfolio '{new_portfolio_name}' created!")
            st.rerun()
    else:
        st.sidebar.error("Please enter a portfolio name")

st.sidebar.markdown("---")

# Select existing portfolio
st.sidebar.subheader("Select Portfolio")
portfolios = load_portfolios()

if not portfolios:
    st.sidebar.warning("No portfolios found. Create one above!")
    st.info("👈 Create a portfolio in the sidebar to get started")
    st.stop()

portfolio_options = {name: id for id, name in portfolios}
selected_portfolio_name = st.sidebar.selectbox(
    "Choose Portfolio",
    options=list(portfolio_options.keys()),
    key="selected_portfolio"
)
selected_portfolio_id = portfolio_options[selected_portfolio_name]

st.sidebar.markdown("---")

# Add transaction section
st.sidebar.subheader("Add Transaction")
with st.sidebar.form("add_transaction_form"):
    ticker = st.text_input("Ticker Symbol", placeholder="e.g., AAPL").upper()
    transaction_type = st.radio("Type", ["Buy", "Sell"], horizontal=True)
    shares = st.number_input("Number of Shares", min_value=0.01, step=0.01)
    price = st.number_input("Price per Share ($)", min_value=0.01, step=0.01)
    trans_date = st.date_input("Transaction Date", value=datetime.now())
    notes = st.text_area("Notes (optional)", max_chars=200)

    submit_transaction = st.form_submit_button("Add Transaction", type="primary")

    if submit_transaction:
        if ticker and shares > 0 and price > 0:
            trans_datetime = datetime.combine(trans_date, datetime.min.time())
            success = add_transaction(
                engine=engine,
                portfolio_id=selected_portfolio_id,
                ticker=ticker,
                transaction_type=transaction_type.lower(),
                shares=shares,
                price_per_share=price,
                transaction_date=trans_datetime,
                notes=notes
            )
            if success:
                st.sidebar.success(f"Transaction added: {transaction_type} {shares} shares of {ticker}")
                st.rerun()
        else:
            st.sidebar.error("Please fill in all required fields")

st.sidebar.markdown("---")

# Refresh prices button
if st.sidebar.button("🔄 Refresh Prices", type="secondary"):
    with st.spinner("Fetching latest prices..."):
        holdings = get_portfolio_holdings(engine, selected_portfolio_id)
        if holdings is not None and not holdings.empty:
            tickers = holdings['ticker'].tolist()
            update_prices_in_db(tickers, engine)
            st.sidebar.success("Prices updated!")
            st.rerun()
        else:
            st.sidebar.warning("No holdings to refresh")


# ============================================================================
# MAIN AREA
# ============================================================================
st.title(f"Portfolio: {selected_portfolio_name}")

# Get portfolio performance data
performance = get_portfolio_performance(engine, selected_portfolio_id)

if performance is None or performance['positions'].empty:
    st.warning("No positions in this portfolio yet. Add some transactions to get started!")
    st.stop()

positions_df = performance['positions']
total_cost = performance['total_cost']
total_value = performance['total_current_value']
total_gain_loss = performance['total_gain_loss_dollar']
total_gain_loss_pct = performance['total_gain_loss_percent']

# Top metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Value", format_currency(total_value))

with col2:
    st.metric("Total Cost", format_currency(total_cost))

with col3:
    gain_loss_color = "normal" if total_gain_loss >= 0 else "inverse"
    st.metric(
        "Gain/Loss ($)",
        format_currency(total_gain_loss),
        delta=format_currency(total_gain_loss),
        delta_color=gain_loss_color
    )

with col4:
    st.metric(
        "Gain/Loss (%)",
        format_percent(total_gain_loss_pct),
        delta=format_percent(total_gain_loss_pct),
        delta_color=gain_loss_color
    )

st.markdown("---")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 Portfolio Overview", "📈 Performance Charts", "🥧 Holdings Breakdown"])

# ============================================================================
# TAB 1: Portfolio Overview
# ============================================================================
with tab1:
    st.subheader("Current Positions")

    # Format the dataframe for display
    display_df = positions_df.copy()
    display_df['shares'] = display_df['shares'].apply(lambda x: f"{x:.2f}")
    display_df['avg_cost_basis'] = display_df['avg_cost_basis'].apply(format_currency)
    display_df['current_price'] = display_df['current_price'].apply(format_currency)
    display_df['total_cost'] = display_df['total_cost'].apply(format_currency)
    display_df['current_value'] = display_df['current_value'].apply(format_currency)
    display_df['gain_loss_dollar'] = display_df['gain_loss_dollar'].apply(format_currency)
    display_df['gain_loss_percent'] = display_df['gain_loss_percent'].apply(format_percent)

    # Rename columns for display
    display_df.columns = [
        'Ticker', 'Shares', 'Avg Cost', 'Current Price',
        'Total Cost', 'Current Value', 'Gain/Loss ($)', 'Gain/Loss (%)'
    ]

    # Color code the gain/loss columns
    def highlight_gains(row):
        """Apply color formatting to gain/loss columns."""
        colors = [''] * len(row)
        # Check the original numeric value from positions_df
        idx = row.name
        if idx < len(positions_df):
            gain_loss = positions_df.iloc[idx]['gain_loss_dollar']
            if gain_loss > 0:
                colors[-2] = 'background-color: rgba(0, 255, 0, 0.1); color: #00ff00'
                colors[-1] = 'background-color: rgba(0, 255, 0, 0.1); color: #00ff00'
            elif gain_loss < 0:
                colors[-2] = 'background-color: rgba(255, 0, 0, 0.1); color: #ff4444'
                colors[-1] = 'background-color: rgba(255, 0, 0, 0.1); color: #ff4444'
        return colors

    # Display the styled dataframe
    st.dataframe(
        display_df.style.apply(highlight_gains, axis=1),
        use_container_width=True,
        hide_index=True
    )

    # Save snapshot button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("💾 Save Snapshot"):
            if save_portfolio_snapshot(engine, selected_portfolio_id):
                st.success("Portfolio snapshot saved!")
                st.rerun()

# ============================================================================
# TAB 2: Performance Charts
# ============================================================================
with tab2:
    # Portfolio value over time chart
    st.subheader("Portfolio Value Over Time")

    with Session(engine) as session:
        snapshots = session.query(PortfolioSnapshot).filter_by(
            portfolio_id=selected_portfolio_id
        ).order_by(PortfolioSnapshot.snapshot_date).all()

    if snapshots and len(snapshots) > 0:
        snapshot_data = pd.DataFrame([
            {'Date': s.snapshot_date, 'Value': s.total_value}
            for s in snapshots
        ])

        fig_portfolio = go.Figure()
        fig_portfolio.add_trace(go.Scatter(
            x=snapshot_data['Date'],
            y=snapshot_data['Value'],
            mode='lines+markers',
            name='Portfolio Value',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8)
        ))

        fig_portfolio.update_layout(
            title="Portfolio Value History",
            xaxis_title="Date",
            yaxis_title="Value ($)",
            hovermode='x unified',
            template='plotly_dark',
            height=400
        )

        st.plotly_chart(fig_portfolio, use_container_width=True)
    else:
        st.info("No snapshots saved yet. Click 'Save Snapshot' in the Overview tab to start tracking portfolio value over time.")

    st.markdown("---")

    # Stock historical price chart
    st.subheader("Stock Historical Price")

    tickers = positions_df['ticker'].tolist()
    selected_ticker = st.selectbox("Select a stock to view historical prices", tickers)

    if selected_ticker:
        with st.spinner(f"Loading historical data for {selected_ticker}..."):
            hist_df = get_historical_prices(selected_ticker, period="1y")

            if hist_df is not None and not hist_df.empty:
                fig_stock = go.Figure()

                # Add candlestick chart
                fig_stock.add_trace(go.Candlestick(
                    x=hist_df.index,
                    open=hist_df['Open'],
                    high=hist_df['High'],
                    low=hist_df['Low'],
                    close=hist_df['Close'],
                    name=selected_ticker
                ))

                fig_stock.update_layout(
                    title=f"{selected_ticker} - 1 Year Price History",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    template='plotly_dark',
                    height=500,
                    xaxis_rangeslider_visible=False
                )

                st.plotly_chart(fig_stock, use_container_width=True)

                # Show some stats
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("52-Week High", format_currency(hist_df['High'].max()))
                with col2:
                    st.metric("52-Week Low", format_currency(hist_df['Low'].min()))
                with col3:
                    st.metric("Average Volume", f"{hist_df['Volume'].mean():,.0f}")
                with col4:
                    year_change = ((hist_df['Close'].iloc[-1] - hist_df['Close'].iloc[0]) / hist_df['Close'].iloc[0] * 100)
                    st.metric("1-Year Change", format_percent(year_change))
            else:
                st.error(f"Could not load historical data for {selected_ticker}")

# ============================================================================
# TAB 3: Holdings Breakdown
# ============================================================================
with tab3:
    st.subheader("Portfolio Allocation")

    # Create pie chart data
    pie_data = positions_df[['ticker', 'current_value']].copy()

    # Calculate percentages
    pie_data['percentage'] = (pie_data['current_value'] / pie_data['current_value'].sum() * 100)

    # Create pie chart
    fig_pie = px.pie(
        pie_data,
        values='current_value',
        names='ticker',
        title='Portfolio Allocation by Position',
        hole=0.4,  # Donut chart
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    fig_pie.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
    )

    fig_pie.update_layout(
        template='plotly_dark',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.1
        )
    )

    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # Allocation table
    st.subheader("Allocation Details")

    allocation_df = pie_data.copy()
    allocation_df['current_value'] = allocation_df['current_value'].apply(format_currency)
    allocation_df['percentage'] = allocation_df['percentage'].apply(format_percent)
    allocation_df.columns = ['Ticker', 'Current Value', 'Portfolio %']

    st.dataframe(
        allocation_df,
        use_container_width=True,
        hide_index=True
    )

# Footer
st.markdown("---")
st.caption("Data provided by Yahoo Finance via yfinance • Prices may be delayed")
