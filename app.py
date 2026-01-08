import streamlit as st
import requests
import time
import hashlib
import json

# --- Configuração de Página e Sidebar (Igual ao anterior) ---
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

tab1, tab2 = st.tabs(["Listar Ofertas (V2)", "Gerar Link Curto"])

with tab1:
    st.subheader("Ofertas Shopee V2")
    if st.button("Buscar Ofertas"):
        # ATUALIZADO: Usando a estrutura productOfferV2 ou similar conforme a versão atual
        query = """{
            productOfferV2(limit: 5) {
                nodes {
                    productName
                    commissionRate
                    offerLink
                }
            }
        }"""
        
        payload = {"query": query}
        payload_str = json.dumps(payload, separators=(',', ':'))
        
        try:
            headers = gerar_headers(payload_str)
            response = requests.post(ENDPOINT, headers=headers, data=payload_str)
            data = response.json()
            
            if "errors" in data:
                # Se productOfferV2 ainda der erro de nome, a Shopee costuma sugerir o nome correto no erro
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
    # (O código de Mutation para Short Link permanece o mesmo, pois é padrão V2)
    st.subheader("Transformar Link em Afiliado")
    link_original = st.text_input("Cole o link do produto Shopee:")
    if st.button("Gerar Link Curto"):
        query = f'mutation {{ generateShortLink(input: {{ originLinks: ["{link_original}"] }}) {{ shortLinkList {{ shortLink }} }} }}'
        payload = {"query": query}
        payload_str = json.dumps(payload, separators=(',', ':'))
        headers = gerar_headers(payload_str)
        response = requests.post(ENDPOINT, headers=headers, data=payload_str)
        data = response.json()
        if "errors" in data:
            st.error(data['errors'][0]['message'])
        else:
            st.success("Link gerado!")
            st.code(data['data']['generateShortLink']['shortLinkList'][0]['shortLink'])
