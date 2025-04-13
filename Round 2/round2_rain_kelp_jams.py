import json
from typing import Any, List, Dict

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

PRODUCTS = [
    RAINFOREST,
    KELP,
    JAMS
]

class Trader:
    def __init__(self):
        self.limits = {
            RAINFOREST: 50,
            KELP: 50,
            JAMS: 350,
            # Możesz dodać kolejne produkty tutaj
        }
        self.default_prices = {
            RAINFOREST: 10000,
            KELP: 2030,
            JAMS: 6600,

        }
        self.past_prices = dict()
        for product in PRODUCTS:
            self.past_prices[product] = []
        
        self.ema_prices = dict()
        for product in PRODUCTS:
            self.ema_prices[product] = None

        self.ema_param = 0.5

    
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

        # Możesz tu dostosować poziom spreadu i agresję
        

        logger.print(f"KELP | EMA: {fair_price:.2f} | Pos: {position} | BID: {fair_price - spread} x {bid_volume}, ASK: {fair_price + spread} x {ask_volume}")

        return [
            Order(product, int(fair_price - spread), bid_volume),
            Order(product, int(fair_price + spread), ask_volume)
        ]
    #Market making strategia
    def market_make(self, product: str, fair_price: int, spread: int, state: TradingState) -> List[Order]:
        position = self.get_position(product, state)
          # Spread 5 punktów
        buy_volume = max(0, self.limits[product] - position)
        sell_volume = max(0, self.limits[product] + position)

        bid = self.default_prices[product] - spread
        ask = self.default_prices[product] + spread

        logger.print(f"{product} | Pos: {position} | BID: {bid} x {buy_volume}, ASK: {ask} x {sell_volume}")

        return [
            Order(product, bid, buy_volume),
            Order(product, ask, -sell_volume)
        ]
    

    def run(self, state: TradingState) -> tuple[Dict[Symbol, List[Order]], int, str]:
        result = {}
        conversions = 0
        trader_data = ""

        # Market making dla RAINFOREST_RESIN z fair price = 10000 i spreadem 5
        result[RAINFOREST] = self.market_make(RAINFOREST, fair_price=self.default_prices[RAINFOREST], spread=1, state=state)
        result[KELP] = self.ema_strategy(KELP, spread=1, state=state)
        result[JAMS] = self.ema_strategy(JAMS, spread=1, state=state)

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
