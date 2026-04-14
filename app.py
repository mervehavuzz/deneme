import streamlit as st
from huggingface_hub import InferenceClient
import json
import os
from datetime import datetime

# ─────────────────────────────────────────
# 1. SAYFA AYARI VE GÖRSEL TASARIM (UI)
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Siber Hukuk Asistanı",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────
# 2. VERİTABANI İŞLEMLERİ
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
# 3. AKILLI PIPELINE AYARLARI (LOGIC)
# ─────────────────────────────────────────
KVKK_CONTEXT = """
HUKUKİ TASNİF VE KARAR AĞACI:
1. İdari İhlal: Veri güvenliği eksikliği, aydınlatma yükümlülüğü ihlali (KVKK Md. 12).
2. Veri İhlali: Verilerin yetkisiz sızması (KVKK Md. 12/5 - 72 Saat Bildirim Şartı).
3. Siber Suçlar (TCK): Sisteme engelleme/bozma (TCK 244), Verileri yok etme/değiştirme (TCK 244/2), Verileri hukuka aykırı ele geçirme (TCK 136).

İŞLEME ŞARTLARI (Md. 5/2): 
a) Kanun, c) Sözleşme, ç) Hukuki Yükümlülük, e) Hakkın Tesisi, f) Meşru Menfaat (Denge testi zorunlu).
ÖNEMLİ: Suç teşkil eden eylemlerde (hack, hırsızlık, izinsiz giriş) 5/2 maddeleri (meşru menfaat vb.) tartışılamaz; doğrudan İHLAL ve SUÇ denmelidir.
"""

SYSTEM_PROMPT = """Sen uzman bir Siber Hukuk Analiz Motorusun. 
Görevin: Vakaları KVKK ve Türk Ceza Kanunu çerçevesinde analiz etmek.

FORMAT ZORUNLULUĞU:
- **OLAY:** (Kısa teknik özet)
- **HUKUKİ NİTELİK:** (Suç mu, idari ihlal mi, veri işleme mi?)
- **KVKK ANALİZİ:** (Madde 5/2 ve Madde 12 eşleşmesi. Varsa TCK maddesi.)
- **SONUÇ VE ÖNERİ:** (Kısa, net ve uygulanabilir aksiyonlar.)

DİL: Akademik, ciddi ve hukukçu terminolojisine uygun."""

try:
    hf_token = st.secrets["HF_TOKEN"]
    # Muhakeme yeteneği yüksek olan model
    _model_id = "Qwen/Qwen2.5-7B-Instruct" 
    client = InferenceClient(model=_model_id, token=hf_token)
except Exception as e:
    st.error(f"API Bağlantı Hatası: {e}")
    st.stop()

# ─────────────────────────────────────────
# 4. YARDIMCI FONKSİYONLAR (PIPELINE)
# ─────────────────────────────────────────
def internal_validator(text):
    text_lower = text.lower()
    risk_keywords = ["tck", "suç", "hacker", "izinsiz", "ele geçirme"]
    has_risk = any(k in text_lower for k in risk_keywords)
    is_marked_proper = any(k in text_lower for k in ["hukuka uygun", "meşru menfaat"])
    if has_risk and is_marked_proper: return False
    return True

def call_engine(messages, temp=0.2, tokens=1200):
    output = client.chat_completion(
        messages=messages,
        max_tokens=tokens,
        temperature=temp,
        top_p=0.8
    )
    return output.choices[0].message.content

def run_analysis_pipeline(user_query):
    # Son 6 mesajı gönder (Context Window Control)
    history = st.session_state.messages[-6:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": KVKK_CONTEXT}]
    for m in history: messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_query})

    with st.status("⚖️ Hukuki Analiz Yapılıyor...", expanded=True) as status:
        st.write("🔍 Vaka verileri işleniyor...")
        draft = call_engine(messages, temp=0.3)
        
        st.write("⚖️ Mevzuat uyumluluğu denetleniyor...")
        check_prompt = f"Şu analizi denetle ve hataları düzelt, formatı koru:\n{draft}"
        final = call_engine([{"role": "user", "content": check_prompt}], temp=0.1)
        
        if not internal_validator(final):
            final = call_engine([{"role": "user", "content": f"Şu analizi daha tutarlı yaz: {final}"}], temp=0.05)
            
        status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
    return final

# ─────────────────────────────────────────
# 5. GLOBAL CSS (MOR TEMA VE UI ÖZELLİKLERİ)
# ─────────────────────────────────────────
SB = 260
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&display=swap');
*, *::before, *::after {{ box-sizing: border-box; }}
html, body, .stApp {{
    font-family: 'DM Sans', sans-serif !important;
    background: #F8F7FF !important;
    color: #18172B !important;
}}
section[data-testid="stSidebar"], header[data-testid="stHeader"], 
[data-testid="stToolbar"], [data-testid="stDeployButton"], 
[data-testid="collapsedControl"], footer {{ display:none!important; }}

[data-testid="stAppViewContainer"] > section.main {{
    margin-left: {SB}px !important;
    width: calc(100vw - {SB}px) !important;
    padding: 0 !important;
}}
div[data-testid="stMainBlockContainer"] {{
    max-width: 1000px !important; margin-left: auto !important; margin-right: auto !important;
    padding-top: 1rem !important; padding-bottom: 200px !important; 
}}

