import json
import random
import hashlib

random.seed(42)

SIM_PATH = "simulation_data.json"
CHAT_PATH = "AffectorChatSession.json"
OUT_PATH = "MipleDataset.json"

# порядок измерений вектора личности
SENTIMENTS = ["оптимист", "рискованный", "систематичный", "консерватист", "интроверт", "убежденный", "интуитивный"]

SENT_NAMES = {
    "оптимист": "Оптимист",
    "рискованный": "Рискованный",
    "систематичный": "Систематичный",
    "консерватист": "Консерватист",
    "интроверт": "Интроверт",
    "убежденный": "Убеждённый",
    "интуитивный": "Интуитивный",
}

# сферы для акций
THEMES = ["технологии", "медицина", "финансы", "энергетика", "товары", "недвижимость",
          "сырьё", "промышленность", "связь", "спорт", "развлечения", "транспорт", "агро"]

EVENTS_POS = ["Успешный квартал", "Выход нового продукта", "Положительные отзывы о продукте",
              "Рост популярности отрасли", "Крупный заказ от государства", "Слияние с гигантом рынка"]
EVENTS_NEG = ["Кризис на рынке", "Появление нового конкурента", "Провальный квартал",
              "Уход топ-менеджера", "Негативные отзывы о продукте", "Штраф от регулятора", "Утечка данных"]
ALL_EVENTS = EVENTS_POS + EVENTS_NEG


def load_simulation():
    with open(SIM_PATH, encoding="cp1251") as f:
        raw = json.load(f)
    # имена идут в фиксированном порядке каждую эпоху
    names = []
    for rec in raw:
        if rec["name"] not in names:
            names.append(rec["name"])
        else:
            break
    n_stocks = len(names)
    epochs = len(raw) // n_stocks
    series = {name: [] for name in names}
    for i, rec in enumerate(raw):
        series[names[i % n_stocks]].append(rec)
    return names, epochs, series


def assign_sphere(name):
    h = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
    return THEMES[h % len(THEMES)]


def direction(prev_price, price):
    if price > prev_price * 1.002:
        return "рост"
    if price < prev_price * 0.998:
        return "падение"
    return "флэт"


def vol_bucket(vol, price):
    # относительная волатильность (vol/price) в три уровня для решений
    rel = vol / price if price > 0 else 0
    if rel < 0.09:
        return "тихо"
    if rel < 0.14:
        return "качает"
    return "шторм"


def make_personality(active, blend=None):
    # базовый вектор личности: доминанта высокая, остальное шум
    vec = [round(random.uniform(0.02, 0.18), 3) for _ in SENTIMENTS]
    vec[SENTIMENTS.index(active)] = round(random.uniform(0.82, 0.97), 3)
    if blend:
        vec[SENTIMENTS.index(blend)] = round(random.uniform(0.7, 0.9), 3)
    return vec


# ------------------------- библиотека живых реплик -------------------------
# {s} акция, {sf} сфера, {e} событие, {o} другой агент

