import streamlit as st
import requests
import time
import hashlib
import json

st.set_page_config(page_title="Shopee Affiliate V2", page_icon="🛍️")
st.sidebar.header("Autenticação")
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

# CORREÇÃO: Adicionada a terceira aba na lista inicial
tab1, tab2, tab3 = st.tabs(["Listar Ofertas (V2)", "Gerar Link Curto", "Relatório de Vendas"])

with tab1:
    st.subheader("Ofertas Shopee V2")
    if st.button("Buscar Ofertas"):
        query = """{
            productOfferV2(limit: 5) {
                nodes {
                    productName
                    commissionRate
                    offerLink
                }
            }
        }"""
        payload_str = json.dumps({"query": query}, separators=(',', ':'))
        try:
            headers = gerar_headers(payload_str)
            response = requests.post(ENDPOINT, headers=headers, data=payload_str)
            data = response.json()
            if "errors" in data:
                st.error(f"Erro da API: {data['errors'][0]['message']}")
            else:
                nodes = data.get('data', {}).get('productOfferV2', {}).get('nodes', [])
                for offer in nodes:
                    st.write(f"**Produto:** {offer['productName']}")
                    st.write(f"**Comissão:** {offer['commissionRate']}%")
                    st.write(f"[Link da Oferta]({offer['offerLink']})")
                    st.divider()
        except Exception as e:
            st.error(f"Erro na conexão: {e}")

with tab2:
    st.subheader("Transformar Link em Afiliado")
    link_original = st.text_input("Cole o link do produto Shopee:")
    if st.button("Gerar Link Curto"):
        if link_original:
            query = f'mutation {{ generateShortLink(input: {{ originLinks: ["{link_original}"] }}) {{ shortLinkList {{ shortLink }} }} }}'
            payload_str = json.dumps({"query": query}, separators=(',', ':'))
            headers = gerar_headers(payload_str)
            response = requests.post(ENDPOINT, headers=headers, data=payload_str)
            data = response.json()
            if "errors" in data:
                st.error(data['errors'][0]['message'])
            else:
                short_link = data['data']['generateShortLink']['shortLinkList'][0]['shortLink']
                st.success("Link gerado!")
                st.code(short_link)

import datetime

with tab3:
    st.subheader("📊 métricas Principais")

    # 1. Filtro de Data (Interface estilo Shopee)
    hoje = datetime.date.today()
    tres_dias_atras = hoje - datetime.timedelta(days=3)
    
    col_data, _ = st.columns([1, 2])
    with col_data:
        periodo = st.date_input(
            "Período dos dados",
            value=(tres_dias_atras, hoje),
            max_value=hoje,
            help="O intervalo máximo permitido é de 3 meses."
        )

    # Verificação para garantir que o usuário selecionou início e fim
    if isinstance(periodo, tuple) and len(periodo) == 2:
        data_inicio, data_fim = periodo
        
        # Converter datas para Unix Timestamp (Segundos)
        ts_inicio = int(time.mktime(data_inicio.timetuple()))
        # Adicionamos 86399 segundos para cobrir até o final do dia escolhido
        ts_fim = int(time.mktime(data_fim.timetuple())) + 86399

        # 2. Carregamento Automático: A query roda sempre que as variáveis acima mudam
        query = f"""{{
            conversionReport(purchaseTimeStart: {ts_inicio}, purchaseTimeEnd: {ts_fim}, limit: 100) {{
                nodes {{
                    totalCommission
                    conversionStatus
                    orders {{
                        items {{
                            itemPrice
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
                st.error(f"Erro na API: {data['errors'][0]['message']}")
            else:
                vendas = data.get('data', {}).get('conversionReport', {}).get('nodes', [])
                
                # Cálculos das métricas
                total_pedidos = len(vendas)
                comissao_total = sum(float(v.get('totalCommission', 0)) for v in vendas)
                valor_total_pedidos = 0
                itens_vendidos = 0
                
                for v in vendas:
                    for order in v.get('orders', []):
                        for item in order.get('items', []):
                            valor_total_pedidos += float(item.get('itemPrice', 0))
                            itens_vendidos += 1

                # 3. Layout de Cards (Igual ao seu print da Shopee)
                c1, c2, c3 = st.columns(3)
                c4, c5, c6 = st.columns(3)
                
                c1.metric("Pedido", total_pedidos)
                c2.metric("Comissão est.(R$)", f"{comissao_total:.2f}")
                c3.metric("Itens vendidos", itens_vendidos)
                c4.metric("Valor do pedido(R$)", f"{valor_total_pedidos:.1f}")
                c5.metric("Cliques", "---", help="Dados de cliques não disponíveis via API de conversão.")
                c6.metric("Novos compradores", "0")

        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
    else:
        st.info("Selecione a data de início e fim no calendário acima.")