#custom-sidebar {{
    position: fixed; top: 0; left: 0; width: {SB}px; height: 100vh;
    background: linear-gradient(160deg, #5B2FD9 0%, #7C3FFC 40%, #6A2EE8 100%);
    box-shadow: 4px 0 32px rgba(124,63,252,0.35);
    display: flex; flex-direction: column; z-index: 9999; overflow: hidden;
}}
.sb-header {{ padding: 22px 16px 18px; border-bottom: 1px solid rgba(255,255,255,0.15); }}
.sb-badge {{ font-size: 0.58rem; font-weight: 700; color: rgba(255,255,255,0.55); text-transform: uppercase; margin-bottom: 10px; }}
.sb-botname {{ font-size: 1.25rem; font-weight: 800; color: #fff; margin-bottom: 14px; }}
.sb-profile {{ display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: rgba(255,255,255,0.12); border-radius: 10px; }}
.sb-avatar {{ width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,0.25); display: flex; align-items: center; justify-content: center; color: #fff; }}
.sb-name {{ font-size: 0.88rem; font-weight: 700; color: #fff; }}
.sb-role {{ font-size: 0.65rem; color: rgba(255,255,255,0.65); }}
.sb-new-btn {{ width: 90%; margin: 14px auto; padding: 10px; background: linear-gradient(135deg, #C47FFF 0%, #A040FF 100%); border: none; border-radius: 10px; color: #fff; font-weight: 700; cursor: pointer; }}
.sb-history {{ flex: 1; overflow-y: auto; padding: 10px; }}
.sb-chat-btn {{ width: 100%; text-align: left; background: transparent; border: none; color: rgba(237,233,255,0.75); padding: 8px; cursor: pointer; border-radius: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.sb-active {{ background: rgba(255,255,255,0.18); color: #fff; border-left: 2px solid #fff; }}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stMarkdownContainer"] {{
    background: #7C5CFC !important; color: #fff !important; border-radius: 16px 16px 4px 16px !important; padding: 11px 16px !important;
}}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stMarkdownContainer"] {{
    background: #fff !important; color: #18172B !important; border: 1px solid #E4E0FF !important; border-radius: 4px 16px 16px 16px !important; padding: 13px 18px !important;
}}

[data-testid="stBottom"] {{
    position: fixed !important; bottom: 0 !important; left: {SB}px !important; width: calc(100vw - {SB}px) !important;
    background: rgba(248,247,255,0.92) !important; backdrop-filter: blur(16px) !important; padding: 10px 0 !important;
}}
[data-testid="stBottomBlockContainer"]::after {{
    content: "⚠️ Bu platform hukuki tavsiye niteliği taşımamaktadır. Yalnızca genel rehberlik amaçlıdır.";
    display: block; font-size: 0.72rem; color: #7B78A0; text-align: center; margin-top: 8px;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 6. SIDEBAR İÇERİĞİ
# ─────────────────────────────────────────
db_sb = load_db()
grouped = sorted(db_sb.keys(), reverse=True)
history_html = ""
for cid in grouped:
    msgs_s = db_sb.get(cid, [])
    lbl = (msgs_s[0].get("title") or msgs_s[0]["content"][:22] + "…") if msgs_s else "Analiz"
    active = "sb-active" if cid == st.session_state.get("chat_id") else ""
    history_html += f"<button class='sb-chat-btn {active}' onclick=\"goLoad('{cid}')\">💬 {lbl}</button>"

st.markdown(f"""
<div id="custom-sidebar">
  <div class="sb-header">
    <div class="sb-badge">Bilişim Güvenliği Teknolojisi<br>Bitirme Projesi</div>
    <div class="sb-botname">⚖️ Siber Hukuk Botu</div>
    <div class="sb-profile"><div class="sb-avatar">MH</div><div><div class="sb-name">Merve Havuz</div><div class="sb-role">Proje Sahibi</div></div></div>
  </div>
  <div class="sb-new-wrap"><button class="sb-new-btn" onclick="goNew()">＋&nbsp;&nbsp;Yeni Analiz</button></div>
  <div class="sb-history">{history_html}</div>
</div>
<script>
function goNew() {{ window.location.href = window.location.pathname + '?sb_action=new'; }}
function goLoad(cid) {{ window.location.href = window.location.pathname + '?sb_action=load&sb_cid=' + cid; }}
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 7. ANA İÇERİK VE ANALİZ
# ─────────────────────────────────────────
if "chat_id" not in st.session_state: st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if "messages" not in st.session_state: st.session_state.messages = []
if "queued" not in st.session_state: st.session_state.queued = ""

params = st.query_params
if params.get("sb_action") == "new":
    st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.messages = []
    st.query_params.clear()
    st.rerun()

pending = st.session_state.queued
if pending:
    st.session_state.queued = ""
    st.session_state.messages.append({"role": "user", "content": pending})
    with st.chat_message("user", avatar="👤"): st.markdown(pending)
    with st.chat_message("assistant", avatar="⚖️"):
        ans = run_analysis_pipeline(pending)
        st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        save_current()

if not st.session_state.messages:
    spacer_left, center_content, spacer_right = st.columns([1.8, 7, 0.2])
    with center_content:
        st.markdown('<h1 style="text-align:center;">⚖️ Siber Hukuk Portalı</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#6B6890;">Hukuki vakayı veya dijital haklarınızı yazın, analiz edelim.</p>', unsafe_allow_html=True)
        if st.button("Örnek Senaryo: Veri İhlali Bildirimi"):
            st.session_state.queued = "Bir şirket çalışanı müşteri listesini çalarsa ne olur?"
            st.rerun()
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "⚖️"):
            st.markdown(msg["content"])

if user_input := st.chat_input("Hukuki vakayı buraya yazın..."):
    with st.chat_message("user", avatar="👤"): st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("assistant", avatar="⚖️"):
        ans = run_analysis_pipeline(user_input)
        st.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        save_current()
