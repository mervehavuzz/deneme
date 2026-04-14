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
        except Exception:
            pass
    return {}

def save_db(data: dict) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_current() -> None:
    db = load_db()
    db[st.session_state.chat_id] = st.session_state.messages
    save_db(db)

# ─────────────────────────────────────────
# API & MODEL (GÜNCELLENEN KISIM)
# ─────────────────────────────────────────
SYSTEM_PROMPT = """Senin Rolün:
Siber güvenlik hukuku, KVKK ve yapay zeka hukuku alanlarında uzman bir hukuk analiz motorusun.

Temel Görev:
Verilen senaryolarda veri işleme faaliyetlerini hukuki açıdan değerlendir, ilgili KVKK hükümlerine göre analiz yap ve sonucu gerekçelendir.

Zorunlu Analiz Metodolojisi:
Her cevap aşağıdaki sırayla ilerlemek zorundadır:

1. Veri İşleme Faaliyetini Tanımla
- Hangi veri işleniyor
- Kim işliyor (veri sorumlusu)
- Amaç ne

2. Hukuki Dayanak Analizi
- Açık rıza var mı? Varsa geçerli mi (belirli, bilgilendirilmiş, özgür irade)
- Açık rıza yoksa şu şartları TEK TEK değerlendir:
  - Kanunda açıkça öngörülme
  - Sözleşmenin kurulması/ifası
  - Hukuki yükümlülük
  - Bir hakkın tesisi/kullanılması/korunması
  - Veri sorumlusunun meşru menfaati

3. Ölçülülük Testi (ZORUNLU)
- Amaç ile araç arasında denge var mı
- Daha az müdahaleci alternatif var mı
- Veri minimizasyonu sağlanmış mı

4. Hukuka Uygunluk Sonucu
- Uygun / Riskli / Aykırı olarak sınıflandır
- Kısa gerekçe ver

5. Uyum Önerileri
- Teknik ve hukuki olarak nasıl uygun hale gelir

Öncelik Kuralı:
Açık rıza son çaredir. Öncelikle diğer hukuki işleme şartları değerlendirilir.
Eğer başka bir hukuki dayanak mevcutsa açık rızaya dayanma.

Çalışan Verisi Kuralı:
İşveren-çalışan ilişkisinde açık rıza kural olarak geçersiz kabul edilir.
Bu tür durumlarda analiz meşru menfaat ve ölçülülük üzerinden yapılır.

Yüksek Müdahale Kuralı:
Sürekli izleme, ekran kaydı, konum takibi gibi yoğun müdahale içeren işlemler
varsayılan olarak yüksek riskli kabul edilir ve sıkı ölçülülük testine tabi tutulur.

Sonuç Kuralı:
“Uygun” sonucu ancak tüm kriterler sağlanıyorsa ver.
Şüphe varsa “Riskli” olarak sınıflandır.

Bilgi Sınırı:
Verilmeyen hiçbir unsuru varsayma. Eksik bilgi varsa analizini bu sınıra göre yap.

Kurallar:
- Kesin hukuki tavsiye verme
- Yorumları KVKK sistematiğine dayandır
- Genel ifadeler kullanma, somut analiz yap
- “Güvenlik”, “etik” gibi soyut genellemelerden kaçın

Dil Kuralı:
Kısa, net ve teknik yaz. Gereksiz açıklama ve tekrar yapma.

Format:
Başlıklar kullan:
- Olay Analizi
- Hukuki Değerlendirme
- Sonuç
- Uyum Adımları

Alan Dışı:
Siber hukuk, KVKK ve yapay zeka hukuku dışındaki soruları reddet

Eğer senaryo eksikse varsayım yapma, sadece verilen bilgiler üzerinden analiz yap"""
try:
    hf_token = st.secrets["HF_TOKEN"]
    # Önerilen Model: Qwen 2.5 7B Instruct
    _model_id = "Qwen/Qwen2.5-7B-Instruct" 
    client = InferenceClient(model=_model_id, token=hf_token)
except Exception as e:
    st.error(f"API Bağlantı Hatası: {e}")
    st.stop()

# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
if "chat_id" not in st.session_state:
    st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if "messages" not in st.session_state:
    db0 = load_db()
    st.session_state.messages = db0.get(st.session_state.chat_id, [])
if "queued" not in st.session_state:
    st.session_state.queued = ""

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
            temperature=0.3,
            top_p=0.9
        ):
            token = message.choices[0].delta.content
            if token:
                text += token
                placeholder.markdown(text + "▌")
    except Exception as e:
        placeholder.error(f"⚠️ Yanıt oluşturulurken hata: {e}")
        return "Üzgünüm, şu an yanıt üretemiyorum."

    placeholder.markdown(text)
    return text

