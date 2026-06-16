import math

import torch
import torch.nn as nn

# архитектура повторяет MipleModel из ноутбука, чтобы загрузить чекпоинт mrplip_17M_3


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


class MipleModel(nn.Module):
    def __init__(self, vocab_size, embed_size, block_size, heads, decisions_count, emotions_count, market_features, sentiments_count, tactics_count, n_layers, dropout=0.2):
        super().__init__()
        self.dropout = nn.Dropout(0.2)
        self.block_size = block_size
        self.token_embed = nn.Embedding(vocab_size, embed_size)
        self.pos_embed = nn.Embedding(block_size, embed_size)

        self.blocks = nn.Sequential(*[Block(embed_size, heads, dropout) for _ in range(n_layers)])

        self.market_proj = nn.Linear(market_features, embed_size)
        self.sent_proj = nn.Linear(sentiments_count, embed_size)

        combined_input_size = (embed_size * 3) + emotions_count + sentiments_count

        self.buy_decision = nn.Sequential(
            nn.Linear(combined_input_size, embed_size),
            nn.ReLU(),
            nn.Linear(embed_size, embed_size),
            nn.Linear(embed_size, decisions_count),
        )

        self.emotions_choicer = nn.Linear(combined_input_size, emotions_count)
        self.tactic_choicer = nn.Linear(combined_input_size, tactics_count)


        self.stock_selector = nn.Sequential(
            nn.Linear(embed_size * 2, embed_size),
            nn.ReLU(),
            nn.Linear(embed_size, 1),
        )

        self.ln_f = nn.LayerNorm(embed_size)
        self.fc = nn.Linear(embed_size, vocab_size)

    def forward(self, market_seq, prompt_seq, news_seq, current_emotions, sentiments_config):
        B, T = prompt_seq.shape

        token_embeddings = self.token_embed(prompt_seq)
        position_embeddings = self.pos_embed(torch.arange(T, device=prompt_seq.device))
        x = token_embeddings + position_embeddings
        x = self.blocks(x)

        market_emb = self.market_proj(market_seq)
        news_emb = self.token_embed(news_seq)

        market_emb_mean = torch.mean(market_emb, dim=1)
        news_emb_mean = torch.mean(news_emb, dim=1)
        x_mean = torch.mean(x, dim=1)

        sent_emb = self.sent_proj(sentiments_config)

        combined = torch.cat((x_mean, market_emb_mean, news_emb_mean, current_emotions, sentiments_config), dim=1)

        trade_logits = self.buy_decision(combined)
        trade_logits = self.dropout(trade_logits)
        new_emotions = self.emotions_choicer(combined)
        new_emotions = self.dropout(new_emotions)

        tactic_logits = self.tactic_choicer(combined)
        tactic_logits = self.dropout(tactic_logits)

        n_stocks = market_emb.shape[1]
        sent_rep = sent_emb.unsqueeze(1).expand(-1, n_stocks, -1)
        stock_feat = torch.cat((market_emb, sent_rep), dim=2)
        stock_logits = self.stock_selector(stock_feat).squeeze(-1)
        stock_logits = self.dropout(stock_logits)

        x_norm = self.ln_f(x)
        text_logits = self.fc(x_norm)

        return trade_logits, new_emotions, tactic_logits, stock_logits, text_logits
