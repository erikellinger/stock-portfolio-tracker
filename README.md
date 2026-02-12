# Stock Portfolio Tracker

A Python-based application for tracking and analyzing stock portfolio performance. This tool allows users to monitor their investments, view real-time stock data, and analyze portfolio metrics through an interactive Streamlit dashboard.

## Features

- **Portfolio Management**: Create multiple portfolios and track buy/sell transactions
- **Real-time Stock Data**: Fetch current and historical stock prices using Yahoo Finance
- **Performance Analytics**: Calculate gain/loss, cost basis, and portfolio value
- **Interactive Dashboard**: Professional Streamlit interface with charts and visualizations
- **Data Persistence**: SQLite database to store portfolios, transactions, and price history
- **Portfolio Snapshots**: Save and track portfolio value over time

## Project Structure

```
stock-portfolio-tracker/
├── src/
│   ├── app.py                  # Streamlit dashboard
│   ├── database.py             # SQLAlchemy database models
│   ├── portfolio_manager.py   # Portfolio and transaction management
│   └── stock_fetcher.py        # Stock data fetching via yfinance
├── data/                       # Database and data files
├── tests/                      # Test files
├── logs/                       # Application logs
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variable template
└── README.md                  # This file
```

## Installation

1. Clone or download this repository

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Copy `.env.example` to `.env` and add your API keys if needed:
```bash
cp .env.example .env
```

## Usage

### Running the Dashboard

Start the Streamlit dashboard:
```bash
streamlit run src/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Dashboard Features

**Sidebar:**
- Create new portfolios
- Select between existing portfolios
- Add buy/sell transactions
- Refresh current stock prices

**Main Tabs:**
1. **Portfolio Overview** - View all positions with current values and gain/loss
2. **Performance Charts** - Track portfolio value over time and view stock price history
3. **Holdings Breakdown** - Visualize portfolio allocation with pie charts

### Testing Individual Modules

Each module can be tested independently:

```bash
# Test database setup
python src/database.py

# Test stock data fetching
python src/stock_fetcher.py

# Test portfolio management
python src/portfolio_manager.py
```

## Technologies Used

- **Streamlit** - Interactive web dashboard
- **pandas** - Data manipulation and analysis
- **yfinance** - Real-time stock data from Yahoo Finance
- **SQLAlchemy** - Database ORM
- **Plotly** - Interactive charts and visualizations
- **SQLite** - Local database storage

## License

This project is open source and available for personal use.
