# 📈 Stock Portfolio Tracker

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://stock-portfolio-tracker-nxjswebeluqdkunu4cqnjy.streamlit.app/)

A full-stack web application for tracking stock portfolio performance with real-time market data. Users can manage multiple portfolios, record transactions, and visualize their investment performance through interactive charts and analytics. Built with Python and Streamlit, featuring a SQLite database backend and integration with the Yahoo Finance API.

## Features

- **Real-time stock price tracking** via Yahoo Finance API
- **Interactive portfolio performance dashboard** with gain/loss calculations and cost basis tracking
- **Historical price charts** with candlestick visualization for technical analysis
- **Portfolio allocation breakdown** with pie charts and percentage distribution
- **Automated daily price updates** for all holdings
- **SQLite database** for persistent storage of portfolios, transactions, and historical snapshots
- **Full test suite** with 15 unit tests covering core functionality

## Tech Stack

**Backend:**
- Python 3.11
- SQLAlchemy (ORM)
- SQLite (Database)
- pandas (Data manipulation)
- yfinance API (Market data)

**Frontend:**
- Streamlit (Web framework)
- Plotly (Interactive visualizations)

**Testing & Deployment:**
- pytest (Unit testing)
- Streamlit Cloud (Production deployment)

## How to Run Locally

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/stock-portfolio-tracker.git
cd stock-portfolio-tracker
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
streamlit run src/app.py
```

4. **Access the dashboard**
   - Open your browser to `http://localhost:8501`
   - Create a portfolio and start adding transactions

5. **(Optional) Run tests**
```bash
pytest tests/ -v
```

## Project Structure

```
stock-portfolio-tracker/
├── src/
│   ├── app.py                  # Streamlit dashboard UI
│   ├── database.py             # SQLAlchemy models and DB setup
│   ├── portfolio_manager.py   # Business logic for portfolios
│   └── stock_fetcher.py        # Yahoo Finance API integration
├── tests/
│   ├── conftest.py             # Pytest fixtures
│   └── test_portfolio_manager.py  # Unit tests
├── data/                       # SQLite database storage
├── logs/                       # Application logs
├── requirements.txt
└── README.md
```

## What I Learned

This project gave me hands-on experience with several important concepts:

- **Building end-to-end data pipelines** - From fetching external API data to storing it in a database and presenting it through a web interface

- **Database design and ORM usage** - Designed a relational schema with SQLAlchemy for portfolios, transactions, and price history, including proper foreign key relationships and cascade deletes

- **API integration with error handling** - Implemented robust error handling for the yfinance API, including retry logic, rate limiting awareness, and graceful degradation when data is unavailable

- **Building interactive dashboards** - Created a user-friendly Streamlit interface that non-technical users can navigate, with real-time updates and responsive visualizations

- **Writing unit tests for data pipelines** - Developed 15 unit tests using pytest with in-memory databases to ensure data integrity and business logic correctness

- **Deploying a data application to production** - Learned the process of deploying a Streamlit app to the cloud, managing dependencies, and handling persistent storage in a production environment

---

**Note:** This application uses the Yahoo Finance API through the yfinance library. Market data may be delayed by 15-20 minutes. This project is for educational purposes only and should not be used as financial advice.
