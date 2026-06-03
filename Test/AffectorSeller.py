import math
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from Affectors import *

class ClassificationAff:
    def __init__(self, idx, dataset):
        self.idx = idx
        self.dataset = dataset
        self.chat_blocks = []
        self.classification_blocks = []
        self.labels_blocks = []
        self.idx_2_all_words = {}

    def get_tokens(self):
        words = []
        labels = []
        answers_words = []
        
        for data in self.dataset:
            text = data["text"].lower()
            label = data["label"]
            answer = data["answer"].lower()

            words.extend(text.split())
            labels.append(label)
            answers_words.extend(answer.split())

        w_2idx = {word: idx for idx, word in enumerate(set(words))}
        idx_2w = {idx: word for word, idx in w_2idx.items()}
        labels_dict = {label: idx for idx, label in enumerate(set(labels))}
        answ_2idx = {word: idx for idx, word in enumerate(set(answers_words))}
        idx_2answ = {idx: word for word, idx in answ_2idx.items()}

        return w_2idx, idx_2w, labels_dict, answ_2idx, idx_2answ

    def build_classification_blocks(self):
        w_2idx, idx_2w, labels, answ_2idx, _ = self.get_tokens()

        if not self.classification_blocks:
            for word, idx in w_2idx.items():
                block = AffectionBlock(idx=idx, entered_blocks=[], output_blocks=[], base_affection=0.5)
                self.classification_blocks.append(block)
                self.idx_2_all_words[idx] = word

        for label, idx in labels.items():
            actual_idx = idx + len(w_2idx)
            block = AffectionBlock(idx=actual_idx, entered_blocks=[], output_blocks=[], base_affection=0.5)
            self.labels_blocks.append(block)
            self.idx_2_all_words[actual_idx] = f"__label__{label}"

        for data in self.dataset:
            text = data["text"].lower()
            label = data["label"]

            label_block = self.labels_blocks[labels[label]]

            for word in text.split():
                word_block = self.classification_blocks[w_2idx[word]]

                if label_block not in word_block.output_blocks:
                    word_block.output_blocks.append(label_block)
                if word_block not in label_block.entered_blocks:
                    label_block.entered_blocks.append(word_block)

    def build_chat_blocks(self):
        w_2idx, idx_2w, labels, answ_2idx, idx_2answ = self.get_tokens()

        if not self.classification_blocks:
            for word, idx in w_2idx.items():
                block = AffectionBlock(idx=idx, entered_blocks=[], output_blocks=[], base_affection=0.5)
                self.classification_blocks.append(block)
                self.idx_2_all_words[idx] = word

        start_answ_idx = len(w_2idx) + len(labels)
        for word, idx in answ_2idx.items():
            actual_idx = idx + start_answ_idx
            block = AffectionBlock(idx=actual_idx, entered_blocks=[], output_blocks=[], base_affection=0.5)
            self.chat_blocks.append(block)
            self.idx_2_all_words[actual_idx] = word

        for data in self.dataset:
            text = data["text"].lower()
            answer = data["answer"].lower()
            answ_words = answer.split()

            if answ_words:
                first_answ_block = self.chat_blocks[answ_2idx[answ_words[0]]]
                for word in text.split():
                    word_block = self.classification_blocks[w_2idx[word]]
                    
                    if first_answ_block not in word_block.output_blocks:
                        word_block.output_blocks.append(first_answ_block)
                    if word_block not in first_answ_block.entered_blocks:
                        first_answ_block.entered_blocks.append(word_block)

            for i in range(len(answ_words) - 1):
                current_word_block = self.chat_blocks[answ_2idx[answ_words[i]]]
                next_word_block = self.chat_blocks[answ_2idx[answ_words[i+1]]]

                if next_word_block not in current_word_block.output_blocks:
                    current_word_block.output_blocks.append(next_word_block)
                if current_word_block not in next_word_block.entered_blocks:
                    next_word_block.entered_blocks.append(current_word_block)
                        
    def get_word_by_idx(self, idx):
        return self.idx_2_all_words.get(idx, None)

