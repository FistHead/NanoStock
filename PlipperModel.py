import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset,DataLoader
import math

import json
from torch.utils.data import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

device_name = 'cuda' if torch.cuda.is_available() else 'cpu'
print(device_name)
text_model_name = "Qwen/Qwen3-0.6B"
tokenizer = AutoTokenizer.from_pretrained(text_model_name)
txt_model = AutoModelForCausalLM.from_pretrained(
    text_model_name,
    torch_dtype=torch.float32
).to(device_name)

class Plipper(nn.Module):
    def __init__(self, text_model, emotions_size, sentiments_size, stock_features_size, decisions_size):
        super().__init__()
        self.txt_mod = text_model
        self.emb_size = 1024
        
        self.dropout = nn.Dropout(0.2)
        
        agent_state_size = self.emb_size + sentiments_size
        
        self.emotions_layer = nn.Sequential(
            nn.Linear(agent_state_size, (self.emb_size + sentiments_size)//2),
            nn.Sigmoid(),
            nn.Linear((self.emb_size + sentiments_size)//2, emotions_size)
        )
        
        scoring_input_size = agent_state_size + stock_features_size
        
        self.decision_layer = nn.Linear(agent_state_size, decisions_size)
        
        self.stocks_scoring = nn.Sequential(
            nn.Linear(scoring_input_size, scoring_input_size//2),
            nn.ReLU(),
            nn.Linear(scoring_input_size//2, 1)
        )
        
    def forward(self, input_ids, attention_mask, sentiments, stocks_data):
        
        outputs = self.txt_mod(input_ids=input_ids, attention_mask=attention_mask,output_hidden_states=True)
        
        lm_logits = outputs.logits
        last_hidden_states = outputs.hidden_states[-1]
        batch_size = input_ids.shape[0]
        sequence_lengths = attention_mask.sum(dim=1) - 1
        
        text_embeddings = last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]
        
        agent_state = torch.cat([text_embeddings, sentiments], dim=1)
        agent_state = self.dropout(agent_state)
        
        emotion_logits = self.emotions_layer(agent_state)
        decisions_logits = self.decision_layer(agent_state)
        
        num_stocks = stocks_data.shape[1]
        agent_state_expanded = agent_state.unsqueeze(1).expand(-1, num_stocks, -1)
        combined_stocks = torch.cat([agent_state_expanded, stocks_data], dim=2)
        stock_scores = self.stocks_scoring(combined_stocks)
        stock_scores = stock_scores.squeeze(-1)
    
        return lm_logits, emotion_logits, stock_scores, decisions_logits
    
class MainDataset(Dataset):
    def __init__(self, json_data, tokenizer, max_length=256):
        self.data = json_data
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # словари для перевода текста в числа
        self.trend_mapping = {"рост": 1.0, "флэт": 0.0, "падение": -1.0}
        

        self.sector_mapping = {}
        sector_idx = 0
        for item in self.data:
            for stock_info in item['stocks_states'].values():
                sector = stock_info[0]
                if sector not in self.sector_mapping:
                    self.sector_mapping[sector] = sector_idx
                    sector_idx += 1

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        events_str = ", ".join(item['events'])
        messages_str = " | ".join(item['messages'])
        
        prompt = f"События: {events_str}\nЧат: {messages_str}\nТактика: {item['tactic']}\nМысли:"
        full_text = prompt + " " + item['answer'] + self.tokenizer.eos_token
        
        encoding = self.tokenizer(
            full_text,
            padding='max_length',
            truncation=True,
            max_length=self.max_length,
            return_tensors='pt'
        )

        sentiments = torch.tensor(item['basic_sentiments_parameters'], dtype=torch.float32)
        stocks_tensor_list = []
        target_stock_idx = 0
        
        for i, (stock_name, stock_info) in enumerate(item['stocks_states'].items()):
            sector_str, price, trend_str, vol = stock_info
            
            # Оцифровка
            sector_num = float(self.sector_mapping[sector_str])
            trend_num = self.trend_mapping.get(trend_str, 0.0)
            

            stock_features = [sector_num, price, trend_num, vol]
            stocks_tensor_list.append(stock_features)
            

            if stock_name == item['target_stock']:
                target_stock_idx = i
                
        stocks_tensor = torch.tensor(stocks_tensor_list, dtype=torch.float32)

        target_emotions = torch.tensor(item['emotions'], dtype=torch.float32)
        target_decisions = torch.tensor(item['decisions'], dtype=torch.float32)
        target_stock_idx_tensor = torch.tensor(target_stock_idx, dtype=torch.long)

        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'sentiments': sentiments,
            'stocks_data': stocks_tensor,
            # таргеты для обучения:
            'target_emotions': target_emotions,
            'target_decisions': target_decisions,
            'target_stock_idx': target_stock_idx_tensor
        }
        
emotions_size = 3
sentiments_size = 7
stock_features_size = 4
decisions_size = 3 

model = Plipper(
    text_model=txt_model,
    emotions_size=emotions_size,
    sentiments_size=sentiments_size,
    stock_features_size=stock_features_size,
    decisions_size=decisions_size
).to(device_name)

with open('MipleDataset.json', 'r', encoding='utf-8') as f:
    raw_json_data = json.load(f)


dataset = MainDataset(
    json_data=raw_json_data, 
    tokenizer=tokenizer, 
    max_length=256
)

dataloader = DataLoader(
    dataset, 
    batch_size=4, 
    shuffle=True,
    drop_last=False
)

def predict(model, tokenizer, prompt_text, current_sentiments, current_stocks, max_new_tokens=50):
    model.eval()
    with torch.no_grad():
        inputs = tokenizer(prompt_text, return_tensors='pt').to(device_name)
        input_ids = inputs['input_ids']
        attention_mask = inputs['attention_mask']
        
        sentiments = torch.tensor([current_sentiments], dtype=torch.float32).to(device_name)
        stocks_data = torch.tensor([current_stocks], dtype=torch.float32).to(device_name)

        lm_logits, emotion_logits, stock_scores, decisions_logits = model(
            input_ids, attention_mask, sentiments, stocks_data
        )
        
        predicted_emotions = emotion_logits[0].cpu().numpy()
        predicted_decisions = decisions_logits[0].cpu().numpy()
        

        best_stock_idx = torch.argmax(stock_scores[0]).item()


        generated_ids = input_ids.clone()
        
        for _ in range(max_new_tokens):
            attention_mask = torch.ones_like(generated_ids).to(device_name)
            outputs = model(generated_ids, attention_mask, sentiments, stocks_data)
            lm_logits = outputs[0]
            
            next_token_logits = lm_logits[:, -1, :] 
            

            next_token = torch.argmax(next_token_logits, dim=-1).unsqueeze(0)
            
            generated_ids = torch.cat([generated_ids, next_token], dim=1)
            
            if next_token.item() == tokenizer.eos_token_id:
                break
                
        prompt_length = input_ids.shape[1]
        generated_text = tokenizer.decode(generated_ids[0][prompt_length:], skip_special_tokens=True)
        
        return {
            "text_response": generated_text.strip(),
            "emotions": predicted_emotions,
            "decisions": predicted_decisions,
            "selected_stock_idx": best_stock_idx
        }