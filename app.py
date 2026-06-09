import streamlit as st
from huggingface_hub import InferenceClient
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
# 2. HUKUK HAFIZASI VE MEVZUAT SİSTEMİ
# ─────────────────────────────────────────
HUKUK_DB = {
    "yetkisiz_erisim":       {"madde": "TCK 243",          "aciklama": "Bilişim sistemine girme suçu."},
    "sistem_bozma":          {"madde": "TCK 244",          "aciklama": "Sistemi engelleme, bozma, verileri yok etme."},
    "veri_calma":            {"madde": "TCK 136",          "aciklama": "Kişisel verileri hukuka aykırı ele geçirme."},
    "mail_okuma":            {"madde": "TCK 132",          "aciklama": "Haberleşmenin gizliliğini ihlal."},
    "is_yeri_gozetleme":     {"madde": "TCK 132",          "aciklama": "İşyerinde yazışmaların izlenmesi — haberleşme gizliliği ihlali."},
    "veri_guvenligi":        {"madde": "KVKK Madde 12",    "aciklama": "Veri güvenliği yükümlülükleri."},
    "mesru_menfaat":         {"madde": "KVKK Madde 5/2-f", "aciklama": "Meşru menfaat işleme şartı."},
    "acik_riza":             {"madde": "KVKK Madde 5/1",   "aciklama": "Açık rıza ile veri işleme."},
    "santaj":                {"madde": "TCK 107",          "aciklama": "Şantaj suçu — para veya yarar karşılığı tehdit."},
    "tehdit":                {"madde": "TCK 106",          "aciklama": "Tehdit suçu."},
    "ifsa":                  {"madde": "TCK 134",          "aciklama": "Özel hayatın gizliliğini ihlal."},
    "hesap_ele_gecirme":     {"madde": "TCK 243",          "aciklama": "Bilişim sistemine hukuka aykırı erişim."},
    "dolandiricilik":        {"madde": "TCK 158/2-f",      "aciklama": "Bilişim sistemleri araç kılınarak dolandırıcılık."},
    "oltalama":              {"madde": "TCK 243",          "aciklama": "Bilişim sistemine girme (oltalama amaçlı)."},
    "kimlik_taklidi":        {"madde": "TCK 136",          "aciklama": "Başkasına ait verileri yayma/kullanma."},
    "taciz":                 {"madde": "TCK 105/123",      "aciklama": "Cinsel taciz veya kişilerin huzurunu bozma."},
    "ozel_goruntu_ifsasi":   {"madde": "TCK 134+226",      "aciklama": "Özel görüntü ifşası — özel hayat gizliliği ve müstehcenlik."},
    "sosyal_medya_erisim":   {"madde": "TCK 243",          "aciklama": "Sosyal medya hesabına yetkisiz erişim."},
    "veri_ihlali":           {"madde": "KVKK Madde 12",    "aciklama": "Kişisel verilerin güvenliğinin ihlali."},
    "hakaret":               {"madde": "TCK 125",          "aciklama": "Hakaret suçu."},
    "platform_sorumlulugu":  {"madde": "5651 Sayılı Kanun","aciklama": "İnternet ortamında yapılan yayınların düzenlenmesi."},
}

