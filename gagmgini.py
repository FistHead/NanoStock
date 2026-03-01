import matplotlib.pyplot as plt
import random

# код коина
class Coin:
    def __init__(self, name, invested_price,coins_count):
        self.name = name
        self.invested_price = invested_price
        self.coins_count = coins_count
        self.users_hold = 0
        self.coins_on_market = 0
        self.current_price = self.invested_price/self.coins_count
        self.capitalization = 0


    def update_capitalization(self):
        self.capitalization = self.current_price * self.coins_on_market

    # вывод статы коина
    @property
    def debug_coin_stats(self):
        return ('current coins holder', self.users_hold), ('current currency', self.current_price), ('coins count', self.coins_count),('capitalization', self.capitalization)

# юзер
class User:
    #инициализация параметров
    def __init__(self, first_name, last_name, money):
        self.first_name = first_name
        self.last_name = last_name
        self.money = money
        self.coins_in_account = {'world_coin': money}


    def get_total_wealth(self, coins_list):

        total = self.coins_in_account.get('world_coin', 0)
        for coin in coins_list:
            amount = self.coins_in_account.get(coin.name, 0)
            total += amount * coin.current_price
        return total

    @property
    def debug_user_stats(self):
        return ('first name', self.first_name), ('last name', self.last_name), ('money', self.money), ('coins in account', self.coins_in_account)

    # покупка коинов
    def buy_coin(self, coin:Coin,coins_to_buy):
        cost = coins_to_buy * coin.current_price
        if coins_to_buy > coin.coins_count:
            return f'{self.first_name} {self.last_name}, has not enough money to buy!'
        if coins_to_buy > self.money:
            return f'{self.first_name} {self.last_name}, has not enough money to buy!'
        else:
            if coin.name not in self.coins_in_account.keys():
                coin.users_hold += 1

            self.coins_in_account['world_coin'] = round(self.money - cost, 2)
            self.coins_in_account[coin.name] = self.coins_in_account.get(coin.name, 0) + coins_to_buy

            coin.coins_on_market += coins_to_buy
            coin.current_price *= (1 + coins_to_buy/coin.coins_count)
            self.money = self.coins_in_account['world_coin']
            coin.update_capitalization()

            return f'{self.first_name} {self.last_name} bought {coins_to_buy} {coin.name}'

    def sell_coin(self, coin:Coin,coins_to_sell):
        user_amount = self.coins_in_account.get(coin.name, 0)

        if user_amount < coins_to_sell:
            return f"{self.first_name} has not enough {coin.name}"

        revenue = coins_to_sell * coin.current_price

        self.coins_in_account[coin.name] -= coins_to_sell
        self.coins_in_account['world_coin'] += revenue

        coin.coins_on_market -= coins_to_sell
        coin.current_price = coin.current_price * (1 - coins_to_sell / coin.coins_count)
        coin.coins_count += coins_to_sell
        self.money = self.coins_in_account['world_coin']
        coin.update_capitalization()
        return f'{self.first_name} {self.last_name} sold {coins_to_sell} {coin.name}'


world_coin = Coin('world_coin', 1_000_000_000, 1_000_000_000)


# --- Инициализация объектов ---
# Твои монеты (альткоины)
btc = Coin('MEME', 100, 1000)
lab = Coin('Labubu', 100, 1000)
pivo = Coin('Pivocoin', 100, 1000)
coins_list = [btc, lab, pivo]

# Твои игроки
players = [
    User('Abue', 'Babe', 1000),
    User('Whale', 'The_Rich', 1000),
    User('Elon', 'Musk', 1000),
    User('BOMZHARA', '', 10,),
    User('Hamster', 'Investor', 1000)
]

players[3].coins_in_account['Pivocoin'] = 10
# --- Настройка графиков ---
plt.ion()
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))
plt.subplots_adjust(hspace=0.5)

steps_x = [0]
history = {c.name: [c.current_price] for c in coins_list}
wld_price_history = [1.0]  # Начальная цена Worldcoin
wealth_history = {p.first_name: [p.get_total_wealth(coins_list)] for p in players}

# Линии графиков
lines_coin = {c.name: ax1.plot(steps_x, history[c.name], label=c.name)[0] for c in coins_list}
line_wld, = ax2.plot(steps_x, wld_price_history, color='gold', linewidth=2, label='Worldcoin Price')
lines_wealth = {p.first_name: ax3.plot(steps_x, wealth_history[p.first_name], label=p.first_name)[0] for p in players}

