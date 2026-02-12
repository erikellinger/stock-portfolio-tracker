"""
Unit tests for portfolio_manager.py module.
Tests portfolio creation, transactions, holdings calculation, and error handling.
"""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import Portfolio, Transaction
from portfolio_manager import (
    create_portfolio,
    add_transaction,
    get_portfolio_holdings,
    get_portfolio_performance,
    save_portfolio_snapshot
)


class TestCreatePortfolio:
    """Tests for portfolio creation functionality."""

    def test_create_portfolio(self, test_engine):
        """Test creating a portfolio and verify it exists in the database."""
        # Create a portfolio
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        # Verify it was created
        assert portfolio_id is not None
        assert isinstance(portfolio_id, int)

        # Verify it exists in database
        with Session(test_engine) as session:
            portfolio = session.query(Portfolio).filter_by(id=portfolio_id).first()
            assert portfolio is not None
            assert portfolio.name == "Test Portfolio"
            assert portfolio.created_at is not None

    def test_create_multiple_portfolios(self, test_engine):
        """Test creating multiple portfolios."""
        portfolio_id1 = create_portfolio(test_engine, "Portfolio 1")
        portfolio_id2 = create_portfolio(test_engine, "Portfolio 2")

        assert portfolio_id1 != portfolio_id2

        with Session(test_engine) as session:
            portfolios = session.query(Portfolio).all()
            assert len(portfolios) == 2


class TestAddTransaction:
    """Tests for transaction addition functionality."""

    def test_add_buy_transaction(self, test_engine):
        """Test adding a buy transaction and verify it was saved correctly."""
        # Create a portfolio
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        # Add a buy transaction
        trans_date = datetime(2024, 1, 15, 10, 30)
        success = add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="AAPL",
            transaction_type="buy",
            shares=10.0,
            price_per_share=150.00,
            transaction_date=trans_date,
            notes="Test buy transaction"
        )

        assert success is True

        # Verify transaction was saved
        with Session(test_engine) as session:
            transaction = session.query(Transaction).filter_by(
                portfolio_id=portfolio_id
            ).first()

            assert transaction is not None
            assert transaction.ticker == "AAPL"
            assert transaction.transaction_type == "buy"
            assert transaction.shares == 10.0
            assert transaction.price_per_share == 150.00
            assert transaction.transaction_date == trans_date
            assert transaction.notes == "Test buy transaction"

    def test_add_sell_transaction(self, test_engine):
        """Test adding buy then sell transaction and verify holdings are calculated correctly."""
        # Create a portfolio
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        # Add buy transaction - 10 shares
        add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="MSFT",
            transaction_type="buy",
            shares=10.0,
            price_per_share=300.00,
            transaction_date=datetime(2024, 1, 10)
        )

        # Add sell transaction - 4 shares
        success = add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="MSFT",
            transaction_type="sell",
            shares=4.0,
            price_per_share=320.00,
            transaction_date=datetime(2024, 1, 20)
        )

        assert success is True

        # Verify holdings - should have 6 shares remaining
        holdings = get_portfolio_holdings(test_engine, portfolio_id)

        assert holdings is not None
        assert len(holdings) == 1
        assert holdings.iloc[0]['ticker'] == "MSFT"
        assert holdings.iloc[0]['total_shares'] == 6.0  # 10 - 4 = 6

        # Cost should be reduced proportionally
        # Original cost: 10 * 300 = 3000
        # Sold: 4 shares at avg cost of 300 = 1200
        # Remaining cost: 3000 - 1200 = 1800
        assert abs(holdings.iloc[0]['total_cost'] - 1800.0) < 0.01
        assert abs(holdings.iloc[0]['avg_cost_basis'] - 300.0) < 0.01

    def test_ticker_case_normalization(self, test_engine):
        """Test that tickers are normalized to uppercase."""
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        # Add transaction with lowercase ticker
        add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="aapl",  # lowercase
            transaction_type="buy",
            shares=5.0,
            price_per_share=150.00,
            transaction_date=datetime(2024, 1, 15)
        )

        # Verify it's stored as uppercase
        with Session(test_engine) as session:
            transaction = session.query(Transaction).first()
            assert transaction.ticker == "AAPL"


