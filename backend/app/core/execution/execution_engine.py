"""
ExecutionEngine — The ONLY layer that communicates with the broker.

In this implementation the broker integration is abstracted behind a
BrokerClient interface so it can be swapped for live API clients (OANDA,
Interactive Brokers, MT5, etc.) without touching any other layer.

The engine validates that a RiskCheckResult was approved before placing any
order — providing a final gate.
"""

import uuid
from typing import Any

from app.schemas.execution import CloseOrderRequest, ExecutionRequest, ExecutionResult, ModifyOrderRequest
from app.schemas.risk import RiskCheckResult


class BrokerClient:
    """
    Placeholder broker client.
    Replace `_send_order` with a real HTTP client (e.g. OANDA REST v20,
    MT5 via MetaApi, IBKR TWS API, etc.).
    """

    def place_order(self, request: ExecutionRequest) -> dict[str, Any]:
        # Simulate order placement
        order_id = str(uuid.uuid4())[:12].upper()
        return {
            "order_id": order_id,
            "status": "FILLED",
            "fill_price": request.entry_price,
            "symbol": request.symbol,
            "direction": request.direction,
            "lot_size": request.lot_size,
        }

    def modify_order(self, request: ModifyOrderRequest) -> dict[str, Any]:
        return {
            "order_id": request.broker_order_id,
            "status": "MODIFIED",
            "new_stop_loss": request.new_stop_loss,
            "new_take_profit": request.new_take_profit,
        }

    def close_order(self, request: CloseOrderRequest) -> dict[str, Any]:
        return {
            "order_id": request.broker_order_id,
            "status": "CLOSED",
            "lot_size_closed": request.lot_size,
        }


class ExecutionEngine:
    def __init__(self, broker_client: BrokerClient | None = None) -> None:
        self._broker = broker_client or BrokerClient()

    def place_order(
        self, request: ExecutionRequest, risk_result: RiskCheckResult
    ) -> ExecutionResult:
        """Place a market/limit order.  Requires an approved RiskCheckResult."""
        if not risk_result.approved:
            return ExecutionResult(
                success=False,
                symbol=request.symbol,
                direction=request.direction,
                lot_size=request.lot_size,
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
                error=f"Risk check failed: {risk_result.rejection_reason}",
            )

        try:
            response = self._broker.place_order(request)
            return ExecutionResult(
                success=True,
                broker_order_id=response.get("order_id"),
                symbol=request.symbol,
                direction=request.direction,
                lot_size=request.lot_size,
                entry_price=response.get("fill_price"),
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
                raw_response=response,
            )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                symbol=request.symbol,
                direction=request.direction,
                lot_size=request.lot_size,
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
                error=str(exc),
            )

    def modify_order(self, request: ModifyOrderRequest) -> dict[str, Any]:
        return self._broker.modify_order(request)

    def close_order(self, request: CloseOrderRequest) -> dict[str, Any]:
        return self._broker.close_order(request)

    def move_to_breakeven(self, broker_order_id: str, entry_price: float) -> dict[str, Any]:
        """Move stop loss to entry price (breakeven)."""
        req = ModifyOrderRequest(
            broker_order_id=broker_order_id,
            new_stop_loss=entry_price,
        )
        return self._broker.modify_order(req)

    def partial_close(self, broker_order_id: str, lot_size: float) -> dict[str, Any]:
        req = CloseOrderRequest(broker_order_id=broker_order_id, lot_size=lot_size)
        return self._broker.close_order(req)
