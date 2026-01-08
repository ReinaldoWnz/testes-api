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
st.set_page_config(page_title="Dashboard Automatizado Shopee", layout="wide")

# --- Autenticação via Sidebar ---
st.sidebar.header("🔑 Configurações API")
APP_ID = st.sidebar.text_input("AppID", value="1818441000")
SECRET = st.sidebar.text_input("Secret (Senha)", type="password")
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

def gerar_headers(payload_str):
    timestamp = str(int(time.time()))
    factor = APP_ID + timestamp + payload_str + SECRET
    signature = hashlib.sha256(factor.encode('utf-8')).hexdigest()
    return {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

# --- Filtros de Data Automáticos ---
st.sidebar.header("📅 Filtros de Período")
fuso_br = pytz.timezone('America/Sao_Paulo')
hoje_br = datetime.datetime.now(fuso_br).date()
padrao_inicio = hoje_br - datetime.timedelta(days=7)

periodo = st.sidebar.date_input("Selecione o Período", value=(padrao_inicio, hoje_br), max_value=hoje_br)

# --- Função de Busca de Dados ---
@st.cache_data(ttl=600) # Cache de 10 minutos para não estourar limite da API
def buscar_dados_shopee(inicio, fim):
    ts_inicio = int(fuso_br.localize(datetime.datetime.combine(inicio, datetime.time.min)).timestamp())
    ts_fim = int(fuso_br.localize(datetime.datetime.combine(fim, datetime.time.max)).timestamp())

    query = f"""{{
        conversionReport(purchaseTimeStart: {ts_inicio}, purchaseTimeEnd: {ts_fim}, limit: 100) {{
            nodes {{
                purchaseTime
                conversionStatus
                totalCommission
                completeTime
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
        
        nodes = data.get('data', {}).get('conversionReport', {}).get('nodes', [])
        return nodes, None
    except Exception as e:
        return None, str(e)

# --- Processamento dos Dados ---
if SECRET:
    if isinstance(periodo, tuple) and len(periodo) == 2:
        nodes, erro = buscar_dados_shopee(periodo[0], periodo[1])
        
        if erro:
            st.error(f"Erro na API: {erro}")
        elif nodes:
            # Transformar JSON da API em DataFrame Pandas compatível com o código antigo
            rows = []
            for n in nodes:
                # Extraindo itens para suportar o Top 10
                for order in n.get('orders', []):
                    for item in order.get('items', []):
                        rows.append({
                            "Horário do pedido": pd.to_datetime(n['purchaseTime'], unit='s', utc=True).tz_convert(fuso_br),
                            "Tempo de Conclusão": pd.to_datetime(n['completeTime'], unit='s', utc=True).tz_convert(fuso_br) if n['completeTime'] else pd.NaT,
                            "Status do Pedido": n['conversionStatus'],
                            "Comissão líquida do afiliado(R$)": float(n['totalCommission']),
                            "Nome do Item": item['itemName'],
                            "Qtd": item['qty'],
                            "Valor Item": float(item['itemPrice'])
                        })
            
            df = pd.DataFrame(rows)

            # --- SEÇÃO DE MÉTRICAS (IGUAL AO SEU CÓDIGO) ---
            st.title("📊 Painel de Análise Automatizado")
            
            # Cálculo de Totais
            df_concluido = df[df["Status do Pedido"].str.contains("COMPLETE|SETTLED", case=False, na=False)]
            df_pendente = df[df["Status do Pedido"].str.contains("PENDING", case=False, na=False)]
            
            total_concluido = df_concluido["Comissão líquida do afiliado(R$)"].sum()
            total_pendente = df_pendente["Comissão líquida do afiliado(R$)"].sum()
            total_estimado = total_concluido + total_pendente
            
            col1, col2, col3 = st.columns(3)
            col1.metric("📌 Concluído (Período)", f"R$ {total_concluido:,.2f}")
            col2.metric("📌 Total Estimado (Bruto)", f"R$ {total_estimado:,.2f}")
            col3.metric("📌 Líquido Est. (-11%)", f"R$ {(total_estimado * 0.89):,.2f}")

            # --- GRÁFICOS ---
            st.divider()
            col_esq, col_dir = st.columns(2)
            
            with col_esq:
                agrupado = df.groupby("Status do Pedido")["Comissão líquida do afiliado(R$)"].sum().reset_index()
                fig_bar = px.bar(agrupado, x="Status do Pedido", y="Comissão líquida do afiliado(R$)", title="Comissão por Status")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with col_dir:
                # Top 10 Produtos (Sua lógica de Pop-over)
                with st.popover("🛍️ Ver Top 10 Produtos Mais Vendidos"):
                    top_itens = df.groupby("Nome do Item")["Qtd"].sum().nlargest(10).reset_index()
                    st.table(top_itens.rename(columns={"Nome do Item": "Produto", "Qtd": "Qtd Vendida"}))

            # Tabela de Dados Brutos
            with st.expander("Ver lista detalhada de pedidos"):
                st.dataframe(df)

        else:
            st.info("Nenhum dado encontrado para este período.")
else:
    st.warning("Aguardando Configuração da API (AppID e Secret) na barra lateral.")
