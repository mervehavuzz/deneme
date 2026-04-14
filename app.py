import streamlit as st
from huggingface_hub import InferenceClient
import json
import os
from datetime import datetime

# ─────────────────────────────────────────
# 1. SAYFA AYARI VE GÖRSEL TASARIM (UI)
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Siber Hukuk Analiz Sistemi",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# 2. VERİTABANI İŞLEMLERİ (JSON)
# ─────────────────────────────────────────
DB_FILE = "chat_history.json"

def load_db() -> dict:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def save_db(data: dict) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────
# 3. KURAL MOTORU VE MANTIKSAL ÇERÇEVE (RULE ENGINE)
# ─────────────────────────────────────────
# Modelin uydurmasını engellemek için kuralları çok net ve kısa tutuyoruz.
BASE_RULES = """Sen bir Siber Hukuk Sınıflandırma ve Karar Motorusun. 'Yorum yapan avukat' gibi değil, 'net karar veren bir hakim' gibi davran.
Asla bu formatın dışına çıkma:
**OLAY:** (1 Cümle)
**SINIFLANDIRMA:** (Sadece Biri: TCK SUÇU / KVKK İDARİ İHLAL / HUKUKA UYGUN)
**İLGİLİ MADDELER:** (Sadece Kanun/Madde Numaraları)
**HUKUKİ GEREKÇE:** (Kısa analiz)
**SONUÇ VE AKSİYON:** (Net tavsiye)"""

def pre_process_query(text: str) -> dict:
    """Kullanıcı metnini Python'da tarayıp LLM'e gidecek gizli direktifi belirler."""
    text_lower = text.lower()
    crime_keywords = ["hack", "izinsiz", "çal", "ele geçir", "sızdır", "şifre", "kopyala", "gizlice"]
    
    is_crime = any(kw in text_lower for kw in crime_keywords)
    
    if is_crime:
        directive = "DİKKAT: Bu olayda 'Yetkisiz Erişim / Veri Çalma' tespiti yapıldı. KVKK 5/2 (Meşru Menfaat vb.) ŞARTLARINI ASLA TARTIŞMA. Doğrudan TCK 136, 132 veya 244 kapsamında SUÇ olarak sınıflandır."
    else:
        directive = "DİKKAT: Bu bir kurumsal veri işleme/profilleme vakasıdır. KVKK Madde 5/2 kapsamında 'Ölçülülük' ve 'Denge Testi' (Kullanıcı mahremiyeti vs. Şirket Karı) analizi yap. Otomatik karar verme (Madde 11) boyutunu atlama."
        
    return {"is_crime": is_crime, "directive": directive}

def post_process_validator(llm_output: str, is_crime: bool) -> str:
    """LLM'in çıktısını ekrana basmadan önce son kez denetler (Hard Validator)"""
    output_lower = llm_output.lower()
    
    # Kural 1: Suç olan yerde meşru menfaat geçiyorsa sansürle/düzelt
    if is_crime and "meşru menfaat" in output_lower:
        return llm_output + "\n\n> ⚠️ **Sistem Uyarısı:** Model analizinde 'meşru menfaat' kavramı geçmiş olsa da, Kural Motoru bu eylemin TCK kapsamında **suç** olduğunu tespit etmiştir. Hukuka aykırı eylemlerde meşru menfaat geçerli bir hukuki dayanak olamaz."
    
    # Kural 2: Sınıflandırma başlığı yoksa uyar
    if "**SINIFLANDIRMA:**" not in llm_output:
        return "**SINIFLANDIRMA:** Tespit Edilemedi (Lütfen Formatı Zorlayınız)\n" + llm_output
        
    return llm_output

# ─────────────────────────────────────────
# 4. API BAĞLANTISI (HUGGING FACE)
# ─────────────────────────────────────────
try:
    hf_token = st.secrets["HF_TOKEN"]
    _model_id = "Qwen/Qwen2.5-7B-Instruct" 
    client = InferenceClient(model=_model_id, token=hf_token)
except Exception as e:
    st.error(f"API Bağlantı Hatası: Lütfen Secrets ayarlarınızı kontrol edin. Detay: {e}")
    st.stop()

def call_llm(messages, temp=0.1):
    # Deterministik (kesin) sonuçlar için temperature çok düşük tutuldu
    res = client.chat_completion(messages=messages, max_tokens=800, temperature=temp, top_p=0.8)
    return res.choices[0].message.content

def run_legal_pipeline(user_query: str):
    # 1. Adım: Rule Engine Sınıflandırması
    pre_check = pre_process_query(user_query)
    
    # 2. Adım: Prompt Hazırlığı (Dinamik ve Kilitli)
    sys_prompt = f"{BASE_RULES}\n\n{pre_check['directive']}"
    
    history = st.session_state.messages[-4:] # Sadece son 4 mesaj (Context şişmesini önler)
    messages = [{"role": "system", "content": sys_prompt}]
    for m in history: messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_query})

    with st.status("⚖️ Hukuk Motoru Çalışıyor...", expanded=True) as status:
        st.write("🔍 Python Kural Motoru: Vaka taranıyor...")
        if pre_check['is_crime']: st.error("🚨 Kritik İhlal / TCK Suç şüphesi saptandı.")
        else: st.info("📊 Kurumsal Veri İşleme / KVKK Vakası saptandı.")
        
        st.write("⚙️ LLM Hukuki Metni Üretiyor...")
        raw_output = call_llm(messages)
        
        st.write("🛡️ Çıktı Validator'dan Geçiriliyor...")
        final_output = post_process_validator(raw_output, pre_check['is_crime'])
        
        status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
        
    return final_output

