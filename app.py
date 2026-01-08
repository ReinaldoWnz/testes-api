import streamlit as st
import requests
import time
import hashlib
import json
import datetime
import pytz

# Configurações Iniciais
st.set_page_config(page_title="Shopee Affiliate Dashboard", layout="wide")

# Sidebar - Credenciais
st.sidebar.header("🔑 Autenticação")
APP_ID = st.sidebar.text_input("AppID", value="1818441000")
SECRET = st.sidebar.text_input("Secret (Senha)", type="password")
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql" #

# Função para Gerar Assinatura SHA256
def gerar_headers(payload_str):
    timestamp = str(int(time.time())) #
    # Ordem: AppId + Timestamp + Payload + Secret
    factor = APP_ID + timestamp + payload_str + SECRET
    signature = hashlib.sha256(factor.encode('utf-8')).hexdigest()
    
    return {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

# --- ABAS ---
tab1, tab2, tab3 = st.tabs(["📊 Métricas Principais", "🔗 Gerador de Links", "🛍️ Ofertas V2"])

# --- ABA 1: MÉTRICAS (IGUAL AO PAINEL SHOPEE) ---
with tab1:
    st.subheader("📊 Métricas Principais")
    
    # Filtro de Data com Fuso Horário de Brasília
    fuso_br = pytz.timezone('America/Sao_Paulo')
    hoje_br = datetime.datetime.now(fuso_br).date()
    
    col_date, _ = st.columns([1, 2])
    with col_date:
        periodo = st.date_input("Período dos dados", value=(hoje_br, hoje_br), max_value=hoje_br)

    if isinstance(periodo, tuple) and len(periodo) == 2:
        d_inicio, d_fim = periodo
        # Converte para Timestamps exatos (Início do dia 00:00:00 e fim 23:59:59)
        ts_inicio = int(fuso_br.localize(datetime.datetime.combine(d_inicio, datetime.time.min)).timestamp())
        ts_fim = int(fuso_br.localize(datetime.datetime.combine(d_fim, datetime.time.max)).timestamp())

        # Query ConversionReport V2
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
        
        payload_str = json.dumps({"query": query}, separators=(',', ':')) #
        
        try:
            headers = gerar_headers(payload_str)
            response = requests.post(ENDPOINT, headers=headers, data=payload_str) #
            data = response.json()
            
            if "errors" in data:
                st.error(f"Erro da API: {data['errors'][0]['message']}") #
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

                # Layout de Cards Estilo Shopee
                c1, c2, c3 = st.columns(3)
                c4, c5, c6 = st.columns(3)
                
                c1.metric("Pedido", total_pedidos)
                c2.metric("Comissão est.(R$)", f"{comissao_total:.2f}")
                c3.metric("Itens vendidos", itens_vendidos)
                c4.metric("Valor do pedido(R$)", f"{valor_total_pedidos:.2f}")
                c5.metric("Cliques", "---", help="API de Conversão não retorna cliques.")
                c6.metric("Novos compradores", "0")

        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

# --- ABA 2: GERADOR DE LINKS ---
with tab2:
    st.subheader("🔗 Gerar Link de Afiliado")
    url_input = st.text_input("Cole o link do produto Shopee:")
    if st.button("Gerar Link"):
        if url_input:
            # Mutation para gerar links curtos
            mutation = f'mutation {{ generateShortLink(input: {{ originLinks: ["{url_input}"] }}) {{ shortLinkList {{ shortLink }} }} }}'
            p_load = json.dumps({"query": mutation}, separators=(',', ':'))
            h = gerar_headers(p_load)
            res = requests.post(ENDPOINT, headers=h, data=p_load).json()
            
            if "errors" in res:
                st.error(res['errors'][0]['message'])
            else:
                link = res['data']['generateShortLink']['shortLinkList'][0]['shortLink']
                st.success("Link Encurtado!")
                st.code(link)

# --- ABA 3: OFERTAS (V2) ---
with tab3:
    st.subheader("🛍️ Ofertas Disponíveis (ProductOfferV2)")
    if st.button("Carregar Ofertas"):
        query_v2 = "{ productOfferV2(limit: 5) { nodes { productName commissionRate offerLink } } }"
        p_v2 = json.dumps({"query": query_v2}, separators=(',', ':'))
        h_v2 = gerar_headers(p_v2)
        res_v2 = requests.post(ENDPOINT, headers=h_v2, data=p_v2).json()
        
        if "data" in res_v2:
            for item in res_v2['data']['productOfferV2']['nodes']:
                st.write(f"**{item['productName']}**")
                st.write(f"Comissão: {item['commissionRate']}%")
                st.write(f"[Ver Produto]({item['offerLink']})")
                st.divider()
