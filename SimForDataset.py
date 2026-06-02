from Core import User, Request, Stock, Core, Event 
import matplotlib.pyplot as plt
import random
from faker import Faker
from Affectors import AffectorSeller

users_count = 8
stocks_count = 8
epochs = 5000
fake = Faker('ru_RU')

users = []
stocks = []
core = Core()

event_chance = 0.001
active_events_log = []

SELLER_DATASET_PATH = "AffectorSellerDataset.json"
SENTIMENTS = ["рискованный", "оптимист", "консерватист", "систематичный", "интроверт", "убежденный", "интуитивный"]

GLOBAL_MODEL_PATH = "affector_seller_global.pkl"
global_seller = AffectorSeller()
if not global_seller.load(GLOBAL_MODEL_PATH):
    global_seller.train(SELLER_DATASET_PATH)
    global_seller.save(GLOBAL_MODEL_PATH)

sellers = {}
for s in SENTIMENTS:
    model_path = f"affector_seller_{s}.pkl"
    m = AffectorSeller()
    if not m.load(model_path):
        m.train(SELLER_DATASET_PATH, sentiment=s)
        m.save(model_path)
    sellers[s] = m

for i in range(users_count):
    u = User(fake.first_name(), random.randint(1000, 5000), core)
    u.sentiment = random.choice(SENTIMENTS)
    users.append(u)
    
for i in range(stocks_count):
    s = Stock(fake.word() + str(random.randint(1, 100)), random.randint(1000, 2000), random.randint(1000, 10000))
    stocks.append(s)

price_histories = {stock.name: [] for stock in stocks}
wealth_histories = {user.name: [] for user in users}


events_classes = ['Кризис на рынке','Появление нового конкурента','Успешный квартал','Провальный квартал','Уход топ-менеджера','Выход нового продукта','Положительные отзывы о продукте','Негативные отзывы о продукте','Рост популярности отрасли']
events = [Event(description=events_classes[i], impact=random.uniform(0.8, 1.2), stocks_affected=random.sample(stocks, k=random.randint(1, len(stocks)))) for i in range(len(events_classes))]


for epoch in range(epochs):
    
    if random.random() < event_chance:
        event = random.choice(events)
        event.apply()
        active_events_log.append((epoch, event.description))
    
    recent_news = [desc for e, desc in active_events_log[-3:]]

    for user in users:
        stock = random.choice(stocks)
        prompt = f"Пользователь {user.name} рассматривает акцию {stock.name} по цене {stock.get_price()}"
        seller = sellers[user.sentiment]
        gs = global_seller.scores(prompt=prompt, news=recent_news, sentiment=user.sentiment)
        ss = seller.scores(prompt=prompt, news=recent_news, sentiment=user.sentiment)
        alpha = 0.35
        combo = {k: (1 - alpha) * gs[k] + alpha * ss[k] for k in gs}

        if user.sentiment in ("рискованный", "оптимист"):
            combo["buy"] += 0.25
        elif user.sentiment == "консерватист":
            combo["sell"] += 0.25
        elif user.sentiment == "систематичный":
            combo["hold"] += 0.15
        elif user.sentiment == "интроверт":
            combo["hold"] += 0.25
        elif user.sentiment == "убежденный":
            combo["hold"] += 0.2
        elif user.sentiment == "интуитивный":
            combo["hold"] += 0.1

        action = max(combo, key=combo.get)
        count = random.randint(1, 10)
        
        if action == "buy":
            user.buy_stock(stock, count)
        elif action == "sell":
            user.sell_stock(stock, count)
    
    core.process_requests()
    
    for stock in stocks:
        price_histories[stock.name].append(stock.get_price())
    

    for user in users:
        stock_value = sum(
            next((s.get_price() for s in stocks if s.name == name), 0) * count 
            for name, count in user.holdings.items()
        )
        total_wealth = user.balance + stock_value
        wealth_histories[user.name].append(total_wealth)

# графики
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))


for stock in stocks:
    history = price_histories[stock.name]
    if len(history) < epochs:
        history += [history[-1]] * (epochs - len(history))
    ax1.plot(history[:epochs], label=stock.name)

ax1.set_title("Динамика цен акций")
ax1.set_xlabel("Эпоха")
ax1.set_ylabel("Цена")
ax1.legend()
ax1.grid(True)

for user in users:
    ax2.plot(wealth_histories[user.name][:epochs], label=user.name)

ax2.set_title("Динамика богатства пользователей")
ax2.set_xlabel("Эпоха")
ax2.set_ylabel("Общее богатство")
ax2.legend()
ax2.grid(True)

plt.tight_layout()
plt.show()