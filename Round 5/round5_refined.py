import json
import math
import numpy as np
from typing import Any, List, Dict, Tuple
from statistics import NormalDist
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: Dict[Symbol, List[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders),
            conversions, "", "",
        ]))
        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))
        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list:
        return [
            state.timestamp,
            trader_data,
            [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
            {s: [od.buy_orders, od.sell_orders] for s, od in state.order_depths.items()},
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp] for trades in state.own_trades.values() for t in trades],
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp] for trades in state.market_trades.values() for t in trades],
            state.position,
            [state.observations.plainValueObservations,
             {p: [o.bidPrice, o.askPrice, o.transportFees, o.exportTariff, o.importTariff, o.sugarPrice, o.sunlightIndex]
              for p, o in state.observations.conversionObservations.items()}]
        ]

    def compress_orders(self, orders: Dict[Symbol, List[Order]]) -> list:
        return [[o.symbol, o.price, o.quantity] for ol in orders.values() for o in ol]

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        return value if len(value) <= max_length else value[:max_length - 3] + "..."

logger = Logger()


RAINFOREST = "RAINFOREST_RESIN"
KELP = "KELP"
VOLCANIC_ROCK = "VOLCANIC_ROCK"
VOLCANIC_ROCK_VOUCHER_9500 = "VOLCANIC_ROCK_VOUCHER_9500"
VOLCANIC_ROCK_VOUCHER_9750 = "VOLCANIC_ROCK_VOUCHER_9750"
VOLCANIC_ROCK_VOUCHER_10000 = "VOLCANIC_ROCK_VOUCHER_10000"
VOLCANIC_ROCK_VOUCHER_10250 = "VOLCANIC_ROCK_VOUCHER_10250"
VOLCANIC_ROCK_VOUCHER_10500 = "VOLCANIC_ROCK_VOUCHER_10500"



class Strategy:
    def __init__(self, symbol: str, limit: int):
        self.symbol = symbol
        self.limit = limit
        self.orders: List[Order] = []

    def buy(self, price: int, quantity: int):
        self.orders.append(Order(self.symbol, price, quantity))

    def sell(self, price: int, quantity: int):
        self.orders.append(Order(self.symbol, price, -quantity))

    def get_mid_price(self, state: TradingState) -> float:
        od = state.order_depths.get(self.symbol)
        if not od or not od.buy_orders or not od.sell_orders:
            return 0
        return (max(od.buy_orders) + min(od.sell_orders)) / 2

class MarketMakingStrategy(Strategy):
    def __init__(self, symbol: str, limit: int, default_price: int):
        super().__init__(symbol, limit)
        self.default_price = default_price

    def run(self, state: TradingState) -> Tuple[List[Order], int]:
        self.orders.clear()
        position = state.position.get(self.symbol, 0)
        spread = 4
        bid = self.default_price - spread
        ask = self.default_price + spread
        self.buy(bid, max(0, self.limit - position))
        self.sell(ask, max(0, self.limit + position))
        return self.orders, 0

class EMAStrategy(Strategy):
    def __init__(self, symbol: str, limit: int, alpha=0.5):
        super().__init__(symbol, limit)
        self.alpha = alpha
        self.ema_price = None

    def run(self, state: TradingState) -> Tuple[List[Order], int]:
        self.orders.clear()
        mid = self.get_mid_price(state)
        if self.ema_price is None:
            self.ema_price = mid
        else:
            self.ema_price = self.alpha * mid + (1 - self.alpha) * self.ema_price
        position = state.position.get(self.symbol, 0)
        self.buy(int(self.ema_price - 1), self.limit - position)
        self.sell(int(self.ema_price + 1), self.limit + position)
        return self.orders, 0

class BlackScholesStrategy(Strategy):
    def __init__(self, symbol: str, limit: int, strike_price: int, rock_symbol: str):
        super().__init__(symbol, limit)
        self.strike = strike_price
        self.rock_symbol = rock_symbol
        self.price_history: List[float] = []
        self.cdf = NormalDist().cdf

    def black_scholes(self, St, K, T, r, sigma):
        d1 = (math.log(St / K) + (r + sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return St * self.cdf(d1) - K * math.exp(-r * T) * self.cdf(d2)

    def get_dynamic_sigma(self) -> float:
        if len(self.price_history) < 2:
            return 0.13
        log_returns = [math.log(self.price_history[i] / self.price_history[i-1]) for i in range(1, len(self.price_history))]
        return np.std(log_returns[-20:]) * math.sqrt(365)

    def run(self, state: TradingState) -> Tuple[List[Order], int]:
        self.orders.clear()
        rock_mid = Strategy(self.rock_symbol, 0).get_mid_price(state)
        voucher_mid = self.get_mid_price(state)
        if rock_mid == 0 or voucher_mid == 0:
            return [], 0

        self.price_history.append(voucher_mid)
        if len(self.price_history) > 100:
            self.price_history.pop(0)

        T = max(0, 8_000_000 - state.timestamp) / 8_000_000 * (5 / 365)
        sigma = self.get_dynamic_sigma()
        expected = self.black_scholes(rock_mid, self.strike, T, 0, sigma)

        pos = state.position.get(self.symbol, 0)
        volume = min(10, self.limit - abs(pos))
        spread = 0.5

        logger.print(f"[{self.symbol}] Expected: {expected:.2f}, Market: {voucher_mid:.2f}, Sigma: {sigma:.4f}")

        if voucher_mid > expected + spread:
            self.sell(int(voucher_mid - spread), volume)
        elif voucher_mid < expected - spread:
            self.buy(int(voucher_mid + spread), volume)
        return self.orders, 0



class Trader:
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {
            RAINFOREST: MarketMakingStrategy(RAINFOREST, 50, 10000),
            KELP: EMAStrategy(KELP, 50),
            VOLCANIC_ROCK_VOUCHER_9500: BlackScholesStrategy(VOLCANIC_ROCK_VOUCHER_9500, 200, 9500, VOLCANIC_ROCK),
            VOLCANIC_ROCK_VOUCHER_9750: BlackScholesStrategy(VOLCANIC_ROCK_VOUCHER_9750, 200, 9750, VOLCANIC_ROCK),
            VOLCANIC_ROCK_VOUCHER_10000: BlackScholesStrategy(VOLCANIC_ROCK_VOUCHER_10000, 200, 10000, VOLCANIC_ROCK),
            VOLCANIC_ROCK_VOUCHER_10250: BlackScholesStrategy(VOLCANIC_ROCK_VOUCHER_10250, 200, 10250, VOLCANIC_ROCK),
            VOLCANIC_ROCK_VOUCHER_10500: BlackScholesStrategy(VOLCANIC_ROCK_VOUCHER_10500, 200, 10500, VOLCANIC_ROCK),
        }

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        orders = {}
        conversions = 0
        for symbol, strategy in self.strategies.items():
            if symbol in state.order_depths:
                strat_orders, strat_conversions = strategy.run(state)
                orders[symbol] = strat_orders
                conversions += strat_conversions
        logger.flush(state, orders, conversions, "")
        return orders, conversions, ""