REPLIES = {
    "оптимист": {
        "pos": [
            "Блинский, {s} же ракета! {e} — это билет на луну, залетаю по рынку и не парюсь.",
            "Вы чего кислые? {e} по {sf} — это праздник! {s} только разгоняется, я в плюсе сижу.",
            "Ну я же говорил — {sf} прёт! {s} в космос, кто не зашёл — сам охлобыш.",
            "{e}? Да это лучшее, что случалось с {s}! Беру ещё, тут все станем богатыми.",
        ],
        "neg": [
            "{e}? Да и пофиг, {s} отскочит, она по {sf} всегда отрастает. Откуплю дешевле — красота.",
            "Паникёры, успокойтесь. {e} — это скидка на {s}, а не конец света. Беру на просадке.",
            "{o}, не ной как пердун, {s} ещё всех удивит. Минус сегодня — плюс завтра.",
            "Просадка по {sf}? Так это же подарок! Закупаю {s}, через месяц спасибо скажете.",
        ],
        "neutral": [
            "По {s} тишина, ну и ладно. В {sf} затишье — самое время докупиться по дешёвке.",
            "Нормально всё, {s} стоит — отдыхает перед рывком. Держу и улыбаюсь.",
        ],
    },
    "рискованный": {
        "pos": [
            "{e}?! Всё, захожу в {s} на всю котлету, с плечом! {sf} полетела, кто не рискнул — зануда.",
            "Ва-банк по {s}! {e} — это сигнал, гружу портфель под завязку, тормоза для трусов.",
            "Погнали! {sf} разгоняется, {s} беру максимально. {o}, хватит сопли жевать, залетай!",
            "Адреналинчик пошёл — {e}! Удваиваю позу по {s}, или пан или пропал.",
        ],
        "neg": [
            "{e}? Кровь на улицах — самое время брать! {s} на дне, гружу контртренд, очко не жим-жим.",
            "Все сливают {s} — а я, дурни, наоборот закупаю. {sf} рухнула, значит отскок будет жирный.",
            "{o}, ты сливаешь как пердун на панике, а я в {s} захожу с плечом. Шторм — мой друг.",
            "Паника по {sf} — мой звёздный час. Лоу выкупаю по {s}, потом будете локти кусать.",
        ],
        "neutral": [
            "Скукота, {s} еле дышит. Беру на отскок волатильности, скальпану по-быстрому.",
            "Боковик по {s} — раскачаю на коротке. В {sf} затишье перед бурей, я наготове.",
        ],
    },
    "систематичный": {
        "pos": [
            "По графику {s} пробила сопротивление, {e} подтверждает тренд. Вхожу лесенкой, тейк выставил.",
            "Сигнал по {sf} чистый: {e} + рост объёма. Беру {s} по системе, стоп под локалом.",
            "{o}, не на эмоциях, а по цифрам: {s} в восходящем канале, {e} — катализатор. Докупаю порцию.",
            "Бэктест по {sf} говорит вход. {s} держу по тренду, риск на сделку 2%, всё по плану.",
        ],
        "neg": [
            "{e} ломает структуру по {s}. Стоп-лосс сработал, фиксирую и выхожу, эмоции мимо кассы.",
            "По {sf} сигнал на выход: {e} + пробой вниз. Сливаю {s}, потом пересмотрю на споте.",
            "{o}, не лови падающий нож. {s} в нисходящем по {e}, я в стороне, жду разворота по индикаторам.",
            "Риск-менеджмент важнее чуйки. {s} ниже скользящей — режу позу, кэш на депозит.",
        ],
        "neutral": [
            "{s} в боковике, объёмы пустые. Жду пробоя канала, без сигнала не трогаю.",
            "По {sf} нет триггера — сижу в кэше. {s} на месте, держу до подтверждения.",
        ],
    },
    "консерватист": {
        "pos": [
            "{e}, говорите? Ну допустим. {s} подрос, но я по {sf} спешить не буду, посмотрю квартал.",
            "Рост по {s} — приятно, но я лучше зафиксирую часть. Жадность до добра не доводит.",
            "{o}, не настрать бы в штаны на этом хайпе. {s} держу, но новые деньги не несу.",
            "Хорошо что {sf} ожила. Я свой кусок {s} придержу, остальное — в надёжный кэш.",
        ],
        "neg": [
            "Вот! Я же говорил — {e}. {s} в минус, я давно вышел, сижу в кэше как умный.",
            "{sf} затрясло, {e} — для меня сигнал не геройствовать. {s} продаю, нервы дороже.",
            "{o}, ты охлобыш, лезешь в {s} на панике. Я пересижу в кэше, целее буду.",
            "{e}? Спасибо, обойдусь. Режу риск по {s}, лучше синица в руке.",
        ],
        "neutral": [
            "{s} тихо стоит — вот это мне по душе. По {sf} без сюрпризов, держу спокойно.",
            "Ни рыба ни мясо по {s}. Не трогаю, кэш — мой лучший друг, без суеты.",
        ],
    },
    "интроверт": {
        "pos": [
            "{e}. Молча докупил {s}. Без шума.",
            "{sf} растёт. Взял немного {s}, расписывать не буду.",
            "Норм. {s} в плюс. Я в деле, тихо.",
            "Ага, {e}. Зашёл в {s}. Всё.",
        ],
        "neg": [
            "{e}. Вышел из {s} молча, пока вы орёте.",
            "{sf} вниз. Сократил {s}. Без комментариев.",
            "Шумно тут. Слил {s}, пойду помолчу.",
            "{e}? Понял. {s} закрыл, дальше сами.",
        ],
        "neutral": [
            "{s} стоит. Я тоже постою. Держу.",
            "По {sf} тихо. И мне так лучше. Не трогаю {s}.",
        ],
    },
    "убежденный": {
        "pos": [
            "Я ЖЕ ГОВОРИЛ! {e} по {s} — всё как я и предсказывал. Гниды смеялись, а я докупаю.",
            "{sf} взлетела ровно как я обещал. {s} — моя ставка на годы, добавляю без сомнений.",
            "{o}, кто сомневался — тот зря. {s} прёт, {e} это доказал, я держу до конца.",
            "Моя позиция по {s} железная. {e} — лишь подтверждение, я знал это с самого начала.",
        ],
        "neg": [
            "{e}? Шум для слабаков. {s} — фундамент крепкий, я держу, паникёры пусть бегут.",
            "{sf} трясёт, ну и пусть. {s} я не отдам, моя уверенность не на новостях строится.",
            "{o}, не будь гнидой, не сливай {s} на эмоциях. Я как стоял, так и стою.",
            "{e} меня не пугает. {s} переживёт это, я в неё верю и докуплю на дне.",
        ],
        "neutral": [
            "{s} стоит — и правильно делает. Моя позиция неизменна, я уверен в {sf}.",
            "Болтайте сколько хотите. {s} держу, переубеждать меня бесполезно.",
        ],
    },
    "интуитивный": {
        "pos": [
            "Нутром чую — {s} попрёт! {e} это так, для галочки, у меня чуйка сработала, беру.",
            "Звёзды сошлись по {sf}: {e} и моё предчувствие. {s} — моё, захожу на интуиции.",
            "{o}, я ж нюхом чуял, что {s} стрельнет! {e} — а я уже в позиции, ха.",
            "Что-то ёкнуло — взял {s}. И вон, {e}. Чуйка не подводит, по {sf} вижу рост.",
        ],
        "neg": [
            "Что-то мне муторно по {s}... {e}, ага. Чуйка орёт — выхожу, пока не поздно.",
            "Нутро подсказывает: {sf} посыпется. Сливаю {s}, потом разберёмся почему.",
            "{o}, у меня плохое предчувствие по {s}. {e} — звоночек, я в кэш, нюх не врёт.",
            "Не нравится мне {s}, прям свербит. {e} подтверждает — закрываю, ну его.",
        ],
        "neutral": [
            "По {s} никаких вибраций. Подожду, пока чуйка что-нибудь шепнёт.",
            "{sf} молчит, и нутро молчит. {s} держу, жду знака.",
        ],
    },
}


