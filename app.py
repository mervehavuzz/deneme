import streamlit as st
from huggingface_hub import InferenceClient
import json
import os
from datetime import datetime

# ─────────────────────────────────────────
# SAYFA AYARI
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Siber Hukuk Asistanı",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────
# VERİTABANI
# ─────────────────────────────────────────
DB_FILE = "chat_history.json"

def load_db() -> dict:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    return {}

def save_db(data: dict) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_current() -> None:
    db = load_db()
    db[st.session_state.chat_id] = st.session_state.messages
    save_db(db)

# ─────────────────────────────────────────
# API & MODEL (YENİ MODEL: LLAMA 3.1)
# ─────────────────────────────────────────
SYSTEM_PROMPT = """Sen uzman bir 'Siber Hukuk Analiz Motoru'sun. Görevin KVKK ve Siber Güvenlik hukuku çerçevesinde analiz yapmaktır.

ANALİZ ADIMLARI:
1. Olay Özeti: Olayı hukuki kavramlarla (Veri sorumlusu, veri işleyen, veri ihlali vb.) kısaca tanımla.
2. Hukuki Değerlendirme: 
   - Hangi KVKK maddesi ihlal edildi? (Örn: 5. madde işleme şartları, 12. madde veri güvenliği)
   - Veri sorumlusunun (Şirket) buradaki ihmali nedir?
3. Sorumluluk Analizi: Kişisel kusur (çalışan) ve kurumsal sorumluluk (şirket) ayrımını yap.
4. Teknik ve İdari Önlemler: Somut tavsiyeler ver.

KRİTİK KURALLAR:
- Kesinlikle 'Hukuka aykırı eylem'i (zarar verme, çalma vb.) bir meşru menfaat olarak tanımlama!
- Eğer çalışan başka birinin e-postasına giriyorsa bu 'Haberleşmenin Gizliliğini İhlal' (TCK 132) ve 'Verileri Hukuka Aykırı Ele Geçirme' (TCK 136) suçudur. Analizine bunları da ekle.
- Şirketin olayı kayıt altına almaması bir 'Veri İhlal Bildirimi' (KVKK 12/5) yükümlülüğü ihlalidir.
- Cevapların akademik, ciddi ve maddeler halinde olsun. Gereksiz tekrardan kaçın."""

try:
    hf_token = st.secrets["HF_TOKEN"]
    # Daha güçlü bir model olan Llama 3.1 8B'ye geçiyoruz
    _model_id = "meta-llama/Llama-3.1-8B-Instruct" 
    client = InferenceClient(model=_model_id, token=hf_token)
except Exception as e:
    st.error(f"API Bağlantı Hatası: {e}")
    st.stop()

# ─────────────────────────────────────────
# YARDIMCILAR
# ─────────────────────────────────────────
def stream_response(prompt: str, placeholder) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in st.session_state.messages:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": prompt})

    text = ""
    try:
        for message in client.chat_completion(
            messages=messages,
            max_tokens=2000,
            stream=True,
            temperature=0.5, # Biraz daha dengeli bir yaratıcılık
            top_p=0.9
        ):
            token = message.choices[0].delta.content
            if token:
                text += token
                placeholder.markdown(text + "▌")
    except Exception as e:
        placeholder.error(f"⚠️ Hata: {e}")
        return "Yanıt üretilemedi."

    placeholder.markdown(text)
    return text

# [Sidebar ve Diğer Arayüz Kodları Aynı Kalacak Şekilde Devam Ediyor...]
# (Kodun geri kalanı öncekiyle aynı, sadece yukarıdaki model ve prompt kısmını güncelledim)
