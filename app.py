import streamlit as st
from huggingface_hub import InferenceClient
import json
import os
import re
from datetime import datetime

# ─────────────────────────────────────────
# 1. SAYFA VE ARAYÜZ (UI) AYARLARI
# ─────────────────────────────────────────
st.set_page_config(page_title="Siber Hukuk Analiz Sistemi", page_icon="⚖️", layout="wide")

# ─────────────────────────────────────────
# 2. PYTHON HUKUK HAFIZASI (LOOKUP TABLE)
# ─────────────────────────────────────────
# Model artık madde uydurmayacak. Kararı bu tablo verecek.
HUKUK_DB = {
    "yetkisiz_erisim": {"madde": "TCK 243", "aciklama": "Bilişim sistemine girme suçu."},
    "sistem_bozma": {"madde": "TCK 244", "aciklama": "Sistemi engelleme, bozma, verileri yok etme."},
    "veri_calma": {"madde": "TCK 136", "aciklama": "Kişisel verileri, hukuka aykırı olarak bir başkasına verme, yayma veya ele geçirme."},
    "mail_okuma": {"madde": "TCK 132", "aciklama": "Haberleşmenin gizliliğini ihlal."},
    "veri_guvenligi": {"madde": "KVKK Madde 12", "aciklama": "Veri güvenliğine ilişkin idari ve teknik tedbirler."},
    "mesru_menfaat": {"madde": "KVKK Madde 5/2-f", "aciklama": "İlgili kişinin temel hak ve özgürlüklerine zarar vermemek kaydıyla meşru menfaat."},
    "acik_riza": {"madde": "KVKK Madde 5/1", "aciklama": "Kişisel veriler ilgili kişinin açık rızası olmaksızın işlenemez."}
}

# ─────────────────────────────────────────
# 3. RAG ALTYAPISI (MEVZUAT OKUYUCU)
# ─────────────────────────────────────────
def retrieve_mevzuat(ilgili_maddeler):
    """
    Eğer dizinde 'mevzuat.txt' adlı bir dosya varsa, modelin uydurmasını engellemek için
    ilgili kanun metinlerini direkt bu dosyadan çeker (RAG).
    """
    if not os.path.exists("mevzuat.txt"):
        return "Not: 'mevzuat.txt' dosyası bulunamadı. Lütfen mevzuat metinlerini içeren dosyayı ana dizine ekleyin."
    
    # Gerçek bir sistemde burada vektör araması (FAISS/Chroma) yapılır.
    # Şimdilik basit bir anahtar kelime/madde taraması simüle ediyoruz.
    bulunan_metinler = []
    try:
        with open("mevzuat.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            for madde in ilgili_maddeler:
                for line in lines:
                    if madde.split(" ")[1] in line: # Örn: TCK 136 -> '136' yı arar
                        bulunan_metinler.append(line.strip())
        return " | ".join(bulunan_metinler) if bulunan_metinler else "Mevzuat metni bulunamadı."
    except Exception:
        return "Mevzuat dosyası okunamadı."

# ─────────────────────────────────────────
# 4. API BAĞLANTISI
# ─────────────────────────────────────────
try:
    hf_token = st.secrets["HF_TOKEN"]
    _model_id = "Qwen/Qwen2.5-7B-Instruct" 
    client = InferenceClient(model=_model_id, token=hf_token)
except Exception as e:
    st.error(f"API Hatası: {e}")
    st.stop()

def call_llm(prompt, sys_prompt="Sen bir asistansın.", temp=0.1):
    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}]
    res = client.chat_completion(messages=messages, max_tokens=1000, temperature=temp)
    return res.choices[0].message.content

