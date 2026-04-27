import streamlit as st
import mysql.connector
import ftplib
import os
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Espião Bucal - Produção", layout="wide", page_icon="🦷")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'usuario' not in st.session_state:
    st.session_state['usuario'] = None
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# --- FUNÇÕES DE CONEXÃO ---

def conectar_banco():
    """Estabelece conexão com o MySQL da HostGator via st.secrets"""
    try:
        db_config = st.secrets["mysql"]
        conn = mysql.connector.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
            connection_timeout=10 # Timeout para evitar travamento em produção
        )
        return conn
    except Exception as e:
        st.sidebar.error(f"Erro Crítico de Banco: {e}")
        return None

def upload_foto_ftp(caminho_local, nome_arquivo):
    """Realiza o upload da foto para a HostGator via FTP"""
    try:
        # Credenciais conforme validado no FileZilla
        ftp_host = "69.49.241.31" 
        ftp_user = "espiao@francotec.com.br"
        ftp_pass = "Helena@!*2026"
        
        ftp = ftplib.FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        
        # MODO PASSIVO: Obrigatório para infraestrutura Cloud (Streamlit)
        ftp.set_pasv(True) 
        
        # Tenta entrar no diretório (ajustado para a estrutura HostGator)
        try:
            ftp.cwd('fotos_registro')
        except:
            ftp.cwd('public_html/fotos_registro')
        
        with open(caminho_local, 'rb') as f:
            ftp.storbinary(f'STOR {nome_arquivo}', f)
        
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Falha no servidor de imagens (FTP): {e}")
        return False

# --- INTERFACE DE LOGIN ---

def tela_login():
    st.title("🦷 Espião Bucal - Login")
    with st.form("form_login"):
        user = st.text_input("Usuário").strip()
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Acessar Sistema")
        
        if submit:
            conn = conectar_banco()
            if conn:
                cursor = conn.cursor(dictionary=True)
                # Altere 'usuarios' para o nome exato da sua tabela
                query = "SELECT id, usuario, senha FROM usuarios WHERE usuario = %s AND senha = %s"
                cursor.execute(query, (user, password))
                resultado = cursor.fetchone()
                
                if resultado:
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = resultado['usuario']
                    st.session_state['user_id'] = resultado['id']
                    conn.close()
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
                conn.close()

# --- DASHBOARD PRINCIPAL ---

def dashboard():
    st.sidebar.title(f"Bem-vindo, {st.session_state['usuario']}")
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    st.title("📸 Registro de Uso do Aparelho")
    
    # Componente de Câmera
    foto_camera = st.camera_input("Tire uma foto usando o aparelho")
    
    if foto_camera:
        nome_arquivo = f"registro_{st.session_state['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        caminho_temp = os.path.join("temp", nome_arquivo)
        
        # Cria pasta temporária se não existir
        if not os.path.exists("temp"):
            os.makedirs("temp")

        # Salva localmente para processar
        with open(caminho_temp, "wb") as f:
            f.write(foto_camera.getbuffer())
        
        with st.spinner("Enviando para o servidor..."):
            sucesso_ftp = upload_foto_ftp(caminho_temp, nome_arquivo)
            
            if sucesso_ftp:
                # Registra no Banco de Dados
                conn = conectar_banco()
                if conn:
                    try:
                        cursor = conn.cursor()
                        # Altere para os campos da sua tabela de logs
                        sql = "INSERT INTO registros_fotos (usuario_id, nome_arquivo, data_hora) VALUES (%s, %s, %s)"
                        cursor.execute(sql, (st.session_state['user_id'], nome_arquivo, datetime.now()))
                        conn.commit()
                        st.success("✅ Registro concluído com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco: {e}")
                    finally:
                        conn.close()
                
                # Limpa arquivo temporário
                if os.path.exists(caminho_temp):
                    os.remove(caminho_temp)

# --- EXECUÇÃO PRINCIPAL ---

if __name__ == "__main__":
    # Barra lateral de status (Auto-Diagnóstico)
    conn_status = conectar_banco()
    if conn_status:
        st.sidebar.success("📡 Servidor HostGator: Online")
        conn_status.close()
    else:
        st.sidebar.warning("⚠️ Servidor HostGator: Offline")

    # Controle de Rotas
    if not st.session_state['logado']:
        tela_login()
    else:
        dashboard()