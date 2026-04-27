import streamlit as st
import mysql.connector
import ftplib
import os
import pandas as pd
from datetime import datetime
from PIL import Image

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Espião Bucal - Produção", layout="wide", page_icon="🦷")

# --- ESTILIZAÇÃO CSS PERSONALIZADA ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .main-title { color: #2c3e50; text-align: center; font-weight: bold; margin-bottom: 20px; }
    .status-box { padding: 10px; border-radius: 5px; border: 1px solid #dee2e6; background-color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO (Evita o erro 'usuario') ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'usuario' not in st.session_state:
    st.session_state['usuario'] = None
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'nivel' not in st.session_state:
    st.session_state['nivel'] = None

# --- FUNÇÕES DE INFRAESTRUTURA ---

def conectar_banco():
    """Conexão centralizada com tratamento de exceção"""
    try:
        conf = st.secrets["mysql"]
        conn = mysql.connector.connect(
            host=conf["host"],
            port=conf["port"],
            database=conf["database"],
            user=conf["user"],
            password=conf["password"],
            connection_timeout=15
        )
        return conn
    except Exception as e:
        st.error(f"Falha na infraestrutura de dados: {e}")
        return None

def upload_foto_ftp(caminho_local, nome_arquivo):
    """Upload via FTP com Modo Passivo para HostGator"""
    try:
        ftp_host = "69.49.241.31" 
        ftp_user = "espiao@francotec.com.br"
        ftp_pass = "Helena@!*2026"
        
        ftp = ftplib.FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        ftp.set_pasv(True) # Crítico para o Streamlit Cloud
        
        # Estrutura de diretório validada no cPanel
        try:
            ftp.cwd('/public_html/fotos_registro')
        except:
            ftp.cwd('fotos_registro')
            
        with open(caminho_local, 'rb') as f:
            ftp.storbinary(f'STOR {nome_arquivo}', f)
        
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Falha na persistência da imagem: {e}")
        return False

# --- COMPONENTES DA INTERFACE ---

def tela_login():
    st.markdown("<h1 class='main-title'>🦷 Espião Bucal</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.subheader("Autenticação")
            user = st.text_input("Usuário").strip()
            pw = st.text_input("Senha", type="password")
            btn_login = st.form_submit_button("Entrar")
            
            if btn_login:
                conn = conectar_banco()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT id, usuario, nivel FROM usuarios WHERE usuario = %s AND senha = %s", (user, pw))
                    res = cursor.fetchone()
                    
                    if res:
                        st.session_state.update({
                            'logado': True,
                            'usuario': res['usuario'],
                            'user_id': res['id'],
                            'nivel': res['nivel']
                        })
                        conn.close()
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")
                    conn.close()

def dashboard():
    # Header e Logout
    col_t, col_l = st.columns([5, 1])
    col_t.title(f"Bem-vindo, {st.session_state['usuario']}")
    if col_l.button("Sair"):
        st.session_state.clear()
        st.rerun()

    tab1, tab2 = st.tabs(["📸 Novo Registro", "📊 Histórico"])

    with tab1:
        st.subheader("Captura de Monitoramento")
        foto = st.camera_input("Registre o uso do aparelho agora")
        
        if foto:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_img = f"user_{st.session_state['user_id']}_{timestamp}.jpg"
            
            with open(nome_img, "wb") as f:
                f.write(foto.getbuffer())
            
            with st.spinner("Processando..."):
                if upload_foto_ftp(nome_img, nome_img):
                    conn = conectar_banco()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO registros_fotos (usuario_id, nome_arquivo, data_hora) VALUES (%s, %s, %s)",
                            (st.session_state['user_id'], nome_img, datetime.now())
                        )
                        conn.commit()
                        conn.close()
                        st.success("✅ Registro realizado com sucesso!")
                        if os.path.exists(nome_img): os.remove(nome_img)

    with tab2:
        st.subheader("Seus Registros Recentes")
        conn = conectar_banco()
        if conn:
            query = "SELECT data_hora, nome_arquivo FROM registros_fotos WHERE usuario_id = %s ORDER BY data_hora DESC"
            df = pd.read_sql(query, conn, params=(st.session_state['user_id'],))
            st.dataframe(df, use_container_width=True)
            conn.close()

# --- ORQUESTRAÇÃO PRINCIPAL ---

if __name__ == "__main__":
    # Barra lateral com Status Real
    st.sidebar.markdown("### Status do Sistema")
    c = conectar_banco()
    if c:
        st.sidebar.success("● Servidor HostGator: OK")
        c.close()
    else:
        st.sidebar.error("● Servidor HostGator: OFFLINE")

    if not st.session_state['logado']:
        tela_login()
    else:
        dashboard()

# Linha 165 (Aproximadamente, dependendo dos comentários e espaçamentos)