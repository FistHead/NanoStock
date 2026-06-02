import math
import random

class Core:
    def __init__(self):
        self.requests_queue = []
    
    def add_request(self, request):
        self.requests_queue.append(request)
        
    def process_requests(self):
        while self.requests_queue:
            request = self.requests_queue.pop(0)
            request.complete()

class User:
    def __init__(self, name, balance, core):
        self.name = name
        self.balance = balance
        self.holdings = {}
        self.core = core

    def get_portfolio_info(self):
        return {
            "name": self.name,
            "balance": self.balance,
            "holdings": self.holdings
        }

    def buy_stock(self, stock, count):
        if count <= 0:
            return False
        total_price = stock.get_price() * count
        if self.balance >= total_price:
            self.balance -= total_price
            req = Request("buy", stock, count, self)
            self.core.add_request(req)
            return True
        return False

    def sell_stock(self, stock, count):
        if count <= 0:
            return False
        if self.holdings.get(stock.name, 0) >= count:

            self.holdings[stock.name] -= count
            if self.holdings[stock.name] == 0:
                del self.holdings[stock.name]
                
            req = Request("sell", stock, count, self)
            self.core.add_request(req)
            return True
        return False


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
            
            # Рост цены: умножение на (1 + delta)
            coefficient = 1 + delta
            self.stock.apply_impact(coefficient)
            
        elif self.type == "sell":
            # Начисление денег по актуальной цене исполнения ордера
            current_price = self.stock.get_price()
            payout = current_price * self.count
            self.user.balance += payout
            
            self.stock.holders[self.user.name] = self.stock.holders.get(self.user.name, 0) - self.count
            if self.stock.holders[self.user.name] <= 0:
                if self.user.name in self.stock.holders:
                    del self.stock.holders[self.user.name]
            
            coefficient = 1 / (1 + delta)
            self.stock.apply_impact(coefficient)


class Stock:
    def __init__(self, name, count, invested):
        self.name = name
        self.total_shares = count
        self.__price = invested / count
        self.holders = {}
        self.price_history = [self.__price]

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
    
    def get_total_count(self):
        return self.total_shares


class Bot(User):
    def __init__(self, name, balance, core, strategy):
        super().__init__(name, balance, core)
        self.strategy = strategy


class Event:
    def __init__(self, description, impact, stocks_affected):
        self.description = description
        self.impact = impact  # Коэффициент вроде 1.05 или 0.95
        self.stocks_affected = stocks_affected

    def apply(self):
        for stock in self.stocks_affected:
            stock.apply_impact(self.impact)
            
class Bot(User):
    def __init__(self, name, balance, core, mood, affector_model, word_blocks, idx_2w):
        super().__init__(name, balance, core)
        self.mood = mood
        self.affector_model = affector_model
        self.word_blocks = word_blocks
        self.idx_2w = idx_2w

    def evaluate_market(self, news_context, stock):
        """ Бот анализирует новость через AffectorText и принимает торговое решение """
        thought, confidence = self.affector_model.generate_with_confidence(
            prompt=news_context,
            current_mood=self.mood,
            word_blocks=self.word_blocks,
            idx_2w=self.idx_2w,
            max_len=15
        )
        
        volume = max(1, int((confidence / 100) * 5))
        

        negative_markers = ['кризис', 'упал', 'нестабильность', 'опасный', 'минус', 'паники', 'пофиг', 'риски', 'плохо']
        positive_descriptions = ['отлично', 'успех', 'рост', 'шанс', 'готов', 'выиграем', 'вперед', 'купить']
        
        thought_lower = thought.lower()
        

        if self.mood == 'оптимист' or self.mood == 'рискованный':
            action = "buy"
        elif self.mood == 'консерватист' or self.mood == 'интроверт':
            action = "sell"
        else:
            action = random.choice(["buy", "sell"])
            
        if any(marker in thought_lower for marker in negative_markers):
            action = "sell"
        elif any(marker in thought_lower for marker in positive_descriptions):
            action = "buy"
            
        return action, volume, thought