import matplotlib.pyplot as plt
import random
import copy
import torch
import torch.nn as nn
from Stock import Coin, User


class NanoModel(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(NanoModel, self).__init__()
        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, num_layers=1, batch_first=True)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Sigmoid(),
            nn.Linear(hidden_size // 2, output_size)
        )
        self.target = nn.Linear(hidden_size, 1)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = x.unsqueeze(-1)
        out, _ = self.lstm(x)
        out = self.relu(out[:, -1, :])
        target = self.target(out)
        chances = self.classifier(out)
        return chances, target


def crash(coin_list, percentage):
    for coin in coin_list:
        coin.currency *= (1 - percentage / 100)


def stock_boom(coin_list, percentage):
    for coin in coin_list:
        coin.currency *= (1 + percentage / 100)


def calc_single_y(price_block):
    v_min, v_max = min(price_block), max(price_block)
    diff = v_max - v_min
    k = diff / len(price_block) if diff != 0 else 1
    y_last = price_block[-1]
    x = 1 / (y_last * k + 1e-8) if y_last != 0 else 0
    n = (y_last - v_min) / diff if diff != 0 else 0.5
    return [x, 1 - n, n, 0.5]


def main():
    steps = 2048
    users_count = 1
    coins_count = 16
    each_ai_users_count = 2
    percent_to_stock = 1
    target_liquidity_per_user = 1000

    world_coin = Coin('world_coin', 10 ** 9, 10 ** 9)
    world_manager = [0, [world_coin]]

    users_list = []
    ai_users = []

    events = ['crash', 'boom', 'nothing']
    events_weight = [5, 5, 90]

    for i in range(users_count):
        u = User(f'user{i}', 1000, world_coin, world_manager[1])
        u.initialize_nick()
        u.register_in_wc()
        users_list.append(u)

    models_list = ['stocker11.pth', 'stocker_l.pth', 'stocker2.pth','stocker_ampepa.pth']
    loaded_models = {}
    for m_path in models_list:
        m = NanoModel(1, 32, 3)
        try:
            m.load_state_dict(torch.load(m_path, weights_only=True))
        except:
            pass
        m.eval()
        loaded_models[m_path] = m

    for i in range(each_ai_users_count):
        for m_path in models_list:
            nick = f"{m_path.split('.')[0]}_{i}"
            neuro_user = User(nick, random.randint(500, 2000), world_coin, world_manager[1])
            neuro_user.initialize_nick()
            neuro_user.register_in_wc()
            neuro_user.model = copy.deepcopy(loaded_models[m_path])
            users_list.append(neuro_user)
            ai_users.append(neuro_user)

    for i in range(coins_count):
        world_manager[1].append(Coin(f'Coin{i}', random.randint(5000, 50000), random.randint(1000, 10000)))

    history = {
        'prices': {coin.name: [] for coin in world_manager[1]},
        'wealth': {user.nickname: [] for user in users_list}
    }

    for step in range(steps):
        event = random.choices(events, weights=events_weight, k=1)[0]
        if event == 'crash':
            crash(world_manager[1][1:], random.randint(10, 25))
        elif event == 'boom':
            stock_boom(world_manager[1][1:], random.randint(5, 30))

        for user in users_list:
            target_coin = random.choice(world_manager[1][1:])
            coin_hist = history['prices'][target_coin.name]

            if len(coin_hist) >= 32:
                window = coin_hist[-32:]
                norm_window = [p / (window[0] + 1e-8) for p in window]

                if user in ai_users:
                    input_data = torch.tensor([norm_window], dtype=torch.float32)
                    with torch.no_grad():
                        chances, target_val = user.model(input_data)
                        chances = chances[0].tolist()
                        target_val = target_val.item()

                    if chances[1] > chances[0]:
                        buy_amount = user.wc_count * 0.2 * min(target_val, random.uniform(0.1, 1.0))
                        user.buy(buy_amount, target_coin)
                    else:
                        user.sell(target_val, target_coin)
                else:
                    r = calc_single_y(norm_window)
                    if r[2] * random.uniform(1, 2) > r[1]:
                        user.buy(r[0], target_coin)
                    else:
                        user.sell(r[0], target_coin)

            world_manager[0] += user.apply_request(percent_to_stock)

        current_wc_supply = sum(u.wc_count for u in users_list) + world_manager[0]
        target_wc_supply = len(users_list) * target_liquidity_per_user

        if current_wc_supply < target_wc_supply:
            shortage = (target_wc_supply - current_wc_supply) / len(users_list)
            for u in users_list:
                u.receive_yield(shortage)
            world_manager[0] = max(0, world_manager[0] - (target_wc_supply - current_wc_supply))

        world_coin.currency = 1.0
        world_coin.on_market = sum(u.wc_count for u in users_list)
        world_coin.capitalization = world_coin.on_market

        for coin in world_manager[1]:
            history['prices'][coin.name].append(coin.currency)
        for user in users_list:
            current_wealth = user.wc_count + sum(user.wallet.get(c.name, 0) * c.currency for c in world_manager[1][1:])
            history['wealth'][user.nickname].append(current_wealth)

    return history


def graphics(history):
    plt.style.use('ggplot')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    for coin_name, prices in history['prices'].items():
        if coin_name != 'world_coin':
            ax1.plot(prices, label=coin_name, linewidth=1)
    ax1.set_title('Market Prices (in WC)')
    ax1.legend(loc='upper right', ncol=2)

    for user_nick, wealth in history['wealth'].items():
        ax2.plot(wealth, label=user_nick, alpha=0.7)
    ax2.set_title('User Net Worth')
    ax2.set_xlabel('Step')
    ax2.legend(loc='upper right', ncol=2)
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    h = main()
    graphics(h)