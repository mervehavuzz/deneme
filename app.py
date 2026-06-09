import streamlit as st
from huggingface_hub import InferenceClient
import json
import os
import re
from datetime import datetime

# ─────────────────────────────
# 1. SESSION DB
# ─────────────────────────────
if "browser_db" not in st.session_state:
    st.session_state.browser_db = {}

def load_db():
    return st.session_state.browser_db

def save_db(data):
    st.session_state.browser_db = data


# ─────────────────────────────
# 2. HUKUK DB (DÜZELTİLMİŞ)
# ─────────────────────────────
HUKUK_DB = {
    "yetkisiz_erisim": {"madde": "TCK 243", "aciklama": "Bilişim sistemine hukuka aykırı giriş"},
    "sistem_bozma": {"madde": "TCK 244", "aciklama": "Sistemi engelleme, bozma, veri değiştirme"},
    "veri_calma": {"madde": "TCK 136", "aciklama": "Kişisel verileri hukuka aykırı ele geçirme"},
    "mail_okuma": {"madde": "TCK 132", "aciklama": "Haberleşmenin gizliliğini ihlal"},
    "ifsa": {"madde": "TCK 134", "aciklama": "Özel hayatın gizliliğini ihlal"},
    "santaj": {"madde": "TCK 107", "aciklama": "Şantaj"},
    "tehdit": {"madde": "TCK 106", "aciklama": "Tehdit"},
    "hakaret": {"madde": "TCK 125", "aciklama": "Hakaret"},
    "dolandiricilik": {"madde": "TCK 158/2-f", "aciklama": "Nitelikli dolandırıcılık"},
    "kimlik_taklidi": {"madde": "KİŞİLİK HAKKI İHLALİ", "aciklama": "Sahte profil / isim kullanımı"},
    "sahte_hesap": {"madde": "KİŞİLİK HAKKI İHLALİ", "aciklama": "Sosyal medya kimlik taklidi"},
    "oltalama": {"madde": "TCK 158", "aciklama": "Dolandırıcılık yöntemi (tek başına suç değil)"},
    "tuketici_uyusmazligi": {"madde": "6502", "aciklama": "Ayıplı mal / tüketici uyuşmazlığı"},
    "ozel_hayat_ifsa": {"madde": "TCK 134", "aciklama": "Özel görüntü veya fotoğraf ifşası"},
    "kvkk": {"madde": "KVKK 12", "aciklama": "Veri güvenliği yükümlülüğü"}
}

# ─────────────────────────────
# 3. MEVZUAT
# ─────────────────────────────
MEVZUAT_FALLBACK = {
    "125": "Hakaret suçu...",
    "134": "Özel hayatın gizliliğini ihlal...",
    "136": "Kişisel verilerin hukuka aykırı ele geçirilmesi...",
    "243": "Bilişim sistemine girme...",
    "244": "Sistemi engelleme ve veri değiştirme...",
    "107": "Şantaj suçu...",
    "158": "Nitelikli dolandırıcılık..."
}

def retrieve_mevzuat(maddeler):
    out = []
    for m in maddeler:
        num = re.search(r"\d+", m)
        if num:
            k = num.group()
            if k in MEVZUAT_FALLBACK and MEVZUAT_FALLBACK[k] not in out:
                out.append(MEVZUAT_FALLBACK[k])
    return "\n".join(out) if out else "Mevzuat bulunamadı"


# ─────────────────────────────
# 4. LLM
# ─────────────────────────────
hf_token = st.secrets["HF_TOKEN"]
client = InferenceClient(model="Qwen/Qwen2.5-7B-Instruct", token=hf_token)


SYSTEM_PROMPT = """
Sen Türkiye hukuk sistemi konusunda yardımcı bir analiz asistanısın.

KURAL SETİ:
- Kesin hüküm verme (suçtur/ceza alır YAZMA)
- "değerlendirilebilir" dili kullan
- Aynı bilgiyi tekrar etme
- Uydurma madde yazma
- Mantıksız suç eşleşmesi yapma

MADDE KULLANIM KURALLARI:
- 243 → sadece sisteme yetkisiz giriş
- 244 → sistem/veri manipülasyonu
- 134 → özel hayat ifşası
- 136 → veri ele geçirme
- 158 → dolandırıcılık (gerçek aldatma varsa)
- 125 → hakaret
- 107 → şantaj (para/menfaat varsa)
- 6502 → tüketici uyuşmazlığı (ürün/alışveriş)

FORMAT:
OLAYIN HUKUKİ NİTELİĞİ
OLASI SUÇ VE İHLALLER
HUKUKİ DEĞERLENDİRME
PRATİK ADIMLAR
BAŞVURU YOLLARI
"""


def call_llm(prompt):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    res = client.chat_completion(messages=messages, max_tokens=1200, temperature=0.2)
    return res.choices[0].message.content


# ─────────────────────────────
# 5. PIPELINE
# ─────────────────────────────
def run_pipeline(user_query):

    class_prompt = f"""
Senaryo: {user_query}

Şu etiketlerden uygun olanları seç:
{list(HUKUK_DB.keys())}

SADECE JSON:
{{"etiketler": []}}
"""

    raw = call_llm(class_prompt)

    try:
        tags = json.loads(re.search(r"\{.*\}", raw).group(0))["etiketler"]
    except:
        tags = []

    maddeler = []
    for t in tags:
        if t in HUKUK_DB:
            maddeler.append(HUKUK_DB[t]["madde"])

    maddeler = list(dict.fromkeys(maddeler))

    mevzuat = retrieve_mevzuat(maddeler)

    final_prompt = f"""
Olay: {user_query}

İlgili maddeler: {maddeler}

Mevzuat:
{mevzuat}

Sadece verilen olayla doğrudan ilişkili maddeleri kullan.
Emin değilsen madde yazma.

Analiz yap.
"""

    return call_llm(final_prompt)


# ─────────────────────────────
# 6. STREAMLIT UI
# ─────────────────────────────
st.set_page_config(page_title="Siber Hukuk Analiz Sistemi", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
.stApp { background: #F8F7FF !important; }

/* Sidebar Genel Arka Planı */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #5B2FD9 0%, #7C3FFC 40%, #6A2EE8 100%) !important;
}

/* Sidebar İçindeki Normal Başlık ve Düz Metinlerin Beyaz Kalması */
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] div { 
    color: white !important; 
}

/* Sidebar İçindeki Butonların Yazı Fontunun Siyah Yapılması */
[data-testid="stSidebar"] button p {
    color: #1A1A1A !important;
    font-weight: 500 !important;
}

/* Mesaj Balonları */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #7C5CFC !important; border-radius: 15px 15px 5px 15px !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: white !important; border: 1px solid #E4E0FF !important; border-radius: 5px 15px 15px 15px !important;
}
</style>
""", unsafe_allow_html=True)
db = load_db()

if "chat_id" not in st.session_state:
    st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")

if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Siber Hukuk Analiz Sistemi")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Senaryoyu yaz"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        answer = run_pipeline(prompt)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

    db[st.session_state.chat_id] = st.session_state.messages
    save_db(db)

