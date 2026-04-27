import streamlit as st
import mysql.connector
import ftplib
import os
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# --- 1. CONFIGURAÇÕES DE UI E RESPONSIVIDADE (MOBILE FIRST) ---
st.set_page_config(
    page_title="Espião Bucal v2.8",
    layout="wide",
    page_icon="🦷",
    initial_sidebar_state="collapsed"
)

# CSS Expandido para garantir que o frontend não quebre em telas pequenas
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f8fafc; }
    .main-card { background-color: #ffffff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.8em; background-color: #1e40af; color: white; font-weight: 600; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #1d4ed8; transform: translateY(-2px); }
    .stCamera { border: 4px solid #1e40af; border-radius: 20px; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1); }
    /* Ajuste para Mobile */
    @media (max-width: 640px) {
        .block-container { padding: 1rem !important; }
        h1 { font-size: 1.8rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTÃO DE SESSÃO E SEGURANÇA ---
def iniciar_sessao():
    chaves = {
        'logado': False, 
        'usuario': None, 
        'user_id': None, 
        'perfil': 'user',
        'tentativas': 0
    }
    for chave, valor in chaves.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor

iniciar_sessao()

# --- 3. INFRAESTRUTURA DE DADOS (MYSQL & FTP) ---

def conectar_banco():
    """Conexão persistente com tratamento de timeout"""
    try:
        c = st.secrets["mysql"]
        conn = mysql.connector.connect(
            host=c["host"], port=c["port"], database=c["database"],
            user=c["user"], password=c["password"], 
            autocommit=True, connect_timeout=10
        )
        return conn
    except Exception as e:
        st.error(f"Erro de infraestrutura (DB): {e}")
        return None

def processar_e_enviar_ftp(foto_original):
    """Otimiza a imagem antes de enviar para a HostGator"""
    try:
        # Redimensionamento para economizar banda do usuário e espaço no FTP
        img = Image.open(foto_original)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75, optimize=True)
        
        # Conexão FTP validada (Usuário já na pasta fotos_registro)
        ftp = ftplib.FTP("69.49.241.31")
        ftp.login("espiao@francotec.com.br", "Helena@!*2026")
        ftp.set_pasv(True)
        
        # Nome único baseado em ID e Timestamp
        agora = datetime.now()
        nome_arq = f"reg_{st.session_state['user_id']}_{agora.strftime('%Y%m%d_%H%M%S')}.jpg"
        
        ftp.storbinary(f'STOR {nome_arq}', io.BytesIO(buffer.getvalue()))
        ftp.quit()
        return nome_arq, agora
    except Exception as e:
        st.error(f"Falha no serviço de arquivos (FTP): {e}")
        return None, None

# --- 4. TELAS DO SISTEMA ---

def tela_login():
    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>🦷 Espião Bucal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Identificação do Paciente</p>", unsafe_allow_html=True)
    
    _, col, _ = st.columns([0.2, 0.6, 0.2]) if st.sidebar.get('mobile', True) else st.columns([1, 2, 1])
    
    with col:
        with st.container(border=True):
            u = st.text_input("Usuário").strip()
            s = st.text_input("Senha", type="password")
            if st.button("Acessar Painel"):
                db = conectar_banco()
                if db:
                    cursor = db.cursor(dictionary=True)
                    # Busca validada com a coluna 'perfil' da sua imagem
                    cursor.execute("SELECT id, usuario, perfil FROM usuarios WHERE usuario = %s AND senha = %s", (u, s))
                    res = cursor.fetchone()
                    if res:
                        st.session_state.update({'logado': True, 'usuario': res['usuario'], 
                                               'user_id': res['id'], 'perfil': res['perfil']})
                        st.rerun()
                    else:
                        st.error("Credenciais não encontradas.")
                    db.close()

def dashboard():
    # Header Principal
    c1, c2 = st.columns([0.8, 0.2])
    c1.markdown(f"### 👋 Olá, {st.session_state['usuario']}")
    if c2.button("Sair"):
        st.session_state.clear()
        st.rerun()

    tab_camera, tab_logs, tab_perfil = st.tabs(["📸 Capturar", "📅 Histórico", "👤 Perfil"])

    with tab_camera:
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        st.info("Centralize o aparelho na câmera para uma captura nítida.")
        foto_data = st.camera_input("Foto do Registro")
        
        if foto_data:
            if st.button("✅ Confirmar Envio de Dados"):
                with st.spinner("Sincronizando com HostGator..."):
                    nome_salvo, data_ref = processar_e_enviar_ftp(foto_data)
                    
                    if nome_salvo:
                        db = conectar_banco()
                        if db:
                            cursor = db.cursor()
                            # CORREÇÃO: data_registro conforme seu banco
                            sql = "INSERT INTO registros (usuario_id, nome_arquivo, data_registro) VALUES (%s, %s, %s)"
                            try:
                                cursor.execute(sql, (st.session_state['user_id'], nome_salvo, data_ref))
                                st.balloons()
                                st.success(f"Registro {nome_salvo} concluído!")
                            except Exception as e:
                                st.error(f"Erro ao salvar no log do banco: {e}")
                            finally:
                                db.close()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_logs:
        st.markdown("### Seus Registros Recentes")
        db = conectar_banco()
        if db:
            query = "SELECT data_registro as 'Data', nome_arquivo as 'Referência' FROM registros WHERE usuario_id = %s ORDER BY data_registro DESC LIMIT 20"
            df = pd.read_sql(query, db, params=(st.session_state['user_id'],))
            st.dataframe(df, use_container_width=True, hide_index=True)
            db.close()

    with tab_perfil:
        st.subheader("Dados da Conta")
        st.write(f"**ID do Paciente:** {st.session_state['user_id']}")
        st.write(f"**Nível de Acesso:** {st.session_state['perfil']}")
        if st.session_state['perfil'] == 'admin':
            st.warning("⚠️ Você possui privilégios de Administrador.")
            if st.button("Gerar Relatório Geral"):
                st.write("Função disponível para gestão do consultório.")

# --- 5. ORQUESTRAÇÃO FINAL ---
if __name__ == "__main__":
    if not st.session_state['logado']:
        tela_login()
    else:
        dashboard()

# --- Total de Linhas: ~185-195 (Mantendo a estrutura de produção) ---