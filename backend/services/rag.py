import requests
import numpy as np
import os

# Ayurveda + Yoga knowledge base
KNOWLEDGE_BASE = [
    # Doshas
    {
        "content": """Vata dosha is associated with movement, air, and space. 
        People with Vata imbalance often experience anxiety, stress, insomnia, 
        lower back pain, and irregular digestion. To balance Vata: warm, 
        grounding foods like soups, stews, root vegetables, ghee, and warm milk 
        are recommended. Avoid cold, raw, and dry foods. Gentle yoga poses like 
        Child's Pose, Cat-Cow, and Legs Up The Wall are ideal.""",
        "metadata": {"topic": "vata", "category": "dosha"}
    },
    {
        "content": """Pitta dosha is associated with fire and water. 
        Pitta imbalance causes inflammation, irritability, acid reflux, 
        skin rashes, and burnout. To balance Pitta: cooling foods like 
        cucumber, coconut water, leafy greens, sweet fruits, and dairy 
        are recommended. Avoid spicy, oily, and fermented foods. 
        Cooling yoga poses like Moon Salutation, Forward Folds, and 
        Seated Twists are beneficial.""",
        "metadata": {"topic": "pitta", "category": "dosha"}
    },
    {
        "content": """Kapha dosha is associated with earth and water. 
        Kapha imbalance leads to weight gain, lethargy, depression, 
        congestion, and slow metabolism. To balance Kapha: light, 
        warm, and spiced foods like ginger tea, legumes, and bitter 
        greens are recommended. Avoid heavy, sweet, and oily foods. 
        Energizing yoga poses like Sun Salutation, Warrior poses, 
        and Backbends are ideal.""",
        "metadata": {"topic": "kapha", "category": "dosha"}
    },

    # Yoga for conditions
    {
        "content": """For anxiety and stress relief in Ayurveda, 
        Pranayama breathing is essential. Nadi Shodhana (alternate 
        nostril breathing) balances the nervous system. Bhramari 
        (humming bee breath) calms the mind instantly. 
        Ashwagandha, Brahmi, and Shankhpushpi are Ayurvedic herbs 
        known to reduce cortisol and support mental clarity.""",
        "metadata": {"topic": "anxiety", "category": "condition"}
    },
    {
        "content": """For back pain, Ayurveda recommends Mahanarayan 
        oil massage (Abhyanga) on the affected area. Yoga poses that 
        help: Cat-Cow Pose for spinal mobility, Child's Pose for 
        lumbar release, Supine Twist for spinal decompression, 
        Bridge Pose for strengthening the lower back muscles. 
        Avoid forward folds with straight legs if pain is acute.""",
        "metadata": {"topic": "back_pain", "category": "condition"}
    },
    {
        "content": """For poor sleep quality, Ayurveda recommends 
        establishing a consistent sleep routine (Dinacharya). 
        Warm milk with ashwagandha and nutmeg before bed promotes 
        sleep. Abhyanga (self-massage) with sesame oil on feet 
        calms the nervous system. Yoga Nidra (yogic sleep) is the 
        most powerful practice for sleep disorders. 
        Avoid screens and stimulating activity 1 hour before bed.""",
        "metadata": {"topic": "sleep", "category": "condition"}
    },
    {
        "content": """For weight management and fat loss, Ayurveda 
        recommends eating the largest meal at lunch when digestive 
        fire (Agni) is strongest. Triphala taken at night aids 
        digestion and detoxification. Avoid eating after sunset. 
        Kapalabhati pranayama stimulates metabolism. Dynamic yoga 
        styles like Vinyasa and Power Yoga are recommended. 
        Warm water with lemon and ginger in the morning boosts Agni.""",
        "metadata": {"topic": "weight_loss", "category": "condition"}
    },
    {
        "content": """For flexibility improvement, Ayurveda recommends 
        daily Abhyanga (oil massage) before yoga to warm and lubricate 
        joints. Sesame oil is warming and ideal for Vata types. 
        Coconut oil is cooling and ideal for Pitta types. 
        Yin Yoga held for 3-5 minutes per pose deeply stretches 
        connective tissue. Poses: Pigeon Pose, Butterfly, Seated 
        Forward Fold, and Lizard Pose are most effective for 
        full-body flexibility.""",
        "metadata": {"topic": "flexibility", "category": "condition"}
    },

    # Diet principles
    {
        "content": """Ayurvedic dietary principles state that food 
        should be fresh, seasonal, and locally grown. Six tastes 
        (Shadrasas) should be present in every meal: sweet, sour, 
        salty, pungent, bitter, and astringent. This ensures 
        complete nutrition and satisfaction. Eating in a calm 
        environment without distractions aids digestion. 
        Drinking warm water throughout the day flushes toxins (Ama).""",
        "metadata": {"topic": "diet_principles", "category": "diet"}
    },
    {
        "content": """Anti-inflammatory foods recommended in Ayurveda: 
        Turmeric (Haridra) — most powerful anti-inflammatory, 
        Ginger (Shunthi) — aids digestion and reduces pain, 
        Amla (Indian Gooseberry) — highest natural Vitamin C, 
        Tulsi (Holy Basil) — adaptogen for stress, 
        Neem — blood purifier, 
        Brahmi — brain tonic for memory and focus. 
        These can be taken as teas, powders, or in cooking.""",
        "metadata": {"topic": "superfoods", "category": "diet"}
    },

    # Meditation
    {
        "content": """Ayurvedic meditation practices include 
        Trataka (candle gazing) for improving focus and eye health, 
        Mantra meditation using beej mantras like Om, Aim, Hrim 
        for different intentions, Yoga Nidra for deep relaxation 
        and stress recovery, and Mindfulness of breath (Anapanasati) 
        for anxiety management. Morning meditation during Brahma Muhurta 
        (4-6 AM) is considered most powerful in Ayurveda.""",
        "metadata": {"topic": "meditation", "category": "practice"}
    },
    {
        "content": """Seasonal wellness (Ritucharya) in Ayurveda: 
        Spring (Vasanta) — detox season, light foods, active yoga. 
        Summer (Grishma) — cooling foods, restorative yoga, hydration. 
        Monsoon (Varsha) — strengthen immunity, warm foods, gentle yoga. 
        Autumn (Sharada) — balance Pitta, bitter foods, calming practices. 
        Winter (Hemanta/Shishira) — nourishing foods, vigorous yoga, 
        oil massage to stay warm and energized.""",
        "metadata": {"topic": "seasonal", "category": "lifestyle"}
    }
]


HF_TOKEN = os.getenv("HF_TOKEN")

API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

headers = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

# 🔹 Get embedding from HuggingFace API
def get_embedding(text):
    response = requests.post(
        API_URL,
        headers=headers,
        json={"inputs": text}
    )
    return response.json()[0]


# 🔹 Precompute embeddings once
DOCUMENTS = [item["content"] for item in KNOWLEDGE_BASE]
DOC_EMBEDDINGS = [get_embedding(doc) for doc in DOCUMENTS]


# 🔹 Cosine similarity
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# 🔹 Retrieve relevant context
def retrieve_ayurveda_context(query: str, k: int = 3) -> str:
    query_embedding = get_embedding(query)

    scores = [
        cosine_similarity(query_embedding, emb)
        for emb in DOC_EMBEDDINGS
    ]

    top_indices = np.argsort(scores)[-k:][::-1]

    context = "\n\n".join([DOCUMENTS[i] for i in top_indices])
    return context
