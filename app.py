import streamlit as st
from huggingface_hub import InferenceClient
import json
import os
from datetime import datetime

# ─────────────────────────────────────────
# 1. SİSTEM YAPILANDIRMASI VE BAĞLAM (CONTEXT)
# ─────────────────────────────────────────
st.set_page_config(page_title="Siber Hukuk Analiz Sistemi", page_icon="⚖️", layout="wide")

# KVKK Karar Ağacı ve Bilgi Seti
KVKK_CONTEXT = """
HUKUKİ TASNİF VE KARAR AĞACI:
1. İdari İhlal: Veri güvenliği eksikliği, aydınlatma yükümlülüğü ihlali (KVKK Md. 12).
2. Veri İhlali: Verilerin yetkisiz sızması (KVKK Md. 12/5 - 72 Saat Bildirim Şartı).
3. Siber Suçlar (TCK): Sisteme engelleme/bozma (TCK 244), Verileri yok etme/değiştirme (TCK 244/2), Verileri hukuka aykırı ele geçirme (TCK 136).

İŞLEME ŞARTLARI (Md. 5/2): 
a) Kanun, c) Sözleşme, ç) Hukuki Yükümlülük, e) Hakkın Tesisi, f) Meşru Menfaat (Denge testi zorunlu).
ÖNEMLİ: Suç teşkil eden eylemlerde (hack, hırsızlık) 5/2 maddeleri (meşru menfaat vb.) tartışılamaz; doğrudan İHLAL denmelidir.
"""

SYSTEM_PROMPT = """Sen uzman bir Siber Hukuk Analiz Motorusun. 
Görevin: Vakaları KVKK ve Türk Ceza Kanunu çerçevesinde 'Double-Pass' (çift aşamalı) yöntemle analiz etmek.

FORMAT ZORUNLULUĞU (Bu şablonun dışına çıkma):
- **OLAY:** (Kısa teknik özet)
- **HUKUKİ NİTELİK:** (Suç mu, idari ihlal mi, veri işleme mi?)
- **KVKK ANALİZİ:** (Madde 5/2 ve Madde 12 eşleşmesi. Varsa TCK maddesi.)
- **SONUÇ VE ÖNERİ:** (Kısa, net ve uygulanabilir aksiyonlar.)

DİL: Akademik, kesin ve hukukçu terminolojisine uygun."""

# ─────────────────────────────────────────
# 2. API VE MODEL AYARLARI
# ─────────────────────────────────────────
try:
    hf_token = st.secrets["HF_TOKEN"]
    _model_id = "Qwen/Qwen2.5-7B-Instruct" 
    client = InferenceClient(model=_model_id, token=hf_token)
except Exception as e:
    st.error(f"API Hatası: {e}")
    st.stop()

# ─────────────────────────────────────────
# 3. MANTIKSAL DENETİM (RULE-BASED VALIDATOR)
# ─────────────────────────────────────────
def internal_validator(text):
    """LLM çıktısını kullanıcıya sunmadan önce Python tarafında süzgeçten geçirir."""
    text_lower = text.lower()
    # Eğer cevapta suç ibareleri geçiyor ama 'uygun' deniyorsa risklidir.
    risk_keywords = ["tck", "suç", "hacker", "izinsiz", "ele geçirme"]
    has_risk = any(k in text_lower for k in risk_keywords)
    is_marked_proper = any(k in text_lower for k in ["hukuka uygun", "meşru menfaat"])
    
    if has_risk and is_marked_proper:
        return False # Hatalı mantık eşleşmesi
    return True

# ─────────────────────────────────────────
# 4. AKILLI PIPELINE (DOUBLE-PASS INFERENCE)
# ─────────────────────────────────────────
def call_engine(messages, temp=0.2, tokens=1000):
    output = client.chat_completion(
        messages=messages,
        max_tokens=tokens,
        temperature=temp,
        top_p=0.8
    )
    return output.choices[0].message.content

def run_analysis_pipeline(user_query):
    # Geçmişi sınırla (Context Window Control)
    history = st.session_state.messages[-6:]
    
    # Adım 1: İlk Taslak Oluşturma (Reasoning)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": KVKK_CONTEXT}
    ]
    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_query})

    with st.status("Hukuki Analiz Motoru Çalışıyor...", expanded=True) as status:
        st.write("🔍 Vaka verileri işleniyor...")
        draft = call_engine(messages, temp=0.3)
        
        # Adım 2: Denetim ve Düzenleme (Self-Correction)
        st.write("⚖️ Mevzuat uyumluluğu denetleniyor...")
        check_prompt = f"""
        Aşağıdaki hukuki analizi Siber Hukuk kurallarına göre denetle ve hataları düzelt:
        ---
        {draft}
        ---
        KRİTİK DENETİM:
        1. Suç teşkil eden eylem 'meşru menfaat' olarak gösterilmiş mi? (Varsa düzelt).
        2. KVKK Madde 5/2 ve Md. 12 doğru eşleşmiş mi?
        3. Yanıt 'FORMAT ZORUNLULUĞU'na %100 uyuyor mu?
        
        Sadece en doğru final metnini döndür.
        """
        final = call_engine([{"role": "user", "content": check_prompt}], temp=0.1)
        
        # Adım 3: Rule-Based Validation
        if not internal_validator(final):
            st.warning("⚠️ Mantıksal çelişki tespit edildi, yeniden stabilize ediliyor...")
            final = call_engine([{"role": "user", "content": f"Şu analizi daha tutarlı ve kesin bir dille yaz: {final}"}], temp=0.05)
            
        status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
    return final

# ─────────────────────────────────────────
# 5. KULLANICI ARAYÜZÜ (UI) VE SESSION
# ─────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# CSS Tasarımı
st.markdown("""<style>
    .stApp { background: #F9FAFB; }
    [data-testid="stChatMessage"] { border: 1px solid #E5E7EB; border-radius: 12px; }
    .sidebar-text { color: #4B5563; font-size: 0.9rem; }
</style>""", unsafe_allow_html=True)

# Yan Panel (Sidebar)
with st.sidebar:
    st.title("⚖️ Mevzuat Paneli")
    st.markdown("---")
    st.write("**Proje Sahibi:** Merve Havuz")
    st.write("**Sistem:** Siber Hukuk Pipeline v2.0")
    if st.button("Sohbeti Temizle"):
        st.session_state.messages = []
        st.rerun()

# Ana Ekran
st.title("🛡️ Siber Hukuk Analiz Portalı")
st.caption("KVKK ve TCK Odaklı Yapay Zeka Denetim Sistemi")

# Sohbet Geçmişini Görüntüle
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "⚖️"):
        st.markdown(msg["content"])

# Giriş Alanı
if prompt := st.chat_input("Hukuki vakayı veya soruyu giriniz..."):
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar="⚖️"):
        response = run_analysis_pipeline(prompt)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
