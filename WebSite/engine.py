import os
import sys
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import Core
import brains

EXPRESSIONS = ["happy", "sad", "neutral", "surprised"]
RANDOM_STOCK_WORDS = ["лиловый", "поезд", "вектор", "орбита", "ягода", "квант", "север",
                      "пламя", "кобальт", "ручей", "гранит", "вихрь", "омега", "тополь"]
RANDOM_MIPLE_NAMES = ["Альфа", "Система", "Интро", "Экстра", "Оптик", "Квант", "Вектор",
                      "Гамма", "Зенит", "Орион", "Феникс", "Дельта"]


def _gen_id():
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(8))


class Simulation:
    def __init__(self, name):
        self.id = _gen_id()
        self.name = name
        self.core = Core.Core()
        self.stocks = {}        # name -> Core.Stock
        self.candles = {}       # name -> [{open,high,low,close,vol}]
        self.prev_close = {}    # name -> цена прошлого шага
        self.miples = []        # [{id,name,model,traits,sentiments,expr}]
        self.users = {}         # miple_id -> Core.User
        self.chat = []          # реплики миплов
        self.events = []        # лог событий
        self.recent_events = [] # последние события для новостей
        self.wealth = {}        # miple_id -> история богатства по шагам
        self.seeded = set()     # миплы со стартовой позицией
        self.step_no = 0

    # ---- создание ----
    def add_stock(self, name, count, invested):
        if name in self.stocks:
            return False
        stock = Core.Stock(name, int(count), float(invested))
        self.stocks[name] = stock
        self.candles[name] = []
        self.prev_close[name] = stock.get_price()
        return True

    def add_random_stock(self):
        name = random.choice(RANDOM_STOCK_WORDS) + str(random.randint(10, 99))
        while name in self.stocks:
            name = random.choice(RANDOM_STOCK_WORDS) + str(random.randint(10, 99))
        return self.add_stock(name, random.randint(800, 2000), random.randint(2000, 9000))

    def add_miple(self, name, model, traits, expr, balance=10000):
        mid = _gen_id()
        sentiments = brains.traits_to_sentiments(traits or [])
        self.miples.append({"id": mid, "name": name, "model": model,
                            "traits": traits or [], "sentiments": sentiments, "expr": expr})
        self.users[mid] = Core.User(name, float(balance), self.core)
        self.wealth[mid] = [round(float(balance), 2)]
        return mid

    def add_random_miple(self, model=None):
        name = random.choice(RANDOM_MIPLE_NAMES) + "_" + str(random.randint(1, 99))
        traits = random.sample(list(brains.TRAIT2SENT.keys()), random.randint(1, 2))
        model = model or random.choice(["mrplip_17M_3", "AffectorSeller"])
        return self.add_miple(name, model, traits, random.choice(EXPRESSIONS))

    def remove_miple(self, mid):
        self.miples = [m for m in self.miples if m["id"] != mid]
        self.users.pop(mid, None)
        self.wealth.pop(mid, None)

    def autofill(self, n_stocks=4, n_miples=4, model=None):
        for _ in range(n_stocks):
            self.add_random_stock()
        for _ in range(n_miples):
            self.add_random_miple(model)

    # ---- симуляция ----
    def _stocks_states(self):
        states = {}
        for name, stock in self.stocks.items():
            price = stock.get_price()
            states[name] = [brains.assign_sphere(name), round(price, 4),
                            brains.direction(self.prev_close.get(name, price), price),
                            round(stock.current_volatility(), 5)]
        return states

    def _maybe_event(self):
        # иногда происходит рыночное событие
        if not self.stocks or random.random() > 0.22:
            return None
        desc = random.choice(brains.ALL_EVENTS)
        pos = desc in brains.EVENTS_POS
        affected = random.sample(list(self.stocks.values()), random.randint(1, len(self.stocks)))
        impact = random.uniform(1.04, 1.12) if pos else random.uniform(0.88, 0.97)
        Core.Event(desc, impact, affected).apply()
        rec = {"step": self.step_no, "description": desc, "polarity": "pos" if pos else "neg",
               "stocks": [s.name for s in affected]}
        self.events.append(rec)
        self.recent_events = ([desc] + self.recent_events)[:3]
        return rec

    def _cap_count(self, stock, want):
        # ограничиваем сделку долей от всех акций, иначе цена улетает экспоненциально
        cap = max(1, int(stock.get_total_count() * 0.06))
        return max(0, min(int(want), cap))

    def _execute(self, user, stock, decision):
        price = stock.get_price()
        if decision == "buy":
            # размер позиции немного варьируется — импульсы цены разной величины
            want = (user.balance * random.uniform(0.08, 0.22)) / price if price > 0 else 0
            count = self._cap_count(stock, want)
            if count > 0:
                user.buy_stock(stock, count)
        elif decision == "sell":
            held = user.holdings.get(stock.name, 0)
            if held > 0:
                user.sell_stock(stock, self._cap_count(stock, max(1, int(held * random.uniform(0.3, 0.7)))))

    def _organic_drift(self):
        # лёгкое естественное колебание цен — чтобы свечи были живыми, а не одинаковыми
        for stock in self.stocks.values():
            for _ in range(random.randint(1, 3)):
                stock.apply_impact(random.uniform(0.984, 1.017))

    def _seed_portfolios(self):
        # стартовая позиция: миплу нужно чем-то владеть, иначе ему нечего продавать
        for m in self.miples:
            if m["id"] in self.seeded:
                continue
            user = self.users[m["id"]]
            stock = self.stocks[random.choice(list(self.stocks))]
            want = (user.balance * random.uniform(0.2, 0.45)) / stock.get_price() if stock.get_price() > 0 else 0
            count = self._cap_count(stock, want)
            if count > 0:
                user.buy_stock(stock, count)
            self.seeded.add(m["id"])

    def step(self):
        if not self.stocks or not self.miples:
            return self.snapshot()
        self.step_no += 1

        self._seed_portfolios()  # новички получают стартовую позицию

        start_idx = {n: len(s.price_history) - 1 for n, s in self.stocks.items()}
        event = self._maybe_event()
        self._organic_drift()  # фоновый шум рынка до сделок

        order = self.miples[:]
        random.shuffle(order)
        context = [c["text"] for c in self.chat[-4:]]  # миплы видят последние реплики

        for m in order:
            brain = brains.get_brain(m["model"])
            states = self._stocks_states()
            try:
                res = brain.predict(states, self.recent_events, context[-4:], m["sentiments"])
            except Exception as e:
                res = {"answer": "...", "target_stock": next(iter(self.stocks)),
                       "decision": "hold", "tactic": "наблюдение", "error": str(e)}
            target = res["target_stock"] if res["target_stock"] in self.stocks else next(iter(self.stocks))
            self._execute(self.users[m["id"]], self.stocks[target], res["decision"])

            line = f"{m['name']}: {res['answer']}".strip()
            context.append(line)
            self.chat.append({"step": self.step_no, "miple": m["name"], "miple_id": m["id"],
                              "model": m["model"], "expr": m["expr"], "text": res["answer"],
                              "decision": res["decision"], "tactic": res["tactic"], "target": target})

        self.core.process_requests()
        for stock in self.stocks.values():
            stock.order_book.flush()
        self._organic_drift()  # фоновый шум после сделок — формирует тени свечей

        # запись свечей за шаг
        for name, stock in self.stocks.items():
            seg = stock.price_history[start_idx[name]:]
            if not seg:
                seg = [stock.get_price()]
            self.candles[name].append({"open": round(seg[0], 4), "close": round(seg[-1], 4),
                                       "high": round(max(seg), 4), "low": round(min(seg), 4),
                                       "vol": round(stock.current_volatility(), 5)})
            self.prev_close[name] = stock.get_price()

        # история богатства каждого мипла
        for m in self.miples:
            u = self.users[m["id"]]
            worth = u.balance + sum(self.stocks[n].get_price() * c for n, c in u.holdings.items() if n in self.stocks)
            self.wealth.setdefault(m["id"], []).append(round(worth, 2))
        return self.snapshot(event)

    # ---- сериализация ----
    def portfolios(self):
        out = []
        for m in self.miples:
            u = self.users[m["id"]]
            worth = u.balance + sum(self.stocks[n].get_price() * c for n, c in u.holdings.items() if n in self.stocks)
            out.append({"id": m["id"], "name": m["name"], "model": m["model"], "expr": m["expr"],
                        "traits": m["traits"], "sentiments": m["sentiments"],
                        "balance": round(u.balance, 2), "holdings": dict(u.holdings),
                        "worth": round(worth, 2), "wealth": self.wealth.get(m["id"], [])[-150:]})
        return out

    def _stock_change(self, name):
        # изменение цены за последний шаг, %
        c = self.candles.get(name)
        if not c or c[-1]["open"] == 0:
            return 0.0
        last = c[-1]
        return round((last["close"] - last["open"]) / last["open"] * 100, 2)

    def market_analytics(self):
        # сводка по рынку и разбивка по сферам
        spheres = {}
        for name, stock in self.stocks.items():
            sph = brains.assign_sphere(name)
            ch = self._stock_change(name)
            g = spheres.setdefault(sph, {"sphere": sph, "count": 0, "value": 0.0, "change": 0.0, "up": 0, "down": 0})
            g["count"] += 1
            g["value"] += stock.get_price() * stock.get_total_count()
            g["change"] += ch
            g["up"] += 1 if ch > 0 else 0
            g["down"] += 1 if ch < 0 else 0
        out = []
        for g in spheres.values():
            g["change"] = round(g["change"] / g["count"], 2)
            g["value"] = round(g["value"], 0)
            out.append(g)
        out.sort(key=lambda x: x["value"], reverse=True)
        total_value = round(sum(s.get_price() * s.get_total_count() for s in self.stocks.values()), 0)
        avg_change = round(sum(self._stock_change(n) for n in self.stocks) / len(self.stocks), 2) if self.stocks else 0.0
        return {"total_value": total_value, "avg_change": avg_change,
                "stocks": len(self.stocks), "spheres": out}

    def snapshot(self, last_event=None):
        return {
            "id": self.id, "name": self.name, "step": self.step_no,
            "stocks": [{"name": n, "price": round(s.get_price(), 4), "sphere": brains.assign_sphere(n),
                        "change": self._stock_change(n), "candles": self.candles[n]}
                       for n, s in self.stocks.items()],
            "miples": self.miples,
            "portfolios": self.portfolios(),
            "market": self.market_analytics(),
            "chat": self.chat[-60:],
            "events": self.events[-20:],
            "last_event": last_event,
        }

    def meta(self):
        return {"id": self.id, "name": self.name, "step": self.step_no,
                "stocks": len(self.stocks), "miples": len(self.miples)}
