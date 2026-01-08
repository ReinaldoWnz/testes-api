import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
import hashlib
import json
import datetime
import pytz

# --- Configurações Iniciais ---
st.set_page_config(page_title="Shopee Dashboard Automatizado", layout="wide")

# Estilo para esconder o drag and drop (já que agora é automático)
st.markdown("<style>.st-emotion-cache-1c7y2o4 {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- Sidebar: Autenticação e Filtros ---
st.sidebar.header("🔑 Configurações API")
APP_ID = st.sidebar.text_input("AppID", value="1818441000")
SECRET = st.sidebar.text_input("Secret (Senha)", type="password")
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

st.sidebar.markdown("---")
st.sidebar.header("📅 Filtros de Período")
fuso_br = pytz.timezone('America/Sao_Paulo')
hoje_br = datetime.datetime.now(fuso_br).date()
padrao_inicio = hoje_br - datetime.timedelta(days=7)

periodo = st.sidebar.date_input("Selecione o Período", value=(padrao_inicio, hoje_br), max_value=hoje_br)

def gerar_headers(payload_str):
    timestamp = str(int(time.time()))
    factor = APP_ID + timestamp + payload_str + SECRET
    signature = hashlib.sha256(factor.encode('utf-8')).hexdigest()
    return {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

@st.cache_data(ttl=600)
def buscar_dados_shopee(inicio, fim):
    if not SECRET: return None, "Aguardando Secret"
    
    ts_inicio = int(fuso_br.localize(datetime.datetime.combine(inicio, datetime.time.min)).timestamp())
    ts_fim = int(fuso_br.localize(datetime.datetime.combine(fim, datetime.time.max)).timestamp())

    # Query Corrigida: Removido completeTime que causava o erro
    query = f"""{{
        conversionReport(purchaseTimeStart: {ts_inicio}, purchaseTimeEnd: {ts_fim}, limit: 100) {{
            nodes {{
                purchaseTime
                conversionStatus
                totalCommission
                orders {{
                    items {{
                        itemName
                        itemPrice
                        qty
                    }}
                }}
            }}
        }}
    }}"""
    
    payload_str = json.dumps({"query": query}, separators=(',', ':'))
    try:
        headers = gerar_headers(payload_str)
        response = requests.post(ENDPOINT, headers=headers, data=payload_str)
        data = response.json()
        
        if "errors" in data:
            return None, data['errors'][0]['message']
        
        return data.get('data', {}).get('conversionReport', {}).get('nodes', []), None
    except Exception as e:
        return None, str(e)

# --- Processamento Principal ---
st.title("📊 Painel de Análise Shopee (API Auto)")

if SECRET:
    if isinstance(periodo, tuple) and len(periodo) == 2:
        with st.spinner('Buscando dados na Shopee...'):
            nodes, erro = buscar_dados_shopee(periodo[0], periodo[1])
        
        if erro:
            st.error(f"Erro na API: {erro}")
            if "10035" in erro:
                st.warning("Dica: O erro 10035 indica que a Shopee ainda não liberou o acesso da sua conta à API. Entre em contato com o suporte deles.")
        elif nodes:
            # Transformação para DataFrame
            rows = []
            for n in nodes:
                # Mapeamento para o formato do seu código antigo
                dt_pedido = pd.to_datetime(n['purchaseTime'], unit='s', utc=True).tz_convert(fuso_br)
                status = n['conversionStatus']
                comissao = float(n.get('totalCommission', 0))
                
                # Extraindo itens para o Top 10
                for order in n.get('orders', []):
                    for item in order.get('items', []):
                        rows.append({
                            "Horário do pedido": dt_pedido,
                            "Status do Pedido": status,
                            "Comissão líquida do afiliado(R$)": comissao,
                            "Nome do Item": item.get('itemName', 'N/A'),
                            "Qtd": item.get('qty', 0),
                            "Valor Item": float(item.get('itemPrice', 0))
                        })
            
            df = pd.DataFrame(rows)

            # --- Layout de Cartões ---
            st.subheader("📌 Resumo Financeiro")
            # Agrupando por status para os cards
            total_concluido = df[df["Status do Pedido"].isin(["COMPLETE", "SETTLED"])]["Comissão líquida do afiliado(R$)"].sum()
            total_pendente = df[df["Status do Pedido"] == "PENDING"]["Comissão líquida do afiliado(R$)"].sum()
            total_estimado = total_concluido + total_pendente

            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Concluído", f"R$ {total_concluido:,.2f}")
            c2.metric("⏳ Pendente", f"R$ {total_pendente:,.2f}")
            c3.metric("📈 Total Estimado Líquido (-11%)", f"R$ {(total_estimado * 0.89):,.2f}")

            # --- Gráficos ---
            st.divider()
            col_graf1, col_graf2 = st.columns(2)

            with col_graf1:
                df_status = df.groupby("Status do Pedido")["Comissão líquida do afiliado(R$)"].sum().reset_index()
                fig_pie = px.pie(df_status, names="Status do Pedido", values="Comissão líquida do afiliado(R$)", title="Distribuição por Status")
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_graf2:
                # Top 10 Produtos (Pop-over original)
                with st.popover("🛍️ Ver Top 10 Produtos Mais Vendidos"):
                    top_itens = df.groupby("Nome do Item")["Qtd"].sum().nlargest(10).reset_index()
                    st.table(top_itens.rename(columns={"Nome do Item": "Produto", "Qtd": "Vendidos"}))

            # Tabela detalhada
            with st.expander("📄 Visualizar Tabela de Dados Brutos"):
                st.dataframe(df)
        else:
            st.info("Nenhum pedido encontrado para o período selecionado.")
else:
    st.info("👋 Por favor, insira o seu **Secret (Senha)** na barra lateral para carregar os dados automaticamente.")

st.sidebar.markdown("---")
st.sidebar.caption("Versão API V2 Integrada")