# ─────────────────────────────────────────
# 5. GLOBAL CSS (KUSURSUZ MOR TEMA)
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
.stApp { background: #F8F7FF !important; color: #18172B !important; }

/* Sidebar Native Styling */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #5B2FD9 0%, #7C3FFC 40%, #6A2EE8 100%) !important;
    border-right: none !important;
    box-shadow: 4px 0 32px rgba(124,63,252,0.35);
}
[data-testid="stSidebar"] * { color: white !important; border-color: rgba(255,255,255,0.1) !important; }

/* Profile Box in Sidebar */
.sb-profile-box {
    background: rgba(255,255,255,0.12); border-radius: 10px; padding: 15px; margin-bottom: 20px;
    display: flex; align-items: center; gap: 12px;
}
.sb-avatar-circle {
    width: 40px; height: 40px; border-radius: 50%; background: rgba(255,255,255,0.25);
    display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px;
}

/* Chat Messages */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #7C5CFC !important; border-radius: 16px 16px 4px 16px !important; margin-bottom: 15px;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) * { color: white !important; }

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: white !important; border: 1px solid #E4E0FF !important; border-radius: 4px 16px 16px 16px !important; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.02);
}

/* Input Area Fix */
[data-testid="stBottom"] { background: transparent !important; }
[data-testid="stChatInput"] { background: white !important; border: 1px solid #E4E0FF !important; border-radius: 12px !important; box-shadow: 0 4px 20px rgba(124,63,252,0.1) !important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 6. SESSION & STATE YÖNETİMİ
# ─────────────────────────────────────────
if "chat_id" not in st.session_state: st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if "messages" not in st.session_state: st.session_state.messages = []
if "queued" not in st.session_state: st.session_state.queued = ""

db = load_db()

# ─────────────────────────────────────────
# 7. SİDEBAR (NATIVE & STABİL)
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='font-size: 0.65rem; font-weight: bold; color: rgba(255,255,255,0.6); text-transform: uppercase; margin-bottom: 5px;'>Bitirme Projesi</div>
        <div style='font-size: 1.5rem; font-weight: 800; margin-bottom: 20px;'>⚖️ Siber Hukuk</div>
        <div class='sb-profile-box'>
            <div class='sb-avatar-circle'>MH</div>
            <div>
                <div style='font-weight: 700; font-size: 1rem;'>Merve Havuz</div>
                <div style='font-size: 0.75rem; color: rgba(255,255,255,0.7);'>Proje Sahibi</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("➕ Yeni Analiz Başlat", use_container_width=True):
        st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("<hr style='opacity: 0.2; margin: 15px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.8rem; opacity: 0.7; margin-bottom: 10px;'>GEÇMİŞ ANALİZLER</div>", unsafe_allow_html=True)
    
    for cid in sorted(db.keys(), reverse=True):
        msgs = db[cid]
        if not msgs: continue
        title = msgs[0]["content"][:25] + "..."
        if st.button(f"💬 {title}", key=cid, use_container_width=True):
            st.session_state.chat_id = cid
            st.session_state.messages = msgs
            st.rerun()

# ─────────────────────────────────────────
# 8. ANA İÇERİK VE İŞLEYİŞ
# ─────────────────────────────────────────
# Eğer queued'da işlem varsa hemen başlat
if st.session_state.queued:
    user_query = st.session_state.queued
    st.session_state.queued = ""
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="👤"): st.markdown(user_query)
    with st.chat_message("assistant", avatar="⚖️"):
        ans = run_legal_pipeline(user_query)
        st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        db[st.session_state.chat_id] = st.session_state.messages
        save_db(db)

# Boş ekran (İlk açılış)
if not st.session_state.messages:
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align:center;'>🛡️ Siber Hukuk Analiz Portalı</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#7B78A0; font-size:1.1rem; margin-bottom:40px;'>Kural Tabanlı Hukuk Motoru (Rule Engine) & Yapay Zeka (LLM) Entegrasyonu.</p>", unsafe_allow_html=True)
        
        st.markdown("**🧪 Örnek Senaryolarla Test Edin:**")
        c1, c2 = st.columns(2)
        if c1.button("🔒 Senaryo 1: Çalışanın mailleri gizlice okuması (TCK Testi)", use_container_width=True):
            st.session_state.queued = "Bir çalışan arkadaşının bilgisayarını açık bulup e-postalarını gizlice kopyalıyor ve şirkete şikayet ediyor."
            st.rerun()
        if c2.button("📱 Senaryo 2: E-ticaret Dinamik Fiyatlandırma (KVKK Testi)", use_container_width=True):
            st.session_state.queued = "E-ticaret sitemizde kullanıcıların tıklama verilerini analiz edip (profilleme) onlara özel farklı fiyatlar gösteriyoruz."
            st.rerun()

# Mesaj geçmişini renderla
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "⚖️"):
        st.markdown(msg["content"])

# Kullanıcı Girişi
if user_input := st.chat_input("Hukuki senaryoyu detaylıca buraya yazın..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"): st.markdown(user_input)
    
    with st.chat_message("assistant", avatar="⚖️"):
        answer = run_legal_pipeline(user_input)
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        db[st.session_state.chat_id] = st.session_state.messages
        save_db(db)