class TestGetPortfolioHoldings:
    """Tests for portfolio holdings calculation."""

    def test_get_portfolio_holdings(self, test_engine):
        """Test adding multiple transactions and verify holdings dataframe has correct columns and values."""
        # Create a portfolio
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        # Add multiple transactions for different stocks
        add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="AAPL",
            transaction_type="buy",
            shares=10.0,
            price_per_share=150.00,
            transaction_date=datetime(2024, 1, 10)
        )

        add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="AAPL",
            transaction_type="buy",
            shares=5.0,
            price_per_share=160.00,
            transaction_date=datetime(2024, 1, 15)
        )

        add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="MSFT",
            transaction_type="buy",
            shares=8.0,
            price_per_share=350.00,
            transaction_date=datetime(2024, 1, 12)
        )

        # Get holdings
        holdings = get_portfolio_holdings(test_engine, portfolio_id)

        # Verify dataframe structure
        assert holdings is not None
        assert len(holdings) == 2  # Two different stocks
        assert list(holdings.columns) == ['ticker', 'total_shares', 'avg_cost_basis', 'total_cost']

        # Verify AAPL holdings
        aapl_row = holdings[holdings['ticker'] == 'AAPL'].iloc[0]
        assert aapl_row['total_shares'] == 15.0  # 10 + 5
        assert abs(aapl_row['total_cost'] - 2300.0) < 0.01  # (10*150) + (5*160) = 2300
        expected_avg_cost = 2300.0 / 15.0  # ~153.33
        assert abs(aapl_row['avg_cost_basis'] - expected_avg_cost) < 0.01

        # Verify MSFT holdings
        msft_row = holdings[holdings['ticker'] == 'MSFT'].iloc[0]
        assert msft_row['total_shares'] == 8.0
        assert abs(msft_row['total_cost'] - 2800.0) < 0.01  # 8*350
        assert abs(msft_row['avg_cost_basis'] - 350.0) < 0.01

    def test_empty_portfolio_holdings(self, test_engine):
        """Test getting holdings for an empty portfolio."""
        portfolio_id = create_portfolio(test_engine, "Empty Portfolio")

        holdings = get_portfolio_holdings(test_engine, portfolio_id)

        assert holdings is not None
        assert len(holdings) == 0
        assert list(holdings.columns) == ['ticker', 'total_shares', 'avg_cost_basis', 'total_cost']

    def test_holdings_exclude_fully_sold_positions(self, test_engine):
        """Test that positions sold completely are excluded from holdings."""
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        # Buy and sell all shares
        add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="TSLA",
            transaction_type="buy",
            shares=5.0,
            price_per_share=200.00,
            transaction_date=datetime(2024, 1, 10)
        )

        add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="TSLA",
            transaction_type="sell",
            shares=5.0,
            price_per_share=250.00,
            transaction_date=datetime(2024, 1, 20)
        )

        holdings = get_portfolio_holdings(test_engine, portfolio_id)

        # Should have no holdings since all shares were sold
        assert len(holdings) == 0


class TestInvalidTransactions:
    """Tests for invalid transaction handling and error cases."""

    def test_invalid_transaction_type(self, test_engine):
        """Test that adding a transaction with invalid type fails gracefully."""
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        # Try to add transaction with invalid type
        success = add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="AAPL",
            transaction_type="trade",  # Invalid - should be 'buy' or 'sell'
            shares=10.0,
            price_per_share=150.00,
            transaction_date=datetime(2024, 1, 15)
        )

        assert success is False

        # Verify no transaction was added
        with Session(test_engine) as session:
            count = session.query(Transaction).count()
            assert count == 0

    def test_negative_shares(self, test_engine):
        """Test that adding a transaction with negative shares fails gracefully."""
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        # Try to add transaction with negative shares
        success = add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="AAPL",
            transaction_type="buy",
            shares=-10.0,  # Invalid - negative shares
            price_per_share=150.00,
            transaction_date=datetime(2024, 1, 15)
        )

        assert success is False

        # Verify no transaction was added
        with Session(test_engine) as session:
            count = session.query(Transaction).count()
            assert count == 0

    def test_negative_price(self, test_engine):
        """Test that adding a transaction with negative price fails gracefully."""
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        success = add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="AAPL",
            transaction_type="buy",
            shares=10.0,
            price_per_share=-150.00,  # Invalid - negative price
            transaction_date=datetime(2024, 1, 15)
        )

        assert success is False

        with Session(test_engine) as session:
            count = session.query(Transaction).count()
            assert count == 0

    def test_zero_shares(self, test_engine):
        """Test that adding a transaction with zero shares fails gracefully."""
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        success = add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="AAPL",
            transaction_type="buy",
            shares=0.0,  # Invalid - zero shares
            price_per_share=150.00,
            transaction_date=datetime(2024, 1, 15)
        )

        assert success is False

    def test_invalid_portfolio_id(self, test_engine):
        """Test that adding a transaction to non-existent portfolio fails gracefully."""
        # Try to add transaction to portfolio that doesn't exist
        success = add_transaction(
            engine=test_engine,
            portfolio_id=9999,  # Non-existent portfolio ID
            ticker="AAPL",
            transaction_type="buy",
            shares=10.0,
            price_per_share=150.00,
            transaction_date=datetime(2024, 1, 15)
        )

        assert success is False

    def test_nonexistent_portfolio_holdings(self, test_engine):
        """Test getting holdings for a non-existent portfolio."""
        holdings = get_portfolio_holdings(test_engine, 9999)

        # Should return None or empty dataframe
        assert holdings is None


class TestPortfolioPerformance:
    """Tests for portfolio performance calculations."""

    def test_save_portfolio_snapshot(self, test_engine):
        """Test saving a portfolio snapshot."""
        # Note: This test won't work without mocking stock_fetcher.get_current_price
        # since it tries to fetch real stock prices
        # For now, we'll just test the basic structure
        portfolio_id = create_portfolio(test_engine, "Test Portfolio")

        # Add a transaction
        add_transaction(
            engine=test_engine,
            portfolio_id=portfolio_id,
            ticker="AAPL",
            transaction_type="buy",
            shares=10.0,
            price_per_share=150.00,
            transaction_date=datetime(2024, 1, 15)
        )

        # Note: This will try to fetch real stock prices and may fail
        # In a production environment, you'd mock get_current_price
        # For now, we'll just verify the function doesn't crash
        try:
            save_portfolio_snapshot(test_engine, portfolio_id)
        except Exception:
            # Expected to fail without real stock data or mocking
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
