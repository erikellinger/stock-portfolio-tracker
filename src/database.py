"""
Database models and setup for Stock Portfolio Tracker.
Uses SQLAlchemy 2.0+ with DeclarativeBase.
"""
import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, ForeignKey, String, Float, Integer, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session


# Get the absolute path to the data directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATABASE_PATH = os.path.join(DATA_DIR, 'portfolio.db')
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Portfolio(Base):
    """Portfolio table to store user portfolios."""
    __tablename__ = 'portfolios'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    snapshots: Mapped[list["PortfolioSnapshot"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Portfolio(id={self.id}, name='{self.name}')>"


class Transaction(Base):
    """Transaction table to store buy/sell transactions."""
    __tablename__ = 'transactions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey('portfolios.id'), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'buy' or 'sell'
    shares: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_share: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, ticker='{self.ticker}', type='{self.transaction_type}', shares={self.shares})>"


class StockPrice(Base):
    """Stock price table to cache historical stock prices."""
    __tablename__ = 'stock_prices'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    def __repr__(self):
        return f"<StockPrice(ticker='{self.ticker}', price={self.price}, timestamp='{self.timestamp}')>"


class PortfolioSnapshot(Base):
    """Portfolio snapshot table to store historical portfolio values."""
    __tablename__ = 'portfolio_snapshots'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey('portfolios.id'), nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(back_populates="snapshots")

    def __repr__(self):
        return f"<PortfolioSnapshot(portfolio_id={self.portfolio_id}, value={self.total_value}, date='{self.snapshot_date}')>"


def init_db():
    """
    Initialize the database by creating all tables if they don't exist.

    Returns:
        engine: SQLAlchemy engine instance
    """
    # Ensure the data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Create engine
    engine = create_engine(DATABASE_URL, echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    print(f"Database initialized at: {DATABASE_PATH}")
    return engine


def get_engine():
    """
    Get the database engine.

    Returns:
        engine: SQLAlchemy engine instance
    """
    return create_engine(DATABASE_URL, echo=False)


if __name__ == "__main__":
    """Test database creation when run directly."""
    print("=" * 60)
    print("Testing Database Setup")
    print("=" * 60)

    # Initialize the database
    engine = init_db()

    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\nTables created: {', '.join(tables)}")
    print(f"Total tables: {len(tables)}")

    # Test basic insert and query
    with Session(engine) as session:
        # Create a test portfolio
        test_portfolio = Portfolio(name="Test Portfolio")
        session.add(test_portfolio)
        session.commit()

        # Query it back
        portfolio = session.query(Portfolio).filter_by(name="Test Portfolio").first()
        print(f"\nTest insert successful: {portfolio}")

        # Clean up test data
        session.delete(portfolio)
        session.commit()
        print("Test data cleaned up.")

    print("\n" + "=" * 60)
    print("Database setup completed successfully!")
    print("=" * 60)