# mevzuat.txt içeriği — dosya bulunamazsa bu sözlük kullanılır
MEVZUAT_FALLBACK = {
    "106": "TCK 106 - Tehdit suçu: Bir başkasını, kendisinin veya yakınının hayatına, vücut veya cinsel dokunulmazlığına yönelik bir saldırı gerçekleştireceğinden bahisle tehdit eden kişi, altı aydan iki yıla kadar hapis cezası ile cezalandırılır. Malvarlığı itibarıyla büyük bir zarara uğratacağından veya sair bir kötülük edeceğinden bahisle tehditte ise, mağdurun şikayeti üzerine, altı aya kadar hapis veya adlî para cezasına hükmolunur.",
    "107": "TCK 107 - Şantaj suçu: Hakkı olan veya yükümlü olduğu bir şeyi yapacağından veya yapmayacağından bahisle, bir kimseyi kanuna aykırı veya yükümlü olmadığı bir şeyi yapmaya veya yapmamaya ya da haksız çıkar sağlamaya zorlayan kişi, bir yıldan üç yıla kadar hapis ve beşbin güne kadar adlî para cezası ile cezalandırılır. Kendisine veya başkasına yarar sağlamak maksadıyla bir kişinin şeref veya saygınlığına zarar verecek nitelikteki hususların açıklanacağı veya isnat edileceği tehdidinde bulunulması halinde de aynı ceza verilir.",
    "123": "TCK 123 - Kişilerin huzur ve sükununu bozma: Sırf huzur ve sükununu bozmak maksadıyla bir kimseye ısrarlı bir şekilde; telefon edilmesi, gürültü yapılması ya da aynı maksatla hukuka aykırı başka bir davranışta bulunulması halinde, mağdurun şikayeti üzerine faile üç aydan bir yıla kadar hapis cezası verilir.",
    "125": "TCK 125 - Hakaret suçu: Bir kimseye onur, şeref ve saygınlığını rencide edebilecek nitelikte somut bir fiil veya olgu isnat eden ya da sövmek suretiyle bir kimsenin onur, şeref ve saygınlığına saldıran kişi, üç aydan iki yıla kadar hapis veya adlî para cezası ile cezalandırılır.",
    "132": "TCK 132 - Haberleşmenin gizliliğini ihlal: Kişiler arasındaki haberleşmenin gizliliğini ihlal eden kimse, bir yıldan üç yıla kadar hapis cezası ile cezalandırılır. Bu gizlilik ihlali haberleşme içeriklerinin kaydedilmesi suretiyle gerçekleşirse verilecek ceza bir kat artırılır.",
    "134": "TCK 134 - Özel hayatın gizliliğini ihlal: Kişilerin özel hayatının gizliliğini ihlal eden kimse, bir yıldan üç yıla kadar hapis cezası ile cezalandırılır. Gizliliğin görüntü veya seslerin kayda alınması suretiyle ihlal edilmesi halinde, verilecek ceza bir kat artırılır. Bu görüntü veya seslerin hukuka aykırı olarak ifşa edilmesi halinde, iki yıldan beş yıla kadar hapis cezası verilir.",
    "136": "TCK 136 - Kişisel verileri hukuka aykırı olarak ele geçirme veya yayma: Kişisel verileri, hukuka aykırı olarak bir başkasına veren, yayan veya ele geçiren kişi, iki yıldan dört yıla kadar hapis cezası ile cezalandırılır.",
    "158": "TCK 158 - Nitelikli dolandırıcılık: Dolandırıcılık suçunun bilişim sistemlerinin, banka veya kredi kurumlarının araç olarak kullanılması suretiyle işlenmesi halinde, üç yıldan on yıla kadar hapis ve beşbin güne kadar adlî para cezasına hükmolunur.",
    "243": "TCK 243 - Bilişim sistemine girme: Bir bilişim sisteminin bütününe veya bir kısmına, hukuka aykırı olarak giren veya orada kalmaya devam eden kimseye bir yıla kadar hapis veya adlî para cezası verilir.",
    "244": "TCK 244 - Sistemi engelleme, bozma, verileri yok etme veya değiştirme: Bir bilişim sisteminin işleyişini engelleyen veya bozan kişi, bir yıldan beş yıla kadar hapis cezası ile cezalandırılır. Bir bilişim sistemindeki verileri bozan, yok eden, değiştiren veya erişilmez kılan kişi, altı aydan üç yıla kadar hapis cezası ile cezalandırılır.",
}

