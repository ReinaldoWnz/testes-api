import streamlit as st
import requests
import time
import hashlib
import json

st.set_page_config(page_title="Shopee Affiliate API Tester", page_icon="🛍️")

st.title("🔌 Shopee Affiliate API - Painel")

# Configurações na Barra Lateral
st.sidebar.header("Configurações de Autenticação")
APP_ID = st.sidebar.text_input("AppID", value="1818441000")
SECRET = st.sidebar.text_input("Secret (Senha)", type="password")
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

st.info("Este painel utiliza o protocolo GraphQL para buscar dados da Shopee.")

# Função para gerar o cabeçalho de autenticação
def gerar_headers(payload_str):
    timestamp = str(int(time.time()))
    # O fator deve ser: AppId + Timestamp + Payload + Secret
    factor = APP_ID + timestamp + payload_str + SECRET
    signature = hashlib.sha256(factor.encode('utf-8')).hexdigest()
    
    return {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

# Seleção de Operação
operacao = st.selectbox("O que deseja buscar?", ["Lista de Ofertas", "Relatório de Conversão"])

if operacao == "Lista de Ofertas":
    query = """{
    brandOffer(limit: 5) {
        nodes {
            brandName
            commissionRate
            offerLink
        }
    }
}"""
else:
    # O intervalo de tempo para conversão deve ser dos últimos 3 meses
    query = """{
    conversionReport(limit: 10) {
        nodes {
            purchaseTime
            orderStatus
            commission
        }
    }
}"""

if st.button("Executar Consulta"):
    if not SECRET:
        st.error("Por favor, insira sua Senha (Secret) na barra lateral.")
    else:
        with st.spinner('Consultando Shopee...'):
            try:
                payload = {"query": query}
                # Formatação estrita para garantir que a assinatura bata com o payload
                payload_str = json.dumps(payload, separators=(',', ':'))
                
                headers = gerar_headers(payload_str)
                response = requests.post(ENDPOINT, headers=headers, data=payload_str)
                
                if response.status_code == 200:
                    data = response.json()
                    if "errors" in data:
                        st.error(f"Erro na API: {data['errors'][0]['message']}")
                    else:
                        st.success("Dados recuperados com sucesso!")
                        st.json(data)
                else:
                    st.error(f"Erro na requisição (Status {response.status_code})")
                    st.code(response.text)
                    
            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")

st.divider()
st.caption("Nota: O limite de chamadas é de 2000 por hora. O ScrollID é necessário para paginação.")
