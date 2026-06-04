import os
import json
import math
import random

# обёртки над двумя "мозгами" миплов: нейросеть mrplip_17M_3 и граф AffectorSeller

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# порядок вектора личности (как в датасете)
SENTIMENTS = ["оптимист", "рискованный", "систематичный", "консерватист",
              "интроверт", "убежденный", "интуитивный"]

# сферы акций
THEMES = ["технологии", "медицина", "финансы", "энергетика", "товары", "недвижимость",
          "сырьё", "промышленность", "связь", "спорт", "развлечения", "транспорт", "агро"]

DIR_MAP = {"рост": 1.0, "флэт": 0.0, "падение": -1.0}

EVENTS_POS = ["Успешный квартал", "Выход нового продукта", "Положительные отзывы о продукте",
              "Рост популярности отрасли", "Крупный заказ от государства", "Слияние с гигантом рынка"]
EVENTS_NEG = ["Кризис на рынке", "Появление нового конкурента", "Провальный квартал",
              "Уход топ-менеджера", "Негативные отзывы о продукте", "Штраф от регулятора", "Утечка данных"]
ALL_EVENTS = EVENTS_POS + EVENTS_NEG

# соответствие черт колеса личности сентиментам датасета
TRAIT2SENT = {
    "optimist": "оптимист",
    "risk": "рискованный",
    "systematic": "систематичный",
    "conservative": "консерватист",
    "introvert": "интроверт",
    "convinced": "убежденный",
    "intuitive": "интуитивный",
}

# названия тактик по паре (решение, сентимент) — из логики датасета
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


def assign_sphere(name):
    import hashlib
    h = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
    return THEMES[h % len(THEMES)]


def direction(prev_price, price):
    if price > prev_price * 1.002:
        return "рост"
    if price < prev_price * 0.998:
        return "падение"
    return "флэт"


def traits_to_sentiments(traits):
    # из черт колеса в список активных сентиментов
    sents = [TRAIT2SENT[t] for t in traits if t in TRAIT2SENT]
    return sents or ["систематичный"]


def dominant_sentiment(sentiments):
    return sentiments[0] if sentiments else "систематичный"


# ------------------------- нейросеть mrplip_17M_3 -------------------------

class MrplipBrain:
    name = "mrplip_17M_3"

    def __init__(self):
        import torch
        from tokenizers import Tokenizer
        from miple_model import MipleModel

        model_dir = os.path.join(ROOT, "Models", "mrplip_17M_3")
        self.tokenizer = Tokenizer.from_file(os.path.join(model_dir, "mrplip_17M_3_tokenizer.json"))
        self.pad_id = self.tokenizer.token_to_id("[PAD]")
        self.sos_id = self.tokenizer.token_to_id("[SOS]")
        self.eos_id = self.tokenizer.token_to_id("[EOS]")

        # словарь тактик строим из датасета (как при обучении)
        with open(os.path.join(ROOT, "MipleDataset.json"), encoding="utf-8") as f:
            tactics = sorted({s["tactic"] for s in json.load(f)})
        self.idx2tactic = {i: t for i, t in enumerate(tactics)}

        ckpt = torch.load(os.path.join(model_dir, "mrplip_17M_3.pth"), map_location="cpu", weights_only=True)
        tactics_count = ckpt["tactic_choicer.weight"].shape[0]
        self.model = MipleModel(
            vocab_size=self.tokenizer.get_vocab_size(), embed_size=512, block_size=512,
            heads=8, decisions_count=3, emotions_count=3, market_features=4,
            sentiments_count=7, tactics_count=tactics_count, n_layers=4,
        )
        self.model.load_state_dict(ckpt)
        self.model.eval()
        self.torch = torch

    def _strip_pad(self, ids):
        return [i for i in ids if i != self.pad_id]

    def _encode_market(self, stocks_states, max_stocks=8):
        names = list(stocks_states.keys())
        rows = []
        for name in names:
            sphere, price, dir_v, vol = stocks_states[name]
            sphere_idx = THEMES.index(sphere) / len(THEMES) if sphere in THEMES else 0.0
            rows.append([sphere_idx, float(price), DIR_MAP.get(dir_v, 0.0), float(vol)])
        while len(rows) < max_stocks:
            rows.append([0.0, 0.0, 0.0, 0.0])
        return self.torch.tensor(rows[:max_stocks], dtype=self.torch.float), names

    def _persona(self, sentiments, base=0.1, strong=0.9):
        vec = self.torch.full((len(SENTIMENTS),), base)
        for s in sentiments:
            if s in SENTIMENTS:
                vec[SENTIMENTS.index(s)] = strong
        return vec.unsqueeze(0)

    def _sample(self, logits, temp):
        # сэмплируем из softmax, чтобы решение не схлопывалось в одно на всю симуляцию
        probs = self.torch.softmax(logits / temp, dim=-1)
        return self.torch.multinomial(probs, 1).item()

    def predict(self, stocks_states, events, messages, sentiments, max_new=28,
                temperature=0.9, decision_temp=1.3):
        torch = self.torch
        with torch.no_grad():
            market, names = self._encode_market(stocks_states)
            market = market.unsqueeze(0)

            news_ids = self._strip_pad(self.tokenizer.encode(" ".join(events)).ids) or [self.sos_id]
            news_seq = torch.tensor([news_ids], dtype=torch.long)

            emotions = torch.zeros(1, 3)
            persona = self._persona(sentiments)

            context = " ".join(messages).strip()
            prompt_text = f"{context} [SOS]".strip()
            prompt = torch.tensor([self._strip_pad(self.tokenizer.encode(prompt_text).ids)], dtype=torch.long)

            trade_logits, _, tactic_logits, stock_logits, _ = self.model(market, prompt, news_seq, emotions, persona)
            decision = ["buy", "sell", "hold"][self._sample(trade_logits[0], decision_temp)]
            tactic = self.idx2tactic.get(tactic_logits.argmax(-1).item(), "ожидание сигнала по индикаторам")
            chosen = names[self._sample(stock_logits[0, :len(names)], decision_temp)]

            generated = []
            for _ in range(max_new):
                if prompt.shape[1] >= self.model.block_size:
                    break
                _, _, _, _, text_logits = self.model(market, prompt, news_seq, emotions, persona)
                logits = text_logits[0, -1]
                probs = torch.softmax(logits / temperature, dim=-1)
                nxt = torch.multinomial(probs, 1).item()
                if nxt == self.eos_id:
                    break
                generated.append(nxt)
                prompt = torch.cat([prompt, torch.tensor([[nxt]])], dim=1)

            answer = self.tokenizer.decode(generated).strip()

        return {"answer": answer, "target_stock": chosen, "decision": decision, "tactic": tactic}