def retrieve_mevzuat(ilgili_maddeler):
    bulunanlar = []

    # Önce dosyadan okumayı dene
    if os.path.exists("mevzuat.txt"):
        try:
            with open("mevzuat.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
            for madde in ilgili_maddeler:
                match = re.search(r'\d+', madde)
                if match:
                    clean = match.group(0)
                    for line in lines:
                        if re.search(rf'\b{clean}\b', line) and line.strip() not in bulunanlar:
                            bulunanlar.append(line.strip())
            if bulunanlar:
                return "\n".join(bulunanlar)
        except:
            pass

    # Dosya yoksa veya boş gelirse fallback sözlüğünü kullan
    for madde in ilgili_maddeler:
        match = re.search(r'\d+', madde)
        if match:
            key = match.group(0)
            if key in MEVZUAT_FALLBACK and MEVZUAT_FALLBACK[key] not in bulunanlar:
                bulunanlar.append(MEVZUAT_FALLBACK[key])

    return "\n".join(bulunanlar) if bulunanlar else "İlgili mevzuat metni bulunamadı."

# ─────────────────────────────────────────
# 3. SAYFA AYARLARI VE TASARIM (CSS)
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
# 4. API VE MANTIK MOTORU
# ─────────────────────────────────────────
try:
    hf_token = st.secrets["HF_TOKEN"]
    client = InferenceClient(model="Qwen/Qwen2.5-7B-Instruct", token=hf_token)
except Exception as e:
    st.error(f"API Hatası: {e}")
    st.stop()

# Güçlendirilmiş sistem promptu — tekrar engeli + doğru madde eşleme kuralları
HUKUKCU_TALIMATI = """Sen Türkiye Cumhuriyeti yasalarına hakim, ihtiyatlı ve profesyonel bir Siber Hukuk Asistanısın.
Görevin kullanıcıya olası hukuki durumlar ve pratik adımlar hakkında rehberlik sunmaktır.

KIRMIZI ÇİZGİLERİN:
1. Kullanıcıyı asla yargılama, ahlaki ders verme veya kurbanı suçlayıcı cümleler kurma.
2. "Şu suç oluşmuştur" veya "ceza alır" gibi kesin hüküm bildiren ifadeler KULLANMA. Daima "değerlendirilebilir", "gündeme gelebilir", "iddia edilmesi halinde", "olayın detayına göre" gibi ihtiyatlı hukuk dili kullan.
3. TEKRAR YASAĞI: Hiçbir cümleyi, maddeyi veya pratik adımı iki kez yazma. Her bilgi yalnızca bir kez geçecek.
4. MADDE SEÇME KURALLARI (bunlara kesinlikle uy):
   - Para veya çıkar karşılığı tehdit varsa → TCK 107 (Şantaj) MUTLAKA değerlendir.
   - İşyerinde patron/şirket tarafından yazışma izleme varsa → TCK 132 (Haberleşme Gizliliği) ve KVKK Madde 12 önceliklidir; TCK 243/244 dışarıdan sisteme giriş içindir, işyeri izlemesine uygulanmaz.
   - Özel görüntü veya fotoğraf ifşası varsa → TCK 134 ve TCK 226 birlikte değerlendir.
   - Sosyal medya/e-posta hesabı ele geçirilmişse → TCK 243.
   - Telefon veya mesajla banka/kimlik bilgisi alınmışsa → TCK 158/2-f (Nitelikli Dolandırıcılık) önceliklidir.
5. KVKK yalnızca kurumsal veri sorumlusu, sistem zafiyeti veya şirket düzeyinde veri ihlali varsa uygula. Bireyler arası vakada "Bu vakada KVKK kapsamında kurumsal veri ihlali unsuru tespit edilmemiştir" yaz.
6. Cevabını KESİNLİKLE şu beş başlıkla yapılandır, başka başlık ekleme:

OLAYIN HUKUKİ NİTELİĞİ
OLASI SUÇ VE İHLALLER
HUKUKİ DEĞERLENDİRME
PRATİK OLARAK YAPILABİLECEKLER
RESMİ BAŞVURU YOLLARI"""

def hukuki_filtre(user_input):
    """Anahtar kelimelerden modele ek sinyal üretir."""
    kurallar = {
        "şantaj":        "TCK 107 (Şantaj) — para veya yarar karşılığı tehdit unsuru",
        "para istedi":   "TCK 107 (Şantaj) — para veya yarar karşılığı tehdit unsuru",
        "para istiyor":  "TCK 107 (Şantaj) — para veya yarar karşılığı tehdit unsuru",
        "tehdit":        "TCK 106 (Tehdit) ihtimali",
        "yayacağım":     "TCK 107 (Şantaj) + TCK 134 (Özel Hayat Gizliliği) ihtimali",
        "yayacak":       "TCK 107 (Şantaj) + TCK 134 (Özel Hayat Gizliliği) ihtimali",
        "fotoğraf":      "TCK 134 (Özel Hayat) + TCK 226 (Müstehcenlik) değerlendirilebilir",
        "görüntü":       "TCK 134 (Özel Hayat) + TCK 226 (Müstehcenlik) değerlendirilebilir",
        "izliyor":       "TCK 132 (Haberleşme Gizliliği) — işyeri bağlamında KVKK Madde 12",
        "takip ediyor":  "TCK 132 (Haberleşme Gizliliği) ihtimali",
        "yazılım kurdu": "TCK 132 (Haberleşme Gizliliği) + KVKK Madde 12 ihtimali",
        "hack":          "TCK 243 (Bilişim Sistemine Girme) ihtimali",
        "hacklendi":     "TCK 243 (Bilişim Sistemine Girme) ihtimali",
        "sızdırıldı":    "TCK 136 (Verileri Yayma) ihtimali",
        "ifşa":          "TCK 134 (Özel Hayat Gizliliği) ihtimali",
        "hakaret":       "TCK 125 (Hakaret) ihtimali",
        "küfür":         "TCK 125 (Hakaret) ihtimali",
    }
    bulunanlar = []
    girdi_kucuk = user_input.lower()
    for anahtar, sinyal in kurallar.items():
        if anahtar in girdi_kucuk and sinyal not in bulunanlar:
            bulunanlar.append(sinyal)

    if bulunanlar:
        return (
            "\n\n[HUKUKİ SİNYAL]: Bu vakada şu potansiyel risk alanları ön plana çıkmaktadır: "
            + ", ".join(bulunanlar)
            + ". Bu sinyalleri kesin suç isnadı olarak değil, değerlendirme çerçevesi olarak kullan."
        )
    return ""

def call_llm(prompt, sys_msg, temp=0.1, gecmis=None):
    """LLM çağrısı — isteğe bağlı konuşma geçmişi desteği ile."""
    messages = [{"role": "system", "content": sys_msg}]
    if gecmis:
        # Son 6 mesajı bağlam olarak ekle (token limitini aşmamak için)
        for msg in gecmis[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})
    res = client.chat_completion(messages=messages, max_tokens=1500, temperature=temp)
    return res.choices[0].message.content