# ─────────────────────────────────────────
# 5. YENİ MİMARİ: KARAR MOTORU (PIPELINE)
# ─────────────────────────────────────────
def run_deterministic_pipeline(user_query):
    with st.status("⚖️ Hukuk Motoru Çalışıyor...", expanded=True) as status:
        
        # 🟢 ADIM 1: SINIFLANDIRMA (LLM Sadece Sınıflandırır)
        st.write("🔍 Aşama 1: Olay Sınıflandırması Yapılıyor...")
        class_sys = "Sen bir veri çıkarım motorusun. Gelen metni analiz et ve SADECE JSON formatında yanıt ver. Başka hiçbir şey yazma."
        class_prompt = f"""Olayı analiz et ve listelenen etiketlerden uyanları 'etiketler' dizisine ekle.
        Etiket Listesi: [yetkisiz_erisim, sistem_bozma, veri_calma, mail_okuma, veri_guvenligi, mesru_menfaat, acik_riza]
        Olay: {user_query}
        Format: {{"etiketler": ["etiket1", "etiket2"]}}"""
        
        raw_json = call_llm(class_prompt, class_sys, temp=0.01)
        
        # JSON'ı güvenli şekilde ayıkla
        try:
            match = re.search(r'\{.*\}', raw_json, re.DOTALL)
            parsed_data = json.loads(match.group(0)) if match else {"etiketler": []}
            secilen_etiketler = parsed_data.get("etiketler", [])
        except:
            secilen_etiketler = []

        # 🟢 ADIM 2: PYTHON HUKUK EŞLEŞTİRMESİ (Mapping)
        st.write("⚙️ Aşama 2: Python Hafızasından Maddeler Çekiliyor...")
        tespit_edilen_maddeler = []
        is_crime = False
        
        for etiket in secilen_etiketler:
            if etiket in HUKUK_DB:
                tespit_edilen_maddeler.append(HUKUK_DB[etiket]["madde"])
                if "TCK" in HUKUK_DB[etiket]["madde"]:
                    is_crime = True
                    
        # Validator Katmanı: Suç varsa meşru menfaati Python siler
        if is_crime and "KVKK Madde 5/2-f" in tespit_edilen_maddeler:
            tespit_edilen_maddeler.remove("KVKK Madde 5/2-f")
            
        if not tespit_edilen_maddeler:
            tespit_edilen_maddeler = ["Tespit Edilemedi - Detaylı bilgi gereklidir."]

        # 🟢 ADIM 3: RAG (MEVZUAT ÇEKİMİ)
        st.write("📚 Aşama 3: Mevzuat Metinleri Okunuyor (RAG)...")
        rag_text = retrieve_mevzuat(tespit_edilen_maddeler)

        # 🟢 ADIM 4: LLM SADECE AÇIKLAMA YAZAR (Generation)
        st.write("✍️ Aşama 4: Hukuki Açıklama Üretiliyor...")
        gen_sys = """Sen bir 'Hukuki Metin Yazıcısı'sın. Asla kanun maddesi uydurma. 
        Sana verilen 'İlgili Maddeler' ve 'Mevzuat Metni' dışına çıkmadan olayı açıkla.
        Format:
        **OLAY:** (Kısa özet)
        **UYGULANACAK MADDELER:** (Sana verilenleri yaz)
        **HUKUKİ GEREKÇE:** (Olay ile maddeleri bağdaştır)
        **SONUÇ:** (Aksiyon planı)"""
        
        gen_prompt = f"""
        Olay: {user_query}
        İlgili Maddeler (Kesin Hüküm): {', '.join(tespit_edilen_maddeler)}
        Kanun/Mevzuat Metni: {rag_text}
        
        Lütfen bu verileri kullanarak formatlı açıklamayı yaz.
        """
        
        final_output = call_llm(gen_prompt, gen_sys, temp=0.2)
        status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
        
    return final_output

# ─────────────────────────────────────────
# 6. GÖRSEL TASARIM (CSS)
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
.stApp { background: #F8F7FF !important; color: #18172B !important; }

[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #5B2FD9 0%, #7C3FFC 40%, #6A2EE8 100%) !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: white !important; }

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #7C5CFC !important; border-radius: 16px 16px 4px 16px !important; margin-bottom: 15px;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) * { color: white !important; }

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: white !important; border: 1px solid #E4E0FF !important; border-radius: 4px 16px 16px 16px !important; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.02);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 7. SİDEBAR VE VERİTABANI YÖNETİMİ
# ─────────────────────────────────────────
db = load_db()
if "chat_id" not in st.session_state: st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if "messages" not in st.session_state: st.session_state.messages = []

with st.sidebar:
    st.markdown("<div style='font-size: 1.5rem; font-weight: 800; margin-bottom: 20px;'>⚖️ Siber Hukuk</div>", unsafe_allow_html=True)
    if st.button("➕ Yeni Analiz Başlat", use_container_width=True):
        st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()

# ─────────────────────────────────────────
# 8. ANA EKRAN İŞLEYİŞİ
# ─────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("<br><br><h1 style='text-align:center;'>🛡️ Siber Hukuk Analiz Portalı</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#7B78A0; font-size:1.1rem;'>Python Lookup & RAG Mimari Destekli Karar Motoru</p>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "⚖️"):
        st.markdown(msg["content"])

if user_input := st.chat_input("Hukuki senaryoyu buraya yazın..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"): st.markdown(user_input)
    
    with st.chat_message("assistant", avatar="⚖️"):
        answer = run_deterministic_pipeline(user_input)
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        db[st.session_state.chat_id] = st.session_state.messages
        save_db(db)
