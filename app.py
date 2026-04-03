import streamlit as st
import google.generativeai as genai
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
# API & MODEL
# ─────────────────────────────────────────
SYSTEM_PROMPT = (
    "Sen uzman bir Siber Hukuk Asistanısın. "
    "Yanıtlarını resmi, maddeli ve Türkiye yasalarına (TCK, KVKK, 5651 sayılı Kanun vb.) "
    "dayandırarak ver. Gerektiğinde ilgili kanun maddelerini belirt. "
    "Yanıtların net, anlaşılır ve uygulanabilir olsun."
)

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    _model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    st.error(f"API Hatası: {e}")
    st.stop()

# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
if "chat_id" not in st.session_state:
    st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if "messages" not in st.session_state:
    db0 = load_db()
    st.session_state.messages = db0.get(st.session_state.chat_id, [])
if "gem_session" not in st.session_state:
    history = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
        for m in st.session_state.messages
    ]
    st.session_state.gem_session = _model.start_chat(history=history)
if "queued" not in st.session_state:
    st.session_state.queued = ""

# ─────────────────────────────────────────
# YARDIMCILAR
# ─────────────────────────────────────────
def stream_response(prompt: str, placeholder) -> str:
    full_prompt = f"{SYSTEM_PROMPT}\n\nKullanıcı: {prompt}"
    response = st.session_state.gem_session.send_message(full_prompt, stream=True)
    text = ""
    for chunk in response:
        text += chunk.text
        placeholder.markdown(text + "▌")
    placeholder.markdown(text)
    return text

def process_message(user_text: str) -> None:
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_text)
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("assistant", avatar="⚖️"):
        ph = st.empty()
        try:
            answer = stream_response(user_text, ph)
            st.session_state.messages.append({"role": "assistant", "content": answer})
            if len(st.session_state.messages) == 2:
                st.session_state.messages[0]["title"] = user_text[:30]
            save_current()
        except Exception as err:
            ph.error(f"⚠️ Hata: {err}")
            st.session_state.messages.pop()

def load_chat(cid: str) -> None:
    db = load_db()
    msgs = db.get(cid, [])
    st.session_state.chat_id = cid
    st.session_state.messages = msgs
    st.session_state.gem_session = _model.start_chat(history=[
        {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
        for m in msgs
    ])
    st.session_state.queued = ""

def new_chat() -> None:
    st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.messages = []
    st.session_state.gem_session = _model.start_chat(history=[])
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
# URL PARAM → AKSİYON
# ─────────────────────────────────────────
params    = st.query_params
sb_action = params.get("sb_action", None)
sb_cid    = params.get("sb_cid", None)

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
SB = 260   # sidebar genişliği

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}
html, body, .stApp {{
    font-family: 'DM Sans', sans-serif !important;
    background: #F8F7FF !important;
    color: #18172B !important;
}}

/* Streamlit chrome gizle */
section[data-testid="stSidebar"]                 {{ display:none!important; }}
header[data-testid="stHeader"]                   {{ display:none!important; }}
[data-testid="stToolbar"]                        {{ display:none!important; }}
[data-testid="stDeployButton"]                   {{ display:none!important; }}
[data-testid="collapsedControl"]                 {{ display:none!important; }}
[data-testid="stSidebarCollapsedControl"]        {{ display:none!important; }}
button[data-testid="baseButton-headerNoPadding"] {{ display:none!important; }}
.stAppDeployButton                               {{ display:none!important; }}
footer                                           {{ display:none!important; }}
[data-testid="stStatusWidget"]                   {{ display:none!important; }}

/* ── ANA İÇERİK YERLEŞİMİ (KÖKTEN ÇÖZÜM) ── */
[data-testid="stAppViewContainer"] > section.main {{
    margin-left: {SB}px !important;
    width: calc(100vw - {SB}px) !important;
    padding: 0 !important;
}}

/* Tüm içeriğin bulunduğu ana kapsayıcıyı merkeze zorla */
div[data-testid="stMainBlockContainer"] {{
    max-width: 900px !important; 
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: 4.5rem !important;
    padding-bottom: 200px !important; /* Alt bar için boşluk */
}}

