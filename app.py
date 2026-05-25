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
    "acik_riza": {"madde": "KVKK Madde 5/1", "aciklama": "Açık rıza ile veri işleme."},
    "santaj": {"madde": "TCK 107", "aciklama": "Şantaj suçu."},
    "tehdit": {"madde": "TCK 106", "aciklama": "Tehdit suçu."},
    "ifsa": {"madde": "TCK 134", "aciklama": "Özel hayatın gizliliğini ihlal."},
    "hesap_ele_gecirme": {"madde": "TCK 243", "aciklama": "Bilişim sistemine hukuka aykırı erişim."},
    "dolandiricilik": {"madde": "TCK 158", "aciklama": "Bilişim sistemleri araç kılınarak dolandırıcılık."},
    "oltalama": {"madde": "TCK 243", "aciklama": "Bilişim sistemine girme (oltalama amaçlı)."},
    "kimlik_taklidi": {"madde": "TCK 136", "aciklama": "Başkasına ait verileri yayma/kullanma."},
    "taciz": {"madde": "TCK 105", "aciklama": "Cinsel taciz veya TCK 123 kişilerin huzurunu bozma."},
    "ozel_goruntu_ifsasi": {"madde": "TCK 134", "aciklama": "Özel hayatın gizliliğini ihlal (görüntü ifşası)."},
    "sosyal_medya_erisim": {"madde": "TCK 243", "aciklama": "Sosyal medya hesabına yetkisiz erişim."},
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
                match = re.search(r'\d+', madde) # Madde içindeki asıl numarayı yakala
                if match:
                    clean_madde = match.group(0)
                    for line in lines:
                        # Regex tam kelime eşleşmesi ile hatalı eşleşmeleri engelle (Örn: 134 -> 1134 olmasın)
                        if re.search(rf'\b{clean_madde}\b', line):
                            # Set() kullanmadan listeye ekle, böylece okuma sırası korunur ve tekrar engellenir
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
    """
    Kullanıcının mesajında kritik kelimeler varsa, 
    bunları potansiyel hukuki risk alanları olarak tespit eder ve LLM'e ihtiyatlı bir sinyal olarak iletir.
    """
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
    Görevin kullanıcıya olası hukuki durumlar ve pratik adımlar hakkında rehberlik sunmaktır. Şunlar senin KIRMIZI ÇİZGİLERİNDİR:
    1. Kullanıcıyı asla yargılamayacaksın, ahlaki ders vermeyeceksin ve kurbanı suçlayıcı cümleler kurmayacaksın.
    2. Kesinlikle "şu suç oluşmuştur", "ceza alır" gibi kesin hüküm bildiren ifadeler KULLANMAYACAKSIN. Bunun yerine daima "değerlendirilebilir", "gündeme gelebilir", "iddia edilmesi halinde", "olayın detayına göre" gibi ihtiyatlı hukuk dili kullanacaksın.
    3. Olayın bağlamına göre TCK 106, 107, 125, 123, 134, 135, 136, 157, 243, 244 ve KVKK gibi ilgili tüm maddeleri özgürce değerlendirebilirsin.
    4. Analizlerini tarafsız, empatik ve hukuki terminolojiye uygun yapacaksın."""
    
    messages = [
        {"role": "system", "content": hukukçu_talimati}, 
        {"role": "user", "content": prompt}
    ]
    
    res = client.chat_completion(messages=messages, max_tokens=1000, temperature=temp)
    return res.choices[0].message.content

def run_pipeline(user_query):
    with st.status("⚖️ Hukuk Motoru Analiz Yapıyor...", expanded=True) as status:
        # Sınıflandırma
        st.write("🔍 Aşama 1: Vaka Sınıflandırılıyor...")
        class_prompt = f"""Aşağıdaki hukuki senaryoyu analiz et ve İLGİLİ TÜM etiketleri JSON formatında döndür. 
        Birden fazla etiket seçebilirsin.

        Senaryo: {user_query}

        Etiket Seçenekleri: [hesap_ele_gecirme, dolandiricilik, oltalama, kimlik_taklidi, taciz, ozel_goruntu_ifsasi, sosyal_medya_erisim, veri_ihlali, tehdit, santaj, hakaret, platform_sorumlulugu, yetkisiz_erisim, sistem_bozma, veri_calma, mail_okuma, veri_guvenligi, mesru_menfaat, acik_riza]
        Format: {{"etiketler": []}}"""
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
        gen_sys = """Sen uzman, ihtiyatlı ve kapsayıcı bir siber hukuk danışmanısın. Cevabında ceza hukuku boyutunu (bireysel suçlar) ve idare hukuku boyutunu (kurumların veya veri sorumlularının yükümlülüklerini) kesin çizgilerle birbirinden ayırmalısın. Kesin hüküm kurmaktan kaçınarak profesyonel bir analiz yap."""
        
        gen_prompt = f"""Olay: {user_query}
        Öncelikli İlgili Maddeler: {maddeler}
        Mevzuat Metinleri: {mevzuat_metni}
        
        Lütfen cevabını KESİNLİKLE aşağıdaki şablon, başlıklar ve kurallar çerçevesinde yapılandır:
        
        OLAYIN HUKUKİ NİTELİĞİ
        (Vakanın siber hukuk alanındaki genel tanımı)
        
        OLASI SUÇ VE İHLALLER
        - Ceza Hukuku (TCK): (Failin somut hangi hareketi hangi TCK maddesindeki suçu oluşturabilir? Kesin hüküm vermeden, ihtiyatlı bir dille açıkla.)
        - İdare Hukuku (KVKK): (Burada sistemi işleten kurumun/veri sorumlusunun bir veri ihlali veya güvenlik zafiyeti var mıdır? KVKK Madde 12 kapsamında değerlendirilebilir mi?)
        
        HUKUKİ DEĞERLENDİRME
        (Somut fail davranışını temel alarak, olayın gelişimini hukuk süzgecinden geçir. Failin 'başkasına ait açık oturumu kullanması' veya 'izinsiz girmesi' fiillerini ceza hukuku ve idare hukuku ayrımına sadık kalarak analiz et.)
        
        PRATİK OLARAK YAPILABİLECEKLER
        (Mağdurun siber güvenlik ve delil tespiti açısından yapması gereken somut eylemler. Örn: Ekran görüntüsü alma, platform yetkililerine/sistem yöneticilerine durumu hemen bildirme, oturumları uzaktan kapatma vb. Uydurma veya imkansız tavsiyeler verme.)
        
        RESMİ BAŞVURU YOLLARI
        (Cumhuriyet Başsavcılığı'na siber suçlar bürosu üzerinden suç duyurusunda bulunulması, idari şikayet mekanizmaları veya kurumsal disiplin süreçleri hakkında yasal yolları belirt.)"""
        
        final = call_llm(gen_prompt, gen_sys, temp=0.2)
        status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
    return final

# ─────────────────────────────────────────
# 5. SIDEBAR VE ANA EKRAN
# ─────────────────────────────────────────
db = load_db()
if "chat_id" not in st.session_state: st.session_state.chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_titles" not in st.session_state: st.session_state.chat_titles = {}

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

st.title("🛡️ Siber Hukuk Analiz Portalı")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "⚖️"):
        st.markdown(msg["content"])

if prompt := st.chat_input("Hukuki senaryoyu buraya yazın..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"): 
        st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="⚖️"):
        # 1. Filtreyi çalıştırıp ek talimatı hazırlıyoruz
        ek_bilgi = hukuki_filtre(prompt)
        
        # 2. Pipeline'a 'prompt' ile 'ek_bilgi'yi birleştirip gönderiyoruz
        answer = run_pipeline(prompt + ek_bilgi)
        
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        
        # Geçmişe kaydetme ve veritabanı güncelleme
        db[st.session_state.chat_id] = st.session_state.messages
        save_db(db)
