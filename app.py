import streamlit as st
import google.generativeai as genai
import re
import time
from datetime import datetime
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

# ─────────────────────────────────────────
# 1. SEANS YÖNETİMİ
# ─────────────────────────────────────────
if "browser_db" not in st.session_state:
    st.session_state.browser_db = {}

def load_db(): return st.session_state.browser_db
def save_db(data): st.session_state.browser_db = data

# ─────────────────────────────────────────
# 2. MEVZUAT VERİTABANI
# ─────────────────────────────────────────
MEVZUAT = {
    "106": "TCK 106 - Tehdit: Bir başkasını hayatına, vücut veya cinsel dokunulmazlığına yönelik saldırı gerçekleştireceğinden bahisle tehdit eden kişi altı aydan iki yıla kadar hapis cezası ile cezalandırılır.",
    "107": "TCK 107 - Şantaj: Bir kişinin şeref veya saygınlığına zarar verecek hususların açıklanacağı tehdidiyle yarar sağlamaya zorlama; bir yıldan üç yıla kadar hapis ve adlî para cezası.",
    "123": "TCK 123 - Huzur ve sükunu bozma: Israrlı telefon veya mesajla kişinin huzurunu bozma; üç aydan bir yıla kadar hapis.",
    "125": "TCK 125 - Hakaret: Onur ve saygınlığı rencide eden fiil veya sövme; üç aydan iki yıla kadar hapis veya adlî para cezası.",
    "132": "TCK 132 - Haberleşme gizliliğini ihlal: Kişiler arasındaki haberleşmenin gizliliğini ihlal; bir yıldan üç yıla kadar hapis. İçerik kaydedilmişse ceza bir kat artırılır.",
    "134": "TCK 134 - Özel hayat gizliliğini ihlal: Özel hayatı ihlal eden kimseye bir yıldan üç yıla kadar hapis. Görüntü/ses ifşası halinde iki yıldan beş yıla kadar hapis.",
    "136": "TCK 136 - Kişisel verileri yayma: Kişisel verileri hukuka aykırı olarak başkasına veren veya yayan kişi iki yıldan dört yıla kadar hapis cezası ile cezalandırılır.",
    "158": "TCK 158/2-f - Nitelikli dolandırıcılık: Bilişim sistemleri araç kılınarak dolandırıcılık; üç yıldan on yıla kadar hapis ve adlî para cezası.",
    "226": "TCK 226 - Müstehcenlik: Müstehcen görüntülerin üretilmesi veya dağıtılması; altı aydan iki yıla kadar hapis ve adlî para cezası.",
    "243": "TCK 243 - Bilişim sistemine girme: Bir bilişim sistemine hukuka aykırı olarak giren kimseye bir yıla kadar hapis veya adlî para cezası verilir.",
    "244": "TCK 244 - Sistemi bozma: Bilişim sisteminin işleyişini engelleyen veya bozan kişi bir yıldan beş yıla kadar hapis cezası ile cezalandırılır.",
}

# ─────────────────────────────────────────
# 3. KEYWORD BAZLI MADDE TESPİTİ
# ─────────────────────────────────────────
KURALLAR = [
    (["şantaj", "para istiyor", "para istedi", "ödeme iste", "para ver", "para gönder"],
     ["107", "106"], False),
    (["fotoğraf", "görüntü", "video", "ifşa", "yayacak", "yayacağım", "sızdır", "özel resim"],
     ["134", "226", "107"], False),
    (["hack", "hacklendi", "hesabım ele", "şifrem değişti", "giriş yapamıyorum",
      "hesabıma girdi", "hesabım çalındı"],
     ["243", "136"], False),
    (["instagram", "twitter", "facebook", "tiktok", "sosyal medya hesabım"],
     ["243", "136"], False),
    (["banka", "kredi kartı", "para çekildi", "dolandırıcı", "dolandırıldım",
      "sahte mesaj", "aradılar", "telefon açıp"],
     ["158", "243"], False),
    (["patronum", "işyerinde", "şirket bilgisayarı", "yazışmalarımı takip",
      "izliyor", "gözetliyor", "yazılım kurdu", "ekranımı"],
     ["132"], True),
    (["hakaret", "küfür", "aşağıladı", "rezil etti", "onurumu"],
     ["125"], False),
    (["tehdit", "zarar vereceğim", "saldıracağım", "öldüreceğim"],
     ["106"], False),
    (["mesaj atmaya devam", "aramayı bırakmıyor", "ısrarlı", "defalarca aradı", "rahatsız ediyor"],
     ["123"], False),
    (["kişisel verilerim", "verilerimi sattı", "verilerimi yaydı", "bilgilerimi paylaştı"],
     ["136"], False),
]

