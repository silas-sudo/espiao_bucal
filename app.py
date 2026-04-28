import streamlit as st
import mysql.connector
import ftplib
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import os

# --- 1. CONFIGURAÇÕES DE INTERFACE ---
st.set_page_config(
    page_title="Espião Bucal Pro", 
    page_icon="🦷", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Bloco CSS - REMOVE O TOPO E DEFINE AS CLASSES DE ESTILO
st.markdown("""
    <style>
    /* Esconde o cabeçalho padrão para um visual limpo */
    header, .stAppHeader, [data-testid="stHeader"] { 
        display: none !important; 
        visibility: hidden !important;
    }
    
    /* Colamos o conteúdo no topo da tela */
    .block-container { 
        padding-top: 0rem !important; 
        padding-bottom: 1rem !important;
    }

    /* Estilização dos Cards do Dashboard */
    .card-tempo { 
        background-color: #1e1e1e; 
        border: 1px solid #333; 
        border-radius: 12px; 
        padding: 15px; 
        text-align: center; 
        margin-bottom: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    
    /* Padronização dos Botões */
    .stButton button { 
        width: 100%; 
        border-radius: 10px; 
        height: 3.5em; 
        font-weight: bold; 
    }
    
    /* A Classe que estava causando o problema - ajustada para ser flutuante */
    .login-box { 
        max-width: 400px; 
        margin: 0 auto; 
        padding: 2.5rem; 
        border: 1px solid #333; 
        border-radius: 15px; 
        background-color: #0e1117; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CAMADA DE INFRAESTRUTURA (MYSQL & FTP) ---

def conectar_bd():
    """Conexão segura com o MySQL HostGator via st.secrets"""
    try:
        c = st.secrets["mysql"]
        conn = mysql.connector.connect(
            host=c["host"], 
            port=c.get("port", 3306), 
            database=c["database"],
            user=c["user"], 
            password=c["password"], 
            autocommit=True
        )
        if conn.is_connected():
            return conn
    except mysql.connector.Error as err:
        st.error(f"Erro de Conexão MySQL: {err}")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
    return None

def gerenciar_ftp(acao, nome_arquivo=None, foto_buffer=None):
    """Protocolo de transferência de arquivos para o servidor Francotec"""
    try:
        ftp_h = "69.49.241.31"
        ftp_u = "espiao@francotec.com.br"
        ftp_p = "Helena@!*2026"
        
        ftp = ftplib.FTP(ftp_h)
        ftp.login(ftp_u, ftp_p)
        ftp.set_pasv(True)
        
        resultado = None
        if acao == "upload":
            img = Image.open(foto_buffer)
            if img.mode != 'RGB': 
                img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            buf.seek(0)
            ftp.storbinary(f'STOR {nome_arquivo}', buf)
            resultado = True
            
        elif acao == "download":
            buf = io.BytesIO()
            ftp.retrbinary(f'RETR {nome_arquivo}', buf.write)
            buf.seek(0)
            resultado = buf.getvalue()
            
        elif acao == "deletar":
            # Remove o arquivo físico para economizar espaço no plano
            ftp.delete(nome_arquivo)
            resultado = True
        
        ftp.quit()
        return resultado
    except Exception as e:
        if acao != "download":
            st.error(f"Falha na operação FTP ({acao}): {e}")
        return None

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- 4. FLUXO DE LOGIN (CORRIGIDO) ---
if not st.session_state.logado:
    # Espaçamento para centralizar verticalmente
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.2, 1])
    
    with col_login:
        # A DIV login-box AGORA ESTÁ DENTRO DA CONDIÇÃO DE LOGIN
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: white;'>🦷 Espião Bucal</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9em;'>Acesso Restrito</p>", unsafe_allow_html=True)
        
        with st.form("form_acesso"):
            usuario_input = st.text_input("Usuário").lower().strip()
            senha_input = st.text_input("Senha", type="password").strip()
            
            btn_acessar = st.form_submit_button("Entrar no Sistema")
            
            if btn_acessar:
                db_conn = conectar_bd()
                if db_conn:
                    cursor = db_conn.cursor(dictionary=True)
                    query = "SELECT * FROM usuarios WHERE LOWER(usuario) = %s AND senha = %s"
                    cursor.execute(query, (usuario_input, senha_input))
                    user_data = cursor.fetchone()
                    db_conn.close()
                    
                    if user_data:
                        st.session_state.logado = True
                        st.session_state.user_info = user_data
                        st.rerun()
                    else:
                        st.error("Usuário ou senha inválidos.")
        
        # Fecha a DIV rigorosamente aqui
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. DASHBOARD (SÓ EXECUTA APÓS LOGIN) ---
current_user = st.session_state.user_info

# Sidebar Lateral
st.sidebar.title(f"👤 {current_user['nome']}")
st.sidebar.write(f"Perfil: **{current_user['perfil'].upper()}**")
st.sidebar.divider()

if st.sidebar.button("Sair / Logout", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# Navegação Baseada no Perfil
if current_user['perfil'] == 'admin':
    menu = st.sidebar.radio("Navegação:", ["📊 Painel de Controle", "👥 Gestão de Usuários"])
else:
    menu = "📷 Meu Registro"

# --- MÓDULO: MEU REGISTRO (PACIENTE) ---
if menu == "📷 Meu Registro":
    st.header("📸 Registro Diário")
    
    db_conn = conectar_bd()
    if db_conn:
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT evento FROM registros WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 1", (current_user['id'],))
        ultimo = cursor.fetchone()
        db_conn.close()
        
        # Lógica de Alternância
        proximo_passo = "Check-out" if ultimo and ultimo['evento'] == "Check-in" else "Check-in"
        
        c_foto, _ = st.columns([2, 1])
        with c_foto:
            img_capturada = st.camera_input("Focar no Aparelho", label_visibility="collapsed")
            st.info(f"Ação requerida: **{proximo_passo}**")
            
            if st.button(f"Confirmar {proximo_passo}", type="primary", use_container_width=True):
                if img_capturada:
                    timestamp = datetime.now()
                    arquivo_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{current_user['id']}_{proximo_passo.lower()}.jpg"
                    
                    with st.spinner("Sincronizando com Servidor..."):
                        if gerenciar_ftp("upload", arquivo_id, img_capturada):
                            db = conectar_bd()
                            cur = db.cursor()
                            cur.execute("INSERT INTO registros (data_hora, evento, nome_foto, usuario_id) VALUES (%s,%s,%s,%s)", (timestamp, proximo_passo, arquivo_id, current_user['id']))
                            db.close()
                            st.toast("Registro efetuado!", icon="✅")
                            st.rerun()
                else:
                    st.warning("⚠️ Capture a foto primeiro.")

# --- MÓDULO: PAINEL DE CONTROLE (ADMIN) ---
elif menu == "📊 Painel de Controle":
    st.header("📊 Painel de Monitoramento")
    
    db_conn = conectar_bd()
    if db_conn:
        df_registros = pd.read_sql("SELECT r.*, u.nome FROM registros r JOIN usuarios u ON r.usuario_id = u.id ORDER BY r.data_hora DESC", db_conn)
        db_conn.close()

        if not df_registros.empty:
            # Opção de Reset
            if st.sidebar.button("🚨 Resetar Banco de Dados"):
                db = conectar_bd(); cur = db.cursor(); cur.execute("SELECT nome_foto FROM registros"); fts = cur.fetchall()
                for f in fts: gerenciar_ftp("deletar", f[0])
                cur.execute("TRUNCATE TABLE registros"); db.close(); st.rerun()

            df_registros['data_hora'] = pd.to_datetime(df_registros['data_hora'])
            
            for paciente_nome, grupo in df_registros.groupby("nome"):
                with st.expander(f"👤 Paciente: {paciente_nome}"):
                    t_acumulado = 0; check_ref = None; grid_cards = []
                    
                    for r in grupo.sort_values('data_hora').itertuples():
                        if r.evento == "Check-in": check_ref = r.data_hora
                        elif r.evento == "Check-out" and check_ref:
                            duracao = (r.data_hora - check_ref).total_seconds()
                            t_acumulado += duracao
                            grid_cards.append({"dia": r.data_hora.strftime('%d/%m'), "t": f"{int(duracao//3600)}h {int((duracao%3600)//60)}m"})
                            check_ref = None
                    
                    st.subheader(f"⏱️ Tempo Total: {int(t_acumulado//3600)}h {int((t_acumulado%3600)//60)}m")
                    
                    # Grid de exibição rápida
                    cols = st.columns(4)
                    for idx, c in enumerate(grid_cards):
                        with cols[idx % 4]:
                            st.markdown(f"<div class='card-tempo'><small>{c['dia']}</small><br><b>{c['t']}</b></div>", unsafe_allow_html=True)
                    
                    st.divider()
                    for r_item in grupo.itertuples():
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.write(f"🔹 {r_item.data_hora.strftime('%H:%M')} | **{r_item.evento}**")
                        if c2.button("🗑️", key=f"d_{r_item.id}"):
                            gerenciar_ftp("deletar", r_item.nome_foto)
                            db = conectar_bd(); cur = db.cursor(); cur.execute("DELETE FROM registros WHERE id=%s", (r_item.id,)); db.close(); st.rerun()
                        if c3.toggle("📷", key=f"v_{r_item.id}"):
                            img_bin = gerenciar_ftp("download", r_item.nome_foto)
                            if img_bin: st.image(img_bin, use_container_width=True)

# --- MÓDULO: GESTÃO DE USUÁRIOS ---
elif menu == "👥 Gestão de Usuários":
    st.header("👥 Administração de Contas")
    db_conn = conectar_bd()
    
    with st.expander("➕ Novo Cadastro"):
        with st.form("add_user"):
            n = st.text_input("Nome Completo")
            u = st.text_input("Login").lower().strip()
            s = st.text_input("Senha")
            p = st.selectbox("Perfil", ["user", "admin"])
            if st.form_submit_button("Salvar"):
                cur = db_conn.cursor(); cur.execute("INSERT INTO usuarios (nome, usuario, senha, perfil) VALUES (%s,%s,%s,%s)", (n,u,s,p)); db_conn.close(); st.rerun()

    u_df = pd.read_sql("SELECT * FROM usuarios", db_conn)
    for row in u_df.itertuples():
        with st.expander(f"👤 {row.nome} ({row.usuario})"):
            c1, c2 = st.columns([3, 1])
            with c1:
                with st.form(f"ed_{row.id}"):
                    en = st.text_input("Nome", row.nome); eu = st.text_input("Login", row.usuario); es = st.text_input("Senha", row.senha)
                    if st.form_submit_button("Atualizar"):
                        cur = db_conn.cursor(); cur.execute("UPDATE usuarios SET nome=%s, usuario=%s, senha=%s WHERE id=%s", (en,eu,es,row.id)); db_conn.close(); st.rerun()
            if c2.button("Excluir", key=f"rm_{row.id}"):
                cur = db_conn.cursor(); cur.execute("DELETE FROM usuarios WHERE id=%s", (row.id,)); db_conn.close(); st.rerun()