def process_message(user_text: str) -> None:
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_text)
    st.session_state.messages.append({"role": "user", "content": user_text})
    
    with st.chat_message("assistant", avatar="⚖️"):
        ph = st.empty()
        answer = stream_response(user_text, ph)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        if len(st.session_state.messages) <= 2:
            st.session_state.messages[0]["title"] = user_text[:30]
        save_current()

def load_chat(cid: str) -> None:
    db = load_db()
    st.session_state.chat_id = cid
    st.session_state.messages = db.get(cid, [])
    st.session_state.queued = ""

def new_chat() -> None:
    st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.messages = []
    st.session_state.queued = ""

def group_by_date(db: dict) -> dict:
    today = datetime.now().date()
    groups: dict = {"Bugün": [], "Bu Hafta": [], "Geçen Hafta": [], "Eskiler": []}
    for cid in sorted(db.keys(), reverse=True):
        try:
            diff = (today - datetime.strptime(cid, "%Y%m%d_%H%M%S").date()).days
            if   diff == 0:  groups["Bugün"].append(cid)
            elif diff <= 7:  groups["Bu Hafta"].append(cid)
            elif diff <= 14: groups["Geçen Hafta"].append(cid)
            else:            groups["Eskiler"].append(cid)
        except Exception:
            groups["Eskiler"].append(cid)
    return groups

# ─────────────────────────────────────────
# URL PARAM AKSİYONLARI
# ─────────────────────────────────────────
params = st.query_params
sb_action = params.get("sb_action", None)
sb_cid = params.get("sb_cid", None)

if sb_action == "new":
    new_chat()
    st.query_params.clear()
    st.rerun()
elif sb_action == "load" and sb_cid:
    load_chat(sb_cid)
    st.query_params.clear()
    st.rerun()

# ─────────────────────────────────────────
# GLOBAL CSS
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
    max-width: 1000px !important; 
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: 1rem !important;
    padding-bottom: 200px !important; 
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
.sb-group-label {{ font-size: 0.56rem; color: rgba(255,255,255,0.45); text-transform: uppercase; padding: 10px 5px; }}
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
# SIDEBAR İÇERİĞİ
# ─────────────────────────────────────────
db_sb = load_db()
grouped = group_by_date(db_sb)
history_html = ""
for grp, cids in grouped.items():
    if cids:
        history_html += f"<span class='sb-group-label'>{grp}</span>"
        for cid in cids:
            msgs_s = db_sb.get(cid, [])
            lbl = (msgs_s[0].get("title") or msgs_s[0]["content"][:22] + "…") if msgs_s else "Analiz"
            active = "sb-active" if cid == st.session_state.chat_id else ""
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
# ANA İÇERİK
# ─────────────────────────────────────────
pending = st.session_state.queued
if pending:
    st.session_state.queued = ""

in_chat = bool(st.session_state.messages) or bool(pending)

if not in_chat:
    spacer_left, center_content, spacer_right = st.columns([1.8, 7, 0.2])
    with center_content:
        st.markdown('<h1 class="wlc-title" style="text-align:center;">⚖️ Siber Hukuk Portalı</h1>', unsafe_allow_html=True)
        st.markdown('<p class="wlc-sub" style="text-align:center;">Hukuki vakayı veya dijital haklarınızı yazın, analiz edelim.</p>', unsafe_allow_html=True)
        
        CARDS = [
            ("🔒", "KVKK İhlali", "Kişisel veri ihlali durumunda ne yapmalıyım?"),
            ("💻", "Siber Saldırı", "Sisteme izinsiz erişimde hukuki adımlar nelerdir?"),
            ("📱", "Sosyal Medya Hukuku", "İnternette hakaret ve iftira davası nasıl açılır?"),
            ("🏛️", "Şikayet Dilekçesi", "BTK'ya şikayet dilekçesi nasıl hazırlanır?"),
        ]
        
        c1, c2 = st.columns(2, gap="medium")
        for i, (icon, title, desc) in enumerate(CARDS):
            col = c1 if i % 2 == 0 else c2
            with col:
                st.markdown(f'<div class="card-outer"><div class="sug-card"><div class="sug-icon">{icon}</div><div class="sug-title">{title}</div><div class="sug-desc">{desc}</div></div>', unsafe_allow_html=True)
                if st.button(title, key=f"card_{i}"):
                    st.session_state.queued = desc
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

else:
    ttl = st.session_state.messages[0].get("title", "Analiz") if st.session_state.messages else "Yeni Analiz"
    st.markdown(f'<div class="chat-topbar"><span class="chat-topbar-dot"></span><span class="chat-topbar-title">{ttl}</span></div>', unsafe_allow_html=True)
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "⚖️"):
            st.markdown(msg["content"])
    
    if pending:
        process_message(pending)

# ─────────────────────────────────────────
# CHAT INPUT
# ─────────────────────────────────────────
if new_input := st.chat_input("Hukuki vakayı buraya yazın..."):
    if not in_chat:
        st.session_state.queued = new_input
        st.rerun()
    else:
        process_message(new_input)
