import streamlit as st
import pandas as pd
import requests
import io

# --- Configurações da Aplicação ---
st.set_page_config(layout="wide", page_title="Automação de Vendas - Jumbo CDP")

st.title("🚀 Recuperação de Carrinho com IA")
st.markdown("Filtra clientes novos (0 pedidos) com pedidos salvos e envia para a Sofia no n8n.")

# Configuração da URL do Webhook na Barra Lateral
st.sidebar.header("Configurações de Conexão")
webhook_url = st.sidebar.text_input(
    "URL do Webhook n8n", 
    placeholder="https://realbureis.app.n8n.cloud/webhook-test/webhook/leads"
)

# --- Definição das Colunas (Conforme seu padrão) ---
COL_ID = 'Codigo Cliente'
COL_NAME = 'Cliente'
COL_PHONE = 'Fone Fixo'
COL_FILTER = 'Quant. Pedidos Enviados'
COL_STATUS = 'Status'
COL_ORDER_ID = 'N. Pedido'
COL_TOTAL_VALUE = 'Valor Total'

@st.cache_data
def process_leads(df_input):
    """
    Filtra leads: apenas clientes novos (0 pedidos anteriores) 
    com o status específico de 'Pedido Salvo'.
    """
    df = df_input.copy()
    
    # Garante que as colunas necessárias existam
    required = [COL_ID, COL_NAME, COL_PHONE, COL_FILTER, COL_STATUS, COL_ORDER_ID, COL_TOTAL_VALUE]
    if not all(c in df.columns for c in required):
        missing = [c for c in required if c not in df.columns]
        raise ValueError(f"Colunas ausentes: {', '.join(missing)}")

    # Converte coluna de filtro para numérico
    df[COL_FILTER] = pd.to_numeric(df[COL_FILTER], errors='coerce').fillna(-1)
    
    # Lógica de Qualificação
    df_qualified = df[
        (df[COL_STATUS] == 'Pedido Salvo') & 
        (df[COL_FILTER] == 0)
    ].drop_duplicates(subset=[COL_ID], keep='first')

    return df_qualified

# --- Interface de Upload ---
uploaded_file = st.file_uploader("Suba o arquivo Excel ou CSV do relatório", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
            
        df_leads = process_leads(df_raw)
        
        # Exibição de Métricas
        st.subheader("Resultados da Filtragem")
        col1, col2 = st.columns(2)
        col1.metric("Total no Arquivo", len(df_raw))
        col2.metric("Leads Qualificados", len(df_leads))

        if not df_leads.empty:
            st.dataframe(df_leads[[COL_NAME, COL_PHONE, COL_ORDER_ID, COL_TOTAL_VALUE]], use_container_width=True)
            
            st.divider()
            st.header("Disparar para n8n")
            
            if st.button("Iniciar Automação de Mensagens IA"):
                if not webhook_url:
                    st.warning("⚠️ Por favor, insira a URL do Webhook no menu lateral.")
                else:
                    with st.spinner("Preparando e enviando dados..."):
                        # --- CORREÇÃO DO ERRO DE JSON (NaN) ---
                        # O fillna('') substitui valores vazios por texto em branco, aceito pelo JSON
                        df_payload = df_leads.fillna('') 
                        payload = df_payload.to_dict(orient='records')
                        
                        try:
                            response = requests.post(webhook_url, json=payload, timeout=15)
                            
                            if response.status_code == 200:
                                st.balloons()
                                st.success("✅ Sucesso! Dados enviados para o n8n.")
                            else:
                                st.error(f"Erro no n8n: Código {response.status_code}")
                                st.write(response.text)
                        except Exception as e:
                            st.error(f"Falha na conexão: {e}")
        else:
            st.info("Nenhum lead qualificado encontrado com os critérios (0 pedidos + Pedido Salvo).")

    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
