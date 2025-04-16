import json
import numpy as np
from typing import Any, List, Dict
from statistics import NormalDist
import math
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders),
            conversions,
            "",
            "",
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

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
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

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        return [[o.symbol, o.price, o.quantity] for ol in orders.values() for o in ol]

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        return value if len(value) <= max_length else value[:max_length - 3] + "..."

logger = Logger()

RAINFOREST = "RAINFOREST_RESIN"
KELP = "KELP"
JAMS = "JAMS"
VOLCANIC_ROCK = "VOLCANIC_ROCK"
VOLCANIC_ROCK_VOUCHER_9500 = "VOLCANIC_ROCK_VOUCHER_9500"
VOLCANIC_ROCK_VOUCHER_9750 = "VOLCANIC_ROCK_VOUCHER_9750"
VOLCANIC_ROCK_VOUCHER_10000 = "VOLCANIC_ROCK_VOUCHER_10000"
VOLCANIC_ROCK_VOUCHER_10250 = "VOLCANIC_ROCK_VOUCHER_10250"
VOLCANIC_ROCK_VOUCHER_10500= "VOLCANIC_ROCK_VOUCHER_10500"

PRODUCTS = [
    RAINFOREST,
    KELP,
    JAMS,
    VOLCANIC_ROCK,
    VOLCANIC_ROCK_VOUCHER_9500,
    VOLCANIC_ROCK_VOUCHER_9750,
    VOLCANIC_ROCK_VOUCHER_10000,
    VOLCANIC_ROCK_VOUCHER_10250,
    VOLCANIC_ROCK_VOUCHER_10500,
]

import json
from typing import Any, List, Dict
from statistics import NormalDist
import math
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState

# ... [Logger definition and constants skipped for brevity]

