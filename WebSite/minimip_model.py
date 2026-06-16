import math

import torch
import torch.nn as nn


class SelfAttention(nn.Module):
    def __init__(self, embed_size, heads):
        super().__init__()
        self.embed_size = embed_size
        self.heads = heads
        self.head_dim = embed_size // heads
        self.qkv = nn.Linear(embed_size, embed_size * 3)
        self.fc_out = nn.Linear(embed_size, embed_size)

    def forward(self, x):
        B, T, C = x.shape
        qkv = self.qkv(x)
        qkv = qkv.reshape(B, T, 3, self.heads, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        mask = torch.tril(torch.ones(T, T)).to(x.device)
        scores = scores.masked_fill(mask == 0, float("-inf"))
        attn = torch.softmax(scores, dim=-1)
        out = attn @ v
        out = out.transpose(1, 2).reshape(B, T, C)
        return self.fc_out(out)


class Block(nn.Module):
    def __init__(self, embed_size, heads, dropout=0.1):
        super().__init__()
        self.attn = SelfAttention(embed_size, heads)
        self.ln1 = nn.LayerNorm(embed_size)
        self.ff = nn.Sequential(
            nn.Linear(embed_size, 4 * embed_size),
            nn.GELU(),
            nn.Linear(4 * embed_size, embed_size),
            nn.Dropout(dropout),
        )
        self.ln2 = nn.LayerNorm(embed_size)

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        x = x + self.ff(self.ln2(x))
        return x


class MiniMip(nn.Module):
    def __init__(self, vocab_size, embedding_dim=256, n_heads=4, block_size=256, n_layers=4, sentimens_count=7, emotions_count=3):
        super().__init__()
        self.block_size = block_size
        self.stock_signs_count = 2
        self.token_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.pos_embedding = nn.Embedding(block_size, embedding_dim)

        self.combined_emb = embedding_dim + self.stock_signs_count + sentimens_count
        self.emo_layer = nn.Linear(self.combined_emb, emotions_count)

        self.stock_selector = nn.Sequential(
            nn.Linear(self.stock_signs_count + sentimens_count, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
        )

        self.decision_layer = nn.Linear(self.combined_emb + emotions_count, 3)

        self.count_selector = nn.Sequential(
            nn.Linear(self.combined_emb, self.combined_emb // 2),
            nn.ReLU(),
            nn.Linear(self.combined_emb // 2, 1),
        )

        self.blocks = nn.Sequential(*[Block(embedding_dim, n_heads) for _ in range(n_layers)])

        self.l_norm = nn.LayerNorm(embedding_dim)
        self.txt_fc = nn.Linear(embedding_dim, vocab_size)

    def forward(self, text, stocks_data, sentiment_data):
        B, T = text.shape
        pos = torch.arange(T, device=text.device)
        pos_emb = self.pos_embedding(pos)
        token_emb = self.token_embedding(text)

        txt = token_emb + pos_emb
        txt = self.blocks(txt)
        txt_features = self.l_norm(txt)
        txt_logits = self.txt_fc(txt_features)

        stocks_mean = stocks_data.mean(dim=1)
        stocks_b = stocks_mean.unsqueeze(1).expand(-1, T, -1)
        combined = torch.cat([txt_features, stocks_b, sentiment_data], dim=-1)

        emo = self.emo_layer(combined)
        count = self.count_selector(combined)

        n_stocks = stocks_data.shape[1]
        sent = sentiment_data[:, 0, :]
        sent_rep = sent.unsqueeze(1).expand(-1, n_stocks, -1)
        stock_feat = torch.cat([stocks_data, sent_rep], dim=-1)
        stock = self.stock_selector(stock_feat).squeeze(-1)

        decision_features = torch.cat([combined, emo], dim=-1)
        decision = self.decision_layer(decision_features)

        return txt_logits, stock, count, decision, emo

    def generate(self, tokenizer, max_len, data, min_new=5, temperature=0.8, max_stocks=8):
        tokenizer.no_padding()
        device = next(self.parameters()).device
        msg_sep = data.get("message_sep", "[MESSAGE]")
        news_sep = data.get("news_sep", "[NEWS]")
        sos_id = tokenizer.token_to_id("[SOS]")
        eos_id = tokenizer.token_to_id("[EOS]")
        pad_id = tokenizer.token_to_id("[PAD]")

        messages = msg_sep.join(data["messages"]) if data["messages"] else ""
        news = news_sep.join(data["news"]) if data["news"] else ""
        text = f"{messages} {news} [SOS]".strip()

        sentiment_vector = data["sentiment"]
        sd = data["stocks_data"]
        sd_keys = list(sd.keys())
        rows = [sd[k] for k in sd_keys]
        while len(rows) < max_stocks:
            rows.append([0.0, 0.0])
        stocks_tensor = torch.tensor([rows[:max_stocks]], dtype=torch.float32, device=device)
        sentiment_tensor = torch.tensor([sentiment_vector], dtype=torch.float32, device=device)

        ids = tokenizer.encode(text).ids
        x = torch.tensor([ids], dtype=torch.long, device=device)
        T = x.shape[1]
        sentiment_exp = sentiment_tensor.unsqueeze(1).expand(-1, T, -1)

        with torch.no_grad():
            txt_logits, stock_logits, count_pred, decision_pred, emo_pred = self(x, stocks_tensor, sentiment_exp)
            chosen_idx = stock_logits[0, :len(sd_keys)].argmax().item()
            selected_key = sd_keys[chosen_idx]
            decision_logits = decision_pred[0].mean(dim=0)

        generated = ids.copy()
        for step in range(max_len):
            x = torch.tensor([generated], dtype=torch.long, device=device)
            T = x.shape[1]
            if T >= self.block_size:
                break
            sentiment_exp = sentiment_tensor.unsqueeze(1).expand(-1, T, -1)
            with torch.no_grad():
                txt_logits, _, _, _, _ = self(x, stocks_tensor, sentiment_exp)
            logits = txt_logits[0, -1].clone()
            for bad_id in (sos_id, pad_id):
                if bad_id is not None:
                    logits[bad_id] = float("-inf")
            if step < min_new and eos_id is not None:
                logits[eos_id] = float("-inf")
            if temperature > 0:
                probs = torch.softmax(logits / temperature, dim=-1)
                next_id = torch.multinomial(probs, 1).item()
            else:
                next_id = logits.argmax().item()
            generated.append(next_id)
            if next_id == eos_id:
                break

        start = generated.index(sos_id) + 1
        answer_ids = []
        for tid in generated[start:]:
            if tid == eos_id:
                break
            answer_ids.append(tid)

        answer = tokenizer.decode(answer_ids)
        return answer, selected_key, stock_logits[0, :len(sd_keys)].tolist(), decision_logits
