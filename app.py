import streamlit as st
import pandas as pd
import requests
import re

# --- Configurações da Aplicação ---
st.set_page_config(layout="wide", page_title="Automação Jumbo CDP", page_icon="🚀")

# Estilo Visual
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3.5em;
        background-color: #25D366;
        color: white;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover {
        background-color: #128C7E;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Recuperação de Carrinho - Sofia & Z-API")
st.markdown("Filtro: **Status = 'Pedido Salvo'** e **Pedidos Enviados = 0**.")

# --- Barra Lateral ---
st.sidebar.header("⚙️ Configurações")
webhook_url = st.sidebar.text_input(
    "URL do Webhook n8n", 
    placeholder="https://sua-instancia.n8n.cloud/webhook/leads"
)

# --- Mapeamento de Colunas da Planilha ---
COL_ID = 'N. Pedido'
COL_NAME = 'Cliente'
COL_PHONE = 'Fone Fixo'
COL_FILTER = 'Quant. Pedidos Enviados'
COL_STATUS = 'Status'
COL_TOTAL_VALUE = 'Valor Total'

def clean_phone(phone):
    """Remove caracteres especiais e garante o prefixo 55."""
    if pd.isna(phone): 
        return ""
    clean = re.sub(r'\D', '', str(phone))
    if not clean: 
        return ""
    # Adiciona 55 para números com DDD (10 ou 11 dígitos)
    if len(clean) in [10, 11]:
        clean = "55" + clean
    return clean

@st.cache_data
def process_leads(df_input):
    df = df_input.copy()
    
    # Remove espaços extras nos nomes das colunas
    df.columns = df.columns.str.strip()
    
    # Validação de colunas obrigatórias
    required = [COL_ID, COL_NAME, COL_PHONE, COL_FILTER, COL_STATUS, COL_TOTAL_VALUE]
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ Colunas ausentes na planilha: {', '.join(missing)}")
        return None

    # Tratamento de dados
    df[COL_FILTER] = pd.to_numeric(df[COL_FILTER], errors='coerce').fillna(-1)
    df[COL_PHONE] = df[COL_PHONE].apply(clean_phone)
    
    # Filtro de Leads Qualificados
    df_qualified = df[
        (df[COL_STATUS] == 'Pedido Salvo') & 
        (df[COL_FILTER] == 0)
    ].drop_duplicates(subset=[COL_ID], keep='first')

    return df_qualified

# --- Interface ---
uploaded_file = st.file_uploader("Suba o arquivo Excel ou CSV", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
            
        df_leads = process_leads(df_raw)
        
        if df_leads is not None:
            st.subheader(f"📊 Leads Qualificados: {len(df_leads)}")
            st.dataframe(df_leads[[COL_ID, COL_NAME, COL_PHONE, COL_TOTAL_VALUE]], use_container_width=True)
            
            if not df_leads.empty:
                st.divider()
                if st.button("🚀 DISPARAR MENSAGENS VIA Z-API"):
                    if not webhook_url:
                        st.warning("⚠️ Insira a URL do Webhook na barra lateral.")
                    else:
                        with st.spinner("Enviando dados para o n8n..."):
                            # Ajuste de payload com 'Telefone' (T maiúsculo) para bater com o n8n
                            payload_df = df_leads.rename(columns={
                                COL_ID: 'id_pedido',
                                COL_NAME: 'nome_cliente',
                                COL_PHONE: 'Telefone',
                                COL_TOTAL_VALUE: 'valor_total'
                            })
                            
                            # Seleção das colunas renomeadas
                            payload = payload_df[['id_pedido', 'nome_cliente', 'Telefone', 'valor_total']].to_dict(orient='records')
                            
                            try:
                                r = requests.post(webhook_url, json=payload, timeout=30)
                                if r.status_code in [200, 201]:
                                    st.balloons()
                                    st.success(f"✅ Sucesso! {len(payload)} contatos enviados.")
                                else:
                                    st.error(f"❌ Erro no n8n: {r.status_code}")
                            except Exception as e:
                                st.error(f"❌ Falha de conexão: {e}")
    except Exception as e:
        st.error(f"💥 Erro ao processar arquivo: {e}")
else:
    st.info("👋 Aguardando planilha para iniciar a recuperação.")
