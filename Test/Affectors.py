import math
import random
import json
import pickle
import os

def sigmoid(x):
    return 1 / (1 + math.exp(-x))


class AffectionBlock:
    def __init__(self, idx, entered_blocks = [], output_blocks = [], base_affection = 0, epsilon = 1e-5):
        self.entered_blocks = entered_blocks
        self.output_blocks = output_blocks
        self.idx = idx
        self.epsilon = epsilon

        self.base_affection = base_affection # базовое влияние блока, которое может быть изменено в процессе забывания
        self.affection = len(self.entered_blocks) + base_affection 
    
    # вычисление влияния блока
    def to_affect(self):
        affects = {}
        if self.affection == 0:
            return affects
        for block in self.entered_blocks:
            denom = block.affection if block.affection > self.epsilon else self.epsilon
            affect = math.fabs(self.affection - block.affection) * (self.affection / denom)
            affects[block.idx] = affect
        return affects

    # процесс забывания блока, который уменьшает его влияние со временем
    def to_forgetting(self, current_idx, forgetting_step = 0.005):
        mem_age = current_idx - self.idx
        if mem_age > 0:
            forget_rate = math.exp(-forgetting_step)
            self.base_affection = forget_rate * self.base_affection
            self.affection = self.base_affection + len(self.entered_blocks)
    
    def out(self):
        return self.affection
    
    def out_sigmoid(self):
        return sigmoid(self.affection)
    
def example_usage():
    example_block = AffectionBlock(idx=0, entered_blocks=[], output_blocks=[], base_affection=0.5)
    block1 = AffectionBlock(idx=1, entered_blocks=[example_block], output_blocks=[], base_affection=0.3)
    block2 = AffectionBlock(idx=2, entered_blocks=[example_block], output_blocks=[block1, example_block], base_affection=0.2)


    print("Affection:", example_block.out())
    print("Sigmoid Affection:", example_block.out_sigmoid())
    print("-"*40)
    print("Affection:", block1.out())
    print("Sigmoid Affection:", block1.out_sigmoid())
    print("-"*40)
    print("Affection:", block2.out())
    print("Sigmoid Affection:", block2.out_sigmoid())