/* ── CUSTOM SIDEBAR ── */
#custom-sidebar {{
    position: fixed;
    top: 0; left: 0;
    width: {SB}px;
    height: 100vh;
    background: linear-gradient(160deg, #5B2FD9 0%, #7C3FFC 40%, #6A2EE8 100%);
    box-shadow: 4px 0 32px rgba(124,63,252,0.35);
    display: flex;
    flex-direction: column;
    z-index: 9999;
    overflow: hidden;
    font-family: 'DM Sans', sans-serif;
}}
.sb-header {{
    padding: 22px 16px 18px;
    border-bottom: 1px solid rgba(255,255,255,0.15);
    flex-shrink: 0;
}}
.sb-badge {{
    font-size: 0.58rem; font-weight: 700;
    color: rgba(255,255,255,0.55);
    text-transform: uppercase; letter-spacing: 0.13em;
    line-height: 1.5; margin-bottom: 10px;
}}
.sb-botname {{
    font-size: 1.25rem; font-weight: 800; color: #fff;
    letter-spacing: -0.01em; line-height: 1.2; margin-bottom: 14px;
}}
.sb-profile {{
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 10px;
}}
.sb-avatar {{
    width: 36px; height: 36px; border-radius: 50%;
    background: rgba(255,255,255,0.25);
    border: 2px solid rgba(255,255,255,0.5);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 800; color: #fff; flex-shrink: 0;
}}
.sb-name {{ font-size: 0.88rem; font-weight: 700; color: #fff; line-height: 1.2; }}
.sb-role {{ font-size: 0.65rem; color: rgba(255,255,255,0.65); margin-top: 2px; }}

.sb-new-wrap {{ padding: 14px 12px 10px; flex-shrink: 0; }}
.sb-new-btn {{
    width: 100%; padding: 10px 0;
    background: linear-gradient(135deg, #C47FFF 0%, #A040FF 50%, #8A1FFF 100%);
    border: none; border-radius: 10px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 700; font-size: 0.84rem; color: #fff;
    cursor: pointer; letter-spacing: 0.01em;
    box-shadow: 0 0 0 1px rgba(196,127,255,0.4),
                0 4px 20px rgba(160,64,255,0.7),
                0 0 40px rgba(160,64,255,0.35);
    transition: all .2s ease;
}}
.sb-new-btn:hover {{
    background: linear-gradient(135deg, #D490FF 0%, #B050FF 50%, #9A30FF 100%);
    transform: translateY(-1px);
    box-shadow: 0 0 0 1px rgba(212,144,255,0.5),
                0 6px 28px rgba(160,64,255,0.85),
                0 0 60px rgba(160,64,255,0.5);
}}
.sb-divider {{ height: 1px; background: rgba(255,255,255,0.15); margin: 0 12px 4px; flex-shrink: 0; }}
.sb-history {{ flex: 1 1 auto; overflow-y: auto; padding-bottom: 16px; }}
.sb-history::-webkit-scrollbar {{ width: 4px; }}
.sb-history::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.25); border-radius: 4px; }}
.sb-group-label {{
    display: block; font-size: 0.56rem; font-weight: 700;
    color: rgba(255,255,255,0.45); text-transform: uppercase;
    letter-spacing: 0.1em; padding: 10px 14px 2px;
}}
.sb-chat-btn {{
    display: block; width: 100%; text-align: left;
    background: transparent; border: none;
    font-family: 'DM Sans', sans-serif; font-size: 0.76rem;
    color: rgba(237,233,255,0.75); border-radius: 6px;
    padding: 6px 12px; cursor: pointer;
    transition: all .15s ease;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.sb-chat-btn:hover {{ background: rgba(255,255,255,0.12); color: #fff; }}
.sb-chat-btn.sb-active {{
    background: rgba(255,255,255,0.18); color: #fff; font-weight: 600;
    border-left: 2px solid rgba(255,255,255,0.9);
    border-radius: 0 6px 6px 0; padding-left: 10px;
}}
.sb-empty {{
    padding: 20px 14px; text-align: center;
    color: rgba(255,255,255,0.35); font-size: 0.72rem; line-height: 1.6;
}}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {{ background: transparent !important; padding: 0.3rem 0 !important; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
    [data-testid="stMarkdownContainer"] {{
    background: #7C5CFC !important; color: #fff !important;
    border-radius: 16px 16px 4px 16px !important; padding: 11px 16px !important;
    box-shadow: 0 2px 10px rgba(124,92,252,.28) !important;
}}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
    [data-testid="stMarkdownContainer"] p,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
    [data-testid="stMarkdownContainer"] li {{ color: #fff !important; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])
    [data-testid="stMarkdownContainer"] {{
    background: #fff !important; color: #18172B !important;
    border: 1px solid #E4E0FF !important; border-radius: 4px 16px 16px 16px !important;
    padding: 13px 18px !important; box-shadow: 0 1px 6px rgba(80,70,180,.07) !important;
}}

/* ── Welcome ekranı ── */
.wlc-title {{
    font-size: 2.2rem; font-weight: 700; color: #18172B;
    text-align: center; margin: 0 0 0.25rem; letter-spacing: -0.02em;
}}
.wlc-sub {{ text-align: center; color: #6B6890; font-size: 0.9rem; margin-bottom: 2.5rem; }}

/* Kart wrapper */
.card-outer {{
    position: relative;
    margin-bottom: 8px;
    height: 100%;
}}
.sug-card {{
    background: #fff;
    border: 1.5px solid #E4E0FF;
    border-radius: 12px;
    padding: 16px;
    height: 100%;
    transition: border-color .15s, box-shadow .15s;
}}
.sug-card:hover {{
    border-color: #B8AEFF;
    box-shadow: 0 4px 16px rgba(124,92,252,.12);
}}
.sug-icon  {{ font-size: 1.4rem; margin-bottom: 8px; }}
.sug-title {{ font-size: 0.9rem; font-weight: 600; color: #18172B; line-height: 1.3; margin-bottom: 4px; }}
.sug-desc  {{ font-size: 0.75rem; color: #7B78A0; margin-top: 2px; line-height: 1.45; }}

/* Görünmez Streamlit butonu */
.card-btn {{
    position: absolute !important;
    inset: 0 !important;
    z-index: 5 !important;
    margin: 0 !important;
    padding: 0 !important;
}}
.card-btn > div,
.card-btn [data-testid="stButtonContainer"],
.card-btn [data-testid="baseButton-secondary"] {{
    position: absolute !important;
    inset: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    height: 100% !important;
    width: 100% !important;
}}
.card-btn button {{
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    min-height: unset !important;
    opacity: 0 !important;
    border: none !important;
    background: transparent !important;
    cursor: pointer !important;
    margin: 0 !important;
    padding: 0 !important;
    z-index: 10 !important;
}}

/* Streamlit column gap */
[data-testid="stHorizontalBlock"] {{
    gap: 16px !important;
    align-items: stretch !important;
}}
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlock"] > div {{
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}}

/* chip butonları */
.chip-row {{
    margin-top: 20px !important;
    display: flex;
    justify-content: center;
}}
.chip-row button {{
    background: #fff !important; color: #5B3FD9 !important;
    border: 1.5px solid #D4CFFF !important; border-radius: 100px !important;
    padding: 6px 16px !important; font-size: 0.78rem !important; font-weight: 600 !important;
    transition: all .15s !important;
    width: 100% !important;
}}
.chip-row button:hover {{ background: #EDE9FF !important; border-color: #7C5CFC !important; }}

.chat-topbar {{
    display: flex; align-items: center; gap: 8px;
    padding: 4px 0 14px; border-bottom: 1px solid #E4E0FF; margin-bottom: 10px;
}}
.chat-topbar-dot {{ width: 7px; height: 7px; background: #22D49A; border-radius: 50%; flex-shrink: 0; }}
.chat-topbar-title {{ font-size: 0.83rem; font-weight: 500; color: #18172B; }}

/* ── Modern Chat input + Uyarı yazısı alt bar ── */
[data-testid="stBottom"] {{
    position: fixed !important;
    bottom: 0 !important;
    left: {SB}px !important;
    width: calc(100vw - {SB}px) !important;
    background: rgba(248,247,255,0.92) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-top: 1px solid rgba(180,170,255,0.3) !important;
    z-index: 999 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    box-shadow: 0 -8px 32px rgba(90,75,200,0.08) !important;
}}

[data-testid="stBottomBlockContainer"] {{
    width: 100% !important;
    max-width: 900px !important; 
    margin: 0 auto !important;
    padding: 12px 1.5rem 0px 1.5rem !important;
}}

/* ESKİ ÜST YAZIYI SİLDİK */
[data-testid="stBottomBlockContainer"]::before {{
    display: none !important; 
}}

/* YENİ UYARI YAZISI KUTUNUN ALTINDA VE DAHA BÜYÜK */
[data-testid="stBottomBlockContainer"]::after {{
    content: "⚠️ Bu platform hukuki tavsiye niteliği taşımamaktadır. Yalnızca genel rehberlik amaçlıdır. Hukuki süreçler için bir avukana danışmanız önerilir.";
    display: block;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.75rem; /* Font büyütüldü */
    font-weight: 500;
    color: #7B78A0;
    text-align: center;
    padding-top: 12px; /* Kutu ile arasına boşluk */
    padding-bottom: 24px; /* Manage App (watermark) butonundan kurtulmak için alt boşluk */
    line-height: 1.5;
}}

/* Input kutusu - Boyutu Küçültüldü */
[data-testid="stChatInput"] {{
    background: #fff !important;
    border: 1.5px solid rgba(180,160,255,0.5) !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 20px rgba(90,75,200,0.10), inset 0 1px 0 rgba(255,255,255,0.9) !important;
    padding: 2px 6px 2px 14px !important; /* Dikey padding (iç boşluk) azaltıldı */
    min-height: 44px !important; /* Minimum yükseklik azaltıldı */
    display: flex !important;
    align-items: center !important;
    transition: all .2s ease !important;
}}
[data-testid="stChatInput"]:focus-within {{
    border-color: #7C5CFC !important;
    box-shadow: 0 0 0 3px rgba(124,92,252,0.12), 0 4px 24px rgba(124,92,252,.18) !important;
}}
[data-testid="stChatInput"] textarea {{
    background: transparent !important; border: none !important;
    outline: none !important; box-shadow: none !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important; color: #18172B !important;
    padding: 8px 0 !important; /* Text alanı dikey padding azaltıldı */
    min-height: 24px !important;
    resize: none !important;
    line-height: 1.4 !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{
    color: #B0ADCC !important;
    font-size: 0.88rem !important;
}}
/* Gönder butonu — boyutu inputa uyarlandı */
[data-testid="stChatInput"] button {{
    background: linear-gradient(135deg, #8B5CFC 0%, #5B30D0 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    width: 34px !important;
    min-width: 34px !important;
    height: 34px !important; /* Buton da küçültüldü */
    box-shadow: 0 4px 14px rgba(90,75,200,.45) !important;
    color: #fff !important;
    transition: all .2s ease !important;
    margin: 0 !important;
    padding: 0 !important;
}}
[data-testid="stChatInput"] button:hover {{
    background: linear-gradient(135deg, #9F70FF 0%, #6B40E8 100%) !important;
    box-shadow: 0 6px 20px rgba(124,92,252,.6) !important;
    transform: translateY(-1px) !important;
}}
[data-testid="stChatInput"] button svg {{ fill: #fff !important; stroke: #fff !important; width: 16px; height: 16px; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CUSTOM SIDEBAR
# ─────────────────────────────────────────
db_sb      = load_db()
grouped    = group_by_date(db_sb)
current_id = st.session_state.chat_id

history_html = ""
has_history  = any(cids for cids in grouped.values())

if not has_history:
    history_html = "<div class='sb-empty'>Henüz geçmiş analiz yok.<br>Yeni bir analiz başlatın.</div>"
else:
    for grp, cids in grouped.items():
        if not cids:
            continue
        history_html += f"<span class='sb-group-label'>{grp}</span>"
        for cid in cids:
            msgs_s   = db_sb.get(cid, [])
            lbl      = (msgs_s[0].get("title") or msgs_s[0]["content"][:22] + "…") if msgs_s else "Analiz"
            lbl_safe = lbl.replace("'", "\\'").replace('"', "&quot;")
            active   = "sb-active" if cid == current_id else ""
            history_html += (
                f"<button class='sb-chat-btn {active}' "
                f"onclick=\"goLoad('{cid}')\">💬 {lbl_safe}</button>"
            )

st.markdown(f"""
<div id="custom-sidebar">
  <div class="sb-header">
    <div class="sb-badge">Bilişim Güvenliği Teknolojisi<br>Bitirme Projesi</div>
    <div class="sb-botname">⚖️ Siber Hukuk Botu</div>
    <div class="sb-profile">
      <div class="sb-avatar">MH</div>
      <div>
        <div class="sb-name">Merve Havuz</div>
        <div class="sb-role">Proje Sahibi</div>
      </div>
    </div>
  </div>
  <div class="sb-new-wrap">
    <button class="sb-new-btn" onclick="goNew()">＋&nbsp;&nbsp;Yeni Analiz</button>
  </div>
  <div class="sb-divider"></div>
  <div class="sb-history">{history_html}</div>
</div>

<script>
function goNew() {{
    var u = new URL(window.location.href);
    u.searchParams.set('sb_action', 'new');
    u.searchParams.delete('sb_cid');
    window.location.href = u.toString();
}}
function goLoad(cid) {{
    var u = new URL(window.location.href);
    u.searchParams.set('sb_action', 'load');
    u.searchParams.set('sb_cid', cid);
    window.location.href = u.toString();
}}
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# ANA ALAN
# ─────────────────────────────────────────
pending = st.session_state.queued
if pending:
    st.session_state.queued = ""

in_chat = bool(st.session_state.messages) or bool(pending)

if not in_chat:
    # --- YIK VE YENİDEN YAP KISMI ---
    # İçeriği css ile değil, doğrudan streamlit kolonlarıyla sağa itip merkeze sabitliyoruz
    spacer_left, center_content, spacer_right = st.columns([1, 8, 1])
    
    with center_content:
        st.markdown('<h1 class="wlc-title">⚖️ Siber Hukuk Portalı</h1>', unsafe_allow_html=True)
        st.markdown('<p class="wlc-sub">Hukuki vakayı veya dijital haklarınızı yazın, analiz edelim.</p>', unsafe_allow_html=True)

        CARDS = [
            ("🔒", "KVKK İhlali",        "Kişisel veri ihlali durumunda ne yapmalıyım?"),
            ("💻", "Siber Saldırı",       "Sisteme izinsiz erişimde hukuki adımlar nelerdir?"),
            ("📱", "Sosyal Medya Hukuku", "İnternette hakaret ve iftira davası nasıl açılır?"),
            ("🏛️", "Şikayet Dilekçesi",  "BTK'ya şikayet dilekçesi nasıl hazırlanır?"),
        ]

        c1, c2 = st.columns(2, gap="medium")
        for i, (icon, title, desc) in enumerate(CARDS):
            col = c1 if i % 2 == 0 else c2
            with col:
                st.markdown(f"""
                <div class="card-outer">
                  <div class="sug-card">
                    <div class="sug-icon">{icon}</div>
                    <div class="sug-title">{title}</div>
                    <div class="sug-desc">{desc}</div>
                  </div>
                  <div class="card-btn">
                """, unsafe_allow_html=True)
                if st.button(title, key=f"card_{i}"):
                    st.session_state.queued = desc
                    st.rerun()
                st.markdown("</div></div>", unsafe_allow_html=True) 

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        CHIPS = [
            ("📄 Dilekçe", "Siber suç için resmi dilekçe oluşturmama yardım et."),
            ("⏱ Süre?",   "Siber suçlarda başvuru ve dava açma süreleri nedir?"),
            ("💰 Ceza?",  "Siber suçlarda öngörülen ceza miktarları nedir?"),
            ("🔍 Kanun",  "Türkiye'de siber suçlarla ilgili kanun maddeleri nelerdir?"),
        ]
        st.markdown("<div class='chip-row'>", unsafe_allow_html=True)
        chip_cols = st.columns(len(CHIPS), gap="small")
        for col_chip, (label, question) in zip(chip_cols, CHIPS):
            with col_chip:
                if st.button(label, key=f"chip_{label}"):
                    st.session_state.queued = question
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

else:
    if st.session_state.messages:
        ttl = st.session_state.messages[0].get(
            "title", st.session_state.messages[0]["content"][:50] + "…"
        )
    else:
        ttl = (pending[:50] + "…") if pending else "Yeni Analiz"

    st.markdown(f"""
    <div class="chat-topbar">
        <span class="chat-topbar-dot"></span>
        <span class="chat-topbar-title">{ttl}</span>
    </div>""", unsafe_allow_html=True)

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
