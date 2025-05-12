# 🏆 IMC Prosperity 3

This repository contains my thought process and algorithms for IMC Prosperity 3 competition. I placed 605th globally and 3rd in Poland with a score of 342 123 seashells, submitting algorithms only in Round 2,3,4 due to lack of time and Easter holidays. 

It was my first encounter with a competition like that and algorithmic trading overall. I've learned many valuable things along the way about trading, programming and financial instruments as a whole. After competition , I am equipped with a completely new experience and ready to further my knowledge in this topic.



# 📜 What is IMC Prosperity?

IMC Prosperity 3 (2025) was an algorithmic trading competition that lasted over 15 days, with over 12000 + teams participating globally. The challenge tasked teams with designing trading algorithms to maximize profits across a variety of simulated produts - replicating real-world scenarios and strategies.

The competition was presented as a game where each team represented an "island" in fictional archipelago and introduced products like Rainforest Resin, Kelp, Squid Ink, Picnic Baskets(ETF analog), Volcanic Rock and Volcanic Rock Vouchers(options) that could be traded using SeaShells, an in-game currency. It started with three products in Round 1 and ended with 15 products by the final round.

In each round, teams submitted a trading algorithm in Python, which was then evaluated against a synthethic marketplace of bot participants. Teams could optimize their algorithm basing on previous round results and data provided by competition organizers.


