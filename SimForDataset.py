import json

from Core import User, Request, Stock, Core, Event 
import matplotlib.pyplot as plt
import random
from faker import Faker


file_path = "simulation_data.json"



users_count = 16
stocks_count = 8
epochs = 10000
fake = Faker('ru_RU')

users = []
stocks = []
core = Core()

event_chance = 0.001
active_events_log = []


for i in range(users_count):
    u = User(fake.first_name(), random.randint(1000, 5000), core)
    users.append(u)
    
for i in range(stocks_count):
    s = Stock(fake.word() + str(random.randint(1, 100)), random.randint(1000, 2000), random.randint(1000, 10000))
    stocks.append(s)

price_histories = {stock.name: [] for stock in stocks}
wealth_histories = {user.name: [] for user in users}


events_classes = ['Кризис на рынке','Появление нового конкурента','Успешный квартал','Провальный квартал','Уход топ-менеджера','Выход нового продукта','Положительные отзывы о продукте','Негативные отзывы о продукте','Рост популярности отрасли']
events = [Event(description=events_classes[i], impact=random.uniform(0.8, 1.2), stocks_affected=random.sample(stocks, k=random.randint(1, len(stocks)))) for i in range(len(events_classes))]

data = []
for epoch in range(epochs):
    
    if random.random() < event_chance:
        event = random.choice(events)
        event.apply()
        active_events_log.append((epoch, event.description))
    
    recent_news = [desc for e, desc in active_events_log[-3:]]

    for user in users:
        stock = random.choice(stocks)
        action = random.choice(["buy", "sell"])
        count = random.randint(1, 10)
        
        if action == "buy":
            user.buy_stock(stock, count)
        elif action == "sell":
            user.sell_stock(stock, count)
    
    core.process_requests()
    
    for stock in stocks:
        price_histories[stock.name].append(stock.get_price())
        data.append(stock.get_step_info(price_histories[stock.name]))

    

    for user in users:
        stock_value = sum(
            next((s.get_price() for s in stocks if s.name == name), 0) * count 
            for name, count in user.holdings.items()
        )
        total_wealth = user.balance + stock_value
        wealth_histories[user.name].append(total_wealth)

with open(file_path, "w") as f: 
    json.dump(data, f, indent=4, ensure_ascii=False)

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