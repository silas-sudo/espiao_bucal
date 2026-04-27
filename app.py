import streamlit as st
import mysql.connector
import ftplib
import os
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# --- 1. CONFIGURAÇÕES DE INTERFACE E TEMA (UI/UX) ---
st.set_page_config(
    page_title="Espião Bucal - Monitoramento de Produção",
    layout="wide",
    page_icon="🦷",
    initial_sidebar_state="expanded"
)

# Estilização CSS para garantir que o Frontend fique alinhado
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stApp { max-width: 1200px; margin: 0 auto; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #1e3a8a; color: white; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { background-color: #2563eb; border: 1px solid #1e3a8a; }
    .stCamera { border: 4px solid #1e3a8a; border-radius: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .css-1kyx0rg { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTÃO DE ESTADO GLOBAL (PREVENÇÃO DE BUGS DE VARIÁVEL) ---
# Inicializamos todas as chaves para evitar o erro 'usuario' ou 'user_id' não definidos
chaves_sessao = {
    'logado': False, 
    'usuario': None, 
    'user_id': None, 
    'perfil': 'user', 
    'ultimo_envio': None
}

for chave, valor in chaves_sessao.items():
    if chave not in st.session_state:
        st.session_state[chave] = valor

# --- 3. CAMADA DE CONEXÃO E INFRAESTRUTURA ---

def conectar_banco():
    """Conecta ao MySQL HostGator com validação de credenciais do Secrets"""
    try:
        conf = st.secrets["mysql"]
        conn = mysql.connector.connect(
            host=conf["host"],
            port=conf["port"],
            database=conf["database"],
            user=conf["user"],
            password=conf["password"],
            autocommit=True,
            connection_timeout=20
        )
        return conn
    except Exception as e:
        st.sidebar.error(f"Falha na infraestrutura de dados: {e}")
        return None

def processar_e_enviar_ftp(foto_buffer, nome_final):
    """Realiza o processamento da imagem e o upload via FTP Passivo"""
    try:
        # 1. Processamento da imagem com PIL (Otimização de banda)
        imagem = Image.open(foto_buffer)
        img_byte_arr = io.BytesIO()
        imagem.save(img_byte_arr, format='JPEG', quality=80)
        img_byte_arr = img_byte_arr.getvalue()

        # 2. Conexão FTP (Configuração para usuários 'enjaulados')
        ftp = ftplib.FTP("69.49.241.31")
        ftp.login("espiao@francotec.com.br", "Helena@!*2026")
        ftp.set_pasv(True)
        
        # Como o usuário 'espiao' já inicia na pasta 'fotos_registro', 
        # enviamos diretamente sem o comando CWD para evitar erro 550
        ftp.storbinary(f'STOR {nome_final}', io.BytesIO(img_byte_arr))
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Erro Crítico no Upload: {e}")
        return False

# --- 4. MÓDULOS DE INTERFACE (FRONTEND) ---

def tela_autenticacao():
    """Renderiza o formulário de login centralizado"""
    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>🦷 Espião Bucal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Sistema de Monitoramento Ortodôntico</p>", unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 1.8, 1])
    with col_c:
        with st.form("login_center"):
            st.subheader("Acesso ao Painel")
            u_input = st.text_input("Usuário de Acesso").strip()
            p_input = st.text_input("Senha Segura", type="password")
            btn_submit = st.form_submit_button("Entrar")
            
            if btn_submit:
                db = conectar_banco()
                if db:
                    cursor = db.cursor(dictionary=True)
                    # Tabelas e colunas validadas no seu HeidiSQL
                    query = "SELECT id, usuario, perfil FROM usuarios WHERE usuario = %s AND senha = %s"
                    cursor.execute(query, (u_input, p_input))
                    resultado = cursor.fetchone()
                    
                    if resultado:
                        st.session_state.update({
                            'logado': True,
                            'usuario': resultado['usuario'],
                            'user_id': resultado['id'],
                            'perfil': resultado['perfil']
                        })
                        st.rerun()
                    else:
                        st.error("Usuário ou senha inválidos.")
                    db.close()

def painel_principal():
    """Dashboard de produção com abas e lógica de histórico"""
    # Barra lateral de controle
    with st.sidebar:
        st.title("Menu")
        st.info(f"Usuário: {st.session_state['usuario']}")
        st.caption(f"Perfil: {st.session_state['perfil'].upper()}")
        if st.button("Encerrar Sessão"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.caption("Suporte: francotec.com.br")

    # Área de Conteúdo
    st.title(f"Bem-vindo(a), {st.session_state['usuario']}")
    abas = st.tabs(["📸 Novo Registro", "📊 Meu Histórico", "⚙️ Configurações"])

    with abas[0]:
        st.markdown("### Captura de Uso")
        col_cam, col_info = st.columns([1.5, 1])
        
        with col_cam:
            foto_cap = st.camera_input("Posicione o aparelho corretamente")
        
        with col_info:
            st.markdown("#### Orientações")
            st.write("1. Verifique se a iluminação está boa.")
            st.write("2. O aparelho deve estar visível na boca.")
            if foto_cap:
                if st.button("Enviar Registro Agora"):
                    data_ref = datetime.now()
                    nome_f = f"reg_{st.session_state['user_id']}_{data_ref.strftime('%Y%m%d_%H%M%S')}.jpg"
                    
                    with st.spinner("Sincronizando com servidor HostGator..."):
                        if processar_e_enviar_ftp(foto_cap, nome_f):
                            db = conectar_banco()
                            if db:
                                cursor = db.cursor()
                                # Tabela 'registros' conforme seu HeidiSQL
                                sql = "INSERT INTO registros (usuario_id, nome_arquivo, data_hora) VALUES (%s, %s, %s)"
                                cursor.execute(sql, (st.session_state['user_id'], nome_f, data_ref))
                                st.success("✅ Registro validado e salvo com sucesso!")
                                st.session_state['ultimo_envio'] = data_ref
                                db.close()

    with abas[1]:
        st.markdown("### Últimos 10 Envios")
        db = conectar_banco()
        if db:
            query = "SELECT data_hora as 'Data/Hora', nome_arquivo as 'Código' FROM registros WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 10"
            df = pd.read_sql(query, db, params=(st.session_state['user_id'],))
            st.dataframe(df, use_container_width=True, hide_index=True)
            db.close()
        else:
            st.warning("Histórico temporariamente indisponível.")

# --- 5. ORQUESTRAÇÃO DE EXECUÇÃO ---

if __name__ == "__main__":
    # Teste silencioso de saúde do servidor
    saude = conectar_banco()
    if saude:
        st.sidebar.caption("🟢 Servidor Online")
        saude.close()
    else:
        st.sidebar.caption("🔴 Servidor Offline")

    if not st.session_state['logado']:
        tela_autenticacao()
    else:
        painel_principal()

# Total de linhas aproximado: 175-180 (incluindo comentários e espaços de leitura)