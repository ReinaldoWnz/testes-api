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

# Sidebar - Configurações
st.sidebar.header("🔑 Configurações API")
APP_ID = st.sidebar.text_input("AppId", value="1818441000")
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

@st.cache_data(ttl=300) # Cache de 5 minutos
def buscar_dados_shopee(inicio, fim):
    if not SECRET: return None, "Aguardando Secret"
    
    # Ajuste preciso de Timestamp para o fuso de Brasília
    ts_inicio = int(fuso_br.localize(datetime.datetime.combine(inicio, datetime.time.min)).timestamp())
    ts_fim = int(fuso_br.localize(datetime.datetime.combine(fim, datetime.time.max)).timestamp())

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

# --- Processamento dos Dados ---
st.title("📊 Painel de Análise Shopee (API Automatizada)")

if SECRET:
    if isinstance(periodo, tuple) and len(periodo) == 2:
        with st.spinner('Sincronizando com a Shopee...'):
            nodes, erro = buscar_dados_shopee(periodo[0], periodo[1])
        
        if erro:
            st.error(f"Erro na API: {erro}")
        elif nodes:
            rows = []
            for n in nodes:
                dt_pedido = pd.to_datetime(n['purchaseTime'], unit='s', utc=True).tz_convert(fuso_br)
                status = n['conversionStatus'].upper()
                comissao = float(n.get('totalCommission', 0))
                
                for order in n.get('orders', []):
                    for item in order.get('items', []):
                        rows.append({
                            "Data": dt_pedido.date(),
                            "Horário": dt_pedido,
                            "Status": status,
                            "Comissão": comissao,
                            "Produto": item.get('itemName', 'N/A'),
                            "Qtd": item.get('qty', 0),
                            "Valor Item": float(item.get('itemPrice', 0))
                        })
            
            df = pd.DataFrame(rows)

            # --- CORREÇÃO: Lógica de Status Concluídos ---
            # 'SETTLED' e 'COMPLETE' são considerados concluídos na Shopee
            df_concluido = df[df["Status"].isin(["COMPLETE", "SETTLED"])]
            df_pendente = df[df["Status"] == "PENDING"]
            df_cancelado = df[df["Status"].isin(["CANCELLED", "INVALID"])]

            # --- Cartões de Métricas (Estilo Original) ---
            total_concluido = df_concluido["Comissão"].sum()
            total_pendente = df_pendente["Comissão"].sum()
            total_estimado = total_concluido + total_pendente

            col1, col2, col3 = st.columns(3)
            col1.metric("📌 Concluído", f"R$ {total_concluido:,.2f}", f"{len(df_concluido)} pedidos")
            col2.metric("📌 Total Estimado (Bruto)", f"R$ {total_estimado:,.2f}")
            col3.metric("📌 Líquido Est. (-11%)", f"R$ {(total_estimado * 0.89):,.2f}")

            # --- Visualização de Gráficos ---
            st.divider()
            col_graf1, col_graf2 = st.columns(2)

            with col_graf1:
                st.subheader("📈 Faturamento Diário (Concluído)")
                faturamento_diario = df_concluido.groupby("Data")["Comissão"].sum().reset_index()
                fig_vendas = px.line(faturamento_diario, x="Data", y="Comissão", markers=True)
                st.plotly_chart(fig_vendas, use_container_width=True)

            with col_graf2:
                # Top 10 Itens (Sua lógica de Pop-over)
                with st.popover("🛍️ Top 10 Produtos Vendidos"):
                    top_itens = df.groupby("Produto")["Qtd"].sum().nlargest(10).reset_index()
                    st.table(top_itens.rename(columns={"Qtd": "Vendidos"}))

            # Tabela detalhada para conferência
            with st.expander("📄 Ver Lista Detalhada de Pedidos"):
                st.dataframe(df.sort_values("Horário", ascending=False))

        else:
            st.info("Nenhum pedido encontrado para este período.")
else:
    st.info("👋 Por favor, insira o **Secret** na barra lateral para começar.")
