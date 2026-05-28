import matplotlib.pyplot as plt
import json
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable

from torch.utils import data
from torch.utils.data import Dataset,DataLoader

from tokenizers import ByteLevelBPETokenizer
from tokenizers.trainers import BpeTrainer
from tokenizers import Tokenizer, models, pre_tokenizers, decoders, trainers, processors
from tokenizers.models import BPE
from tokenizers.pre_tokenizers import Whitespace
import random
from torchinfo import summary

#============================================================================================

class Stock:
    def __init__(self, name, price, volume):
        self.name = name
        self.price = price

        self.volume = volume
        self.market_volume = 0

        self.price_history = [price]
        self.candles = []

#============================================================================================

class Request:
    def __init__(self, user, type, stock, vol):
        if type == 'buy':
            stock.market_volume += vol
            user.wallet['WC'] -= stock.price * vol
            user.wallet[stock.name] = user.wallet.get(stock.name, 0) + vol
            stock.price *= (1 + (vol / stock.volume))

            stock.price_history.append(stock.price)
        elif type == 'sell':
            stock.market_volume -= vol
            user.wallet['WC'] += stock.price * vol
            user.wallet[stock.name] = user.wallet.get(stock.name, 0) - vol
            stock.price *= (1 - (vol / stock.volume))

            stock.price_history.append(stock.price)
        else:
            pass


#============================================================================================
# юзер
class User:
    def __init__(self, Name, Start_cap, Stocks, Model, idx, Network):
        self.idx = idx
        self.name = Name
        self.network = Network

        self.stocks = Stocks

        self.wallet = {'WC': Start_cap}
        self.requests = []

        if Model != None:
            self.model = Model
        else:
            raise Exception('Невозможно зарегистрировать пользователя без модели') 

    def send_message(self, text: str):
        self.network.global_chat[self.name] = text

    def send_request(self, type, stock, vol):
        cost = stock.price * vol
        if type == 'buy':
            if cost <= self.wallet['WC']:
                if vol > stock.volume:
                    return False, 0
                if vol < 0:
                    return False, 0
                Request(self, type, stock, vol)
                return True, vol
            return False, 0

        elif type == 'sell' and stock.name in self.wallet:
            if vol > stock.volume:
                return False, 0
            if vol < 0:
                return False, 0
            if self.wallet.get(stock.name, 0) < vol:
                return False, 0

            Request(self, type, stock, vol)
            return True, vol

        return False, 0
    
    def get_total_wealth(self, all_stocks_prices):
        total_stock_value = sum(self.wallet.get(name, 0) * price for name, price in all_stocks_prices.items())
        return self.wallet['WC'] + total_stock_value
        
#============================================================================================
#набросок соц-сети
class SocialNetwork:
    def __init__(self, Name, Users):
        self.name = Name
        self.users = Users
        self.global_chat = {}

    def __len__(self):
        return len(self.users)

    def add_user(self, user):
        self.users.append(user)

    def remove_user(self, user):
        self.users.remove(user)

#============================================================================================
#модель рассказщика
class StoryTeller(nn.Module):
    def __init__(self, window_size: int, vocab_size: int, emb_size: int, rules_count: int):
        super(StoryTeller, self).__init__()

        self.time_window = nn.Sequential(
            nn.Linear(window_size, emb_size),
            nn.Linear(emb_size, rules_count)
        )

        self.chat_inflation = nn.Linear(emb_size, rules_count)

        self.embedding = nn.Embedding(vocab_size, emb_size)
        self.summary_layer = nn.Linear(rules_count * 2, rules_count)

    def forward(self, text, history):
        emb = self.embedding(text)
        history = self.time_window(history)
        emb_mean = torch.mean(emb, dim=1)
        chat_inf = self.chat_inflation(emb_mean)
        
        all_feautures = torch.cat((history, chat_inf), dim=1)
        res = self.summary_layer(all_feautures)

        return res

#============================================================================================
# датасетики

class MainDataset(Dataset):
    def __init__(self, texts, tokenizer, max_len=512, market_features=5, emotions_count=4):
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.market_features = market_features
        self.emotions_count = emotions_count
        
        self.samples = []
        for text in texts:
            tokens = tokenizer.encode(text).ids
            for i in range(0, len(tokens) - max_len, max_len):
                self.samples.append(tokens[i:i + max_len])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        tokens = torch.tensor(self.samples[index], dtype=torch.long)
        
        prompt_seq = tokens
        news_seq = tokens
        target_seq = tokens 
    
        market_seq = torch.zeros((10, self.market_features), dtype=torch.float32) 
        current_emotions = torch.zeros((self.emotions_count,), dtype=torch.float32)
        
        return market_seq, prompt_seq, news_seq, current_emotions, target_seq
    
#============================================================================================

class MipleDataset(Dataset):
    def __init__(self, tokenizer, history, max_len=512):
        super().__init__()
        self.tokenizer = tokenizer

        self.stocks_data = history['stocks_states']
        self.messages_data = history['messages']
        self.Events = history['events']
        self.emotions_data = history['emotions']


        self.max_len = max_len
        self.chat_samples = []

        for i in range(len(history)):
            text = f"{self.messages_data[i]['input']} [SOS] {self.messages_data[i]['output']} [EOS]"
            self.chat_samples.append(text)

    def __len__(self):
        return len(self.samples)
    def __getitem__(self, index):
        return super().__getitem__(index)
    
    
class TextDataset(Dataset): # текстовый датасет
    def __init__(self, text, tokenizer, max_len=512):
        self.tokenizer = tokenizer
        self.max_len = max_len
        
        # урезка текста до определенной длины
        self.tokens = tokenizer.encode(text).ids
        self.samples = [self.tokens[i:i + max_len] for i in range(0, len(self.tokens), max_len)]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, item):
        return torch.tensor(self.samples[item], dtype=torch.long)