# ------------------------- граф AffectorSeller -------------------------

class AffectorBrain:
    name = "AffectorSeller"

    def __init__(self):
        import sys
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        # AffectionBlock — базовый "нейрон" модели AffectorSeller
        from Affectors.Affectors import AffectionBlock

        self.AffectionBlock = AffectionBlock
        self.word2idx = {}
        self.idx2word = {}
        self.blocks = {}
        self._build()

    def _build(self):
        # граф словесных связей из реплик датасета — на блоках AffectionBlock
        path = os.path.join(ROOT, "MipleDataset.json")
        answers = []
        try:
            with open(path, encoding="utf-8") as f:
                answers = [s["answer"] for s in json.load(f)]
        except Exception:
            answers = ["акция растёт держу позицию", "рынок падает фиксирую прибыль"]

        for ans in answers:
            for w in ans.lower().split():
                if w not in self.word2idx:
                    idx = len(self.word2idx)
                    self.word2idx[w] = idx
                    self.idx2word[idx] = w
                    self.blocks[idx] = self.AffectionBlock(idx=idx, entered_blocks=[], output_blocks=[], base_affection=0.5)

        for ans in answers:
            words = ans.lower().split()
            for a, b in zip(words, words[1:]):
                ba, bb = self.blocks[self.word2idx[a]], self.blocks[self.word2idx[b]]
                if bb not in ba.output_blocks:
                    ba.output_blocks.append(bb)
                if ba not in bb.entered_blocks:
                    bb.entered_blocks.append(ba)

    def _generate(self, seed, max_length=14, temperature=0.7):
        # блуждание по графу влияния от стартового слова
        cur = self.blocks.get(self.word2idx.get(seed))
        if cur is None:
            cur = random.choice(list(self.blocks.values()))
        out = [self.idx2word[cur.idx]]
        for _ in range(max_length):
            targets, weights = [], []
            for nb in cur.output_blocks:
                affects = nb.to_affect()
                if cur.idx in affects:
                    targets.append(nb)
                    weights.append(affects[cur.idx] ** (1.0 / temperature))
            if not targets:
                break
            total = sum(weights) or 1.0
            r, acc = random.random() * total, 0.0
            nxt = targets[-1]
            for nb, w in zip(targets, weights):
                acc += w
                if r <= acc:
                    nxt = nb
                    break
            out.append(self.idx2word[nxt.idx])
            cur = nxt
        return " ".join(out)

    def predict(self, stocks_states, events, messages, sentiments, **kw):
        sent = dominant_sentiment(sentiments)
        # выбор акции по характеру
        items = list(stocks_states.items())
        if sent == "рискованный":
            items.sort(key=lambda kv: kv[1][3], reverse=True)
        elif sent == "консерватист":
            items.sort(key=lambda kv: kv[1][3])
        elif sent in ("систематичный", "оптимист"):
            items.sort(key=lambda kv: kv[1][2] != "рост")
        else:
            random.shuffle(items)
        chosen, state = items[0]
        dir_v = state[2]

        # решение по сентименту и направлению
        polarity = "pos" if any(e in EVENTS_POS for e in events) else ("neg" if events else "neutral")
        r = random.random()
        if sent == "рискованный":
            decision = "buy" if r < 0.6 else "sell"
        elif sent == "консерватист":
            decision = "sell" if polarity == "neg" else ("hold" if r < 0.7 else "buy")
        elif sent == "оптимист":
            decision = "buy" if r < 0.75 else "hold"
        elif sent == "интроверт":
            decision = "buy" if dir_v == "рост" and r < 0.4 else ("sell" if dir_v == "падение" and r < 0.4 else "hold")
        else:
            decision = "buy" if dir_v == "рост" else ("sell" if dir_v == "падение" else "hold")

        tactic = TACTICS.get((decision, sent), "наблюдение за рынком")
        seed = messages[-1].split()[-1].lower() if messages and messages[-1].split() else None
        answer = self._generate(seed)
        return {"answer": answer, "target_stock": chosen, "decision": decision, "tactic": tactic}


# ленивый кэш загруженных мозгов
_CACHE = {}


def get_brain(model_name):
    if model_name not in _CACHE:
        _CACHE[model_name] = MrplipBrain() if model_name == "mrplip_17M_3" else AffectorBrain()
    return _CACHE[model_name]