class Trader:
    def __init__(self):
        self.limits = {
            RAINFOREST: 50,
            KELP: 50,
            JAMS: 350,
            VOLCANIC_ROCK: 400,
            VOLCANIC_ROCK_VOUCHER_9500: 200,
            VOLCANIC_ROCK_VOUCHER_9750: 200,
            VOLCANIC_ROCK_VOUCHER_10000: 200,
            VOLCANIC_ROCK_VOUCHER_10250: 200,
            VOLCANIC_ROCK_VOUCHER_10500: 200,
        }
        self.default_prices = {
            RAINFOREST: 10000,
            KELP: 2030,
            JAMS: 6600,
            VOLCANIC_ROCK: 10000,
            VOLCANIC_ROCK_VOUCHER_9500: 1003,
            VOLCANIC_ROCK_VOUCHER_9750: 754,
            VOLCANIC_ROCK_VOUCHER_10000: 505,
            VOLCANIC_ROCK_VOUCHER_10250: 273,
            VOLCANIC_ROCK_VOUCHER_10500: 100,
        }
        self.past_prices = {product: [] for product in PRODUCTS}
        self.ema_prices = {product: None for product in PRODUCTS}
        self.ema_param = 0.5
        self.cdf = NormalDist().cdf

    def get_mid_price(self, product: str, state: TradingState):
        order_depth = state.order_depths.get(product)
        if not order_depth:
            return self.default_prices[product]

        bids = order_depth.buy_orders
        asks = order_depth.sell_orders

        if not bids or not asks:
            return self.default_prices[product]

        best_bid = max(bids.keys())
        best_ask = min(asks.keys())
        return (best_bid + best_ask) / 2
    
    def get_dynamic_spread(self, product: str, state: TradingState):
        order_depth = state.order_depths.get(product)
        if not order_depth:
            return 0

        bids = order_depth.buy_orders
        asks = order_depth.sell_orders

        if not bids or not asks:
            return 0

        best_bid = max(bids.keys())
        best_ask = min(asks.keys())
        spread = best_ask - best_bid
        return spread / 2

    def update_ema(self, product: str, state: TradingState):
        mid_price = self.get_mid_price(product, state)
        self.past_prices[product].append(mid_price)
        if self.ema_prices[product] is None:
            self.ema_prices[product] = mid_price
        else:
            self.ema_prices[product] = (
                self.ema_param * mid_price + (1 - self.ema_param) * self.ema_prices[product]
            )

    def get_position(self, product: str, state: TradingState) -> int:
        return state.position.get(product, 0)

    def ema_strategy(self, product: str, spread: int, state: TradingState) -> List[Order]:
        self.update_ema(product, state)
        fair_price = self.ema_prices[product]
        position = self.get_position(product, state)
        bid_volume = self.limits[product] - position
        ask_volume = -self.limits[product] - position

        logger.print(f"EMA strategy for {product}: fair_price={fair_price}, bid_volume={bid_volume}, ask_volume={ask_volume}")
        return [
            Order(product, int(fair_price - spread), bid_volume),
            Order(product, int(fair_price + spread), ask_volume)
        ]

    def market_make(self, product: str, fair_price: int, spread: int, state: TradingState) -> List[Order]:
        spread = self.get_dynamic_spread(product, state)
        position = self.get_position(product, state)
        buy_volume = max(0, self.limits[product] - position)
        sell_volume = max(0, self.limits[product] + position)
        bid = self.default_prices[product] - spread
        ask = self.default_prices[product] + spread

        logger.print(f"Market making for {product}: bid={bid}, ask={ask}, buy_volume={buy_volume}, sell_volume={sell_volume}")
        return [
            Order(product, bid, buy_volume),
            Order(product, ask, -sell_volume)
        ]
    

    def get_dynamic_T(self, state: TradingState) -> float:
     ticks_remaining = max(0, 8_000_000 - state.timestamp)
     T = ticks_remaining / 8_000_000 * (5 / 365)
     return T
    def get_dynamic_sigma(self, product: str) -> float:
        prices = self.past_prices[product]
        if len(prices) < 2:
            return 0.13
        
        log_return = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]


        if len(log_return) > 20:
            log_returns = log_return[-20:]

        std_dev = np.std(log_returns)

        return std_dev * math.sqrt(365)

        


     

    def black_scholes_model(self, St: float, K: float, T: float, r: float, sigma: float) -> float:
        d1 = (math.log(St / K) + (r + sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return St * self.cdf(d1) - K * math.exp(-r * T) * self.cdf(d2)

    def black_scholes_strat(self, product: str, strike_price: int, state: TradingState) -> List[Order]:
        volcanic_r_price = self.get_mid_price(VOLCANIC_ROCK, state)
        voucher_price = self.get_mid_price(product, state)

        St = volcanic_r_price
        K = strike_price  # fixed strike price
        T = self.get_dynamic_T(state,)
        r = 0
        sigma = self.get_dynamic_sigma(product)

        expected_price = self.black_scholes_model(St, K, T, r, sigma)
        spread = 0.5

        position = self.get_position(product, state)
        volume = min(10, self.limits[product] - abs(position))

        orders = []
        if voucher_price > expected_price + spread:
            orders.append(Order(product, int(voucher_price - spread), -volume))
        elif voucher_price < expected_price - spread:
            orders.append(Order(product, int(voucher_price + spread), volume))



        logger.print(
        f"[{product}] Expected: {expected_price:.2f}, Market: {voucher_price:.2f}, "
        f"Orders: {orders}, Sigma: {sigma:.4f}, TTE: {T:.4f}, St: {St:.2f}, K: {K}, "
        f"Position: {position}, MaxVol: {volume}")

        return orders

    def run(self, state: TradingState) -> tuple[Dict[Symbol, List[Order]], int, str]:
        result = {}
        conversions = 0
        trader_data = ""
        result[RAINFOREST] = self.market_make(RAINFOREST, fair_price=self.default_prices[RAINFOREST], spread=1, state=state)
        result[KELP] = self.ema_strategy(KELP, spread=5, state=state)
        result[VOLCANIC_ROCK_VOUCHER_9500] = self.black_scholes_strat(product=VOLCANIC_ROCK_VOUCHER_9500, strike_price=9500,state=state)
        result[VOLCANIC_ROCK_VOUCHER_9750] = self.black_scholes_strat(product=VOLCANIC_ROCK_VOUCHER_9750, strike_price=9750,state=state)
        result[VOLCANIC_ROCK_VOUCHER_10000] = self.black_scholes_strat(product=VOLCANIC_ROCK_VOUCHER_10000, strike_price=10000,state=state)
        result[VOLCANIC_ROCK_VOUCHER_10250] = self.black_scholes_strat(product=VOLCANIC_ROCK_VOUCHER_10250, strike_price=10250,state=state)
        result[VOLCANIC_ROCK_VOUCHER_10500] = self.black_scholes_strat(product=VOLCANIC_ROCK_VOUCHER_10500, strike_price=10500,state=state)
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
