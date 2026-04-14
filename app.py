import streamlit as st
import requests

st.title("⚖️ Model Destek Kontrol Paneli")

# 1. GÜVENLİ ADIM: Secrets'tan tokeni oku
try:
    api_token = st.secrets["HF_TOKEN"]
    st.success("✅ 'HF_TOKEN' Secrets içinden başarıyla okundu.")
except Exception:
    st.error("❌ Secrets içinde 'HF_TOKEN' bulunamadı! Lütfen Streamlit Cloud ayarlarına girin.")
    st.stop()

# 2. MODELLERİ ÇEKME FONKSİYONU
def get_supported_models(token):
    headers = {"Authorization": f"Bearer {token}"}
    # Text Generation (Metin Üretme) kategorisindeki en popüler modelleri sorgula
    url = "https://huggingface.co/api/models?filter=text-generation&sort=downloads&direction=-1&limit=15"
    
    with st.spinner("Modeller listeleniyor..."):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Hatası: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            st.error(f"Bağlantı Hatası: {e}")
            return None

# 3. EKRANA YAZDIRMA
models = get_supported_models(api_token)

if models:
    st.write("### Şu an senin için erişilebilir olan modeller:")
    st.info("Bu model isimlerini kopyalayıp ana kodundaki '_model_id' kısmına yapıştırabilirsin.")
    
    for model in models:
        m_id = model['id']
        col1, col2 = st.columns([3, 1])
        col1.code(m_id)
        if col2.button("Seç", key=m_id):
            st.session_state.selected_model = m_id
            st.success(f"Seçildi: {m_id}")

if "selected_model" in st.session_state:
    st.divider()
    st.write(f"**Önerilen Kullanım:**")
    st.code(f'_model_id = "{st.session_state.selected_model}"')
