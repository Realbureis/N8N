import streamlit as st
import pandas as pd
import requests
import re

# --- Configurações da Aplicação ---
st.set_page_config(layout="wide", page_title="Automação Jumbo - Z-API", page_icon="🚀")

# Estilo Visual
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #25D366;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Recuperação de Carrinho - Sofia & Z-API")

# --- Configuração Sidebar ---
st.sidebar.header("⚙️ Configurações")
webhook_url = st.sidebar.text_input(
    "URL do Webhook n8n", 
    placeholder="https://sua-instancia.n8n.cloud/webhook/leads"
)

# --- Mapeamento de Colunas (Atualizado conforme solicitado) ---
COL_ID = 'N. Pedido'         # Alterado de 'Codigo Cliente' para 'N. Pedido'
COL_NAME = 'Cliente'          # Alterado para 'Cliente'
COL_PHONE = 'Fone Fixo'       # Alterado de 'Celular' para 'Fone Fixo'
COL_FILTER = 'Quant. Pedidos Enviados'
COL_STATUS = 'Status'
COL_TOTAL_VALUE = 'Valor Total'

def clean_phone(phone):
    """Limpa caracteres e garante prefixo 55 para o Z-API."""
    if pd.isna(phone): 
        return ""
    # Remove tudo que não é número
    clean = re.sub(r'\D', '', str(phone))
    if not clean: 
        return ""
    # Adiciona 55 se o número tiver apenas DDD + Número (10 ou 11 dígitos)
    if len(clean) in [10, 11]:
        clean = "55" + clean
    return clean

@st.cache_data
def process_leads(df_input):
    df = df_input.copy()
    
    # Validação de colunas obrigatórias
    required = [COL_ID, COL_NAME, COL_PHONE, COL_FILTER, COL_STATUS, COL_TOTAL_VALUE]
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ Colunas não encontradas na planilha: {', '.join(missing)}")
        st.info("Verifique se o nome das colunas na planilha está idêntico ao solicitado.")
        return None

    # Tratamento de dados
    df[COL_FILTER] = pd.to_numeric(df[COL_FILTER], errors='coerce').fillna(-1)
    df[COL_PHONE] = df[COL_PHONE].apply(clean_phone)
    
    # Filtro: Status 'Pedido Salvo' e 0 pedidos enviados
    df_qualified = df[
        (df[COL_STATUS] == 'Pedido Salvo') & 
        (df[COL_FILTER] == 0)
    ].drop_duplicates(subset=[COL_ID], keep='first')

    return df_qualified

# --- Interface de Upload ---
uploaded_file = st.file_uploader("Suba o arquivo Excel ou CSV", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Carregamento
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
            
        df_leads = process_leads(df_raw)
        
        if df_leads is not None:
            st.subheader(f"📊 Leads Qualificados: {len(df_leads)}")
            
            # Exibe os dados que serão enviados
            view_cols = [COL_ID, COL_NAME, COL_PHONE, COL_TOTAL_VALUE]
            st.dataframe(df_leads[view_cols], use_container_width=True)
            
            if not df_leads.empty:
                st.divider()
                if st.button("Disparar Mensagens via Z-API"):
                    if not webhook_url:
                        st.warning("⚠️ Coloque a URL do Webhook do n8n na barra lateral.")
                    else:
                        with st.spinner("Enviando dados para o n8n..."):
                            # Preparação do JSON para o n8n
                            payload = df_leads.rename(columns={
                                COL_ID: 'id_pedido',
                                COL_NAME: 'nome_cliente',
                                COL_PHONE: 'telefone',
                                COL_TOTAL_VALUE: 'valor_total'
                            })[[ 'id_pedido', 'nome_cliente', 'telefone', 'valor_total' ]].to_dict(orient='records')
                            
                            try:
                                response = requests.post(webhook_url, json=payload, timeout=30)
                                if response.status_code in [200, 201]:
                                    st.balloons()
                                    st.success(f"✅ Sucesso! {len(payload)} contatos enviados para o n8n.")
                                else:
                                    st.error(f"❌ Erro no n8n: {response.status_code}")
                            except Exception as e:
                                st.error(f"❌ Falha de conexão: {e}")
            else:
                st.info("Nenhum cliente atende aos critérios (Pedido Salvo e 0 pedidos).")

    except Exception as e:
        st.error(f"💥 Erro ao processar o arquivo: {e}")
else:
    st.info("👋 Aguardando upload da planilha...")