def run_pipeline(user_query, gecmis=None):
    # ─── SELAMLAMA KONTROLÜ ───
    temiz = user_query.strip().lower()
    selamlar = ["merhaba", "selam", "mrb", "slm", "hello", "hi", "iyi günler",
                "iyi akşamlar", "hey", "nasılsın", "kimsin"]
    if temiz in selamlar or len(user_query.strip()) < 4:
        return ("Merhaba! Ben Siber Hukuk Analiz Asistanı. Yaşadığınız siber mağduriyetleri, "
                "şüpheli internet olaylarını veya dijital platformlardaki hukuki sorunlarınızı "
                "buraya yazarak analiz raporu oluşturabilirsiniz. Size nasıl yardımcı olabilirim?")

    with st.status("⚖️ Hukuk Motoru Analiz Yapıyor...", expanded=True) as status:

        # AŞAMA 1 — Sınıflandırma
        st.write("🔍 Aşama 1: Vaka Sınıflandırılıyor...")
        etiketler_str = ", ".join(HUKUK_DB.keys())
        class_prompt = (
            f"Aşağıdaki hukuki senaryoyu analiz et ve İLGİLİ TÜM etiketleri JSON olarak döndür. "
            f"Birden fazla etiket seçebilirsin.\n\nSenaryo: {user_query}\n\n"
            f"Etiket Seçenekleri: [{etiketler_str}]\n\nFormat: {{\"etiketler\": []}}"
        )
        raw_json = call_llm(class_prompt, "Sadece JSON döndür, başka hiçbir şey yazma.", temp=0.01)

        try:
            secilenler = json.loads(
                re.search(r'\{.*\}', raw_json, re.DOTALL).group(0)
            ).get("etiketler", [])
        except:
            secilenler = []

        # AŞAMA 2 — Mevzuat eşleme
        st.write("⚙️ Aşama 2: Mevzuat Verileri Çekiliyor...")
        maddeler = [HUKUK_DB[e]["madde"] for e in secilenler if e in HUKUK_DB]

        # Tekrar eden maddeleri temizle, KVKK çakışmasını gider
        maddeler = list(dict.fromkeys(maddeler))
        if any("TCK" in m for m in maddeler) and "KVKK Madde 5/2-f" in maddeler:
            maddeler.remove("KVKK Madde 5/2-f")

        mevzuat_metni = retrieve_mevzuat(maddeler)

        # AŞAMA 3 — Rapor üretimi
        st.write("✍️ Aşama 3: Rapor Oluşturuluyor...")

        gen_prompt = f"""Olay: {user_query}
Öncelikli İlgili Maddeler: {maddeler}
Mevzuat Metinleri:
{mevzuat_metni}

Lütfen cevabını KESİNLİKLE şu beş başlıkla yapılandır:

OLAYIN HUKUKİ NİTELİĞİ
(Vakanın siber veya genel hukuk alanındaki kısa ve net tanımı)

OLASI SUÇ VE İHLALLER
- Ceza Hukuku (TCK): (Failin somut vakadaki eylemine uyan TCK maddelerini ihtiyatlı dille açıkla)
- İdare Hukuku (KVKK): (Kurumsal veri sorumlusu yoksa "Bu vakada KVKK kapsamında kurumsal veri ihlali unsuru tespit edilmemiştir" yaz)

HUKUKİ DEĞERLENDİRME
(Kullanıcının anlattığı somut olayı özgün şekilde analiz et — şablon cümle kopyalama, hiçbir bilgiyi tekrarlama)

PRATİK OLARAK YAPILABİLECEKLER
(Bu vakaya özgü, birbirinden farklı 4-5 somut adım. Hiçbir adımı tekrarlama.)

RESMİ BAŞVURU YOLLARI
(Bu vakaya en uygun 2-3 başvuru mekanizması — kısa ve net)"""

        final = call_llm(gen_prompt, HUKUKCU_TALIMATI, temp=0.2, gecmis=gecmis)
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
        # Konuşma geçmişini pipeline'a aktar (son mesaj hariç)
        gecmis = st.session_state.messages[:-1] if len(st.session_state.messages) > 1 else None
        answer = run_pipeline(prompt + ek_bilgi, gecmis=gecmis)

        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

        db[st.session_state.chat_id] = st.session_state.messages
        save_db(db)
