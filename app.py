import streamlit as st
import pandas as pd
import requests
import io
import re

# --- Configurações da Aplicação ---
st.set_page_config(layout="wide", page_title="Automação de Vendas - Jumbo CDP", page_icon="🚀")

# Estilo CSS para melhorar o visual
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Recuperação de Carrinho com IA")
st.markdown("Filtra clientes novos (**0 pedidos**) com **pedidos salvos** e envia para a Sofia no n8n.")

# --- Configuração da URL do Webhook na Barra Lateral ---
st.sidebar.header("⚙️ Configurações")
webhook_url = st.sidebar.text_input(
    "URL do Webhook n8n", 
    placeholder="https://sua-instancia.n8n.cloud/webhook/leads",
    help="Insira o endpoint do n8n que receberá os dados."
)

# --- Definição das Colunas ---
COL_ID = 'Codigo Cliente'
COL_NAME = 'Cliente'
COL_PHONE = 'Fone Fixo'
COL_FILTER = 'Quant. Pedidos Enviados'
COL_STATUS = 'Status'
COL_ORDER_ID = 'N. Pedido'
COL_TOTAL_VALUE = 'Valor Total'

def clean_phone(phone):
    """Remove caracteres não numéricos do telefone."""
    if pd.isna(phone):
        return ""
    return re.sub(r'\D', '', str(phone))

@st.cache_data
def process_leads(df_input):
    df = df_input.copy()
    
    # Validação de colunas
    required = [COL_ID, COL_NAME, COL_PHONE, COL_FILTER, COL_STATUS, COL_ORDER_ID, COL_TOTAL_VALUE]
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ Colunas ausentes no arquivo: {', '.join(missing)}")
        return None

    # Tratamento de dados
    df[COL_FILTER] = pd.to_numeric(df[COL_FILTER], errors='coerce').fillna(-1)
    df[COL_PHONE] = df[COL_PHONE].apply(clean_phone)
    
    # Lógica de Qualificação: 0 pedidos + Status 'Pedido Salvo'
    df_qualified = df[
        (df[COL_STATUS] == 'Pedido Salvo') & 
        (df[COL_FILTER] == 0)
    ].drop_duplicates(subset=[COL_ID], keep='first')

    return df_qualified

# --- Interface de Upload ---
uploaded_file = st.file_uploader("Suba o arquivo Excel ou CSV do relatório", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Carregamento do arquivo
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
            
        df_leads = process_leads(df_raw)
        
        if df_leads is not None:
            st.subheader("📊 Resultados da Filtragem")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total no Arquivo", len(df_raw))
            col2.metric("Leads Qualificados", len(df_leads))
            col3.info(f"Filtro: Status='Pedido Salvo' & Pedidos=0")

            if not df_leads.empty:
                # Exibição dos dados
                view_cols = [COL_NAME, COL_PHONE, COL_ORDER_ID, COL_TOTAL_VALUE]
                st.dataframe(df_leads[view_cols], use_container_width=True)
                
                # Botão para baixar CSV localmente
                csv = df_leads.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar Leads Filtrados (CSV)",
                    data=csv,
                    file_name="leads_qualificados.csv",
                    mime="text/csv",
                )

                st.divider()
                st.header("🤖 Automação Sofia (n8n)")
                
                if st.button("Disparar Fluxo de Recuperação"):
                    if not webhook_url:
                        st.warning("⚠️ Insira a URL do Webhook na barra lateral antes de continuar.")
                    else:
                        with st.spinner("Enviando dados para o n8n..."):
                            # Mapeamento para o payload
                            payload_df = df_leads.rename(columns={
                                COL_NAME: 'nome_cliente',
                                COL_PHONE: 'telefone',
                                COL_ORDER_ID: 'id_pedido',
                                COL_TOTAL_VALUE: 'valor_total',
                                COL_ID: 'codigo_cliente'
                            }).fillna('')
                            
                            payload = payload_df.to_dict(orient='records')
                            
                            try:
                                response = requests.post(webhook_url, json=payload, timeout=30)
                                
                                if response.status_code in [200, 201]:
                                    st.balloons()
                                    st.success(f"✅ Sucesso! {len(payload)} leads enviados para o fluxo da Sofia.")
                                else:
                                    st.error(f"❌ Erro no n8n: Código {response.status_code}")
                                    st.code(response.text)
                            except Exception as e:
                                st.error(f"❌ Falha de conexão: {e}")
            else:
                st.info("Nenhum lead encontrado com os critérios de 'Pedido Salvo' e 0 pedidos.")

    except Exception as e:
        st.error(f"💥 Ocorreu um erro inesperado: {e}")

else:
    st.info("👋 Por favor, faça o upload do relatório de vendas para começar.")
