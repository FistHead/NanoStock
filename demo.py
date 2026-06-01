import numpy as np
from matplotlib import pyplot as plt
from names_generator import generate_name
from Core import Stock, Request, User, SocialNetwork
import random 

themes = ['technology', 'healthcare', 'finance', 'energy', 'consumer goods','utilities', 'real estate', 'materials', 'industrials', 'telecommunications','psyhology', 'sports', 'entertainment', 'education', 'transportation', 'agriculture']

#экстра, рискованный, убежденный, оптимист, интроверт, интуитивный, консервативный, систематический
sentiments = [[0.5,0.5,0.5,0.5,0.5,0.5,0.5],
              [0.9,0.001,0.001,0.001,0.001,0.001,0.001]]

users_count = 32
stocks_count = 32

network = SocialNetwork('MIPLELE', [])
stocks = [Stock(generate_name(), random.choice(themes), random.randint(10, 100), random.randint(1000, 10000)) for _ in range(stocks_count)]

users = [
    User(
        Name=generate_name(), 
        Start_cap=random.randint(100, 1000), 
        Stocks=stocks,
        Model=None,
        idx=i, 
        Network=network
    ) 
    for i in range(users_count)
]

network.users = users