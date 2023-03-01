import extra_streamlit_components as stx
import streamlit as st
import requests

from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta
from msal import PublicClientApplication
import jwt

# Configurações da aplicação
CLIENT_ID = st.secrets['azure']['client_id']
TENANT_ID = st.secrets['azure']['tenant_id']
CLIENT_SECRET = st.secrets['azure']['client_secret']
REDIRECT_URI = st.secrets['azure']['redirect_uri']
AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
SCOPE = ["https://graph.microsoft.com/.default"]

# Criação de todas as variaveis utilizadas na Session State
if 'mail' not in st.session_state:
    st.session_state.mail = None

if 'name' not in st.session_state:
    st.session_state.name = None

if 'accounts' not in st.session_state:
    st.session_state.accounts = None

# Define o cookie manager
cookie_manager = stx.CookieManager()
cookie_name = st.secrets['auth_config']['name']
cookie_exp_day = st.secrets['auth_config']['expiry_days']
cookie_key = st.secrets['auth_config']['key']
cookie_exp_date = (datetime.now() + timedelta(days=cookie_exp_day)).timestamp()

# Define a função de verificação de usuário no Cookie Manager
cookie = cookie_manager.get(cookie_name)

# Configura a credencial padrão do Azure
credential = DefaultAzureCredential()

# Configura o client do MSAL
app = PublicClientApplication(
    CLIENT_ID,
    authority=AUTHORITY
)

# Realiza a verificação 
if cookie is not None:
    try:
        cookie = jwt.decode(cookie, key=cookie_key, algorithms=['HS256'])
    except:
        cookie = False

def check_cookie():
    if cookie is not None:
        if cookie['exp_date'] > datetime.utcnow().timestamp():
            if 'name' and 'mail' in cookie:
                st.session_state.name = cookie['name']
                st.session_state.mail = cookie['mail']
                st.session_state.accounts = cookie['accounts']

                return True
            else:
                return False
        else:
            return False
    else:
        return False

# Define a função de login
def login():
    if check_cookie() is False:
        if st.button('Login'):
            flow = app.initiate_device_flow(scopes=SCOPE)
            st.write("Para fazer login, acesse: " + flow['verification_uri'])
            st.write("E insira o código: " + flow['user_code'])
            result = app.acquire_token_by_device_flow(flow)
            access_token = result["access_token"]

            accounts = app.get_accounts()

            # Obtém informações do usuário com o token de acesso
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_data = response.json()

            user_name = user_data['displayName']

            if user_data['mail'] is None:
                user_mail = user_data['userPrincipalName']
            else:
                user_mail = user_data['mail']

            # Define as variaveis de Session State
            st.session_state.name = user_name
            st.session_state.mail = user_mail
            st.session_state.accounts = accounts

            # Cria o token 
            token = jwt.encode(
                {
                    'name':st.session_state['name'],
                    'mail':st.session_state['mail'],
                    'accounts' : st.session_state['accounts'],
                    'exp_date':cookie_exp_date},
                key=cookie_key,
                algorithm='HS256'
            )
            cookie_manager.set(
                cookie_name,
                token,
                expires_at=datetime.now() + timedelta(days=cookie_exp_day))

            return True

    else:
        st.session_state.name = cookie['name']
        st.session_state.mail = cookie['mail']
        st.session_state.mail = cookie['accounts']

        return True

def logout():
    if st.button('Logout'):
        # Limpa as variaveis de Session State
        st.session_state.name = None
        st.session_state.mail = None
        st.session_state.accounts = None

        # Limpa as variaveis de Cookie
        cookie_manager.delete(cookie_name)

        # Limpa o cache de token do aplicativo MSAL
        app.remove_account(st.session_state.accounts[0])

        # Exibe uma mensagem de logout bem-sucedido
        st.write("Você foi desconectado.")

        return True

if login():
    logout()
    st.write(f'Bem vindo {st.session_state.name}')
