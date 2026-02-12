"""
Pytest configuration and shared fixtures for portfolio tracker tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import sys
import os

# Add src directory to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import Base


@pytest.fixture(scope="function")
def test_engine():
    """
    Create an in-memory SQLite database for testing.
    This fixture is function-scoped, so each test gets a fresh database.
    """
    # Create in-memory database
    engine = create_engine('sqlite:///:memory:', echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Clean up
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine):
    """
    Create a database session for testing.
    Automatically rolls back after each test to ensure isolation.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    # Rollback and cleanup
    session.close()
    transaction.rollback()
    connection.close()
