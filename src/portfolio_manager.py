"""
Portfolio manager for tracking stock portfolios and calculating performance.
Handles portfolio creation, transactions, holdings calculation, and performance analysis.
"""
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from database import Portfolio, Transaction, PortfolioSnapshot
from stock_fetcher import get_current_price


def create_portfolio(engine: Engine, name: str) -> Optional[int]:
    """
    Create a new portfolio.

    Args:
        engine: SQLAlchemy engine instance
        name: Name for the portfolio

    Returns:
        Portfolio ID if successful, None otherwise
    """
    try:
        with Session(engine) as session:
            portfolio = Portfolio(name=name)
            session.add(portfolio)
            session.commit()
            session.refresh(portfolio)

            print(f"Portfolio '{name}' created successfully with ID: {portfolio.id}")
            return portfolio.id

    except Exception as e:
        print(f"Error creating portfolio: {str(e)}")
        return None


def add_transaction(
    engine: Engine,
    portfolio_id: int,
    ticker: str,
    transaction_type: str,
    shares: float,
    price_per_share: float,
    transaction_date: datetime,
    notes: str = ""
) -> bool:
    """
    Add a buy or sell transaction to a portfolio.

    Args:
        engine: SQLAlchemy engine instance
        portfolio_id: ID of the portfolio
        ticker: Stock ticker symbol
        transaction_type: 'buy' or 'sell'
        shares: Number of shares
        price_per_share: Price per share at transaction
        transaction_date: Date of the transaction
        notes: Optional notes about the transaction

    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate transaction type
        if transaction_type.lower() not in ['buy', 'sell']:
            print(f"Error: transaction_type must be 'buy' or 'sell', got '{transaction_type}'")
            return False

        # Validate shares and price
        if shares <= 0:
            print(f"Error: shares must be positive, got {shares}")
            return False

        if price_per_share <= 0:
            print(f"Error: price_per_share must be positive, got {price_per_share}")
            return False

        with Session(engine) as session:
            # Verify portfolio exists
            portfolio = session.query(Portfolio).filter_by(id=portfolio_id).first()
            if not portfolio:
                print(f"Error: Portfolio with ID {portfolio_id} not found")
                return False

            transaction = Transaction(
                portfolio_id=portfolio_id,
                ticker=ticker.upper(),
                transaction_type=transaction_type.lower(),
                shares=shares,
                price_per_share=price_per_share,
                transaction_date=transaction_date,
                notes=notes
            )

            session.add(transaction)
            session.commit()

            print(f"Transaction added: {transaction_type.upper()} {shares} shares of {ticker.upper()} @ ${price_per_share:.2f}")
            return True

    except Exception as e:
        print(f"Error adding transaction: {str(e)}")
        return False


def get_portfolio_holdings(engine: Engine, portfolio_id: int) -> Optional[pd.DataFrame]:
    """
    Calculate current holdings by processing all transactions.

    Args:
        engine: SQLAlchemy engine instance
        portfolio_id: ID of the portfolio

    Returns:
        DataFrame with columns: ticker, total_shares, avg_cost_basis, total_cost
        or None if error occurs
    """
    try:
        with Session(engine) as session:
            # Verify portfolio exists
            portfolio = session.query(Portfolio).filter_by(id=portfolio_id).first()
            if not portfolio:
                print(f"Error: Portfolio with ID {portfolio_id} not found")
                return None

            # Get all transactions for this portfolio
            transactions = session.query(Transaction).filter_by(
                portfolio_id=portfolio_id
            ).order_by(Transaction.transaction_date).all()

            if not transactions:
                print(f"No transactions found for portfolio {portfolio_id}")
                return pd.DataFrame(columns=['ticker', 'total_shares', 'avg_cost_basis', 'total_cost'])

            # Process transactions to calculate holdings
            holdings = {}

            for txn in transactions:
                ticker = txn.ticker
                if ticker not in holdings:
                    holdings[ticker] = {
                        'total_shares': 0,
                        'total_cost': 0
                    }

                if txn.transaction_type == 'buy':
                    holdings[ticker]['total_shares'] += txn.shares
                    holdings[ticker]['total_cost'] += txn.shares * txn.price_per_share
                elif txn.transaction_type == 'sell':
                    # Calculate cost basis for sold shares (FIFO or average - using average here)
                    if holdings[ticker]['total_shares'] > 0:
                        avg_cost = holdings[ticker]['total_cost'] / holdings[ticker]['total_shares']
                        holdings[ticker]['total_shares'] -= txn.shares
                        holdings[ticker]['total_cost'] -= txn.shares * avg_cost
                    else:
                        print(f"Warning: Selling {txn.shares} shares of {ticker} but no shares held")

            # Convert to DataFrame
            data = []
            for ticker, values in holdings.items():
                if values['total_shares'] > 0:  # Only include positions with shares
                    avg_cost_basis = values['total_cost'] / values['total_shares'] if values['total_shares'] > 0 else 0
                    data.append({
                        'ticker': ticker,
                        'total_shares': values['total_shares'],
                        'avg_cost_basis': avg_cost_basis,
                        'total_cost': values['total_cost']
                    })

            df = pd.DataFrame(data)
            return df

    except Exception as e:
        print(f"Error calculating portfolio holdings: {str(e)}")
        return None


def get_portfolio_performance(engine: Engine, portfolio_id: int) -> Optional[Dict[str, Any]]:
    """
    Calculate portfolio performance including current value and gain/loss.

    Args:
        engine: SQLAlchemy engine instance
        portfolio_id: ID of the portfolio

    Returns:
        Dictionary containing:
        - positions: DataFrame with per-position performance
        - total_cost: Total amount invested
        - total_current_value: Current total value
        - total_gain_loss_dollar: Total gain/loss in dollars
        - total_gain_loss_percent: Total gain/loss percentage
    """
    try:
        # Get current holdings
        holdings_df = get_portfolio_holdings(engine, portfolio_id)

        if holdings_df is None or holdings_df.empty:
            print(f"No holdings found for portfolio {portfolio_id}")
            return {
                'positions': pd.DataFrame(),
                'total_cost': 0,
                'total_current_value': 0,
                'total_gain_loss_dollar': 0,
                'total_gain_loss_percent': 0
            }

        # Fetch current prices for all tickers
        performance_data = []
        total_cost = 0
        total_current_value = 0

        for _, row in holdings_df.iterrows():
            ticker = row['ticker']
            shares = row['total_shares']
            cost_basis = row['avg_cost_basis']
            position_cost = row['total_cost']

            # Get current price
            current_price = get_current_price(ticker)

            if current_price is None:
                print(f"Warning: Could not fetch current price for {ticker}, skipping from performance calculation")
                continue

            # Calculate performance metrics
            current_value = shares * current_price
            gain_loss_dollar = current_value - position_cost
            gain_loss_percent = (gain_loss_dollar / position_cost * 100) if position_cost > 0 else 0

            performance_data.append({
                'ticker': ticker,
                'shares': shares,
                'avg_cost_basis': cost_basis,
                'current_price': current_price,
                'total_cost': position_cost,
                'current_value': current_value,
                'gain_loss_dollar': gain_loss_dollar,
                'gain_loss_percent': gain_loss_percent
            })

            total_cost += position_cost
            total_current_value += current_value

        # Create performance DataFrame
        performance_df = pd.DataFrame(performance_data)

        # Calculate total portfolio metrics
        total_gain_loss_dollar = total_current_value - total_cost
        total_gain_loss_percent = (total_gain_loss_dollar / total_cost * 100) if total_cost > 0 else 0

        return {
            'positions': performance_df,
            'total_cost': total_cost,
            'total_current_value': total_current_value,
            'total_gain_loss_dollar': total_gain_loss_dollar,
            'total_gain_loss_percent': total_gain_loss_percent
        }

    except Exception as e:
        print(f"Error calculating portfolio performance: {str(e)}")
        return None


def save_portfolio_snapshot(engine: Engine, portfolio_id: int) -> bool:
    """
    Save a snapshot of the portfolio's current total value.

    Args:
        engine: SQLAlchemy engine instance
        portfolio_id: ID of the portfolio

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get current portfolio performance
        performance = get_portfolio_performance(engine, portfolio_id)

        if performance is None:
            print(f"Error: Could not calculate performance for portfolio {portfolio_id}")
            return False

        total_value = performance['total_current_value']

        with Session(engine) as session:
            # Verify portfolio exists
            portfolio = session.query(Portfolio).filter_by(id=portfolio_id).first()
            if not portfolio:
                print(f"Error: Portfolio with ID {portfolio_id} not found")
                return False

            snapshot = PortfolioSnapshot(
                portfolio_id=portfolio_id,
                total_value=total_value,
                snapshot_date=datetime.utcnow()
            )

            session.add(snapshot)
            session.commit()

            print(f"Portfolio snapshot saved: ${total_value:.2f} at {snapshot.snapshot_date}")
            return True

    except Exception as e:
        print(f"Error saving portfolio snapshot: {str(e)}")
        return False


