import streamlit as st
import google.generativeai as genai
import json
import os
import re
from datetime import datetime

# ─────────────────────────────────────────
# 1. TARAYICI BAZLI SEANS VE HAFIZA YÖNETİMİ
# ─────────────────────────────────────────
if "browser_db" not in st.session_state:
    st.session_state.browser_db = {}

def load_db() -> dict:
    return st.session_state.browser_db

def save_db(data: dict) -> None:
    st.session_state.browser_db = data

# ─────────────────────────────────────────
# 2. HUKUK VERİTABANI VE MEVZUAT
# ─────────────────────────────────────────
HUKUK_DB = {
    "yetkisiz_erisim":      {"madde": "TCK 243",           "aciklama": "Bilişim sistemine girme suçu."},
    "sistem_bozma":         {"madde": "TCK 244",           "aciklama": "Sistemi engelleme, bozma, verileri yok etme."},
    "veri_calma":           {"madde": "TCK 136",           "aciklama": "Kişisel verileri hukuka aykırı ele geçirme."},
    "mail_okuma":           {"madde": "TCK 132",           "aciklama": "Haberleşmenin gizliliğini ihlal."},
    "is_yeri_gozetleme":    {"madde": "TCK 132",           "aciklama": "İşyerinde yazışmaların izlenmesi."},
    "veri_guvenligi":       {"madde": "KVKK Madde 12",     "aciklama": "Veri güvenliği yükümlülükleri."},
    "santaj":               {"madde": "TCK 107",           "aciklama": "Şantaj suçu."},
    "tehdit":               {"madde": "TCK 106",           "aciklama": "Tehdit suçu."},
    "ifsa":                 {"madde": "TCK 134",           "aciklama": "Özel hayatın gizliliğini ihlal."},
    "hesap_ele_gecirme":    {"madde": "TCK 243",           "aciklama": "Bilişim sistemine hukuka aykırı erişim."},
    "dolandiricilik":       {"madde": "TCK 158/2-f",       "aciklama": "Bilişim sistemleri araç kılınarak dolandırıcılık."},
    "oltalama":             {"madde": "TCK 243",           "aciklama": "Bilişim sistemine girme (oltalama amaçlı)."},
    "kimlik_taklidi":       {"madde": "TCK 136",           "aciklama": "Başkasına ait verileri yayma/kullanma."},
    "taciz":                {"madde": "TCK 105/123",       "aciklama": "Cinsel taciz veya kişilerin huzurunu bozma."},
    "ozel_goruntu_ifsasi":  {"madde": "TCK 134+226",       "aciklama": "Özel görüntü ifşası."},
    "sosyal_medya_erisim":  {"madde": "TCK 243",           "aciklama": "Sosyal medya hesabına yetkisiz erişim."},
    "veri_ihlali":          {"madde": "KVKK Madde 12",     "aciklama": "Kişisel verilerin güvenliğinin ihlali."},
    "hakaret":              {"madde": "TCK 125",           "aciklama": "Hakaret suçu."},
    "platform_sorumlulugu": {"madde": "5651 Sayılı Kanun", "aciklama": "İnternet ortamında yapılan yayınların düzenlenmesi."},
}

