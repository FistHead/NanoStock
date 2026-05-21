import random
import matplotlib.pyplot as plt
import json
import pandas as pd
import mplfinance as mpf
import datetime

class Stock:
    def __init__(self, name, price, volume):
        self.name = name
        self.price = price

        self.volume = volume
        self.market_volume = 0

        self.price_history = [price]
        self.candles = []


class Market:
    def __init__(self, all_stocks, user_list):
        self.all_stocks = all_stocks
        self.user_list = user_list

        self.users_wealth = {}
        self.history = []

    def calc_user_wealth(self):
        prices = {s.name: s.price for s in self.all_stocks}
        for user in self.user_list:
            self.users_wealth[user.name] = user.get_total_wealth(prices)

        total = sum(self.users_wealth.values())
        print(f"Состояние игроков: {self.users_wealth}, Всего в системе: {total}")

    def crash(self, percentage):
        for m_o in self.all_stocks:
            # before = m_o.currency
            m_o.price *= (1 - percentage / 100)

    def stock_boom(self, percentage):
        for m_o in self.all_stocks:
            # before = m_o.currency
            m_o.price *= (1 + percentage / 100)


    def create_bot(self, name, start_capital, params):
        return Bot(name, start_capital, params)

    def create_bots(self, count: int, start_cap: int, names: list, params_for_each: list, randomize: bool):
        bot_list = []
        if not randomize:
            for c in range(count):
                # print(params_for_each[c])
                # print(names[c])
                r_num = 1000

                if start_cap == 0:
                    r_num = random.randint(100, 500)

                bot_list.append(self.create_bot(names[c],r_num, params_for_each[c]))
        else:
            for c in range(count):
                name = 'bot' + str(c)
                first_parameter = random.uniform(0, 1)
                params = [first_parameter,1 - first_parameter]
                r_num =  1000

                if start_cap == 0:
                    r_num = random.randint(100, 500)

                bot_list.append(self.create_bot(name,r_num, params))

        return bot_list

    def start_simulation(self, steps):
        for step in range(steps):
            step_data = {}

            for stock in self.all_stocks:
                step_data[stock.name] = {
                    'open': stock.price,
                    'high': stock.price,
                    'low': stock.price,
                    'close': stock.price,
                    'volume': 0
                }

            for user in self.user_list:
                if isinstance(user, Bot):
                    random_stock = random.choice(self.all_stocks)
                    before_price = random_stock.price

                    action, vol = user.choice(random_stock)

                    after_price = random_stock.price

                    step_data[random_stock.name]['high'] = max(step_data[random_stock.name]['high'], after_price)
                    step_data[random_stock.name]['low'] = min(step_data[random_stock.name]['low'], after_price)
                    step_data[random_stock.name]['close'] = after_price

                    if action in ['buy', 'sell']:
                        step_data[random_stock.name]['volume'] += vol

            epoch_data = {
                "step": step,
                "prices": {s.name: round(s.price, 4) for s in self.all_stocks},
                "wealth": {
                    u.name: round(u.get_total_wealth({s.name: s.price for s in self.all_stocks}), 2)
                    for u in self.user_list
                },
                "candles": step_data,
            }

            self.history.append(epoch_data)

            for stock in self.all_stocks:
                stock.candles.append(step_data[stock.name])

    def save_history_to_json(self, filename='market_data.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            # Записываем весь накопленный список истории
            json.dump(self.history, f, indent=4, ensure_ascii=False)
        print(f"Статистика сохранена в {filename}")

    def get_prices(self):
        return [(s.name, s.price) for s in self.all_stocks]
    def get_users_wealth(self):
        prices = {s.name: s.price for s in self.all_stocks}
        return [(u.name,u.get_total_wealth(prices)) for u in self.user_list]

    def plot_candles(self, stock):
        import pandas as pd
        import mplfinance as mpf

        if not stock.candles:
            print(f"Нет свечных данных для {stock.name}")
            return

        df = pd.DataFrame(stock.candles)

        # если timestamps нет, создаём искусственный временной индекс
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        df.index = pd.date_range(start=date, periods=len(df), freq='min')

        mpf.plot(
            df,
            type='candle',
            style='charles',
            title=f'Свечной график {stock.name}',
            volume=True,
            figsize=(14, 8)
        )

    def plot_candles_resampled(self, stock, rule='15min'):
        import pandas as pd
        import mplfinance as mpf

        if not stock.candles:
            print(f"Нет свечных данных для {stock.name}")
            return

        df = pd.DataFrame(stock.candles)

        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            print("Ошибка: отсутствуют нужные колонки в candles")
            return

        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
        else:
            df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='min')

        df = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        mpf.plot(
            df,
            type='candle',
            style='charles',
            title=f'Свечной график {stock.name} ({rule})',
            volume=True,
            figsize=(14, 8)
        )


class Request:
    def __init__(self, user, type, stock, vol):
        if type == 'buy':
            stock.market_volume += vol
            user.wallet['WC'] -= stock.price * vol
            user.wallet[stock.name] = user.wallet.get(stock.name, 0) + vol
            stock.price *= (1 + (vol / stock.volume))

            stock.price_history.append(stock.price)
        elif type == 'sell':
            stock.market_volume -= vol
            user.wallet['WC'] += stock.price * vol
            user.wallet[stock.name] = user.wallet.get(stock.name, 0) - vol
            stock.price *= (1 - (vol / stock.volume))

            stock.price_history.append(stock.price)
        else:
            pass


class User:
    def __init__(self, name, start_capital):
        self.name = name
        self.start_capital = start_capital

        self.wallet = {'WC': start_capital}

    def send_request(self, type, stock, vol):
        cost = stock.price * vol
        if type == 'buy':
            if cost <= self.wallet['WC']:
                if vol > stock.volume:
                    return False, 0
                if vol < 0:
                    return False, 0
                Request(self, type, stock, vol)
                return True, vol
            return False, 0

        elif type == 'sell' and stock.name in self.wallet:
            if vol > stock.volume:
                return False, 0
            if vol < 0:
                return False, 0
            if self.wallet.get(stock.name, 0) < vol:
                return False, 0

            Request(self, type, stock, vol)
            return True, vol

        return False, 0

    def get_total_wealth(self, all_stocks_prices):
        total_stock_value = sum(self.wallet.get(name, 0) * price for name, price in all_stocks_prices.items())
        return self.wallet['WC'] + total_stock_value

class Bot(User):
    def __init__(self, name, start_capital, params):
        super().__init__(name, start_capital)
        self.params = params

    def choice(self, stock):
        choices = ['buy', 'sell', 'hold']
        weights = [self.params[0], self.params[1], 0.4]

        random_vol = random.randint(1, 100)
        action = random.choices(choices, weights=weights, k=1)[0]

        success, real_vol = super().send_request(action, stock, random_vol)
        if success:
            return action, real_vol
        return 'hold', 0

