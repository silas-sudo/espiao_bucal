import streamlit as st
import mysql.connector
import ftplib
import os
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# --- 1. CONFIGURAÇÕES DE INTERFACE (UI/UX) ---
st.set_page_config(
    page_title="Espião Bucal - Produção",
    layout="wide",
    page_icon="🦷"
)

# CSS para garantir responsividade real sem quebrar o Streamlit
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stApp { max-width: 1000px; margin: 0 auto; }
    /* Estilização de botões para facilitar o toque no celular */
    .stButton>button { 
        width: 100%; 
        border-radius: 12px; 
        height: 4em; 
        background-color: #1e40af; 
        color: white; 
        font-weight: bold;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .stCamera { border: 5px solid #1e40af; border-radius: 25px; }
    /* Ajuste para esconder menus desnecessários em produção */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. GERENCIAMENTO DE ESTADO SEGURO ---
def inicializar_estado():
    # Evita erros de 'KeyError' ao acessar session_state
    if 'logado' not in st.session_state:
        st.session_state.logado = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'usuario' not in st.session_state:
        st.session_state.usuario = None
    if 'perfil' not in st.session_state:
        st.session_state.perfil = 'user'

inicializar_estado()

# --- 3. CAMADA DE INFRAESTRUTURA (BACKEND) ---

def obter_conexao():
    """Gerencia conexão com MySQL HostGator"""
    try:
        credenciais = st.secrets["mysql"]
        return mysql.connector.connect(
            host=credenciais["host"],
            port=credenciais["port"],
            database=credenciais["database"],
            user=credenciais["user"],
            password=credenciais["password"],
            autocommit=True
        )
    except Exception as e:
        st.error(f"Erro de conexão com a base de dados: {e}")
        return None

def realizar_upload_ftp(arquivo_foto, nome_destino):
    """Executa o upload via FTP otimizado para HostGator"""
    try:
        # Otimização da imagem para economizar cota de disco e banda
        img = Image.open(arquivo_foto)
        if img.mode != 'RGB': img = img.convert('RGB')
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="JPEG", quality=80, optimize=True)
        
        # Conexão validada: o usuário 'espiao' já cai em public_html/fotos_registro
        ftp = ftplib.FTP("69.49.241.31")
        ftp.login("espiao@francotec.com.br", "Helena@!*2026")
        ftp.set_pasv(True)
        
        # Envio binário
        ftp.storbinary(f'STOR {nome_destino}', io.BytesIO(img_buffer.getvalue()))
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Falha técnica no servidor de imagens: {e}")
        return False

# --- 4. MÓDULOS DE INTERFACE ---

def tela_login():
    st.markdown("<h1 style='text-align: center;'>🦷 Espião Bucal</h1>", unsafe_allow_html=True)
    
    # Resolvendo o erro da image_856e35.png: Colunas fixas para responsividade
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        with st.form("identificacao"):
            st.subheader("Acesso do Paciente")
            u_input = st.text_input("Usuário").strip()
            s_input = st.text_input("Senha", type="password")
            btn = st.form_submit_button("Entrar no Sistema")
            
            if btn:
                conn = obter_conexao()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    # Tabelas validadas via phpMyAdmin (image_8575d8.png)
                    query = "SELECT id, usuario, perfil FROM usuarios WHERE usuario = %s AND senha = %s"
                    cursor.execute(query, (u_input, s_input))
                    user_data = cursor.fetchone()
                    
                    if user_data:
                        st.session_state.logado = True
                        st.session_state.user_id = user_data['id']
                        st.session_state.usuario = user_data['usuario']
                        st.session_state.perfil = user_data['perfil']
                        conn.close()
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")

def painel_monitoramento():
    # Cabeçalho de Status
    c_status, c_logout = st.columns([0.8, 0.2])
    c_status.success(f"Conectado: {st.session_state.usuario}")
    if c_logout.button("Sair"):
        st.session_state.clear()
        st.rerun()

    abas = st.tabs(["📸 Registrar Uso", "📊 Histórico de Envios"])

    with abas[0]:
        st.info("Posicione a câmera para mostrar o aparelho claramente.")
        captura = st.camera_input("Capturar Foto")
        
        if captura:
            if st.button("Confirmar e Sincronizar Registro", type="primary"):
                momento = datetime.now()
                # Nome do arquivo seguindo o padrão que já deu certo no seu FTP
                nome_foto_final = f"reg_{st.session_state.user_id}_{momento.strftime('%Y%m%d_%H%M%S')}.jpg"
                
                with st.spinner("Enviando para HostGator..."):
                    if realizar_upload_ftp(captura, nome_foto_final):
                        db = obter_conexao()
                        if db:
                            cursor = db.cursor()
                            # CORREÇÃO: Nomes de colunas conforme image_8575d8.png
                            # usuario_id, nome_foto, data_hora
                            sql = "INSERT INTO registros (usuario_id, nome_foto, data_hora) VALUES (%s, %s, %s)"
                            try:
                                cursor.execute(sql, (st.session_state.user_id, nome_foto_final, momento))
                                st.balloons()
                                st.success("Registro concluído com sucesso!")
                            except Exception as e:
                                st.error(f"Erro ao atualizar banco: {e}")
                            finally:
                                db.close()

    with abas[1]:
        st.markdown("### Seus Registros")
        db = obter_conexao()
        if db:
            # Query ajustada para as colunas reais: data_hora, nome_foto
            query = "SELECT data_hora as 'Data/Hora', nome_foto as 'Arquivo' FROM registros WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 10"
            df = pd.read_sql(query, db, params=(st.session_state.user_id,))
            st.dataframe(df, use_container_width=True, hide_index=True)
            db.close()

# --- 5. EXECUÇÃO DO APLICATIVO ---
if __name__ == "__main__":
    if not st.session_state.logado:
        tela_login()
    else:
        painel_monitoramento()

# Versão de Produção 2.9.2 - Estabilidade Garantida