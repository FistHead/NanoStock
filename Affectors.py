import math
import random
import json
import pickle
import os

class AffectionBlock:
    def __init__(self, idx, entered_blocks = [], output_blocks = [], base_affection = 0, epsilon = 1e-5):
        self.entered_blocks = entered_blocks
        self.output_blocks = output_blocks
        self.idx = idx
        self.epsilon = epsilon

        self.base_affection = base_affection
        self.affection = len(self.entered_blocks) + base_affection
    
    def to_affect(self):
        affects = {}
        if self.affection == 0:
            return affects
        for block in self.entered_blocks:
            denom = block.affection if block.affection > self.epsilon else self.epsilon
            affect = math.fabs(self.affection - block.affection) * (self.affection / denom)
            affects[block.idx] = affect
        return affects

    def to_forgetting(self, current_idx, forgetting_step = 0.005):
        mem_age = current_idx - self.idx
        if mem_age > 0:
            forget_rate = math.exp(-forgetting_step)
            self.base_affection = forget_rate * self.base_affection
            self.affection = self.base_affection + len(self.entered_blocks)

class AffectorText(AffectionBlock):
    def __init__(self, idx, entered_blocks=[], output_blocks=[], base_affection=0, epsilon=0.0001):
        super().__init__(idx, entered_blocks, output_blocks, base_affection, epsilon)
        
        self.w_2idx = {}
        self.word_blocks = {}
        
        self.sentiment_modifiers = {
        "оптимист":      {"boost": 2.0, "forget_speed": 0.0002},
        "рискованный":    {"boost": 2.5, "forget_speed": 0.0001},
        "систематичный":  {"boost": 1.0, "forget_speed": 0.001},
        "консерватист":  {"boost": 0.8, "forget_speed": 0.0015},
        "интроверт":      {"boost": 0.5, "forget_speed": 0.003},
        "убежденный":     {"boost": 1.2, "forget_speed": 0.0005},
        "интуитивный":    {"boost": 1.8, "forget_speed": 0.0004}
        }
        
        self.cfg_sentiments = {
        "рискованный":    {"temperature": 1.5, "forget_speed": 0.0001, "loop_penalty": 0.2}, 
        "оптимист":       {"temperature": 0.9, "forget_speed": 0.0002, "loop_penalty": 0.5},
        "систематичный":  {"temperature": 0.3, "forget_speed": 0.001,  "loop_penalty": 2.0},
        "консерватист":  {"temperature": 0.2, "forget_speed": 0.0015, "loop_penalty": 2.5},
        "интроверт":      {"temperature": 0.4, "forget_speed": 0.003,  "loop_penalty": 1.5},
        "убежденный":     {"temperature": 0.1, "forget_speed": 0.0005, "loop_penalty": 3.0},
        "интуитивный":    {"temperature": 1.1, "forget_speed": 0.0004, "loop_penalty": 0.7}
        }
            
    def train_on_text(self,json_file_path, word_blocks, idx_to_word, unique_words):
        with open(json_file_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
            
        for data_item in dataset:
            
            replics = data_item.get("replics", [])
            news = data_item.get("news", [])
            answer = data_item.get("answer", "")
            sentiments = data_item.get("sentiments", ["|"])
            
            current_sentiment = sentiments[0]
            modifier = self.sentiment_modifiers.get(current_sentiment, {"boost": 1, "forget_speed": 0.0001},)
            
            raw_text = f'{" ".join(replics)} [NEWS] {"".join(news)} [SOS] {answer} [EOS]'
            tokens = raw_text.split()
            
            for i in range(len(tokens)-1):
                curr_w = tokens[i]
                next_w = tokens[i+1]

                for w in (curr_w, next_w):
                    if w not in word_blocks:
                        new_idx = len(word_blocks)
                        initial_affection = 1 * modifier["boost"]
                        word_blocks[w] = AffectionBlock(
                            idx=new_idx, 
                            entered_blocks=[], 
                            output_blocks=[], 
                            base_affection=initial_affection
                        )
                        
                        idx_to_word[new_idx] = w
                
                curr_block = word_blocks[curr_w]
                next_block = word_blocks[next_w]
                
                if curr_block not in next_block.entered_blocks:
                    next_block.entered_blocks.append(curr_block)
                if next_block not in curr_block.entered_blocks:
                    curr_block.output_blocks.append(next_block)
                    
                next_block.base_affection += 0.25 * modifier["boost"]
                
            for block in word_blocks.values():
                block.to_forgetting(len(tokens), forgetting_step=modifier["forget_speed"])

        for block in word_blocks.values():
            block.affection = len(block.entered_blocks) + block.base_affection
            
        print(f'trained on: {len(tokens)} samples')
            
    
    def generate(self, prompt, current_mood, word_blocks, idx_2w, max_len=25):
        cfg = self.cfg_sentiments.get(current_mood, {"temperature": 0.5, "forget_speed": 0.001, "loop_penalty": 1.0})
        
        input_words = prompt.lower().split()
        start_block = None
        
        for w in input_words:
            clean_w = w.strip("?,.!;\"'")
            if not clean_w: continue
            
            found_nodes = [block for word, block in word_blocks.items() if clean_w == word.lower()]
            if not found_nodes:
                 found_nodes = [block for word, block in word_blocks.items() if clean_w in word.lower()]
                 
            if found_nodes:
                start_block = random.choice(found_nodes)
                break
            
        if not start_block:
            if word_blocks:
                start_block = random.choice(list(word_blocks.values()))
            else:
                return "Нет данных для генерации."
            
        current_block = start_block
        generated_words = [idx_2w[current_block.idx]]
        
        visited_counter = {block.idx: 0 for block in word_blocks.values()}
        visited_counter[current_block.idx] += 1
        
        current_step = 0
        
        while len(generated_words) < max_len:
            current_step += 1
            
            for block in word_blocks.values():
                block.to_forgetting(current_step, forgetting_step=cfg["forget_speed"])
                
            candidates = current_block.output_blocks
            if not candidates:
                break
                
            weights = []
            for cand in candidates:
                affects = cand.to_affect()

                base_weight = affects.get(current_block.idx, cand.epsilon)
                base_weight += cand.epsilon * cfg["temperature"]

                penalty = math.exp(-cfg["loop_penalty"] * visited_counter[cand.idx])
                weights.append(base_weight * penalty)
                
            if sum(weights) == 0:
                weights = [1.0] * len(candidates)
                
            next_block = random.choices(candidates, weights=weights, k=1)[0]
            

            next_block.base_affection += 0.5
            next_block.affection = len(next_block.entered_blocks) + next_block.base_affection
            
            word_str = idx_2w[next_block.idx]
            generated_words.append(word_str)
            
            visited_counter[next_block.idx] += 1
            current_block = next_block
            
            if word_str.endswith('.') or word_str.endswith('!') or word_str.endswith('?') or '[EOS]' in word_str:
                break
        
        answer_sentence = " ".join(generated_words)
        

        clean_answer = answer_sentence.replace('[EOS]', '').replace('[SOS]', '').replace('[NEWS]', '')
        
        return clean_answer.strip().capitalize()
    
    def generate_with_confidence(self, prompt, current_mood, word_blocks, idx_2w, max_len=25):
        cfg = self.cfg_sentiments.get(current_mood, {"temperature": 0.5, "forget_speed": 0.001, "loop_penalty": 1.0})
        
        input_words = prompt.lower().split()
        start_block = None
        
        start_stop_words = {"народ", "вы", "мы", "они", "ты", "я", "что", "как", "где", "когда", "почему","если"}

        for w in input_words:
            clean_w = w.strip("?,.!;\"'")
            if not clean_w: continue
            
            if clean_w in start_stop_words:
                continue

            found_nodes = [block for word, block in word_blocks.items() if clean_w == word.lower()]
            if not found_nodes:
                found_nodes = [block for word, block in word_blocks.items() if clean_w in word.lower()]
                
            if found_nodes:
                start_block = random.choice(found_nodes)
                break
        

        if not start_block and word_blocks:
            meaningful_blocks = [b for w, b in word_blocks.items() if w.lower() not in start_stop_words]
            if meaningful_blocks:
                start_block = random.choice(meaningful_blocks)
            else:
                start_block = random.choice(list(word_blocks.values()))
                
        elif not start_block:
            return "no data", 0.0
        
        current_block = start_block
        generated_words = [] 
        
        visited_counter = {block.idx: 0 for block in word_blocks.values()}
        visited_counter[current_block.idx] += 1
        
        confidence_scores = []
        current_step = 0
        
        while len(generated_words) < max_len:
            current_step += 1
            
            for block in word_blocks.values():
                block.to_forgetting(current_step, forgetting_step=cfg["forget_speed"])
                
            candidates = current_block.output_blocks
            if not candidates:
                break
                
            weights = []
            for cand in candidates:
                affects = cand.to_affect()
                base_weight = affects.get(current_block.idx, cand.epsilon)
                base_weight += cand.epsilon * cfg["temperature"]
                penalty = pow(0.5, visited_counter[cand.idx] * cfg["loop_penalty"])
                weights.append(base_weight * penalty)
                
            if sum(weights) > 0:
                max_w = max(weights)
                confidence_scores.append(max_w / (sum(weights) + 1e-9))
                
            total_w = sum(weights)
            if total_w == 0:
                weights = [1.0] * len(candidates)
                
            next_block = random.choices(candidates, weights=weights, k=1)[0]
            
            next_block.base_affection += 0.5
            next_block.affection = len(next_block.entered_blocks) + next_block.base_affection
            
            word_str = idx_2w[next_block.idx]
            generated_words.append(word_str)
            
            visited_counter[next_block.idx] += 1
            current_block = next_block
            
            if word_str.endswith('.') or word_str.endswith('!') or word_str.endswith('?') or '[EOS]' in word_str:
                break
        
        answer_sentence = " ".join(generated_words)
        clean_answer = answer_sentence.replace('[EOS]', '').replace('[SOS]', '').replace('[NEWS]', '').strip()
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        confidence_pct = min(99, max(10, int(avg_confidence * 100)))
        
        return clean_answer.capitalize(), confidence_pct
    
    
    def save(self, word_blocks, idx_2w, filename="aff.pkl"):
        data = { "word_blocks": word_blocks, "idx_2w": idx_2w}    
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
        print(f"model was saved as {filename}")
        
        
    def load(self, filename="mirpus_model.pkl"):
        if not os.path.exists(filename):
            return None
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
            print(f"succesful {filename}")
            return data["word_blocks"], data["idx_2w"]
        except Exception as e:
            print(f"err: {e}")
            return None


class AffectorSeller:
    def __init__(self):
        self.labels = ("buy", "sell", "hold")
        self.doc_counts = {k: 0 for k in self.labels}
        self.word_counts = {k: {} for k in self.labels}
        self.total_words = {k: 0 for k in self.labels}
        self.vocab = set()

    def scores(self, prompt, news=None, sentiment=None):
        if news is None:
            news = []
        if isinstance(news, str):
            news = [news]

        item = {"replics": [prompt], "news": news, "answer": ""}
        tokens = self._tokenize(self._build_text(item, sentiment=sentiment))

        total_docs = sum(self.doc_counts.values()) or 1
        vocab_size = len(self.vocab) or 1
        scores = {}

        for label in self.labels:
            prior = (self.doc_counts[label] + 1) / (total_docs + len(self.labels))
            score = math.log(prior)
            denom = self.total_words[label] + vocab_size
            wc = self.word_counts[label]
            for tok in tokens:
                score += math.log((wc.get(tok, 0) + 1) / denom)
            scores[label] = score

        return scores

    def _tokenize(self, text):
        if not text:
            return []
        cleaned = []
        for ch in text.lower():
            if ch.isalnum() or ch in ("_", "-", " "):
                cleaned.append(ch)
            else:
                cleaned.append(" ")
        return [t for t in "".join(cleaned).split() if t]

    def _build_text(self, item, sentiment=None):
        replics = item.get("replics", []) or []
        news = item.get("news", []) or []
        answer = item.get("answer", "") or ""
        sent = sentiment
        if sent is None:
            sentiments = item.get("sentiments") or []
            sent = sentiments[0] if sentiments else None
        sent_part = f" [SENTIMENT] {sent} " if sent else " "
        return f'{" ".join(replics)} [NEWS] {" ".join(news)}{sent_part}[ANS] {answer}'

    def train(self, json_file_path, sentiment=None):
        with open(json_file_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)

        for item in dataset:
            if sentiment is not None:
                sentiments = item.get("sentiments") or []
                item_sent = sentiments[0] if sentiments else None
                if item_sent != sentiment:
                    continue

            label = (item.get("decision") or "hold").strip().lower()
            if label not in self.doc_counts:
                label = "hold"

            self.doc_counts[label] += 1
            tokens = self._tokenize(self._build_text(item, sentiment=sentiment))
            wc = self.word_counts[label]
            for tok in tokens:
                self.vocab.add(tok)
                wc[tok] = wc.get(tok, 0) + 1
                self.total_words[label] += 1

        return self

    def predict(self, prompt, news=None, sentiment=None):
        scores = self.scores(prompt=prompt, news=news, sentiment=sentiment)
        return max(scores, key=scores.get)

    def predict_with_confidence(self, prompt, news=None, sentiment=None):
        if news is None:
            news = []
        if isinstance(news, str):
            news = [news]

        item = {"replics": [prompt], "news": news, "answer": ""}
        tokens = self._tokenize(self._build_text(item, sentiment=sentiment))

        total_docs = sum(self.doc_counts.values()) or 1
        vocab_size = len(self.vocab) or 1
        raw = []

        for label in self.labels:
            prior = (self.doc_counts[label] + 1) / (total_docs + len(self.labels))
            score = math.log(prior)
            denom = self.total_words[label] + vocab_size
            wc = self.word_counts[label]
            for tok in tokens:
                score += math.log((wc.get(tok, 0) + 1) / denom)
            raw.append((label, score))

        raw.sort(key=lambda x: x[1], reverse=True)
        best_label, best_score = raw[0]
        second_score = raw[1][1] if len(raw) > 1 else best_score - 10.0

        margin = best_score - second_score
        confidence = int(max(10, min(99, 50 + margin * 12)))
        return best_label, confidence

    def save(self, filename="affector_seller.pkl"):
        data = {
            "labels": self.labels,
            "doc_counts": self.doc_counts,
            "word_counts": self.word_counts,
            "total_words": self.total_words,
            "vocab": self.vocab,
        }
        with open(filename, "wb") as f:
            pickle.dump(data, f)
        print(f"model was saved as {filename}")

    def load(self, filename="affector_seller.pkl"):
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, "rb") as f:
                data = pickle.load(f)
            self.labels = tuple(data.get("labels", self.labels))
            self.doc_counts = data.get("doc_counts", self.doc_counts)
            self.word_counts = data.get("word_counts", self.word_counts)
            self.total_words = data.get("total_words", self.total_words)
            self.vocab = data.get("vocab", self.vocab)
            print(f"succesful {filename}")
            return True
        except Exception as e:
            print(f"err: {e}")
            return False
        