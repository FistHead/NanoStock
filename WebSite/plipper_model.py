import torch
import torch.nn as nn


class Plipper(nn.Module):
    def __init__(self, text_model, emotions_size, sentiments_size, stock_features_size, decisions_size):
        super().__init__()
        self.txt_mod = text_model
        self.emb_size = 1024
        self.dropout = nn.Dropout(0.2)
        agent_state_size = self.emb_size + sentiments_size
        self.emotions_layer = nn.Sequential(
            nn.Linear(agent_state_size, (self.emb_size + sentiments_size) // 2),
            nn.Sigmoid(),
            nn.Linear((self.emb_size + sentiments_size) // 2, emotions_size),
        )
        scoring_input_size = agent_state_size + stock_features_size
        self.decision_layer = nn.Linear(agent_state_size, decisions_size)
        self.stocks_scoring = nn.Sequential(
            nn.Linear(scoring_input_size, scoring_input_size // 2),
            nn.ReLU(),
            nn.Linear(scoring_input_size // 2, 1),
        )

    def forward(self, input_ids, attention_mask, sentiments, stocks_data):
        outputs = self.txt_mod(input_ids=input_ids, attention_mask=attention_mask, output_hidden_states=True)
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
        stock_scores = self.stocks_scoring(combined_stocks).squeeze(-1)
        return lm_logits, emotion_logits, stock_scores, decisions_logits
