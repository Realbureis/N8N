import streamlit as st
import pandas as pd
import requests
import re

# --- Configurações da Página ---
st.set_page_config(layout="wide", page_title="Automação Jumbo - Z-API", page_icon="🚀")

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
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Recuperação de Carrinho - Sofia & Z-API")
st.markdown("Filtro: **Status = 'Pedido Salvo'** e **Pedidos Enviados = 0**.")

# --- Barra Lateral ---
st.sidebar.header("⚙️ Configurações de Envio")
webhook_url = st.sidebar.text_input(
    "URL do Webhook n8n", 
    placeholder="https://seu-n8n.cloud/webhook/leads"
)

# --- Definição das Colunas da Planilha ---
COL_ID = 'N. Pedido'
COL_NAME = 'Cliente'
COL_PHONE = 'Fone Fixo'
COL_FILTER = 'Quant. Pedidos Enviados'
COL_STATUS = 'Status'
COL_TOTAL_VALUE = 'Valor Total'

def clean_phone(phone):
    """Limpa o número e garante o prefixo 55 para o Brasil."""
    if pd.isna(phone): 
        return ""
    clean = re.sub(r'\D', '', str(phone))
    if not clean: 
        return ""
    # Se tiver DDD (10 ou 11 dígitos), adiciona o 55
    if len(clean) in [10, 11]:
        clean = "55" + clean
    return clean

@st.cache_data
def process_leads(df_input):
    df = df_input.copy()
    
    # Verifica se todas as colunas necessárias existem
    required = [COL_ID, COL_NAME, COL_PHONE, COL_FILTER, COL_STATUS, COL_TOTAL_VALUE]
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ Colunas ausentes na planilha: {', '.join(missing)}")
        return None

    # Tratamento de dados
    df[COL_FILTER] = pd.to_numeric(df[COL_FILTER], errors='coerce').fillna(-1)
    df[COL_PHONE] = df[COL_PHONE].apply(clean_phone)
    
    # Aplicação dos Filtros
    df_qualified = df[
        (df[COL_STATUS] == 'Pedido Salvo') & 
        (df[COL_FILTER] == 0)
    ].drop_duplicates(subset=[COL_ID], keep='first')

    return df_qualified

# --- Área de Upload ---
uploaded_file = st.file_uploader("Arraste sua planilha (CSV ou Excel) aqui", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
            
        df_leads = process_leads(df_raw)
        
        if df_leads is not None:
            # Painel de Métricas
            c1, c2 = st.columns(2)
            c1.metric("Total no Arquivo", len(df_raw))
            c2.metric("Leads Qualificados", len(df_leads))

            if not df_leads.empty:
                st.subheader("📋 Lista de Envio")
                st.dataframe(
                    df_leads[[COL_ID, COL_NAME, COL_PHONE, COL_TOTAL_VALUE]], 
                    use_container_width=True
                )
                
                st.divider()
                
                if st.button("🚀 DISPARAR MENSAGENS AGORA"):
                    if not webhook_url:
                        st.warning("⚠️ Insira a URL do Webhook na barra lateral antes de disparar.")
                    else:
                        with st.spinner("Enviando dados para o n8n..."):
                            # Simplificação do Payload para o n8n
                            payload = df_leads.rename(columns={
                                COL_ID: 'id_pedido',
                                COL_NAME: 'nome_cliente',
                                COL_PHONE: 'Telefone',
                                COL_TOTAL_VALUE: 'valor_total'
                            })[['id_pedido', 'nome_cliente', 'telefone', 'valor_total']].to_dict(orient='records')
                            
                            try:
                                response = requests.post(webhook_url, json=payload, timeout=30)
                                if response.status_code in [200, 201]:
                                    st.balloons()
                                    st.success(f"✅ Sucesso! {len(payload)} leads enviados para processamento.")
                                else:
                                    st.error(f"❌ Erro no servidor: {response.status_code}")
                            except Exception as e:
                                st.error(f"❌ Erro de conexão: {e}")
            else:
                st.info("Nenhum lead qualificado encontrado com os filtros aplicados.")

    except Exception as e:
        st.error(f"💥 Erro ao processar arquivo: {e}")
else:
    st.info("💡 Dica: O arquivo deve conter as colunas: N. Pedido, Cliente, Fone Fixo, Status e Valor Total.")
