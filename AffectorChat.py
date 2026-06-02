import math
import random
import time
import json
from Affectors import AffectionBlock, AffectorText

word_blocks = {}
idx_2w = {}
unique_words = []

aff = AffectorText(0, entered_blocks=[], output_blocks=[], base_affection=1, epsilon=0.0001)
aff.train_on_text(r'Affectors\AffectorDataset.json', word_blocks, idx_2w, unique_words)

MOODS = ["оптимист", "рискованный", "систематичный", "консерватист", "интроверт", "убежденный", "интуитивный"]

MOOD_NAMES = {
    "оптимист": "Оптимист",
    "рискованный": "Рискованный",
    "систематичный": "Систематичный",
    "консерватист": "Консерватист",
    "интроверт": "Интроверт",
    "убежденный": "Убеждённый",
    "интуитивный": "Интуитивный"
}


chat_log = []

def save_chat_to_json(filename="chat_history.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(chat_log, f, ensure_ascii=False, indent=4)
    print(f'chat saved as {filename}')
    
def print_messenger_message(sender_mood, text, confidence, timestamp=None):
    if timestamp is None:
        timestamp = time.strftime("%H:%M:%S")
    
    name = MOOD_NAMES.get(sender_mood, sender_mood)
    
    if confidence >= 75:
        conf_icon = ":)"
    elif confidence >= 50:
        conf_icon = ":/"
    else:
        conf_icon = ":("
        
    print(f"[{timestamp}] {name}")
    print(f"{conf_icon} уверенность ответа: {confidence}%")
    print(f"MSG: {text}")
    print('\n')
    
    message_entry = {
        "timestamp": timestamp,
        "sender_mood": sender_mood,
        "sender_name": name,
        "text": text,
        "confidence": confidence
    }
    chat_log.append(message_entry)

def run_chat_simulation(affector_instance, initial_prompt, participants, turns=6):
    global chat_log
    chat_log = []
    
    start_timestamp = time.strftime("%H:%M:%S")
    chat_log.append({
        "timestamp": start_timestamp,
        "sender_mood": "system",
        "sender_name": "System",
        "text": initial_prompt,
        "confidence": 100
    })
    
    recent_history = [initial_prompt]
    
    for turn in range(turns):
        current_mood = participants[turn % len(participants)]
        context_for_generation = " ".join(recent_history[-2:]) 
        
        response, confidence = affector_instance.generate_with_confidence(
            prompt=context_for_generation,
            current_mood=current_mood,
            word_blocks=word_blocks,
            idx_2w=idx_2w,
            max_len=32
        )
        
        print_messenger_message(current_mood, response, confidence)
        recent_history.append(response)
        if len(recent_history) > 2:
            recent_history.pop(0)
            
        time.sleep(0.1)
        
START_PROMPT = "Народ вы видели что ркн заблокали?"

CHAT_PARTICIPANTS = [
    "оптимист", 
    "систематичный",
    "интуитивный",  
    "консерватист", 
    "рискованный",
    "убежденный"
]

run_chat_simulation(
    affector_instance=aff,
    initial_prompt=START_PROMPT,
    participants=CHAT_PARTICIPANTS,
    turns=64
)

save_chat_to_json("affectors_chat_session.json")