[Prosperity 3 Wiki](https://imc-prosperity.notion.site/Prosperity-3-Wiki-19ee8453a09380529731c4e6fb697ea4)


# 🧠 Algorithmic Challenge

Only Rounds in which I implemented strategies will be explained below.

## Round 1️⃣

"The first three tradable products are introduced: : Rainforest Resin , Kelp, and Squid Ink. The value of the Rainforest Resin has been stable throughout the history of the archipelago, the value of Kelp has been going up and down over time, and the value of Squid Ink can also swing a bit, but some say there is a pattern to be discovered in its prize progression"

### Rainforest Resin 

Rainforest Resin was the most beginner-friendly product in whole competition, prepared solely for market-making purposes. True price of a product was fixed at 10.000. My strategy for this product was the most basic version of [market making](https://medium.com/blockapex/market-making-mechanics-and-strategies-4daf2122121c) that was just making orders around true price(10.000) with a spread of 2-5.

```python
def market_make(self, product: str, fair_price: int, spread: int, state: TradingState) -> List[Order]:
        position = self.get_position(product, state)

        buy_volume = max(0, self.limits[product] - position)
        sell_volume = max(0, self.limits[product] + position)

        bid = self.default_prices[product] - spread
        ask = self.default_prices[product] + spread

        logger.print(f"{product} | Pos: {position} | BID: {bid} x {buy_volume}, ASK: {ask} x {sell_volume}")

        return [
            Order(product, bid, buy_volume),
            Order(product, ask, -sell_volume)
        ]
```
### Kelp 

Kelp was similar to Rainforest Resin, but major difference was that its price moved sligthly from one timestamp to another. Kelp didn't have fixed true price, like Rainforest Resin did but instead followed a slow version of a [random walk](https://www.investopedia.com/terms/r/randomwalktheory.asp). My strategy for this product was [Exponential Moving Average](https://www.investopedia.com/terms/e/ema.asp) with fixed alpha of 0,5. 
```python
 def update_ema(self, product: str, state: TradingState):
        mid_price = self.get_mid_price(product, state)
        self.past_prices[product].append(mid_price)

        if self.ema_prices[product] is None:
            self.ema_prices[product] = mid_price
        else:
            self.ema_prices[product] = (
                self.ema_param * mid_price + (1 - self.ema_param) * self.ema_prices[product]
            )

def ema_strategy(self, product: str, spread: int, state: TradingState) -> List[Order]:
        self.update_ema(product, state)
        fair_price = self.ema_prices[product]

        position = self.get_position(product, state)
        bid_volume = self.limits[product] - position
        ask_volume = -self.limits[product] - position
        

        logger.print(f"KELP | EMA: {fair_price:.2f} | Pos: {position} | BID: {fair_price - spread} x {bid_volume}, ASK: {fair_price + spread} x {ask_volume}")

        return [
            Order(product, int(fair_price - spread), bid_volume),
            Order(product, int(fair_price + spread), ask_volume)
```
## Round 2️⃣ 

Three new invidiual prducts are introduced: Croissants, Jams and Djembes alongisde with two new baskets(ETF analog): PICNIC_BASKET1 (6x Croissants, 3x Jams, 1x Djembes) and PICNIC_BASKET2 (4x Croissants, 2x Jams). I didn't implement any strategy worth mentioning for these products. For anyone interested, I am suggesting to check great writing of [Frankfurt Hedgehog's](https://github.com/TimoDiehm/imc-prosperity-3) team that described their strategy for this round



## Round 3️⃣ 

"Our inhabitants really like volcanic rock. So much even, that they invented a new tradable good, `VOLCANIC ROCK VOUCHERS`. The vouchers will give you the right but not obligation to buy `VOLCANIC ROCK` at a certain price (strike price) at voucher expiry timestamp. These vouchers can be traded as a separate item on the island’s exchange. Of course you will have to pay a premium for these vouchers, but if your strategy is solid as a rock, SeaShells spoils will be waiting for you on the horizon. 
There are five Volcanic Rock Vouchers, each with their own **strike price** and **premium.** 
At beginning of Round 1, all the Vouchers have 7 trading days to expire. By end of Round 5, vouchers will have 2 trading days left to expire."

Round 3 introduced new products: Volcanic Rock and Volcanic Rock Voucher - call options on underlying Volcanic Rock. Voucher were available with various strike prices - 9500, 9750, 10000, 10250, 10500. Options had seven days until expiry in the first round and was decreasing to two days by Round 5. 

During the competition, organizers shared a theoretical hint encouraging participants to use a more sophisticated approach for pricing `VOLCANIC_ROCK_VOUCHER` options based on volatility smiles.

Although this approach likely allowed for better relative value trading across strikes, I chose a more straightforward solution due to time constraints.
Instead of building a full IV smile model, I implemented a **simple Black-Scholes model  strategy**, which:
- Estimated theoretical option prices using the Black-Scholes formula
- Used dynamic volatility (based on recent log returns) and time to expiry
- Compared the theoretical value to the current market mid-price
- Placed buy/sell orders when the price difference exceeded a predefined spread

```python
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
```
Results of Round 3
![image](https://github.com/user-attachments/assets/e2d8d318-9b7f-49b7-9caf-e8f33a13ce0e)


## Round 4️⃣

"In this fourth round of Prosperity a new luxury product is introduced: MAGNIFICENT MACARONS. MAGNIFICENT MACARONS are a delicacy and their value is dependent on all sorts of observable factors like hours of sun light, sugar prices, shipping costs, in- & export tariffs and suitable storage space. Can you find the right connections to optimize your program? "

I've tried to do some research on Magnificent Macarons and variables that are influencing it's price but couldn't wrap up any strategy worth using and just kept my previous round strategies.

## Round 5️⃣

"The final round of the challenge is already here! And surprise, no new products are introduced for a change. Dull? Probably not, as you do get another treat. The island exchange now discloses to you who the counterparty is you have traded against. This means that the counter_party property of the OwnTrade object is now populated. Perhaps interesting to see if you can leverage this information to make your algorithm even more profitable?" 

Round 5 didn't introduce any new products but instead it disclosed counterparty names you trade against. This Round  happened to be in an Easter Holidays time and it was pretty much the end for me in this competition. I wasn't able to work more on my algorithms and didn't even submit code this round due to workload and family obligations :) 


# Summary 🏁

This was my first encounter with algorithmic trading, and participating in IMC Prosperity 3 turned out to be a great learning experience. While I initially approached it from a programming perspective, I quickly found myself diving deep into the mechanics of trading — from pricing models and volatility to position management and market dynamics.


Despite not having time to explore every edge, this project gave me:
- Stronger skills in structuring trading logic in Python
- A much better understanding of financial derivatives like options
- Insights into how to test and evolve strategies round after round

I walked away from the challenge with a deeper appreciation for algorithmic trading — and with the motivation to explore it even further in the future.






