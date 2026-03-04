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
                "  savings REAL NOT NULL DEFAULT 0,"
                "  savings_updated_at TEXT,"
                "  created_at TEXT NOT NULL"
                ")"
            )
        else:
            # Migrate existing DBs: add savings columns if missing
            cols = {c.name for c in self._db["portfolios"].columns}
            if "savings" not in cols:
                self._db.execute(
                    "ALTER TABLE portfolios ADD COLUMN savings REAL NOT NULL DEFAULT 0"
                )
            if "savings_updated_at" not in cols:
                self._db.execute(
                    "ALTER TABLE portfolios ADD COLUMN savings_updated_at TEXT"
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

        if "activity_log" not in self._db.table_names():
            self._db.execute(
                "CREATE TABLE activity_log ("
                "  id INTEGER PRIMARY KEY,"
                "  portfolio_id INTEGER NOT NULL,"
                "  agent_name TEXT NOT NULL,"
                "  event_type TEXT NOT NULL,"
                "  description TEXT NOT NULL,"
                "  amount REAL,"
                "  balance_after REAL,"
                "  timestamp TEXT NOT NULL,"
                "  FOREIGN KEY(portfolio_id) REFERENCES portfolios(id)"
                ")"
            )

        if "agent_notes" not in self._db.table_names():
            self._db.execute(
                "CREATE TABLE agent_notes ("
                "  id INTEGER PRIMARY KEY,"
                "  portfolio_id INTEGER NOT NULL,"
                "  agent_name TEXT NOT NULL,"
                "  category TEXT NOT NULL DEFAULT 'general',"
                "  title TEXT NOT NULL,"
                "  content TEXT NOT NULL,"
                "  created_at TEXT NOT NULL,"
                "  updated_at TEXT NOT NULL,"
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
            "INSERT INTO portfolios (agent_name, starting_cash, current_cash, savings, savings_updated_at, created_at) "
            "VALUES (?, ?, ?, 0, NULL, ?)",
            [agent_name, self._default_cash, self._default_cash, now],
        )
        pid = self._db.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {
            "id": pid,
            "agent_name": agent_name,
            "starting_cash": self._default_cash,
            "current_cash": self._default_cash,
            "savings": 0.0,
            "savings_updated_at": None,
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
    # Activity log
    # ------------------------------------------------------------------

    def log_activity(
        self,
        portfolio_id: int,
        agent_name: str,
        event_type: str,
        description: str,
        amount: float | None = None,
        balance_after: float | None = None,
    ) -> None:
        """Record an event in the activity log."""
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "INSERT INTO activity_log "
            "(portfolio_id, agent_name, event_type, description, amount, balance_after, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [portfolio_id, agent_name, event_type, description, amount, balance_after, now],
        )

    def get_activity_log(
        self, portfolio_id: int | None = None, limit: int = 100,
    ) -> list[dict]:
        """Return activity events, newest first.

        If portfolio_id is None, returns global activity across all agents.
        """
        if portfolio_id is not None:
            rows = self._db.execute(
                "SELECT * FROM activity_log WHERE portfolio_id = ? ORDER BY id DESC LIMIT ?",
                [portfolio_id, limit],
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?",
                [limit],
            ).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._db.execute("SELECT * FROM activity_log LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

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

        self.log_activity(
            pid, agent_name, "buy",
            f"Bought {quantity} {symbol} @ ${price:,.2f}",
            amount=total, balance_after=new_cash,
        )

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

        pnl_str = f" (P&L: ${pnl:+,.2f})" if pnl else ""
        self.log_activity(
            pid, agent_name, "sell",
            f"Sold {quantity} {symbol} @ ${price:,.2f}{pnl_str}",
            amount=total, balance_after=new_cash,
        )

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
    # Savings
    # ------------------------------------------------------------------

    def accrue_interest(self, portfolio_id: int, apy: float) -> float:
        """Accrue simple daily interest on savings balance.

        Returns the amount of interest accrued.
        """
        row = self._db.execute(
            "SELECT savings, savings_updated_at FROM portfolios WHERE id = ?",
            [portfolio_id],
        ).fetchone()
        if not row:
            return 0.0

        savings, updated_at = row
        if not savings or savings <= 0 or not updated_at:
            # Nothing to accrue — just update timestamp
            now = datetime.now(timezone.utc).isoformat()
            self._db.execute(
                "UPDATE portfolios SET savings_updated_at = ? WHERE id = ?",
                [now, portfolio_id],
            )
            return 0.0

        last = datetime.fromisoformat(updated_at)
        now_dt = datetime.now(timezone.utc)
        days = (now_dt - last).total_seconds() / 86400.0
        if days <= 0:
            return 0.0

        interest = round(savings * (apy / 365.25) * days, 2)
        if interest <= 0:
            now_iso = now_dt.isoformat()
            self._db.execute(
                "UPDATE portfolios SET savings_updated_at = ? WHERE id = ?",
                [now_iso, portfolio_id],
            )
            return 0.0

        new_savings = round(savings + interest, 2)
        now_iso = now_dt.isoformat()

        self._db.execute(
            "UPDATE portfolios SET savings = ?, savings_updated_at = ? WHERE id = ?",
            [new_savings, now_iso, portfolio_id],
        )

        # Look up agent name for activity log
        agent_row = self._db.execute(
            "SELECT agent_name FROM portfolios WHERE id = ?", [portfolio_id]
        ).fetchone()
        if agent_row:
            self.log_activity(
                portfolio_id, agent_row[0], "interest",
                f"Interest accrued: ${interest:,.2f} ({apy*100:.1f}% APY)",
                amount=interest, balance_after=new_savings,
            )

        return interest

    def deposit_savings(self, agent_name: str, amount: float, apy: float) -> dict:
        """Move cash into savings. Accrues interest first.

        Raises ValueError if insufficient cash.
        """
        amount = round(float(amount), 2)
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")

        portfolio = self.get_or_create_portfolio(agent_name)
        pid = portfolio["id"]

        # Accrue any pending interest before modifying
        self.accrue_interest(pid, apy)

        # Re-read after accrual
        portfolio = self.get_portfolio(agent_name)
        if amount > portfolio["current_cash"]:
            raise ValueError(
                f"Insufficient cash: want to deposit ${amount:,.2f} "
                f"but only have ${portfolio['current_cash']:,.2f}"
            )

        new_cash = round(portfolio["current_cash"] - amount, 2)
        new_savings = round(portfolio["savings"] + amount, 2)
        now = datetime.now(timezone.utc).isoformat()

        self._db.execute(
            "UPDATE portfolios SET current_cash = ?, savings = ?, savings_updated_at = ? WHERE id = ?",
            [new_cash, new_savings, now, pid],
        )

        self.log_activity(
            pid, agent_name, "deposit",
            f"Deposited ${amount:,.2f} to savings",
            amount=amount, balance_after=new_cash,
        )

        return {
            "action": "deposit",
            "amount": amount,
            "cash_remaining": new_cash,
            "savings_balance": new_savings,
        }

    def withdraw_savings(self, agent_name: str, amount: float, apy: float) -> dict:
        """Move savings back to cash. Accrues interest first.

        Raises ValueError if insufficient savings.
        """
        amount = round(float(amount), 2)
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")

        portfolio = self.get_or_create_portfolio(agent_name)
        pid = portfolio["id"]

        # Accrue any pending interest before modifying
        self.accrue_interest(pid, apy)

        # Re-read after accrual
        portfolio = self.get_portfolio(agent_name)
        if amount > portfolio["savings"]:
            raise ValueError(
                f"Insufficient savings: want to withdraw ${amount:,.2f} "
                f"but only have ${portfolio['savings']:,.2f}"
            )

        new_savings = round(portfolio["savings"] - amount, 2)
        new_cash = round(portfolio["current_cash"] + amount, 2)
        now = datetime.now(timezone.utc).isoformat()

        self._db.execute(
            "UPDATE portfolios SET current_cash = ?, savings = ?, savings_updated_at = ? WHERE id = ?",
            [new_cash, new_savings, now, pid],
        )

        self.log_activity(
            pid, agent_name, "withdraw",
            f"Withdrew ${amount:,.2f} from savings",
            amount=amount, balance_after=new_cash,
        )

        return {
            "action": "withdraw",
            "amount": amount,
            "cash_remaining": new_cash,
            "savings_balance": new_savings,
        }

    # ------------------------------------------------------------------
    # Agent Notes
    # ------------------------------------------------------------------

    _NOTE_CATEGORIES = {"research", "thesis", "watchlist", "lesson", "general"}

    def save_note(
        self,
        agent_name: str,
        title: str,
        content: str,
        category: str = "general",
        note_id: int | None = None,
    ) -> dict:
        """Create or update a note. Returns the note dict."""
        category = category.lower()
        if category not in self._NOTE_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(sorted(self._NOTE_CATEGORIES))}"
            )

        portfolio = self.get_or_create_portfolio(agent_name)
        pid = portfolio["id"]
        now = datetime.now(timezone.utc).isoformat()

        if note_id is not None:
            # Update existing — verify ownership
            existing = self._db.execute(
                "SELECT id FROM agent_notes WHERE id = ? AND portfolio_id = ?",
                [note_id, pid],
            ).fetchone()
            if not existing:
                raise ValueError(f"Note {note_id} not found for agent '{agent_name}'")

            self._db.execute(
                "UPDATE agent_notes SET title = ?, content = ?, category = ?, updated_at = ? "
                "WHERE id = ?",
                [title, content, category, now, note_id],
            )
            self.log_activity(pid, agent_name, "note_update", f"Updated note: {title}")
            nid = note_id
        else:
            self._db.execute(
                "INSERT INTO agent_notes "
                "(portfolio_id, agent_name, category, title, content, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [pid, agent_name, category, title, content, now, now],
            )
            nid = self._db.execute("SELECT last_insert_rowid()").fetchone()[0]
            self.log_activity(pid, agent_name, "note_create", f"Created note: {title}")

        return {
            "id": nid,
            "agent_name": agent_name,
            "category": category,
            "title": title,
            "content": content,
            "created_at": now if note_id is None else None,
            "updated_at": now,
        }

    def get_notes(
        self, agent_name: str, category: str | None = None, limit: int = 50,
    ) -> list[dict]:
        """List notes for an agent, newest-updated first."""
        portfolio = self.get_portfolio(agent_name)
        if not portfolio:
            return []
        pid = portfolio["id"]

        if category:
            rows = self._db.execute(
                "SELECT * FROM agent_notes WHERE portfolio_id = ? AND category = ? "
                "ORDER BY updated_at DESC LIMIT ?",
                [pid, category.lower(), limit],
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM agent_notes WHERE portfolio_id = ? "
                "ORDER BY updated_at DESC LIMIT ?",
                [pid, limit],
            ).fetchall()

        if not rows:
            return []
        cols = [d[0] for d in self._db.execute("SELECT * FROM agent_notes LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    def search_notes(
        self, agent_name: str, query: str, limit: int = 20,
    ) -> list[dict]:
        """Search notes by title and content (LIKE match)."""
        portfolio = self.get_portfolio(agent_name)
        if not portfolio:
            return []
        pid = portfolio["id"]
        pattern = f"%{query}%"

        rows = self._db.execute(
            "SELECT * FROM agent_notes WHERE portfolio_id = ? "
            "AND (title LIKE ? OR content LIKE ?) "
            "ORDER BY updated_at DESC LIMIT ?",
            [pid, pattern, pattern, limit],
        ).fetchall()

        if not rows:
            return []
        cols = [d[0] for d in self._db.execute("SELECT * FROM agent_notes LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    def delete_note(self, agent_name: str, note_id: int) -> bool:
        """Delete a note with ownership check. Returns True if deleted."""
        portfolio = self.get_portfolio(agent_name)
        if not portfolio:
            return False
        pid = portfolio["id"]

        existing = self._db.execute(
            "SELECT title FROM agent_notes WHERE id = ? AND portfolio_id = ?",
            [note_id, pid],
        ).fetchone()
        if not existing:
            return False

        self._db.execute("DELETE FROM agent_notes WHERE id = ?", [note_id])
        self.log_activity(pid, agent_name, "note_delete", f"Deleted note: {existing[0]}")
        return True

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
        self._db.execute("DELETE FROM agent_notes WHERE portfolio_id = ?", [pid])
        self._db.execute(
            "UPDATE portfolios SET current_cash = starting_cash, savings = 0, savings_updated_at = NULL WHERE id = ?",
            [pid],
        )

        self.log_activity(
            pid, agent_name, "reset",
            f"Portfolio reset to ${portfolio['starting_cash']:,.2f}",
            amount=portfolio["starting_cash"],
            balance_after=portfolio["starting_cash"],
        )

        return True