# Оформление
ax1.set_title("Курсы коинов (в WC)")
ax1.legend(loc='upper left')
ax1.grid(True)

ax2.set_title("Рыночная цена Worldcoin (Индекс активности)")
ax2.set_ylabel("WC")
ax2.grid(True)

ax3.set_title("Капитализация игроков (Total Wealth)")
ax3.legend(loc='upper left')
ax3.grid(True)

# --- Цикл симуляции ---
events = [
    {"name": "Bull Run", "impact": 1.2, "msg": "🚀 РЫНОК РАСТЕТ! Все монеты подорожали на 20%!"},
    {"name": "Market Crash", "impact": 0.5, "msg": "📉 КРАХ! Паника на бирже, цены рухнули вдвое!"},
    {"name": "Exchange Hack", "impact": 0.1, "msg": "💀 ВЗЛОМ! Одна из монет почти обесценилась!"},
    {"name": "Elon Tweet", "impact": 1.5, "msg": "🐦 ИЛОН ТУИТНУЛ! MEME улетает на луну!"}
]

# --- Симуляция с Кризисами и Ликвидациями ---
steps = 10000
for i in range(1, steps + 1):
    # --- СЛУЧАЙНОЕ СОБЫТИЕ (КРИЗИС) ---
    if i % 150 == 0:
        event = random.choice(events)
        target_coin = random.choice(coins_list)

        if event["name"] == "Elon Tweet":
            btc.current_price *= event["impact"]
        elif event["name"] == "Exchange Hack":
            target_coin.current_price *= event["impact"]
        else:
            for c_item in coins_list:
                c_item.current_price *= event["impact"]

        print(f"!!! STEP {i}: {event['msg']}")

    # --- ЛОГИКА ИГРОКОВ (Стратегии остаются) ---
    p = random.choice(players)
    action = 'buy'

    # Elon пампит MEME
    if p.first_name == 'Elon':
        c = btc
        amt = random.randint(30, 80)
        action = 'buy' if p.money > (amt * c.current_price) else 'sell'

    # Whale манипулирует Labubu
    elif p.first_name == 'Whale':
        c = lab
        amt = random.randint(50, 150)
        action = 'buy' if c.current_price < 0.6 else 'sell'

    # BOMZHARA играет на всё (All-in)
    elif p.first_name == 'BOMZHARA':
        c = pivo
        amt = random.randint(1, 10)
        action = 'buy' if p.money > (amt * c.current_price) else 'sell'

    # Hamster покупает на хаях и продает в панике
    elif p.first_name == 'Hamster':
        c = random.choice(coins_list)
        amt = random.randint(5, 20)
        # Если цена монеты за последние 10 шагов упала, хомяк продает всё
        action = 'sell' if i > 10 and history[c.name][-1] < history[c.name][-10] else 'buy'

    else:
        c = random.choice(coins_list)
        amt = random.randint(10, 40)
        action = random.choice(['buy', 'sell'])

    # Выполнение сделки
    if action == 'buy':
        p.buy_coin(c, amt)
    else:
        # Проверяем наличие монет перед продажей (чтобы не было ошибок)
        if p.coins_in_account.get(c.name, 0) > 0:
            p.sell_coin(c, amt if p.coins_in_account[c.name] >= amt else p.coins_in_account[c.name])

    # --- Обновление графиков ---
    steps_x.append(i)
    total_market_vol = sum(coin.coins_on_market for coin in coins_list)
    current_wld_price = 1.0 + (total_market_vol / 5000) + random.uniform(-0.02, 0.02)
    wld_price_history.append(current_wld_price)

    for coin in coins_list:
        history[coin.name].append(coin.current_price)
        lines_coin[coin.name].set_data(steps_x, history[coin.name])

    for player in players:
        # ЛИКВИДАЦИЯ: если капитал упал ниже 1 WC, игрок выбывает
        wealth = player.get_total_wealth(coins_list) * current_wld_price
        if wealth < 1 and i > 100:
            wealth = 0  # Бот обнулился

        wealth_history[player.first_name].append(wealth)
        lines_wealth[player.first_name].set_data(steps_x, wealth_history[player.first_name])

    line_wld.set_data(steps_x, wld_price_history)

    if i % 5 == 0:
        for ax in [ax1, ax2, ax3]:
            ax.relim()
            ax.autoscale_view()

for player in players:
    print(player.debug_user_stats)

print()
print(world_coin.debug_coin_stats)
for coin in coins_list:
    print(coin.debug_coin_stats)

plt.ioff()
plt.show()