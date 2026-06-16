import math
import random
from dataclasses import dataclass


class Market:
    def __init__(self):
        self.users = []


@dataclass
class Order:
    type: str
    stock: 'Stock'
    volume: int
    holder: 'Holder'
    order_price: float


class OrderBook:
    def __init__(self, stock: 'Stock'):
        self.stock = stock
        self.want_to_buy = []
        self.want_to_sell = []
        self.last_price = stock.get_price()

    def add_order(self, order: Order):
        if order.type == 'buy':
            self.want_to_buy.append(order)
            self.want_to_buy.sort(key=lambda x: x.order_price, reverse=True)
        elif order.type == 'sell':
            self.want_to_sell.append(order)
            self.want_to_sell.sort(key=lambda x: x.order_price)
        self.apply()

    def apply(self):
        while self.want_to_buy and self.want_to_sell and self.want_to_buy[0].order_price >= self.want_to_sell[0].order_price:
            buyer = self.want_to_buy[0]
            seller = self.want_to_sell[0]
            match_price = seller.order_price
            self.last_price = match_price
            self.stock._sync_price(match_price)
            match_volume = min(buyer.volume, seller.volume)
            seller.holder.wc += match_volume * match_price
            buyer.holder.wallet[buyer.stock.name] = buyer.holder.wallet.get(buyer.stock.name, 0) + match_volume
            self.stock.holders[buyer.holder.name] = self.stock.holders.get(buyer.holder.name, 0) + match_volume
            self.stock.holders[seller.holder.name] = self.stock.holders.get(seller.holder.name, 0) - match_volume
            if self.stock.holders.get(seller.holder.name, 0) <= 0:
                self.stock.holders.pop(seller.holder.name, None)
            buyer.volume -= match_volume
            seller.volume -= match_volume
            if buyer.volume == 0:
                self.want_to_buy.pop(0)
            if seller.volume == 0:
                self.want_to_sell.pop(0)

    def flush(self):
        while self.want_to_buy:
            o = self.want_to_buy.pop(0)
            h = o.holder
            n = o.stock.name
            h.wallet[n] = h.wallet.get(n, 0) + o.volume
            o.stock.holders[h.name] = o.stock.holders.get(h.name, 0) + o.volume
            delta = o.volume / o.stock.get_total_count()
            o.stock.apply_impact(1 + delta)
        while self.want_to_sell:
            o = self.want_to_sell.pop(0)
            h = o.holder
            payout = o.stock.get_price() * o.volume
            h.wc += payout
            delta = o.volume / o.stock.get_total_count()
            o.stock.apply_impact(1 / (1 + delta))


class Core:
    def __init__(self):
        self.requests_queue = []
        self.days = 0
        self.market = Market()

    def add_request(self, request):
        self.requests_queue.append(request)

    def process_requests(self):
        while self.requests_queue:
            request = self.requests_queue.pop(0)
            request.complete()

    def select_emotion(emotions, miple):
        pass


class Stock:
    def __init__(self, name, count, invested, description="", company=""):
        self.name = name
        self.description = description
        self.company = company
        self.count = count
        self.invested = invested
        self.total_shares = count
        self.__price = invested / count if count else 0.01
        self.holders = {}
        self.price_history = [self.__price]
        self.order_book = OrderBook(self)

    def set_name(self, new_name):
        self.name = new_name

    def set_desc(self, new_desc):
        self.description = new_desc

    def _sync_price(self, price):
        if price <= 0:
            return
        self.__price = price
        self.price_history.append(self.__price)
        self.order_book.last_price = price

    def current_volatility(self):
        if len(self.price_history) < 2:
            return 0
        mean_price = sum(self.price_history) / len(self.price_history)
        variance = sum((price - mean_price) ** 2 for price in self.price_history) / len(self.price_history)
        return math.sqrt(variance)

    def get_total_price(self):
        return self.__price * self.get_total_count()

    def get_total_users(self):
        return len(self.holders)

    def get_price(self):
        return self.__price

    def get_step_info(self, step_data):
        info = {
            "name": self.name,
            "price": self.__price,
            "total_count": self.get_total_count(),
            "total_price": self.get_total_price(),
            "total_users": self.get_total_users(),
            "volatility": self.current_volatility(),
            "high": max(step_data),
            "low": min(step_data),
            "open": step_data[0],
            "close": step_data[-1]
        }
        return info

    def apply_impact(self, impact_coefficient):
        self.__price = max(0.01, self.__price * impact_coefficient)
        self.price_history.append(self.__price)
        self.order_book.last_price = self.__price

    def get_total_count(self):
        return self.total_shares