if __name__ == "__main__":
    """Test portfolio manager functionality when run directly."""
    from database import get_engine, init_db

    print("=" * 80)
    print("Testing Portfolio Manager")
    print("=" * 80)

    # Initialize database
    engine = init_db()

    # Test 1: Create a portfolio
    print("\n1. Creating portfolio:")
    print("-" * 80)
    portfolio_id = create_portfolio(engine, "My Portfolio")

    if portfolio_id is None:
        print("Failed to create portfolio. Exiting test.")
        exit(1)

    # Test 2: Add transactions
    print("\n2. Adding transactions:")
    print("-" * 80)

    # Buy 10 shares of AAPL at $150
    success1 = add_transaction(
        engine=engine,
        portfolio_id=portfolio_id,
        ticker="AAPL",
        transaction_type="buy",
        shares=10,
        price_per_share=150.00,
        transaction_date=datetime(2024, 1, 15),
        notes="Initial AAPL purchase"
    )

    # Buy 5 shares of MSFT at $380
    success2 = add_transaction(
        engine=engine,
        portfolio_id=portfolio_id,
        ticker="MSFT",
        transaction_type="buy",
        shares=5,
        price_per_share=380.00,
        transaction_date=datetime(2024, 1, 20),
        notes="Initial MSFT purchase"
    )

    if not (success1 and success2):
        print("Failed to add transactions. Exiting test.")
        exit(1)

    # Test 3: Get current holdings
    print("\n3. Current holdings:")
    print("-" * 80)
    holdings = get_portfolio_holdings(engine, portfolio_id)
    if holdings is not None and not holdings.empty:
        print(holdings.to_string(index=False))
    else:
        print("No holdings found or error occurred")

    # Test 4: Get portfolio performance
    print("\n4. Portfolio performance:")
    print("-" * 80)
    performance = get_portfolio_performance(engine, portfolio_id)

    if performance and not performance['positions'].empty:
        print("\nPer-Position Performance:")
        print(performance['positions'].to_string(index=False))

        print(f"\n{'=' * 80}")
        print("PORTFOLIO SUMMARY:")
        print(f"{'=' * 80}")
        print(f"Total Cost:          ${performance['total_cost']:,.2f}")
        print(f"Current Value:       ${performance['total_current_value']:,.2f}")
        print(f"Gain/Loss ($):       ${performance['total_gain_loss_dollar']:,.2f}")
        print(f"Gain/Loss (%):       {performance['total_gain_loss_percent']:.2f}%")
    else:
        print("Could not calculate performance")

    # Test 5: Save portfolio snapshot
    print("\n5. Saving portfolio snapshot:")
    print("-" * 80)
    snapshot_saved = save_portfolio_snapshot(engine, portfolio_id)

    if snapshot_saved:
        # Verify snapshot was saved
        with Session(engine) as session:
            snapshot = session.query(PortfolioSnapshot).filter_by(
                portfolio_id=portfolio_id
            ).order_by(PortfolioSnapshot.snapshot_date.desc()).first()
            if snapshot:
                print(f"Verified: Snapshot found with value ${snapshot.total_value:.2f}")

    print("\n" + "=" * 80)
    print("Portfolio Manager test completed!")
    print("=" * 80)