def madde_tespit(user_input):
    girdi = user_input.lower()
    bulunan_nums = []
    kvkk_var = False
    for keywords, maddeler, kvkk in KURALLAR:
        if any(k in girdi for k in keywords):
            for m in maddeler:
                if m not in bulunan_nums:
                    bulunan_nums.append(m)
            if kvkk:
                kvkk_var = True
    mevzuat_metni = "\n".join([MEVZUAT[n] for n in bulunan_nums if n in MEVZUAT])
    madde_listesi = []
    for n in bulunan_nums:
        etiket = "TCK 158/2-f" if n == "158" else f"TCK {n}"
        if etiket not in madde_listesi:
            madde_listesi.append(etiket)
    if kvkk_var:
        madde_listesi.append("KVKK Madde 12")
    return madde_listesi, mevzuat_metni, kvkk_var

# ─────────────────────────────────────────
# 4. SAYFA AYARLARI VE CSS
# ─────────────────────────────────────────
st.set_page_config(page_title="Siber Hukuk Analiz Sistemi", page_icon="⚖️", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
.stApp { background: #F8F7FF !important; }
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #5B2FD9 0%, #7C3FFC 40%, #6A2EE8 100%) !important;
}
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] div { color: white !important; }
[data-testid="stSidebar"] button p { color: #1A1A1A !important; font-weight: 500 !important; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #7C5CFC !important; border-radius: 15px 15px 5px 15px !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: white !important; border: 1px solid #E4E0FF !important;
    border-radius: 5px 15px 15px 15px !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 5. GEMİNİ API KURULUMU (GÜNCELLENDİ)
# ─────────────────────────────────────────
try:
    # YENİ TEMİZ API ANAHTARINI BURAYA YAPIŞTIR (Secrets yerine doğrudan koddan okuyacak)
    YENI_API_KEY = "AIzaSyD0ReXAruklePU10Nhu3lUDkwSuYRt2DAc"
    
    
    genai.configure(api_key=YENI_API_KEY)
    gemini_model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction="""Sen Türkiye Cumhuriyeti yasalarına hakim, ihtiyatlı ve profesyonel bir Siber Hukuk Asistanısın.
        ... (Sistem promptunun geri kalanı aynen kalacak) ..."""
    )
except Exception as e:
    st.error(f"Gemini API Hatası: {e}")
    st.stop()

# ─────────────────────────────────────────
# 6. LLM ÇAĞRISI
# ─────────────────────────────────────────
def call_llm(prompt, gecmis=None):
    bekleme = 5
    for deneme in range(4):
        try:
            history = []
            if gecmis:
                for msg in gecmis[-4:]:
                    role = "user" if msg["role"] == "user" else "model"
                    history.append({"role": role, "parts": [msg["content"]]})
            chat = gemini_model.start_chat(history=history)
            response = chat.send_message(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=8192,  # ← Yarıda kesilme sorunu çözüldü
                )
            )
            return response.text
        except ResourceExhausted:
            if deneme < 3:
                st.warning(f"⏳ Kota sınırı aşıldı. {bekleme} saniye içinde tekrar denenecek...")
                time.sleep(bekleme)
                bekleme *= 2
            else:
                return "⚠️ Google API kotası doldu. Lütfen 1 dakika sonra tekrar deneyin."
        except GoogleAPIError as e:
            return f"API hatası: {str(e)}"
        except Exception as e:
            return f"Beklenmeyen hata: {str(e)}"
    return "Analiz tamamlanamadı."