class Holder:
    def __init__(self, name, start_capital):
        self.name = name
        self.wc = start_capital
        self.wallet = {}

    def order(self, type, stock: Stock, volume: int, own_buy_price):
        if type == 'buy':
            cost = stock.get_price() * volume
            if volume <= 0 or self.wc < cost:
                return None
            self.wc -= cost
            o = Order(type, stock, volume, self, own_buy_price)
            stock.order_book.add_order(o)
            return o
        elif type == 'sell':
            if volume <= 0 or self.wallet.get(stock.name, 0) < volume:
                return None
            self.wallet[stock.name] -= volume
            if self.wallet[stock.name] == 0:
                del self.wallet[stock.name]
            o = Order(type, stock, volume, self, own_buy_price)
            stock.order_book.add_order(o)
            return o
        return None


class User(Holder):
    def __init__(self, name, balance, core):
        super().__init__(name, balance)
        self.core = core

    @property
    def balance(self):
        return self.wc

    @balance.setter
    def balance(self, v):
        self.wc = v

    @property
    def holdings(self):
        return self.wallet

    def get_portfolio_info(self):
        return {
            "name": self.name,
            "balance": self.balance,
            "holdings": self.holdings
        }

    def buy_stock(self, stock, count):
        return self.order('buy', stock, int(count), stock.get_price()) is not None

    def sell_stock(self, stock, count):
        return self.order('sell', stock, int(count), stock.get_price()) is not None


class Request:
    def __init__(self, type, stock, count, user):
        self.type = type
        self.stock = stock
        self.count = count
        self.user = user

    def complete(self):
        delta = self.count / self.stock.get_total_count()

        if self.type == "buy":
            self.user.holdings[self.stock.name] = self.user.holdings.get(self.stock.name, 0) + self.count
            self.stock.holders[self.user.name] = self.stock.holders.get(self.user.name, 0) + self.count
            coefficient = 1 + delta
            self.stock.apply_impact(coefficient)

        elif self.type == "sell":
            current_price = self.stock.get_price()
            payout = current_price * self.count
            self.user.balance += payout
            self.stock.holders[self.user.name] = self.stock.holders.get(self.user.name, 0) - self.count
            if self.stock.holders[self.user.name] <= 0:
                if self.user.name in self.stock.holders:
                    del self.stock.holders[self.user.name]
            coefficient = 1 / (1 + delta)
            self.stock.apply_impact(coefficient)

# класс бота (скорее всего будет удален)
class Bot(User):
    def __init__(self, name, balance, core, strategy):
        super().__init__(name, balance, core)
        self.strategy = strategy

# класс события
class Event:
    def __init__(self, description, impact, stocks_affected):
        self.description = description
        self.impact = impact # коэф влияния
        self.stocks_affected = stocks_affected

    def apply(self):
        for stock in self.stocks_affected:
            stock.apply_impact(self.impact)

# класс фокуса    
class Focus:
    def __init__(self, description, action, days):
        self.description = description
        self.action = action
        self.days = days
        
    def set_parameters(self, desc, ac):
        self.description = desc
        self.action = ac
        print(f'desc has changed to {desc}\naction has changed to {ac}')
        
# класс оружия    
class Weapon:
    def __init__(self, type, attack_power, ico):
        self.type = type
        self.attack_power = attack_power
        self.ico = ico

# пехотная дивизия
class InfantryDivision:
    def __init__(self,name, weapons_in, man_power):
        self.name = name
        self.weapons_in = weapons_in
        self.man_power = man_power
        
# класс дивизии
class Division:
    def __init__(self, army_types_in):
        self.army_types_in = army_types_in
        self.speed = 0
        self.attack = 0
        self.protection = 0
        self.attack_index = 1
        self.organization = 1
        self.level = 0
        self.basic_train_time = 20
        
        
# класс террейна
class Terrain:
    def __init__(self, move_factor, attack_factor, deffence_factor, desc):
        self.move_factor = move_factor
        self.attack_factor = attack_factor
        self.deffence_factor = deffence_factor
        self.desc = desc
    
# класс ячейки территории
class TerritoryCell:
    def __init__(self, position, terrain: Terrain, divisions_on_cell, fortifications):
        self.pos = position
        self.terrain = terrain
        self.fortifications = fortifications
        self.div_on_cell = divisions_on_cell
        
    def apply_factors(self):
        for division in self.div_on_cell:
            division.attack = division.attack * self.terrain.attack_factor
            division.move = division.move * self.terrain.move_factor
            division.protection = division.protection * self.terrain.deffence_factor + (self.fortifications)
            

# класс страны
class Country:
    def __init__(self, core: Core, territory, residents, leader, focus_branch):
        self.core = core
        self.territory = territory
        self.residents = residents
        self.leader = leader
        self.focus_branch = focus_branch

