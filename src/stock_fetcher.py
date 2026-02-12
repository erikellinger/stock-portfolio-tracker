"""
Stock data fetcher using yfinance API.
Handles fetching current prices, historical data, and stock information.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import Engine

from database import StockPrice, get_engine


def get_current_price(ticker: str) -> Optional[float]:
    """
    Get the current price for a single stock ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        Current price as float, or None if unable to fetch
    """
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")

        if data.empty:
            print(f"Warning: No data available for ticker '{ticker}'. It may be invalid.")
            return None

        current_price = data['Close'].iloc[-1]
        return float(current_price)

    except Exception as e:
        print(f"Error fetching current price for {ticker}: {str(e)}")
        return None


def get_historical_prices(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    Get historical price data for a stock ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        period: Time period for historical data. Valid values:
                '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'

    Returns:
        DataFrame with historical prices (Date, Open, High, Low, Close, Volume)
        or None if unable to fetch
    """
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)

        if data.empty:
            print(f"Warning: No historical data available for ticker '{ticker}'.")
            return None

        return data

    except Exception as e:
        print(f"Error fetching historical prices for {ticker}: {str(e)}")
        return None


def get_stock_info(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get basic information about a stock.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        Dictionary containing company name, sector, industry, and market cap
        or None if unable to fetch
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Check if we got valid data
        if not info or 'symbol' not in info:
            print(f"Warning: No information available for ticker '{ticker}'.")
            return None

        # Extract relevant information with fallbacks
        stock_info = {
            'ticker': ticker.upper(),
            'company_name': info.get('longName', info.get('shortName', 'N/A')),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'currency': info.get('currency', 'USD')
        }

        return stock_info

    except Exception as e:
        print(f"Error fetching stock info for {ticker}: {str(e)}")
        return None


def update_prices_in_db(tickers: List[str], engine: Engine) -> Dict[str, bool]:
    """
    Fetch current prices for a list of tickers and save them to the database.

    Args:
        tickers: List of stock ticker symbols
        engine: SQLAlchemy engine instance

    Returns:
        Dictionary mapping ticker to success status (True/False)
    """
    results = {}
    timestamp = datetime.utcnow()

    with Session(engine) as session:
        for ticker in tickers:
            ticker = ticker.upper().strip()

            try:
                # Get current price and volume
                stock = yf.Ticker(ticker)
                data = stock.history(period="1d")

                if data.empty:
                    print(f"Warning: Could not fetch data for {ticker}")
                    results[ticker] = False
                    continue

                current_price = float(data['Close'].iloc[-1])
                volume = int(data['Volume'].iloc[-1]) if 'Volume' in data.columns else None

                # Create StockPrice record
                stock_price = StockPrice(
                    ticker=ticker,
                    price=current_price,
                    volume=volume,
                    timestamp=timestamp
                )

                session.add(stock_price)
                results[ticker] = True
                print(f"[OK] Updated {ticker}: ${current_price:.2f}")

            except Exception as e:
                print(f"[ERROR] Error updating {ticker}: {str(e)}")
                results[ticker] = False

        # Commit all changes
        try:
            session.commit()
            print(f"\nSuccessfully saved {sum(results.values())}/{len(tickers)} prices to database.")
        except Exception as e:
            session.rollback()
            print(f"Error committing to database: {str(e)}")
            return {ticker: False for ticker in tickers}

    return results


if __name__ == "__main__":
    """Test stock fetcher functionality when run directly."""
    print("=" * 70)
    print("Testing Stock Fetcher")
    print("=" * 70)

    test_tickers = ['AAPL', 'MSFT']

    # Test 1: Get current prices
    print("\n1. Testing get_current_price():")
    print("-" * 70)
    for ticker in test_tickers:
        price = get_current_price(ticker)
        if price:
            print(f"  {ticker}: ${price:.2f}")
        else:
            print(f"  {ticker}: Failed to fetch price")

    # Test 2: Get stock info
    print("\n2. Testing get_stock_info():")
    print("-" * 70)
    for ticker in test_tickers:
        info = get_stock_info(ticker)
        if info:
            print(f"  {ticker}:")
            print(f"    Company: {info['company_name']}")
            print(f"    Sector: {info['sector']}")
            print(f"    Industry: {info['industry']}")
            if isinstance(info['market_cap'], int):
                print(f"    Market Cap: ${info['market_cap']:,}")
        else:
            print(f"  {ticker}: Failed to fetch info")

    # Test 3: Get historical prices
    print("\n3. Testing get_historical_prices():")
    print("-" * 70)
    for ticker in test_tickers:
        df = get_historical_prices(ticker, period="1mo")
        if df is not None and not df.empty:
            print(f"  {ticker}: Retrieved {len(df)} days of historical data")
            print(f"    Date range: {df.index[0].date()} to {df.index[-1].date()}")
            print(f"    Latest close: ${df['Close'].iloc[-1]:.2f}")
        else:
            print(f"  {ticker}: Failed to fetch historical data")

    # Test 4: Update prices in database
    print("\n4. Testing update_prices_in_db():")
    print("-" * 70)
    engine = get_engine()
    results = update_prices_in_db(test_tickers, engine)

    # Verify data was saved
    print("\n5. Verifying database save:")
    print("-" * 70)
    with Session(engine) as session:
        for ticker in test_tickers:
            latest = session.query(StockPrice).filter_by(ticker=ticker).order_by(
                StockPrice.timestamp.desc()
            ).first()
            if latest:
                print(f"  {ticker}: ${latest.price:.2f} at {latest.timestamp}")
            else:
                print(f"  {ticker}: No data found in database")

    print("\n" + "=" * 70)
    print("Stock Fetcher test completed!")
    print("=" * 70)
