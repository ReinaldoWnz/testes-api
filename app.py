import streamlit as st
import requests
import time
import hashlib
import json

st.set_page_config(page_title="Shopee Affiliate Panel", page_icon="🛍️")

st.title("🛍️ Painel Afiliado Shopee")

# Configurações na Barra Lateral
st.sidebar.header("Autenticação")
APP_ID = st.sidebar.text_input("AppID", value="1818441000")
SECRET = st.sidebar.text_input("Secret (Senha)", type="password")
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

def gerar_headers(payload_str):
    timestamp = str(int(time.time()))
    # Ordem obrigatória: AppId + Timestamp + Payload + Secret
    factor = APP_ID + timestamp + payload_str + SECRET
    signature = hashlib.sha256(factor.encode('utf-8')).hexdigest()
    
    return {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

# Abas para organizar as funções
tab1, tab2 = st.tabs(["Listar Ofertas", "Gerar Link Curto"])

with tab1:
    st.subheader("Melhores Ofertas de Marcas")
    if st.button("Buscar Ofertas"):
        # Corrigido: Usando 'offerName' em vez de 'brandName' conforme o manual
        query = """{
            brandOffer(limit: 5) {
                nodes {
                    offerName
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
                st.error(f"Erro: {data['errors'][0]['message']}")
            else:
                for offer in data['data']['brandOffer']['nodes']:
                    st.write(f"**Produto:** {offer['offerName']}")
                    st.write(f"**Comissão:** {offer['commissionRate']}%")
                    st.write(f"[Link da Oferta]({offer['offerLink']})")
                    st.divider()
        except Exception as e:
            st.error(f"Erro na conexão: {e}")

with tab2:
    st.subheader("Transformar Link em Afiliado")
    link_original = st.text_input("Cole o link do produto Shopee aqui:")
    
    if st.button("Gerar Link Curto"):
        if link_original:
            # Query específica para gerar links curtos (ShortLink)
            query = f"""
            mutation {{
                generateShortLink(input: {{ originLinks: ["{link_original}"] }}) {{
                    shortLinkList {{
                        shortLink
                    }}
                }}
            }}
            """
            
            payload = {"query": query}
            payload_str = json.dumps(payload, separators=(',', ':'))
            
            headers = gerar_headers(payload_str)
            response = requests.post(ENDPOINT, headers=headers, data=payload_str)
            data = response.json()
            
            if "errors" in data:
                st.error(f"Erro: {data['errors'][0]['message']}")
            else:
                link_gerado = data['data']['generateShortLink']['shortLinkList'][0]['shortLink']
                st.success("Link gerado com sucesso!")
                st.code(link_gerado)
        else:
            st.warning("Insira um link válido.")
