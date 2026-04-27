import streamlit as st
import mysql.connector
import ftplib
import os
import pandas as pd
from datetime import datetime
from PIL import Image

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Espião Bucal - Produção", layout="wide", page_icon="🦷")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .main-title { color: #1e3a8a; text-align: center; font-size: 40px; font-weight: bold; }
    .stButton>button { background-color: #1e3a8a; color: white; border-radius: 8px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE SESSÃO (PREVINE ERROS DE VARIÁVEL) ---
for key in ['logado', 'usuario', 'user_id', 'nivel']:
    if key not in st.session_state:
        st.session_state[key] = None
if 'logado' not in st.session_state or st.session_state['logado'] is None:
    st.session_state['logado'] = False

# --- FUNÇÕES DE CONEXÃO ---

def conectar_banco():
    try:
        conf = st.secrets["mysql"]
        conn = mysql.connector.connect(
            host=conf["host"],
            port=conf["port"],
            database=conf["database"],
            user=conf["user"],
            password=conf["password"],
            connection_timeout=20,
            autocommit=True
        )
        return conn
    except Exception as e:
        st.sidebar.error(f"Erro de Conexão: {e}")
        return None

def upload_foto_ftp(caminho_local, nome_arquivo):
    try:
        ftp_host = "69.49.241.31" 
        ftp_user = "espiao@francotec.com.br"
        ftp_pass = "Helena@!*2026"
        
        ftp = ftplib.FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        ftp.set_pasv(True) 
        
        # Tenta os caminhos prováveis da HostGator
        try:
            ftp.cwd('/public_html/fotos_registro')
        except:
            ftp.cwd('fotos_registro')
            
        with open(caminho_local, 'rb') as f:
            ftp.storbinary(f'STOR {nome_arquivo}', f)
        
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Erro FTP (Imagens): {e}")
        return False

# --- COMPONENTES DA INTERFACE ---

def tela_login():
    st.markdown("<h1 class='main-title'>🦷 Espião Bucal</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.subheader("Login de Acesso")
            user_in = st.text_input("Usuário").strip()
            pass_in = st.text_input("Senha", type="password")
            
            if st.button("Acessar Painel"):
                conn = conectar_banco()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    try:
                        # SQL DEFENSIVO: Buscamos o que é essencial primeiro
                        query = "SELECT * FROM usuarios WHERE usuario = %s AND senha = %s"
                        cursor.execute(query, (user_in, pass_in))
                        res = cursor.fetchone()
                        
                        if res:
                            st.session_state['logado'] = True
                            st.session_state['usuario'] = res.get('usuario')
                            st.session_state['user_id'] = res.get('id')
                            st.session_state['nivel'] = res.get('nivel', 'comum') # Fallback se 'nivel' não existir
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")
                    except mysql.connector.Error as db_err:
                        st.error(f"Erro na Tabela: {db_err.msg}")
                    finally:
                        conn.close()

def dashboard():
    # Barra Superior
    c_title, c_user, c_out = st.columns([4, 2, 1])
    c_title.title("Painel de Monitoramento")
    c_user.write(f"Usuário: **{st.session_state['usuario']}**")
    if c_out.button("Sair"):
        st.session_state.clear()
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📸 Registrar Uso", "📅 Histórico", "⚙️ Configurações"])

    with tab1:
        st.info("Posicione a câmera para mostrar o aparelho claramente.")
        foto = st.camera_input("Capturar Registro")
        
        if foto:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arq = f"registro_{st.session_state['user_id']}_{ts}.jpg"
            
            # Processamento
            with open(nome_arq, "wb") as f:
                f.write(foto.getbuffer())
            
            with st.spinner("Enviando dados..."):
                if upload_foto_ftp(nome_arq, nome_arq):
                    conn = conectar_banco()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            sql = "INSERT INTO registros_fotos (usuario_id, nome_arquivo, data_hora) VALUES (%s, %s, %s)"
                            cursor.execute(sql, (st.session_state['user_id'], nome_arq, datetime.now()))
                            st.success("✅ Registro enviado e salvo no banco!")
                        except Exception as e:
                            st.error(f"Erro ao salvar log: {e}")
                        finally:
                            conn.close()
                
            if os.path.exists(nome_arq):
                os.remove(nome_arq)

    with tab2:
        st.subheader("Seus últimos envios")
        conn = conectar_banco()
        if conn:
            try:
                query = "SELECT data_hora as 'Data/Hora', nome_arquivo as 'Arquivo' FROM registros_fotos WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 10"
                df = pd.read_sql(query, conn, params=(st.session_state['user_id'],))
                st.table(df)
            except:
                st.warning("Ainda não há registros para exibir.")
            finally:
                conn.close()

    with tab3:
        st.write("Configurações do perfil e suporte técnico.")
        if st.session_state['nivel'] == 'admin':
            st.button("Relatório Geral (Admin)")

# --- LOGICA PRINCIPAL ---

if __name__ == "__main__":
    # Verificação de Saúde na Sidebar
    with st.sidebar:
        st.image("https://francotec.com.br/logo.png", width=100) # Exemplo de uso do seu site
        st.divider()
        if conectar_banco():
            st.success("Conectado à HostGator")
        else:
            st.error("Sem resposta do banco")

    if not st.session_state['logado']:
        tela_login()
    else:
        dashboard()

# Aproximadamente 165 linhas com espaçamentos e comentários