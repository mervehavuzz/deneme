import streamlit as st
from huggingface_hub import InferenceClient
import json
import os
import re
from datetime import datetime

# ─────────────────────────────────────────
# 1. TARAYICI BAZLI SEANS VE HAFIZA YÖNETİMİ
# ─────────────────────────────────────────
# Tarayıcı seansı boyunca verilerin kalması ve gizli sekmede karışmaması için st.session_state kullanıyoruz
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
    "yetkisiz_erisim": {"madde": "TCK 243", "aciklama": "Bilişim sistemine girme suçu."},
    "sistem_bozma": {"madde": "TCK 244", "aciklama": "Sistemi engelleme, bozma, verileri yok etme."},
    "veri_calma": {"madde": "TCK 136", "aciklama": "Kişisel verileri hukuka aykırı ele geçirme."},
    "mail_okuma": {"madde": "TCK 132", "aciklama": "Haberleşmenin gizliliğini ihlal."},
    "veri_guvenligi": {"madde": "KVKK Madde 12", "aciklama": "Veri güvenliği yükümlülükleri."},
    "mesru_menfaat": {"madde": "KVKK Madde 5/2-f", "aciklama": "Meşru menfaat işleme şartı."},
    "acik_riza": {"madde": "KVKK Madde 5/1", "aciklama": "Açık rıza ile veri işleme."},
    "santaj": {"madde": "TCK 107", "aciklama": "Şantaj suçu."},
    "tehdit": {"madde": "TCK 106", "aciklama": "Tehdit suçu."},
    "ifsa": {"madde": "TCK 134", "aciklama": "Özel hayatın gizliliğini ihlal."},
    "hesap_ele_gecirme": {"madde": "TCK 243", "aciklama": "Bilişim sistemine hukuka aykırı erişim."},
    "dolandiricilik": {"madde": "TCK 158", "aciklama": "Bilişim sistemleri araç kılınarak veya kamu görevlisi unvanıyla dolandırıcılık."},
    "oltalama": {"madde": "TCK 243", "aciklama": "Bilişim sistemine girme (oltalama amaçlı)."},
    "kimlik_taklidi": {"madde": "TCK 136", "aciklama": "Başkasına ait verileri yayma/kullanma."},
    "taciz": {"madde": "TCK 105", "aciklama": "Cinsel taciz veya TCK 123 kişilerin huzurunu bozma."},
    "ozel_goruntu_ifsasi": {"madde": "TCK 134", "aciklama": "Özel hayatın gizliliğini ihlal (görüntü ifşası)."},
    "sosyal_medya_erisim": {"madde": "TCK 243", "aciklama": "Sosyal medya hesabına yetcisiz erişim."},
    "veri_ihlali": {"madde": "KVKK Madde 12", "aciklama": "Kişisel verilerin güvenliğinin ihlali."},
    "hakaret": {"madde": "TCK 125", "aciklama": "Hakaret suçu."},
    "platform_sorumlulugu": {"madde": "5651 Sayılı Kanun", "aciklama": "İnternet ortamında yapılan yayınların düzenlenmesi."}
}

def retrieve_mevzuat(ilgili_maddeler):
    if not os.path.exists("mevzuat.txt"):
        return "Not: mevzuat.txt bulunamadı, genel bilgilerle devam ediliyor."
    bulunanlar = []
    try:
        with open("mevzuat.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            for madde in ilgili_maddeler:
                match = re.search(r'\d+', madde)
                if match:
                    clean_madde = match.group(0)
                    for line in lines:
                        if re.search(rf'\b{clean_madde}\b', line):
                            if line.strip() not in bulunanlar:
                                bulunanlar.append(line.strip())
        return "\n".join(bulunanlar) if bulunanlar else "İlgili mevzuat metni dosyada bulunamadı."
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

/* Sidebar Genel Arka Planı */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #5B2FD9 0%, #7C3FFC 40%, #6A2EE8 100%) !important;
}

/* Sidebar İçindeki Normal Başlık ve Düz Metinlerin Beyaz Kalması */
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] div { 
    color: white !important; 
}

/* Sidebar İçindeki Butonların Yazı Fontunun Siyah Yapılması */
[data-testid="stSidebar"] button p {
    color: #1A1A1A !important;
    font-weight: 500 !important;
}

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