def pick_target_stock(sentiment, stocks_states):
    # каждый сентимент выбирает акцию по своему характеру
    items = list(stocks_states.items())
    if sentiment == "рискованный":
        items.sort(key=lambda kv: kv[1][3], reverse=True)  # макс волатильность
    elif sentiment == "консерватист":
        items.sort(key=lambda kv: kv[1][3])  # мин волатильность
    elif sentiment == "систематичный":
        items.sort(key=lambda kv: (kv[1][2] != "рост", kv[1][3]))  # тренд вверх и спокойнее
    elif sentiment == "оптимист":
        items.sort(key=lambda kv: kv[1][2] != "рост")  # что растёт
    elif sentiment == "убежденный":
        items.sort(key=lambda kv: kv[0])  # стабильно одна и та же по имени
    else:
        random.shuffle(items)
    name = items[0][0]
    return name, items[0][1]


TACTICS = {
    ("buy", "рискованный"): "вход с плечом на импульсе",
    ("buy", "систематичный"): "лесенка покупок по тренду",
    ("buy", "оптимист"): "купи и держи",
    ("buy", "консерватист"): "осторожный набор малой долей",
    ("buy", "убежденный"): "усреднение и долгосрочное удержание",
    ("buy", "интуитивный"): "вход по предчувствию разворота",
    ("buy", "интроверт"): "тихий набор позиции",
    ("sell", "рискованный"): "агрессивная фиксация и шорт",
    ("sell", "систематичный"): "стоп-лосс и выход в кэш",
    ("sell", "консерватист"): "сокращение риска, уход в кэш",
    ("sell", "оптимист"): "частичная фиксация прибыли",
    ("sell", "убежденный"): "разгрузка слабой позиции",
    ("sell", "интуитивный"): "выход по плохому предчувствию",
    ("sell", "интроверт"): "молчаливая фиксация",
    ("hold", "рискованный"): "ожидание волатильности",
    ("hold", "систематичный"): "ожидание сигнала по индикаторам",
    ("hold", "консерватист"): "удержание кэша и наблюдение",
    ("hold", "оптимист"): "удержание в расчёте на рост",
    ("hold", "убежденный"): "железное удержание позиции",
    ("hold", "интуитивный"): "ожидание знака чуйки",
    ("hold", "интроверт"): "пассивное удержание",
}


