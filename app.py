import streamlit as st
import mysql.connector
import ftplib
import os
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# --- 1. CONFIGURAÇÃO E ESTILO (UI/UX) ---
st.set_page_config(page_title="Espião Bucal - Sistema de Monitoramento", layout="wide", page_icon="🦷")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stApp { max-width: 1200px; margin: 0 auto; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #1e3a8a; color: white; font-weight: bold; }
    .stCamera { border: 3px solid #1e3a8a; border-radius: 15px; }
    .header-box { padding: 20px; background-color: #ffffff; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTÃO DE SESSÃO (PREVINE ERROS DE VARIÁVEL NULA) ---
session_vars = {'logado': False, 'usuario': None, 'user_id': None, 'nivel': 'comum'}
for var, val in session_vars.items():
    if var not in st.session_state:
        st.session_state[var] = val

# --- 3. FUNÇÕES DE INFRAESTRUTURA (BACKEND) ---

def conectar_banco():
    """Gerencia a conexão com o MySQL da HostGator"""
    try:
        c = st.secrets["mysql"]
        conn = mysql.connector.connect(
            host=c["host"], port=c["port"], database=c["database"],
            user=c["user"], password=c["password"], 
            autocommit=True, connection_timeout=15
        )
        return conn
    except Exception as e:
        st.sidebar.error(f"Erro de Banco: {e}")
        return None

def upload_ftp_producao(caminho_local, nome_arquivo):
    """Executa o upload via FTP com Modo Passivo ativado"""
    try:
        ftp = ftplib.FTP("69.49.241.31")
        ftp.login("espiao@francotec.com.br", "Helena@!*2026")
        ftp.set_pasv(True)
        
        # Lógica de diretório adaptativa
        try:
            ftp.cwd('/public_html/fotos_registro')
        except:
            ftp.cwd('fotos_registro')
            
        with open(caminho_local, 'rb') as f:
            ftp.storbinary(f'STOR {nome_arquivo}', f)
        
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Erro de comunicação FTP: {e}")
        return False

# --- 4. LÓGICA DE NEGÓCIO E TELAS ---

def tela_login():
    """Interface de autenticação centralizada"""
    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>🦷 Espião Bucal</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("auth_form"):
            st.markdown("### Acesso Restrito")
            user_input = st.text_input("Usuário").strip()
            pass_input = st.text_input("Senha", type="password")
            btn_entrar = st.form_submit_button("Entrar no Sistema")
            
            if btn_entrar:
                db = conectar_banco()
                if db:
                    cursor = db.cursor(dictionary=True)
                    # SQL Defensivo para evitar erros de coluna
                    cursor.execute("SELECT * FROM usuarios WHERE usuario = %s AND senha = %s", (user_input, pass_input))
                    user_data = cursor.fetchone()
                    
                    if user_data:
                        st.session_state.update({
                            'logado': True, 'usuario': user_data['usuario'],
                            'user_id': user_data['id'], 'nivel': user_data.get('nivel', 'comum')
                        })
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas ou conta inativa.")
                    db.close()

def dashboard_usuario():
    """Painel principal do cliente/usuário"""
    # Header de Boas-vindas
    with st.container():
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"## Bem-vindo, {st.session_state['usuario']} ✨")
        if c2.button("Sair do Sistema"):
            st.session_state.clear()
            st.rerun()
    
    st.write("---")
    tab_reg, tab_hist, tab_info = st.tabs(["📸 Registrar Uso", "📅 Meu Histórico", "ℹ️ Informações"])

    with tab_reg:
        st.markdown("### Captura de Monitoramento")
        col_c, col_t = st.columns([2, 1])
        
        with col_c:
            img_file = st.camera_input("Tire a foto para validar o uso")
        
        with col_t:
            st.info("Certifique-se de que o aparelho esteja visível e a iluminação esteja adequada.")
            if img_file:
                if st.button("Confirmar e Enviar Registro"):
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    nome_f = f"user_{st.session_state['user_id']}_{ts}.jpg"
                    
                    # Processamento de Imagem (Redimensionamento para otimizar FTP)
                    img = Image.open(img_file)
                    img.save(nome_f, quality=85, optimize=True)
                    
                    with st.spinner("Sincronizando com o servidor..."):
                        if upload_ftp_producao(nome_f, nome_f):
                            db = conectar_banco()
                            if db:
                                cursor = db.cursor()
                                sql = "INSERT INTO registros_fotos (usuario_id, nome_arquivo, data_hora) VALUES (%s, %s, %s)"
                                cursor.execute(sql, (st.session_state['user_id'], nome_f, datetime.now()))
                                db.close()
                                st.success("✅ Registro enviado com sucesso!")
                                if os.path.exists(nome_f): os.remove(nome_f)
                        else:
                            st.error("Erro ao subir imagem. Tente novamente.")

    with tab_hist:
        st.markdown("### Seus Registros Recentes")
        db = conectar_banco()
        if db:
            query = "SELECT data_hora as 'Data', nome_arquivo as 'Ref' FROM registros_fotos WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 10"
            df = pd.read_sql(query, db, params=(st.session_state['user_id'],))
            st.dataframe(df, use_container_width=True)
            db.close()

    with tab_info:
        st.markdown("### Orientações Técnicas")
        st.write("Este sistema monitora o tempo de uso do seu aparelho ortodôntico.")
        if st.session_state['nivel'] == 'admin':
            st.warning("Acesso Administrativo detectado. Use o menu lateral para relatórios.")

# --- 5. LÓGICA DE EXECUÇÃO PRINCIPAL ---

if __name__ == "__main__":
    # Barra lateral de status discreta
    with st.sidebar:
        st.markdown("### 🖥️ Status da Rede")
        status_db = conectar_banco()
        if status_db:
            st.success("Banco de Dados: Online")
            status_db.close()
        else:
            st.error("Banco de Dados: Offline")
        st.divider()
        st.caption("Versão 2.4.1 - Produção")

    # Orquestrador de Telas
    if not st.session_state['logado']:
        tela_login()
    else:
        dashboard_usuario()

# --- FIM DO CÓDIGO (APROX. 165 LINHAS) ---