# ─────────────────────────────────────────
# 7. ANA PIPELINE
# ─────────────────────────────────────────
SELAMLAR = {"merhaba", "selam", "mrb", "slm", "hello", "hi",
            "iyi günler", "iyi akşamlar", "hey", "nasılsın", "kimsin"}

def run_pipeline(user_query, gecmis=None):
    temiz = user_query.strip().lower()
    if temiz in SELAMLAR or len(user_query.strip()) < 4:
        return ("Merhaba! Ben Siber Hukuk Analiz Asistanıyım. Yaşadığınız siber mağduriyeti "
                "veya dijital hukuk sorununuzu anlatın; TCK ve KVKK kapsamında analiz edeyim.")

    with st.status("⚖️ Analiz Yapılıyor...", expanded=True) as status:
        st.write("⚙️ İlgili mevzuat tespit ediliyor...")
        maddeler, mevzuat_metni, kvkk_var = madde_tespit(user_query)

        kvkk_paragraf = (
            "- İdare Hukuku (KVKK): Patron/işveren veri sorumlusu sıfatıyla "
            "KVKK Madde 12 kapsamında yükümlüdür. Çalışanın yazışmalarının "
            "rıza alınmadan izlenmesi veri güvenliği ihlali olarak değerlendirilebilir."
            if kvkk_var else
            "- İdare Hukuku (KVKK): Bu vakada KVKK kapsamında kurumsal "
            "veri ihlali unsuru tespit edilmemiştir."
        )

        st.write("✍️ Hukuki rapor oluşturuluyor...")
        prompt = f"""Olay: {user_query}

Tespit Edilen Maddeler: {maddeler if maddeler else "Genel hukuki değerlendirme yapılacak"}

Mevzuat:
{mevzuat_metni if mevzuat_metni else "Genel TCK hükümleri uygulanacak"}

Cevabını KESİNLİKLE şu beş başlıkla yaz. Hiçbir bilgiyi tekrarlama:

OLAYIN HUKUKİ NİTELİĞİ
(Vakanın kısa ve net hukuki tanımı — 2-3 cümle)

OLASI SUÇ VE İHLALLER
- Ceza Hukuku (TCK): (Tespit edilen maddeleri ihtiyatlı dille açıkla)
{kvkk_paragraf}

HUKUKİ DEĞERLENDİRME
(Somut olayın özgün analizi — 3-4 cümle, şablon cümle kopyalama)

PRATİK OLARAK YAPILABİLECEKLER
(Bu vakaya özgü, birbirinden farklı 4 somut adım)

RESMİ BAŞVURU YOLLARI
(En uygun 2-3 başvuru mekanizması — kısa ve net)"""

        final = call_llm(prompt, gecmis=gecmis)
        status.update(label="✅ Analiz Tamamlandı!", state="complete", expanded=False)

    return final

# ─────────────────────────────────────────
# 8. SIDEBAR VE ANA EKRAN
# ─────────────────────────────────────────
db = load_db()
if "chat_id" not in st.session_state:
    st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("### ⚖️ Siber Hukuk Analiz")
    st.write("**Merve Havuz** - Bitirme Projesi")
    if st.button("➕ Yeni Analiz", use_container_width=True):
        st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    for cid in sorted(db.keys(), reverse=True):
        first_user_msg = next(
            (m["content"] for m in db.get(cid, []) if m["role"] == "user"), ""
        )
        if first_user_msg:
            words = first_user_msg.split()
            display_title = " ".join(words[:4]) + ("..." if len(words) > 4 else "")
        else:
            display_title = f"💬 Analiz {cid[:10]}"
        if st.button(display_title, key=cid, use_container_width=True):
            st.session_state.chat_id = cid
            st.session_state.messages = db[cid]
            st.rerun()

st.title("Siber Hukuk Analiz Portalı")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "⚖️"):
        st.markdown(msg["content"])

if prompt := st.chat_input("Hukuki senaryoyu buraya yazın..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="⚖️"):
        gecmis = st.session_state.messages[:-1] if len(st.session_state.messages) > 1 else None
        answer = run_pipeline(prompt, gecmis=gecmis)
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        db[st.session_state.chat_id] = st.session_state.messages
        save_db(db)
