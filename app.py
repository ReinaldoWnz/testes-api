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

with tab3:
    st.subheader("📊 Resumo de Métricas (Últimos 3 Dias)")
    
    if st.button("Atualizar Painel"):
        agora = int(time.time())
        tres_dias_atras = agora - (3 * 24 * 60 * 60)
        
        # Query ajustada para pegar dados de conversão
        query = f"""{{
            conversionReport(purchaseTimeStart: {tres_dias_atras}, purchaseTimeEnd: {agora}, limit: 100) {{
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
                st.error(f"Erro: {data['errors'][0]['message']}")
            else:
                vendas = data.get('data', {}).get('conversionReport', {}).get('nodes', [])
                
                # Cálculo das métricas estilo Shopee
                total_pedidos = len(vendas)
                comissao_total = sum(float(v['totalCommission']) for v in vendas)
                valor_total_pedidos = 0
                itens_vendidos = 0
                
                for v in vendas:
                    for order in v.get('orders', []):
                        for item in order.get('items', []):
                            valor_total_pedidos += float(item.get('itemPrice', 0))
                            itens_vendidos += 1

                # Exibição em Colunas (Cards)
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Pedidos", total_pedidos)
                with col2:
                    st.metric("Comissão Est. (R$)", f"{comissao_total:.2f}")
                with col3:
                    st.metric("Itens Vendidos", itens_vendidos)
                with col4:
                    st.metric("Valor do Pedido (R$)", f"{valor_total_pedidos:.2f}")

                st.divider()
                st.info("Nota: A API de Afiliados não fornece o número de 'Cliques' em tempo real através do conversionReport. Esses dados são consolidados apenas no portal.")

        except Exception as e:
            st.error(f"Erro ao processar métricas: {e}")
