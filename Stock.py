import random
import asyncio



class Coin:
    def __init__(self, name, invested_wc, coins_count):
        # сид параметры монеты
        self.name = name
        self.invested = invested_wc
        self.coins_count = coins_count

        # основные параметры монеты
        self.holders = {}
        self.on_market = 0
        self.currency = invested_wc / coins_count
        self.capitalization = self.currency * self.on_market

    @property
    def draw_statistics(self):
        return f'Current currency: {self.currency}, current holders count: {len(self.holders)}, capitalization: {self.capitalization}'



# world_coin = Coin('world_coin', 10 ** 9, 10 ** 9)
# print(world_coin.draw_statistics)

class User:
    def __init__(self, nickname='', wc_count=1000, wc_coin=None, coin_list = [],model = '',debug = False):
        self.nickname = nickname
        self.wc_count = wc_count
        self.wc = wc_coin
        self.coin_list = coin_list
        self.debug = debug
        self.model = model

        self.wallet = {}
        self.requests = []


    def initialize_nick(self):
        if self.nickname == '':
            self.nickname = f'@{random.randint(0, 10000)}'
        else:
            self.nickname = f'@{self.nickname}'

        print(f'Nickname has been initialized as {self.nickname}')

    def register_in_wc(self):
        self.wc.holders[self.nickname] = self.wc_count
        self.wallet[self.wc.name] = self.wc_count

        print(f'User: {self.nickname} registered in system')

    @property
    def draw_statistics(self):
        return f'Nick: {self.nickname}, model: {type(self.model)}, wallet: {self.wallet}, requests: {self.requests}'

    # запрос покупки монеты
    def buy(self, buy_count, coin: Coin):
        # проверяем условия покупки
        if self.wc_count < coin.currency * buy_count:
            return f'{self.nickname} has not enough money to buy'
        elif buy_count > coin.coins_count:
            return f'{coin.name} below buy request'
        else:
            # создаем запрос покупки
            self.wc_count -= coin.currency * buy_count
            self.wallet[self.wc.name] = self.wc_count
            self.requests.append(('buy', {coin.name: buy_count}))

    # запрос продажи монеты
    def sell(self, sell_count, coin: Coin):
        self.requests.append(('sell', {coin.name: sell_count}))

    # обработка запросов
    def apply_request(self, precent_to_bank):
        sum_to_bank = 0
        for req_type, data in self.requests:
            key = list(data.keys())[0]
            amount = data[key]
            coin = next(c for c in self.coin_list if c.name == key)

            if req_type == 'buy':
                fee_coins = (precent_to_bank / 100) * amount
                sum_to_bank += fee_coins * coin.currency
                coin.on_market += amount
                coin.currency *= (1 + amount / coin.coins_count)
                self.wallet[key] = self.wallet.get(key, 0) + (amount - fee_coins)

            elif req_type == 'sell':
                user_has = self.wallet.get(key, 0)
                actual_sell = min(amount, user_has)
                if actual_sell <= 0: continue

                fee_wc = ((precent_to_bank - 0.5) / 100) * actual_sell * coin.currency
                sum_to_bank += fee_wc
                coin.on_market -= actual_sell

                payout = (actual_sell * coin.currency) - fee_wc
                self.wc_count += payout
                self.wallet[self.wc.name] = self.wc_count
                coin.currency *= (1 - actual_sell / coin.coins_count)
                self.wallet[key] -= actual_sell

            coin.capitalization = coin.currency * coin.on_market
        self.requests.clear()
        if self.debug == True:
            print(self.draw_statistics)
        return sum_to_bank

    def receive_yield(self, amount):
        """Начисление базового дохода или процента на остаток (стейкинг)"""
        self.wc_count += amount
        self.wallet[self.wc.name] = self.wc_count
        # увеличивает денежную массу, предотвращая дефляцию

# demo_coin = Coin('demo', 14, 100)

# world_bank = [0,[world_coin, demo_coin]]
# precent_to_bank = 15.0
# commission = 2.0

# demo_user = User('', 1000, world_coin,world_bank[1])
# demo_user.initialize_nick()
# demo_user.register_in_wc()

# print(demo_user.draw_statistics)
# demo_user.buy(10, demo_coin)

# demo_user.sell(8, demo_coin)
# print(demo_user.draw_statistics)

# world_bank[0] += demo_user.apply_request(commission)
# print(world_bank[0])