def plot_affection_graph(classification_aff):
    w_2idx, idx_2w, labels, answ_2idx, idx_2answ = classification_aff.get_tokens()
    
    all_blocks = (
        classification_aff.classification_blocks + 
        classification_aff.labels_blocks + 
        classification_aff.chat_blocks
    )
    
    for block in all_blocks:
        block.affection = len(block.entered_blocks) + block.base_affection

    G = nx.DiGraph()
    labels_mapping = {}
    node_colors = []

    for word, idx in w_2idx.items():
        G.add_node(idx)
        labels_mapping[idx] = word
        node_colors.append("#A0C4FF")

    for label, idx in labels.items():
        actual_idx = idx + len(w_2idx)
        G.add_node(actual_idx)
        labels_mapping[actual_idx] = f"__label__{label}"
        node_colors.append("#FFADAD")

    start_answ_idx = len(w_2idx) + len(labels)
    for word, idx in answ_2idx.items():
        actual_idx = idx + start_answ_idx
        G.add_node(actual_idx)
        labels_mapping[actual_idx] = f"__reply__{word}"
        node_colors.append("#CAFFBF")

    for block in all_blocks:
        affects = block.to_affect()
        for target_idx, weight in affects.items():
            G.add_edge(target_idx, block.idx, weight=weight)

    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, k=1.5, seed=42)
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2500, alpha=0.9)
    nx.draw_networkx_labels(G, pos, labels=labels_mapping, font_size=10, font_weight="bold")

    edges = G.edges(data=True)
    if edges:
        weights = [edge[2]['weight'] for edge in edges]
        max_weight = max(weights) if max(weights) > 0 else 1
        edge_widths = [(w / max_weight) * 5 + 1 for w in weights]
        
        nx.draw_networkx_edges(
            G, pos, 
            edgelist=edges, 
            width=edge_widths, 
            edge_color="#4A4A4A", 
            arrowsize=20, 
            arrowstyle="->"
        )
        
        edge_labels = {(u, v): f"{d['weight']:.2f}" for u, v, d in edges}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9, label_pos=0.3)

    plt.axis("off")
    plt.tight_layout()
    plt.show()

class AffectionGenerator:
    def __init__(self, classification_aff):
        self.aff = classification_aff
        self.all_blocks = {}
        for b in (self.aff.classification_blocks + self.aff.labels_blocks + self.aff.chat_blocks):
            self.all_blocks[b.idx] = b

    def generate(self, input_text, max_length=5, temperature=1.0):
        words = input_text.lower().split()
        current_block = None

        last_word = words[-1]
        w_2idx, _, _, _, _ = self.aff.get_tokens()
        
        if last_word in w_2idx:
            current_block = self.aff.classification_blocks[w_2idx[last_word]]
        else:
            print("Слово не найдено в словаре.")
            return ""

        generated_words = [last_word]

        for _ in range(max_length):
            for b in self.all_blocks.values():
                b.affection = len(b.entered_blocks) + b.base_affection
                
            targets = []
            weights = []
            
            for out_block in current_block.output_blocks:
                if out_block in self.aff.labels_blocks:
                    continue
                affects = out_block.to_affect()
                if current_block.idx in affects:
                    targets.append(out_block.idx)
                    weights.append(affects[current_block.idx])

            if not targets:
                break

            weights = np.array(weights, dtype=np.float64)
            weights = np.clip(weights, 1e-10, None)
            weights = weights ** (1.0 / temperature)
            probabilities = weights / np.sum(weights)

            next_idx = np.random.choice(targets, p=probabilities)
            next_block = self.all_blocks[next_idx]
            
            word = self.aff.get_word_by_idx(next_idx)
            if word:
                generated_words.append(word)
            else:
                break

            current_block = next_block

        text = " ".join(generated_words[1:])

        return text

dataset = [
    {"text": "Акции openai взелели вверх", "label": "sell" , "answer": "Сюдааа, щас продам свои акции"},
    {"text": "Акции банка упали вниз", "label": "buy" , "answer": "Опа, возможно удастся залететь в поезд"},
    {"text": "Фондовый рынок ожидает стабильный рост", "label": "hold" , "answer": "Так, нужно удерживать свои акции, тогда я смогу заработать больше"},
]

classification_aff = ClassificationAff(idx=0, dataset=dataset)
classification_aff.build_classification_blocks()
classification_aff.build_chat_blocks()

generator = AffectionGenerator(classification_aff)
output = generator.generate("взелели вверх", max_length=16, temperature=0.6)
print("Сгенерированный ответ:", output)

plot_affection_graph(classification_aff=classification_aff)