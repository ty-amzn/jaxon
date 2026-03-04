"""SQLite store for paper trading portfolios, positions, and orders."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlite_utils


class PaperTradingStore:
    """Persistent paper trading store backed by SQLite."""

    def __init__(self, db_path: Path, default_starting_cash: float = 100_000.0) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_utils.Database(str(db_path))
        self._default_cash = default_starting_cash
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        if "portfolios" not in self._db.table_names():
            self._db.execute(
                "CREATE TABLE portfolios ("
                "  id INTEGER PRIMARY KEY,"
                "  agent_name TEXT NOT NULL UNIQUE,"
                "  starting_cash REAL NOT NULL,"
                "  current_cash REAL NOT NULL,"
                "  created_at TEXT NOT NULL"
                ")"
            )

        if "positions" not in self._db.table_names():
            self._db.execute(
                "CREATE TABLE positions ("
                "  id INTEGER PRIMARY KEY,"
                "  portfolio_id INTEGER NOT NULL,"
                "  symbol TEXT NOT NULL,"
                "  quantity REAL NOT NULL,"
                "  avg_cost REAL NOT NULL,"
                "  UNIQUE(portfolio_id, symbol),"
                "  FOREIGN KEY(portfolio_id) REFERENCES portfolios(id)"
                ")"
            )

        if "orders" not in self._db.table_names():
            self._db.execute(
                "CREATE TABLE orders ("
                "  id INTEGER PRIMARY KEY,"
                "  portfolio_id INTEGER NOT NULL,"
                "  symbol TEXT NOT NULL,"
                "  side TEXT NOT NULL,"
                "  quantity REAL NOT NULL,"
                "  price REAL NOT NULL,"
                "  total REAL NOT NULL,"
                "  executed_at TEXT NOT NULL,"
                "  FOREIGN KEY(portfolio_id) REFERENCES portfolios(id)"
                ")"
            )

        if "snapshots" not in self._db.table_names():
            self._db.execute(
                "CREATE TABLE snapshots ("
                "  id INTEGER PRIMARY KEY,"
                "  portfolio_id INTEGER NOT NULL,"
                "  total_value REAL NOT NULL,"
                "  cash REAL NOT NULL,"
                "  positions_value REAL NOT NULL,"
                "  timestamp TEXT NOT NULL,"
                "  FOREIGN KEY(portfolio_id) REFERENCES portfolios(id)"
                ")"
            )

    # ------------------------------------------------------------------
    # Portfolio CRUD
    # ------------------------------------------------------------------

    def get_or_create_portfolio(self, agent_name: str) -> dict:
        """Get existing portfolio or create a new one with default starting cash."""
        row = self._db.execute(
            "SELECT * FROM portfolios WHERE agent_name = ?", [agent_name]
        ).fetchone()
        if row:
            cols = [d[0] for d in self._db.execute("SELECT * FROM portfolios LIMIT 0").description]
            return dict(zip(cols, row))

        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "INSERT INTO portfolios (agent_name, starting_cash, current_cash, created_at) "
            "VALUES (?, ?, ?, ?)",
            [agent_name, self._default_cash, self._default_cash, now],
        )
        pid = self._db.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {
            "id": pid,
            "agent_name": agent_name,
            "starting_cash": self._default_cash,
            "current_cash": self._default_cash,
            "created_at": now,
        }

    def list_portfolios(self) -> list[dict]:
        """Return all portfolios."""
        rows = self._db.execute("SELECT * FROM portfolios ORDER BY agent_name").fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._db.execute("SELECT * FROM portfolios LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    def get_portfolio(self, agent_name: str) -> dict | None:
        """Return a portfolio by agent name, or None."""
        row = self._db.execute(
            "SELECT * FROM portfolios WHERE agent_name = ?", [agent_name]
        ).fetchone()
        if not row:
            return None
        cols = [d[0] for d in self._db.execute("SELECT * FROM portfolios LIMIT 0").description]
        return dict(zip(cols, row))

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_positions(self, portfolio_id: int) -> list[dict]:
        """Return all positions for a portfolio."""
        rows = self._db.execute(
            "SELECT * FROM positions WHERE portfolio_id = ? ORDER BY symbol",
            [portfolio_id],
        ).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._db.execute("SELECT * FROM positions LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    def _get_position(self, portfolio_id: int, symbol: str) -> dict | None:
        """Return a single position or None."""
        row = self._db.execute(
            "SELECT * FROM positions WHERE portfolio_id = ? AND symbol = ?",
            [portfolio_id, symbol],
        ).fetchone()
        if not row:
            return None
        cols = [d[0] for d in self._db.execute("SELECT * FROM positions LIMIT 0").description]
        return dict(zip(cols, row))

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------

    def execute_buy(
        self, agent_name: str, symbol: str, quantity: float, price: float,
    ) -> dict:
        """Execute a buy order. Returns the order record.

        Raises ValueError if insufficient cash.
        """
        symbol = symbol.upper()
        quantity = float(quantity)
        price = float(price)
        total = round(quantity * price, 2)

        portfolio = self.get_or_create_portfolio(agent_name)
        pid = portfolio["id"]

        if total > portfolio["current_cash"]:
            raise ValueError(
                f"Insufficient cash: need ${total:,.2f} but only have "
                f"${portfolio['current_cash']:,.2f}"
            )

        # Deduct cash
        new_cash = round(portfolio["current_cash"] - total, 2)
        self._db.execute(
            "UPDATE portfolios SET current_cash = ? WHERE id = ?", [new_cash, pid]
        )

        # Update or create position (weighted average cost)
        pos = self._get_position(pid, symbol)
        if pos:
            new_qty = pos["quantity"] + quantity
            new_avg = round(
                (pos["avg_cost"] * pos["quantity"] + price * quantity) / new_qty, 4
            )
            self._db.execute(
                "UPDATE positions SET quantity = ?, avg_cost = ? "
                "WHERE portfolio_id = ? AND symbol = ?",
                [new_qty, new_avg, pid, symbol],
            )
        else:
            self._db.execute(
                "INSERT INTO positions (portfolio_id, symbol, quantity, avg_cost) "
                "VALUES (?, ?, ?, ?)",
                [pid, symbol, quantity, price],
            )

        # Record order
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "INSERT INTO orders (portfolio_id, symbol, side, quantity, price, total, executed_at) "
            "VALUES (?, ?, 'buy', ?, ?, ?, ?)",
            [pid, symbol, quantity, price, total, now],
        )
        order_id = self._db.execute("SELECT last_insert_rowid()").fetchone()[0]

        return {
            "id": order_id,
            "symbol": symbol,
            "side": "buy",
            "quantity": quantity,
            "price": price,
            "total": total,
            "executed_at": now,
            "cash_remaining": new_cash,
        }

    def execute_sell(
        self, agent_name: str, symbol: str, quantity: float, price: float,
    ) -> dict:
        """Execute a sell order. Returns the order record.

        Raises ValueError if insufficient shares.
        """
        symbol = symbol.upper()
        quantity = float(quantity)
        price = float(price)
        total = round(quantity * price, 2)

        portfolio = self.get_or_create_portfolio(agent_name)
        pid = portfolio["id"]

        pos = self._get_position(pid, symbol)
        if not pos or pos["quantity"] < quantity:
            held = pos["quantity"] if pos else 0
            raise ValueError(
                f"Insufficient shares: want to sell {quantity} {symbol} "
                f"but only hold {held}"
            )

        # Add cash
        new_cash = round(portfolio["current_cash"] + total, 2)
        self._db.execute(
            "UPDATE portfolios SET current_cash = ? WHERE id = ?", [new_cash, pid]
        )

        # Update position
        new_qty = pos["quantity"] - quantity
        if new_qty < 0.0001:  # effectively zero
            self._db.execute(
                "DELETE FROM positions WHERE portfolio_id = ? AND symbol = ?",
                [pid, symbol],
            )
        else:
            self._db.execute(
                "UPDATE positions SET quantity = ? WHERE portfolio_id = ? AND symbol = ?",
                [new_qty, pid, symbol],
            )

        # Record order
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "INSERT INTO orders (portfolio_id, symbol, side, quantity, price, total, executed_at) "
            "VALUES (?, ?, 'sell', ?, ?, ?, ?)",
            [pid, symbol, quantity, price, total, now],
        )
        order_id = self._db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # P&L for this trade
        pnl = round((price - pos["avg_cost"]) * quantity, 2)

        return {
            "id": order_id,
            "symbol": symbol,
            "side": "sell",
            "quantity": quantity,
            "price": price,
            "total": total,
            "executed_at": now,
            "cash_remaining": new_cash,
            "realized_pnl": pnl,
        }

    # ------------------------------------------------------------------
    # Order history
    # ------------------------------------------------------------------

    def get_orders(self, portfolio_id: int, limit: int = 50) -> list[dict]:
        """Return recent orders for a portfolio, newest first."""
        rows = self._db.execute(
            "SELECT * FROM orders WHERE portfolio_id = ? ORDER BY id DESC LIMIT ?",
            [portfolio_id, limit],
        ).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._db.execute("SELECT * FROM orders LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def save_snapshot(
        self, portfolio_id: int, total_value: float, cash: float, positions_value: float,
    ) -> None:
        """Save a portfolio value snapshot for charting."""
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "INSERT INTO snapshots (portfolio_id, total_value, cash, positions_value, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            [portfolio_id, total_value, cash, positions_value, now],
        )

    def get_snapshots(self, portfolio_id: int, limit: int = 100) -> list[dict]:
        """Return snapshots for a portfolio, oldest first."""
        rows = self._db.execute(
            "SELECT * FROM snapshots WHERE portfolio_id = ? ORDER BY id ASC LIMIT ?",
            [portfolio_id, limit],
        ).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._db.execute("SELECT * FROM snapshots LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset_portfolio(self, agent_name: str) -> bool:
        """Reset a portfolio to starting cash, clearing positions and orders.

        Returns True if portfolio existed.
        """
        portfolio = self.get_portfolio(agent_name)
        if not portfolio:
            return False

        pid = portfolio["id"]
        self._db.execute("DELETE FROM positions WHERE portfolio_id = ?", [pid])
        self._db.execute("DELETE FROM orders WHERE portfolio_id = ?", [pid])
        self._db.execute("DELETE FROM snapshots WHERE portfolio_id = ?", [pid])
        self._db.execute(
            "UPDATE portfolios SET current_cash = starting_cash WHERE id = ?", [pid]
        )
        return True