MEVZUAT = {
    "106": "TCK 106 - Tehdit suçu: Bir başkasını, kendisinin veya yakınının hayatına, vücut veya cinsel dokunulmazlığına yönelik bir saldırı gerçekleştireceğinden bahisle tehdit eden kişi, altı aydan iki yıla kadar hapis cezası ile cezalandırılır.",
    "107": "TCK 107 - Şantaj suçu: Kendisine veya başkasına yarar sağlamak maksadıyla bir kişinin şeref veya saygınlığına zarar verecek nitelikteki hususların açıklanacağı veya isnat edileceği tehdidinde bulunulması halinde bir yıldan üç yıla kadar hapis ve beşbin güne kadar adlî para cezası verilir.",
    "123": "TCK 123 - Kişilerin huzur ve sükununu bozma: Sırf huzur ve sükununu bozmak maksadıyla bir kimseye ısrarlı bir şekilde telefon edilmesi veya aynı maksatla hukuka aykırı başka bir davranışta bulunulması halinde üç aydan bir yıla kadar hapis cezası verilir.",
    "125": "TCK 125 - Hakaret suçu: Bir kimseye onur, şeref ve saygınlığını rencide edebilecek nitelikte somut bir fiil veya olgu isnat eden kişi, üç aydan iki yıla kadar hapis veya adlî para cezası ile cezalandırılır.",
    "132": "TCK 132 - Haberleşmenin gizliliğini ihlal: Kişiler arasındaki haberleşmenin gizliliğini ihlal eden kimse, bir yıldan üç yıla kadar hapis cezası ile cezalandırılır. İçeriklerin kaydedilmesi suretiyle ihlal halinde ceza bir kat artırılır.",
    "134": "TCK 134 - Özel hayatın gizliliğini ihlal: Kişilerin özel hayatının gizliliğini ihlal eden kimse bir yıldan üç yıla kadar hapis cezası ile cezalandırılır. Görüntü veya seslerin hukuka aykırı olarak ifşa edilmesi halinde iki yıldan beş yıla kadar hapis cezası verilir.",
    "136": "TCK 136 - Kişisel verileri hukuka aykırı olarak ele geçirme veya yayma: Kişisel verileri hukuka aykırı olarak bir başkasına veren, yayan veya ele geçiren kişi, iki yıldan dört yıla kadar hapis cezası ile cezalandırılır.",
    "158": "TCK 158 - Nitelikli dolandırıcılık: Bilişim sistemlerinin araç olarak kullanılması suretiyle dolandırıcılık suçunun işlenmesi halinde üç yıldan on yıla kadar hapis ve beşbin güne kadar adlî para cezasına hükmolunur.",
    "226": "TCK 226 - Müstehcenlik: Müstehcen görüntü, yazı veya sözleri içeren ürünlerin üretilmesi, dağıtılması veya yayınlanması halinde altı aydan iki yıla kadar hapis ve adlî para cezasına hükmolunur.",
    "243": "TCK 243 - Bilişim sistemine girme: Bir bilişim sisteminin bütününe veya bir kısmına hukuka aykırı olarak giren veya orada kalmaya devam eden kimseye bir yıla kadar hapis veya adlî para cezası verilir.",
    "244": "TCK 244 - Sistemi engelleme, bozma, verileri yok etme: Bir bilişim sisteminin işleyişini engelleyen veya bozan kişi bir yıldan beş yıla kadar hapis cezası ile cezalandırılır.",
}

def retrieve_mevzuat(maddeler):
    bulunanlar = []
    for madde in maddeler:
        nums = re.findall(r'\d+', madde)
        for n in nums:
            if n in MEVZUAT and MEVZUAT[n] not in bulunanlar:
                bulunanlar.append(MEVZUAT[n])
    return "\n".join(bulunanlar) if bulunanlar else "İlgili mevzuat bulunamadı."

# ─────────────────────────────────────────
# 3. SAYFA AYARLARI VE CSS
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
[data-testid="stSidebar"] button p {
    color: #1A1A1A !important;
    font-weight: 500 !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #7C5CFC !important;
    border-radius: 15px 15px 5px 15px !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: white !important;
    border: 1px solid #E4E0FF !important;
    border-radius: 5px 15px 15px 15px !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 4. GEMİNİ API VE MANTIK MOTORU
# ─────────────────────────────────────────
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-001",
        generation_config={"temperature": 0.2, "max_output_tokens": 1500}
    )
except Exception as e:
    st.error(f"Gemini API Hatası: {e}")
    st.stop()

