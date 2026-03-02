import matplotlib.pyplot as plt
import random
from Stock import Coin,User


import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
#--------------------------------------------------------
class TradeNetLSTM(nn.Module):
    def __init__(self, input_size,num_layers, hidden_size, output_size):
        super(TradeNetLSTM, self).__init__()


        self.lstm = nn.LSTM(input_size=input_size,
                                    hidden_size=hidden_size,
                                    num_layers=num_layers,
                                    batch_first=True,
                                    dropout=0.2)
        self.fc = nn.Linear(hidden_size,hidden_size)

        self.fc1 = nn.Linear(hidden_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = x.unsqueeze(-1)

        _, (h_n, _) = self.lstm(x)

        out = h_n[-1]

        out = self.fc1(out)
        out = self.relu(out)
        out = self.fc2(out)

        first_part = out[:, :1]
        other_part = out[:, 1:]

        first_activated = torch.relu(first_part)
        other_activated = torch.sigmoid(other_part)

        return torch.cat((first_activated, other_activated), dim=1)

#--------------------------------------------------------

class TradeNet(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(TradeNet, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.relu(x)


        x = self.fc3(x)


        first_part = x[:, :1]
        other_part = x[:, 1:]


        first_activated = torch.relu(first_part)
        other_activated = torch.sigmoid(other_part)
        return torch.cat((first_activated, other_activated), dim=1)

import torch
import torch.nn as nn
import math

class PositionalEncoding(nn.Module):
    """Добавляет информацию о порядке цен в последовательности"""
    def __init__(self, d_model, max_len=5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x):
        # x shape: [batch_size, seq_len, d_model]
        x = x + self.pe[:x.size(1), :]
        return x

class TradeTransformer(nn.Module):
    def __init__(self, input_size, d_model, nhead, num_layers, output_size, dim_feedforward=512):
        super(TradeTransformer, self).__init__()

        # 1. Проекция входной цены в размерность модели (d_model)
        self.embedding = nn.Linear(input_size, d_model)

        # 2. Позиционное кодирование (обязательно, т.к. в трансформере нет встроенного понятия очереди)
        self.pos_encoder = PositionalEncoding(d_model)

        # 3. Слой Transformer Encoder
        encoder_layers = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead,
                                                    dim_feedforward=dim_feedforward,
                                                    batch_first=True, dropout=0.1)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers=num_layers)

        # 4. Выходная голова
        self.fc_out = nn.Linear(d_model, output_size)
        self.relu = nn.ReLU()

    def forward(self, x):
        # x: [batch, seq_len] -> [batch, seq_len, 1]
        if x.dim() == 2:
            x = x.unsqueeze(-1)

        # Подготовка данных
        x = self.embedding(x) # [batch, seq_len, d_model]
        x = self.pos_encoder(x)

        # Проход через трансформер
        output = self.transformer_encoder(x)

        # Берем среднее по всем шагам или только последний шаг
        # Для трейдинга лучше брать последний (самый актуальный)
        out = output[:, -1, :]

        out = self.fc_out(out)

        # Ваша логика активации (из прошлых версий)
        volume = self.relu(out[:, :1])
        probs = torch.sigmoid(out[:, 1:])

        return torch.cat((volume, probs), dim=1)

# Пример инициализации:
# d_model должен делиться на nhead без остатка!
#--------------------------------------------------------
#функция обвала рынка
def crash(coin_list,percentage):
    for coin in coin_list:
        before = coin.currency
        coin.currency *= (1 - percentage/100)
        # print(f'{coin.name} before:{before} after:{coin.currency}')

#демонстрация
# d_coin_list = [Coin(f'd_coin{i}',random.randint(10,100),random.randint(10,100)) for i in range(3)]
# crash(d_coin_list,40)

#--------------------------------------------------------
#функция бума на рынке
def stock_boom(coin_list,percentage):
    for coin in coin_list:
        before = coin.currency
        coin.currency *= (1 + percentage/100)
        # print(f'{coin.name} before:{before} after:{coin.currency}')

#демонстрация
# d_coin_list = [Coin(f'd_coin{i}',random.randint(10,100),random.randint(10,100)) for i in range(3)]
# stock_boom(d_coin_list,10)

#--------------------------------------------------------

def main():
    steps = 2000 # шаги
    users_count = 2 # кол-во юзеров
    coins_count = 8# кол-во коинов
    ai_users_count = 16
    percent_to_stock = 1.5 # процент в биржу

    # создание главного коина
    world_coin = Coin('world_coin',10**9,10**9)
    world_manager = [0,[world_coin]]

    users_list = []
    ai_users = []


    # создание событий
    events = ['crash','boom','nothing']
    events_weight = [5,5,90]

    for i in range(users_count):
        u = User('user'+str(i),1000,world_coin,world_manager[1])
        u.initialize_nick()
        u.register_in_wc()
        users_list.append(u)

    for i in range(ai_users_count):
        n_path = f'nanol_transformer.pth'
        model = TradeTransformer(input_size=1, d_model=32, nhead=2, num_layers=2, output_size=4)
        model.load_state_dict(torch.load(n_path))
        model.eval()
        nick = f"{n_path.split('.')[0]}_{i}"

        neuro_user = User(nick,1000,world_coin,world_manager[1])
        neuro_user.initialize_nick()
        neuro_user.register_in_wc()
        users_list.append(neuro_user)
        ai_users.append(neuro_user)


    for i in range(coins_count):
        world_manager[1].append(Coin(f'Coin{i}',random.randint(1000,100000),random.randint(1000,100000)))


    history = {
        'prices': {coin.name: [] for coin in world_manager[1]},
        'wealth': {user.nickname: [] for user in users_list}
    }

    for step in range(steps):
        event = random.choices(events,weights=events_weight,k=1)[0]

        if event == 'crash':
            crash(world_manager[1],random.randint(10,25))
        elif event == 'boom':
            stock_boom(world_manager[1],random.randint(5,30))

        for user in users_list:

            if user in ai_users:
                # print(user.nickname)
                target_coin = random.choice(world_manager[1][1:])  # кроме world_coin
                coin_history = history['prices'][target_coin.name]


                if len(coin_history) >= 128:

                    input_data = torch.tensor([coin_history[-128:]], dtype=torch.float32)


                    input_data = input_data / (input_data[0, 0] + 1e-8)

                    with torch.no_grad():
                        # Предсказание: [Price_Ref, Buy_Prob, Sell_Prob, Hold_Prob]
                        prediction = model(input_data)
                        # print(prediction)


                    probs = prediction[0, 1:]
                    action_idx = torch.argmax(probs).item()  # BuyCount, Buy, Sell, Hold

                    if action_idx == 0:  # Buy
                        # Первый элемент для объема закупа
                        volume = int(prediction[0, 0].item() % 1000) + 1
                        print(volume)
                        user.buy(volume, target_coin)
                    elif action_idx == 1:  # Sell
                        volume = int(prediction[0, 0].item() % 1000) + 1
                        user.sell(volume, target_coin)
                else:
                    u_events = ['buy', 'sell']
                    target = random.choice(world_manager[1])
                    decision = random.choice(u_events)

                    if decision == 'buy':
                        user.buy(random.randint(1, 1000), target)
                    elif decision == 'sell':
                        user.sell(random.randint(1, 1000), target)





            user.apply_request(percent_to_stock)

            # запись богатства в историю
            total_wealth = user.wc_count
            for c in world_manager[1]:
                total_wealth += user.wallet.get(c.name, 0) * c.currency
            history['wealth'][user.nickname].append(total_wealth)

        # запись курса монет в историю
        for coin in world_manager[1]:
            history['prices'][coin.name].append(coin.currency)

    return history

#--------------------------------------------------------
# Построение графиков
def graphics(history):
    plt.style.use('ggplot')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # График цен
    for coin_name, prices in history['prices'].items():
        if coin_name != 'world_coin':
            ax1.plot(prices, label=coin_name)
    ax1.set_title('Динамика курсов монет')
    ax1.set_ylabel('Цена в WC')
    ax1.legend()

    # График капитала
    for user_nick, wealth_history in history['wealth'].items():
        ax2.plot(wealth_history, label=user_nick)
    ax2.set_title('Капитализация пользователей (Net Worth)')
    ax2.set_ylabel('Общая стоимость активов')
    ax2.set_xlabel('Шаги симуляции')
    ax2.legend()

    plt.tight_layout()
    plt.show()

#--------------------------------------------------------

if __name__ == '__main__':
    h = main()
    graphics(h)