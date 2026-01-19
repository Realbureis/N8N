import streamlit as st
import pandas as pd
import requests
import io
from urllib.parse import quote

# --- Configurações da Aplicação ---
st.set_page_config(layout="wide", page_title="Automação Jumbo CDP - Recuperação IA")

st.title("🤖 Recuperação de Carrinho com IA (n8n + OpenAI)")
st.markdown("Filtra leads qualificados e envia automaticamente para o fluxo de IA no n8n.")

# Configurações do n8n (Mude para sua URL quando criar o Webhook)
N8N_WEBHOOK_URL = st.sidebar.text_input("URL do Webhook n8n", "https://seu-n8n.com/webhook/recuperacao-jumbo")

# --- Definição das Colunas (Mantendo seu padrão) ---
COL_ID = 'Codigo Cliente'
COL_NAME = 'Cliente'
COL_PHONE = 'Fone Fixo'
COL_FILTER = 'Quant. Pedidos Enviados' 
COL_STATUS = 'Status' 
COL_ORDER_ID = 'N. Pedido' 
COL_TOTAL_VALUE = 'Valor Total' 

@st.cache_data
def process_data(df_input):
    df = df_input.copy()
    
    # 1. Checagem de colunas
    required_cols = [COL_ID, COL_NAME, COL_PHONE, COL_FILTER, COL_STATUS, COL_ORDER_ID, COL_TOTAL_VALUE]
    if not all(col in df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df.columns]
        raise ValueError(f"Faltam colunas: {', '.join(missing)}")

    # 2. Limpeza e Filtro: Cliente NOVO (0 pedidos) e Pedido Salvo
    df[COL_FILTER] = pd.to_numeric(df[COL_FILTER], errors='coerce').fillna(-1)
    
    # Identifica leads que nunca compraram e estão com pedido parado
    df_qualified = df[
        (df[COL_STATUS] == 'Pedido Salvo') & 
        (df[COL_FILTER] == 0)
    ].drop_duplicates(subset=[COL_ID], keep='first')

    return df_qualified

# --- Interface ---
uploaded_file = st.file_uploader("Suba o relatório CSV ou XLSX", type=["csv", "xlsx"])

if uploaded_file:
    try:
        df_original = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df_leads = process_data(df_original)
        
        st.success(f"Encontrados {len(df_leads)} leads qualificados.")
        st.dataframe(df_leads[[COL_NAME, COL_PHONE, COL_TOTAL_VALUE, COL_ORDER_ID]])

        if not df_leads.empty:
            st.divider()
            st.subheader("🚀 Disparar para n8n")
            
            if st.button("Iniciar Automação de Mensagens IA"):
                with st.spinner("Enviando dados para o n8n..."):
                    # Preparamos os dados para o n8n
                    payload = df_leads.to_dict(orient='records')
                    
                    try:
                        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
                        if response.status_code == 200:
                            st.balloons()
                            st.success("✅ Sucesso! O n8n recebeu os leads e a Sofia iniciará os contatos.")
                        else:
                            st.error(f"Erro no n8n: Status {response.status_code}")
                    except Exception as e:
                        st.error(f"Falha na conexão: {e}")
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