def hukuki_filtre(user_input):
    kurallar = {
        "şantaj": "Şantaj suçu (Örn: TCK 107) ihtimali",
        "tehdit": "Tehdit suçu (Örn: TCK 106) ihtimali",
        "sızdırıldı": "Verileri hukuka aykırı olarak verme veya yayma ihtimali (Örn: TCK 136)",
        "ifşa": "Özel hayatın gizliliğini ihlal ihtimali (Örn: TCK 134)",
        "izinsiz giriş": "Bilişim sistemine girme ihtimali (Örn: TCK 243)",
        "hack": "Bilişim sistemine girme veya sistemi bozma ihtimali (Örn: TCK 243, 244)",
        "küfür": "Hakaret suçu ihtimali (Örn: TCK 125)",
        "hakaret": "Hakaret suçu ihtimali (Örn: TCK 125)"
    }
    
    ek_talimat = ""
    bulunan_maddeler = []
    girdi_kucuk = user_input.lower()
    
    for anahtar_kelime, madde in kurallar.items():
        if anahtar_kelime in girdi_kucuk:
            bulunan_maddeler.append(madde)
            
    if bulunan_maddeler:
        ek_talimat = "\n\n[HUKUKİ SİNYAL BİLGİSİ]: Bu vakada şu potansiyel hukuki risk alanları gündeme gelebilir: " + ", ".join(bulunan_maddeler) + ". "
        ek_talimat += "Lütfen bu durumları kesin bir suç isnadı olarak kabul etme. Kendi hukuki reasoning süzgecinden geçirerek, 'değerlendirilebilir', 'gündeme gelebilir' gibi ihtiyatlı bir dille analiz et."
            
    return ek_talimat

def call_llm(prompt, sys_msg, temp=0.1):
    hukukçu_talimati = """Sen Türkiye Cumhuriyeti yasalarına hakim, ihtiyatlı ve profesyonel bir Siber Hukuk Asistanısın. 
    Görevin kullanıcıya olası hukuki durumlar og pratik adımlar hakkında rehberlik sunmaktır. Şunlar senin KIRMIZI ÇİZGİLERİNDİR:
    1. Kullanıcıyı asla yargılamayacaksın, ahlaki ders vermeyeceksin ve kurbanı suçlayıcı cümleler kurmayacaksın.
    2. Kesinlikle "şu suç oluşmuştur", "ceza alır" gibi kesin hüküm bildiren ifadeler KULLANMAYACAKSIN. Bunun yerine daima "değerlendirilebilir", "gündeme gelebilir", "iddia edilmesi halinde", "olayın detayına göre" gibi ihtiyatlı hukuk dili kullanacaksın.
    3. Olayın bağlamına göre TCK 106, 107, 125, 123, 134, 135, 136, 157, 158, 243, 244 og KVKK gibi ilgili tüm maddeleri özgürce değerlendirebilirsin.
    4. Analizlerini tarafsız, empatik ve siber hukuka uygun yapacaksın."""
    
    messages = [
        {"role": "system", "content": hukukçu_talimati}, 
        {"role": "user", "content": prompt}
    ]
    res = client.chat_completion(messages=messages, max_tokens=1500, temperature=temp)
    return res.choices[0].message.content

