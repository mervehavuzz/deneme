import streamlit as st
from huggingface_hub import InferenceClient
import json
import os
import re
from datetime import datetime

# ─────────────────────────────────────────
# 1. VERİTABANI FONKSİYONLARI (EN ÜSTTE OLMALI)
# ─────────────────────────────────────────
DB_FILE = "chat_history.json"

def load_db() -> dict:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_db(data: dict) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────
# 2. HUKUK HAFIZASI VE MEVZUAT SİSTEMİ
# ─────────────────────────────────────────
HUKUK_DB = {
    "yetkisiz_erisim": {"madde": "TCK 243", "aciklama": "Bilişim sistemine girme suçu."},
    "sistem_bozma": {"madde": "TCK 244", "aciklama": "Sistemi engelleme, bozma, verileri yok etme."},
    "veri_calma": {"madde": "TCK 136", "aciklama": "Kişisel verileri hukuka aykırı ele geçirme."},
    "mail_okuma": {"madde": "TCK 132", "aciklama": "Haberleşmenin gizliliğini ihlal."},
    "veri_guvenligi": {"madde": "KVKK Madde 12", "aciklama": "Veri güvenliği yükümlülükleri."},
    "mesru_menfaat": {"madde": "KVKK Madde 5/2-f", "aciklama": "Meşru menfaat işleme şartı."},
    "acik_riza": {"madde": "KVKK Madde 5/1", "aciklama": "Açık rıza ile veri işleme."}
}

def retrieve_mevzuat(ilgili_maddeler):
    if not os.path.exists("mevzuat.txt"):
        return "Not: mevzuat.txt bulunamadı, genel bilgilerle devam ediliyor."
    bulunanlar = []
    try:
        with open("mevzuat.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            for madde in ilgili_maddeler:
                clean_madde = re.sub(r'[^0-9]', '', madde) # Sadece rakamları al (136, 132 gibi)
                for line in lines:
                    if clean_madde in line and len(clean_madde) > 1:
                        bulunanlar.append(line.strip())
        return "\n".join(set(bulunanlar)) if bulunanlar else "İlgili mevzuat metni dosyada bulunamadı."
    except: return "Mevzuat okunurken hata oluştu."

# ─────────────────────────────────────────
# 3. SAYFA AYARLARI VE TASARIM (CSS)
# ─────────────────────────────────────────
st.set_page_config(page_title="Siber Hukuk Analiz Sistemi", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
.stApp { background: #F8F7FF !important; }

/* Sidebar Tasarımı */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #5B2FD9 0%, #7C3FFC 40%, #6A2EE8 100%) !important;
}
[data-testid="stSidebar"] * { color: white !important; }

/* Mesaj Balonları */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #7C5CFC !important; border-radius: 15px 15px 5px 15px !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: white !important; border: 1px solid #E4E0FF !important; border-radius: 5px 15px 15px 15px !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 4. API VE MANTIK MOTORU
# ─────────────────────────────────────────
try:
    hf_token = st.secrets["HF_TOKEN"]
    client = InferenceClient(model="Qwen/Qwen2.5-7B-Instruct", token=hf_token)
except Exception as e:
    st.error(f"API Hatası: {e}")
    st.stop()

def call_llm(prompt, sys_msg, temp=0.1):
    messages = [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]
    res = client.chat_completion(messages=messages, max_tokens=1000, temperature=temp)
    return res.choices[0].message.content

def run_pipeline(user_query):
    with st.status("⚖️ Hukuk Motoru Analiz Yapıyor...", expanded=True) as status:
        # Sınıflandırma
        st.write("🔍 Aşama 1: Vaka Sınıflandırılıyor...")
        class_prompt = f"Olayı analiz et ve uyan etiketleri JSON olarak ver: [yetkisiz_erisim, veri_calma, mail_okuma, veri_guvenligi, mesru_menfaat]\nOlay: {user_query}\nFormat: {{\"etiketler\": []}}"
        raw_json = call_llm(class_prompt, "Sadece JSON döndür.", temp=0.01)
        
        try:
            secilenler = json.loads(re.search(r'\{.*\}', raw_json, re.DOTALL).group(0)).get("etiketler", [])
        except: secilenler = []

        # Mapping & RAG
        st.write("⚙️ Aşama 2: Mevzuat Verileri Çekiliyor...")
        maddeler = [HUKUK_DB[e]["madde"] for e in secilenler if e in HUKUK_DB]
        if any("TCK" in m for m in maddeler) and "KVKK Madde 5/2-f" in maddeler:
            maddeler.remove("KVKK Madde 5/2-f") # Suç varsa meşru menfaat tartışılamaz
        
        mevzuat_metni = retrieve_mevzuat(maddeler)

        # Final Yazım
        st.write("✍️ Aşama 3: Rapor Oluşturuluyor...")
        gen_sys = "Sen uzman bir hukuk yazıcısısın. Verilen maddeler ve mevzuat metni dışına çıkmadan profesyonel analiz yap."
        gen_prompt = f"Olay: {user_query}\nİlgili Maddeler: {maddeler}\nGerçek Metinler: {mevzuat_metni}\nFormat: OLAY, ANALİZ, SONUÇ."
        
        final = call_llm(gen_prompt, gen_sys, temp=0.2)
        status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
    return final

# ─────────────────────────────────────────
# 5. SIDEBAR VE ANA EKRAN
# ─────────────────────────────────────────
db = load_db()
if "chat_id" not in st.session_state: st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if "messages" not in st.session_state: st.session_state.messages = []

with st.sidebar:
    st.markdown("### ⚖️ Siber Hukuk Analiz")
    st.write("**Merve Havuz** - Bitirme Projesi")
    if st.button("➕ Yeni Analiz", use_container_width=True):
        st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    for cid in sorted(db.keys(), reverse=True):
        if st.button(f"💬 {cid[:13]}...", key=cid, use_container_width=True):
            st.session_state.chat_id = cid
            st.session_state.messages = db[cid]
            st.rerun()

st.title("🛡️ Siber Hukuk Analiz Portalı")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "⚖️"):
        st.markdown(msg["content"])

if prompt := st.chat_input("Hukuki senaryoyu buraya yazın..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"): st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="⚖️"):
        answer = run_pipeline(prompt)
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        db[st.session_state.chat_id] = st.session_state.messages
        save_db(db)