def decide(sentiment, polarity, direction_v, vbucket):
    # возвращает (decision_onehot[buy,sell,hold], emotions[angry,sadness,joy])
    buy = [1, 0, 0]
    sell = [0, 1, 0]
    hold = [0, 0, 1]

    r = random.random()
    if sentiment == "оптимист":
        dec = buy if r < 0.8 else hold
    elif sentiment == "рискованный":
        if vbucket == "шторм":
            dec = buy if r < 0.6 else sell
        else:
            dec = buy if r < 0.7 else (sell if r < 0.85 else hold)
    elif sentiment == "систематичный":
        if polarity == "pos" and direction_v == "рост":
            dec = buy if r < 0.75 else hold
        elif polarity == "neg":
            dec = sell if r < 0.7 else hold
        else:
            dec = hold
    elif sentiment == "консерватист":
        if polarity == "neg" or vbucket == "шторм":
            dec = sell if r < 0.6 else hold
        else:
            dec = hold if r < 0.7 else buy
    elif sentiment == "интроверт":
        if polarity == "pos":
            dec = buy if r < 0.4 else hold
        elif polarity == "neg":
            dec = sell if r < 0.4 else hold
        else:
            dec = hold
    elif sentiment == "убежденный":
        if polarity == "pos":
            dec = buy if r < 0.6 else hold
        else:
            dec = hold if r < 0.8 else buy
    else:  # интуитивный
        if polarity == "pos":
            dec = buy if r < 0.65 else hold
        elif polarity == "neg":
            dec = sell if r < 0.6 else hold
        else:
            dec = hold if r < 0.6 else (buy if r < 0.8 else sell)

    # эмоции привязаны к решению и полярности
    angry = sadness = joy = 0.0
    if dec == buy:
        joy = round(random.uniform(0.6, 0.95), 2)
        if polarity == "neg":
            angry = round(random.uniform(0.2, 0.5), 2)
    elif dec == sell:
        if polarity == "neg":
            sadness = round(random.uniform(0.5, 0.9), 2)
            angry = round(random.uniform(0.3, 0.7), 2)
        else:
            joy = round(random.uniform(0.4, 0.7), 2)
    else:  # hold
        if polarity == "neg":
            sadness = round(random.uniform(0.2, 0.5), 2)
        else:
            joy = round(random.uniform(0.2, 0.5), 2)

    return dec, [angry, sadness, joy]


def reply_for(sentiment, polarity, stock, sphere, event, other):
    bucket = polarity if polarity in ("pos", "neg") else "neutral"
    tmpl = random.choice(REPLIES[sentiment][bucket])
    return tmpl.format(s=stock, sf=sphere, e=event, o=other)