def run_pipeline(user_query):
    # ─── SOHBET VE SELAMLAMA KONTROLÜ ───
    temiz_girdi = user_query.strip().lower()
    selamlar = ["merhaba", "selam", "mrb", "slm", "hello", "hi", "iyi günler", "iyi akşamlar", "hey", "nasılsın", "kimsin"]
    
    if temiz_girdi in selamlar or len(user_query.strip()) < 4:
        return "Merhaba! Ben Siber Hukuk Analiz Asistanı. Yaşadığınız siber mağduriyetleri, şüpheli internet olaylarını veya dijital platformlardaki hukuki sorunlarınızı buraya yazarak analiz raporu oluşturabilirsiniz. Size nasıl yardımcı olabilirim?"

    with st.status("⚖️ Hukuk Motoru Analiz Yapıyor...", expanded=True) as status:
        # Sınıflandırma
        st.write("🔍 Aşama 1: Vaka Sınıflandırılıyor...")
        class_prompt = f"""Aşağıdaki hukuki senaryoyu analiz et og İLGİLİ TÜM etiketleri JSON formatında döndür. Birden fazla etiket seçebilirsin. Senaryo: {user_query} Etiket Seçenekleri: [hesap_ele_gecirme, dolandiricilik, oltalama, kimlik_taklidi, taciz, ozel_goruntu_ifsasi, sosyal_medya_erisim, veri_ihlali, tehdit, santaj, hakaret, platform_sorumlulugu, yetkisiz_erisim, sistem_bozma, veri_calma, mail_okuma, veri_guvenligi, mesru_menfaat, acik_riza] Format: {{"etiketler": []}}"""
        raw_json = call_llm(class_prompt, "Sadece JSON döndür.", temp=0.01)
        
        try:
            secilenler = json.loads(re.search(r'\{.*\}', raw_json, re.DOTALL).group(0)).get("etiketler", [])
        except: secilenler = []

        # Mapping & RAG
        st.write("⚙️ Aşama 2: Mevzuat Verileri Çekiliyor...")
        maddeler = [HUKUK_DB[e]["madde"] for e in secilenler if e in HUKUK_DB]
        if any("TCK" in m for m in maddeler) and "KVKK Madde 5/2-f" in maddeler:
            maddeler.remove("KVKK Madde 5/2-f")
        
        mevzuat_metni = retrieve_mevzuat(maddeler)

        # Final Yazım
        st.write("✍️ Aşama 3: Rapor Oluşturuluyor...")
        gen_sys = """Sen uzman, ihtiyatlı ve kapsayıcı bir siber hukuk danışmanısın. Cevabında ceza hukuku boyutunu (bireysel suçlar) ve idare hukuku boyutunu (kurumların veya veri sorumlularının yükümlülüklerini) kesin çizgilerle birbirinden ayırmalısın. Şablonda yazan parantez içi açıklamalara göre değil, sadece kullanıcının anlattığı somut vakaya göre analiz üretmelisin."""
        
        gen_prompt = f"""Olay: {user_query} 
        Öncelikli İlgili Maddeler: {maddeler} 
        Mevzuat Metinleri: {mevzuat_metni} 
        
        Lütfen cevabını KESİNLİKLE aşağıdaki şablona ve başlıklara göre yapılandır. Şablondaki parantez içi örnek talimatları metnine dahil etme, onları sadece rehber kabul et:
        
        OLAYIN HUKUKİ NİTELİĞİ
        (Vakanın siber veya genel hukuk alanındaki gerçek tanımı)
        
        OLASI SUÇ VE İHLALLER
        - Ceza Hukuku (TCK): (Failin somut vakadaki eylemine uyan TCK maddelerini ihtiyatlı dille açıkla. Eğer olay siber suç değilse zorla siber maddeler dayatma, dolandırıcılık veya tehdit ise ona odaklan.)
        - İdare Hukuku (KVKK): (Eğer olayda kurumsal bir veri sorumlusu, sistem zafiyeti veya veri ihlali yoksa 'İdare hukuku kapsamında kurumsal bir veri ihlali unsuru tespit edilmemiştir' notu düş.)
        
        HUKUKİ DEĞERLENDİRME
        (Kullanıcının anlattığı somut fail davranışlarını temel alarak olayı analiz et. Örnek şablon cümlelerini buraya kopyalama.)
        
        PRATİK OLARAK YAPILABİLECEKLER
        (Mağdurun yaşadığı somut olaya tam uyan, uygulanabilir adımlar yaz. Telefon dolandırıcılığı ise kapatıp emniyet birimlerini aramasını; hesap çalınması ise 2FA ve şifre işlemlerini öner. Alakasız durumlarda uzaktan oturum kapatma gibi ezbere siber güvenlik maddeleri yazma.)
        
        RESMİ BAŞVURU YOLLARI
        (En uygun yasal başvuru mekanizmalarını belirt. Cumhuriyet Başsavcılıkları, emniyet birimleri veya ilgili idari kurulları somut vakaya göre eşleştir.)"""
        
        final = call_llm(gen_prompt, gen_sys, temp=0.3)
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
    
    # Geçmiş analizleri listeleme
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
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "⚖️"):
        st.markdown(msg["content"])

if prompt := st.chat_input("Hukuki senaryoyu buraya yazın..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"): 
        st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="⚖️"):
        ek_bilgi = hukuki_filtre(prompt)
        answer = run_pipeline(prompt + ek_bilgi)
        
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        
        db[st.session_state.chat_id] = st.session_state.messages
        save_db(db)