SISTEM_PROMPTU = """Sen Türkiye Cumhuriyeti yasalarına hakim, ihtiyatlı ve profesyonel bir Siber Hukuk Asistanısın.

KIRMIZI ÇİZGİLERİN:
1. Kullanıcıyı asla yargılama, ahlaki ders verme veya kurbanı suçlayıcı cümleler kurma.
2. "Şu suç oluşmuştur" veya "ceza alır" gibi kesin hüküm ifadeleri KULLANMA. Daima "değerlendirilebilir", "gündeme gelebilir", "iddia edilmesi halinde" gibi ihtiyatlı dil kullan.
3. TEKRAR YASAĞI: Hiçbir cümleyi, maddeyi veya adımı iki kez yazma. Her bilgi yalnızca bir kez geçecek.
4. MADDE SEÇME KURALLARI:
   - Para veya çıkar karşılığı tehdit → TCK 107 (Şantaj) MUTLAKA değerlendir
   - Özel görüntü/fotoğraf ifşası veya tehdidi → TCK 134 ve TCK 226 birlikte değerlendir
   - İşyerinde patron tarafından yazışma izleme → TCK 132 önceliklidir; TCK 243/244 bu vakaya uygulanmaz
   - Sosyal medya/e-posta hesabı ele geçirme → TCK 243
   - Telefon veya mesajla banka/kimlik bilgisi alma → TCK 158/2-f önceliklidir
   - İşyeri vakasında patron veri sorumlusu sıfatıyla KVKK Madde 12'ye tabidir; "ihlal yok" yazma
5. Bireyler arası vakada (kurumsal taraf yoksa) KVKK bölümüne "Bu vakada KVKK kapsamında kurumsal veri ihlali unsuru tespit edilmemiştir" yaz.
6. Cevabını KESİNLİKLE şu beş başlıkla yapılandır:

OLAYIN HUKUKİ NİTELİĞİ
OLASI SUÇ VE İHLALLER
HUKUKİ DEĞERLENDİRME
PRATİK OLARAK YAPILABİLECEKLER
RESMİ BAŞVURU YOLLARI"""

def hukuki_filtre(user_input):
    kurallar = {
        "şantaj":        "TCK 107 (Şantaj) — para veya yarar karşılığı tehdit",
        "para istedi":   "TCK 107 (Şantaj) — para veya yarar karşılığı tehdit",
        "para istiyor":  "TCK 107 (Şantaj) — para veya yarar karşılığı tehdit",
        "yayacağım":     "TCK 107 (Şantaj) + TCK 134 (Özel Hayat) + TCK 226 (Müstehcenlik)",
        "yayacak":       "TCK 107 (Şantaj) + TCK 134 (Özel Hayat) + TCK 226 (Müstehcenlik)",
        "fotoğraf":      "TCK 134 (Özel Hayat) + TCK 226 (Müstehcenlik)",
        "görüntü":       "TCK 134 (Özel Hayat) + TCK 226 (Müstehcenlik)",
        "izliyor":       "TCK 132 (Haberleşme Gizliliği) + KVKK Madde 12",
        "takip ediyor":  "TCK 132 (Haberleşme Gizliliği)",
        "yazılım kurdu": "TCK 132 (Haberleşme Gizliliği) + KVKK Madde 12",
        "hacklendi":     "TCK 243 (Bilişim Sistemine Girme)",
        "hack":          "TCK 243 (Bilişim Sistemine Girme)",
        "sızdırıldı":    "TCK 136 (Verileri Yayma)",
        "ifşa":          "TCK 134 (Özel Hayat Gizliliği)",
        "hakaret":       "TCK 125 (Hakaret)",
        "küfür":         "TCK 125 (Hakaret)",
        "tehdit":        "TCK 106 (Tehdit)",
    }
    bulunanlar = []
    girdi_kucuk = user_input.lower()
    for anahtar, sinyal in kurallar.items():
        if anahtar in girdi_kucuk and sinyal not in bulunanlar:
            bulunanlar.append(sinyal)
    if bulunanlar:
        return (
            "\n\n[HUKUKİ SİNYAL]: Şu maddeleri öncelikli değerlendir: "
            + ", ".join(bulunanlar)
        )
    return ""

def call_llm(prompt, gecmis=None):
    """Gemini API çağrısı — konuşma geçmişi desteği ile."""
    try:
        chat = model.start_chat(history=[])
        # Sistem promptunu ilk mesaj olarak ekle
        tam_prompt = SISTEM_PROMPTU + "\n\n" + prompt
        if gecmis:
            # Geçmiş mesajları Gemini formatına çevir
            history = []
            for msg in gecmis[-6:]:
                role = "user" if msg["role"] == "user" else "model"
                history.append({"role": role, "parts": [msg["content"]]})
            chat = model.start_chat(history=history)
        response = chat.send_message(tam_prompt)
        return response.text
    except Exception as e:
        return f"Analiz sırasında hata oluştu: {str(e)}"