def build():
    names, epochs, series = load_simulation()
    spheres = {name: assign_sphere(name) for name in names}

    # расставляем события по таймлайну (в исходных данных их нет)
    event_at = {}
    ep = random.randint(10, 30)
    while ep < epochs:
        event_at[ep] = random.choice(ALL_EVENTS)
        ep += random.randint(12, 35)

    dataset = []
    sample_epochs = sorted(event_at.keys())

    for ep in sample_epochs:
        event = event_at[ep]
        polarity = "pos" if event in EVENTS_POS else "neg"
        recent = [event_at[e] for e in sample_epochs if e <= ep][-3:]

        # состояние всех акций на эпохе
        stocks_states = {}
        for name in names:
            rec = series[name][ep]
            prev = series[name][ep - 1]["price"] if ep > 0 else rec["open"]
            stocks_states[name] = [
                spheres[name],
                round(rec["price"], 4),
                direction(prev, rec["price"]),
                round(rec["volatility"], 5),
            ]

        # диалог: каждый сентимент реагирует, видя предыдущие реплики
        chat_context = []
        turn_order = SENTIMENTS[:]
        random.shuffle(turn_order)
        for sentiment in turn_order:
            tname, tstate = pick_target_stock(sentiment, stocks_states)
            tsphere, tprice, tdir, tvol = tstate
            vbucket = vol_bucket(tvol, tprice)
            dec, emo = decide(sentiment, polarity, tdir, vbucket)
            dec_name = ["buy", "sell", "hold"][dec.index(1)]
            other = SENT_NAMES[random.choice([s for s in SENTIMENTS if s != sentiment])]
            answer = reply_for(sentiment, polarity, tname, tsphere, event, other)

            sample = {
                "answer": answer,
                "messages": chat_context[-4:],
                "emotions": emo,
                "events": recent,
                "basic_sentiments_parameters": make_personality(sentiment),
                "stocks_states": stocks_states,
                "target_stock": tname,
                "decisions": dec,
                "tactic": TACTICS[(dec_name, sentiment)],
                "active_sentiment": sentiment,
            }
            dataset.append(sample)
            chat_context.append(answer)

    # блендовые сэмплы: человек настраивает смесь из двух сентиментов
    blend_pairs = [("интуитивный", "систематичный"), ("оптимист", "рискованный"),
                   ("консерватист", "убежденный"), ("рискованный", "интуитивный")]
    for ep in sample_epochs[::3]:
        event = event_at[ep]
        polarity = "pos" if event in EVENTS_POS else "neg"
        recent = [event_at[e] for e in sample_epochs if e <= ep][-3:]
        stocks_states = {}
        for name in names:
            rec = series[name][ep]
            prev = series[name][ep - 1]["price"] if ep > 0 else rec["open"]
            stocks_states[name] = [spheres[name], round(rec["price"], 4),
                                   direction(prev, rec["price"]), round(rec["volatility"], 5)]
        a, b = random.choice(blend_pairs)
        tname, tstate = pick_target_stock(a, stocks_states)
        tsphere, tprice, tdir, tvol = tstate
        vbucket = vol_bucket(tvol, tprice)
        dec, emo = decide(a, polarity, tdir, vbucket)
        dec_name = ["buy", "sell", "hold"][dec.index(1)]
        other = SENT_NAMES[b]
        # смешанная реплика: половина от одного, половина от другого
        part_a = reply_for(a, polarity, tname, tsphere, event, other)
        part_b = reply_for(b, polarity, tname, tsphere, event, SENT_NAMES[a])
        answer = part_a + " " + part_b.split(" ", 1)[-1]
        dataset.append({
            "answer": answer,
            "messages": [],
            "emotions": emo,
            "events": recent,
            "basic_sentiments_parameters": make_personality(a, blend=b),
            "stocks_states": stocks_states,
            "target_stock": tname,
            "decisions": dec,
            "tactic": TACTICS[(dec_name, a)],
            "active_sentiment": f"{a}+{b}",
        })

    random.shuffle(dataset)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"сэмплов: {len(dataset)}  эпох с событиями: {len(sample_epochs)}  акций: {len(names)}")


if __name__ == "__main__":
    build()