def run_pipeline(user_query, gecmis=None):
    # Selamlama kontrolü
    temiz = user_query.strip().lower()
    selamlar = ["merhaba", "selam", "mrb", "slm", "hello", "hi",
                "iyi günler", "iyi akşamlar", "hey", "nasılsın", "kimsin"]
    if temiz in selamlar or len(user_query.strip()) < 4:
        return ("Merhaba! Ben Siber Hukuk Analiz Asistanıyım. Yaşadığınız siber mağduriyeti, "
                "şüpheli internet olayını veya dijital platformdaki hukuki sorununuzu anlatın; "
                "TCK, KVKK ve ilgili mevzuat kapsamında analiz ederek pratik adımları sunayım.")

    with st.status("⚖️ Hukuk Motoru Analiz Yapıyor...", expanded=True) as status:

        # AŞAMA 1 — Sınıflandırma
        st.write("🔍 Aşama 1: Vaka Sınıflandırılıyor...")
        etiketler_str = ", ".join(HUKUK_DB.keys())
        class_prompt = (
            f"Aşağıdaki hukuki senaryoyu analiz et ve ilgili TÜM etiketleri JSON olarak döndür. "
            f"Yalnızca JSON döndür, başka hiçbir şey yazma.\n\n"
            f"Senaryo: {user_query}\n\n"
            f"Etiket Seçenekleri: [{etiketler_str}]\n\n"
            f"Format: {{\"etiketler\": []}}"
        )
        raw_json = call_llm(class_prompt)
        try:
            secilenler = json.loads(
                re.search(r'\{.*\}', raw_json, re.DOTALL).group(0)
            ).get("etiketler", [])
        except:
            secilenler = []

        # AŞAMA 2 — Mevzuat eşleme
        st.write("⚙️ Aşama 2: Mevzuat Verileri Çekiliyor...")
        maddeler = list(dict.fromkeys(
            [HUKUK_DB[e]["madde"] for e in secilenler if e in HUKUK_DB]
        ))
        if any("TCK" in m for m in maddeler) and "KVKK Madde 5/2-f" in maddeler:
            maddeler.remove("KVKK Madde 5/2-f")
        mevzuat_metni = retrieve_mevzuat(maddeler)

        # AŞAMA 3 — Rapor
        st.write("✍️ Aşama 3: Hukuki Rapor Oluşturuluyor...")
        gen_prompt = f"""Olay: {user_query}
Öncelikli İlgili Maddeler: {maddeler}
Mevzuat Metinleri:
{mevzuat_metni}

Cevabını KESİNLİKLE şu beş başlıkla yapılandır. Hiçbir bilgiyi tekrarlama:

OLAYIN HUKUKİ NİTELİĞİ
(Vakanın kısa ve net hukuki tanımı)

OLASI SUÇ VE İHLALLER
- Ceza Hukuku (TCK): (Somut eyleme uyan TCK maddeleri, ihtiyatlı dil ile)
- İdare Hukuku (KVKK): (Kurumsal taraf varsa yükümlülükler; yoksa "Bu vakada KVKK kapsamında kurumsal veri ihlali unsuru tespit edilmemiştir" yaz)

HUKUKİ DEĞERLENDİRME
(Somut olayın özgün analizi — şablon cümle kopyalama)

PRATİK OLARAK YAPILABİLECEKLER
(Bu vakaya özgü, birbirinden farklı 4-5 somut adım — hiçbir adımı tekrarlama)

RESMİ BAŞVURU YOLLARI
(Bu vakaya en uygun 2-3 başvuru mekanizması)"""

        final = call_llm(gen_prompt, gecmis=gecmis)
        status.update(label="✅ Analiz Tamamlandı!", state="complete", expanded=False)

    return final

# ─────────────────────────────────────────
# 5. SIDEBAR VE ANA EKRAN
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
        if cid in db and db[cid]:
            first_user_msg = next((m["content"] for m in db[cid] if m["role"] == "user"), "")
            if first_user_msg:
                words = first_user_msg.split()
                display_title = " ".join(words[:4]) + ("..." if len(words) > 4 else "")
            else:
                display_title = f"💬 Analiz {cid[:10]}"
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
        ek_bilgi = hukuki_filtre(prompt)
        gecmis = st.session_state.messages[:-1] if len(st.session_state.messages) > 1 else None
        answer = run_pipeline(prompt + ek_bilgi, gecmis=gecmis)
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        db[st.session_state.chat_id] = st.session_state.messages
        save_db(db)
