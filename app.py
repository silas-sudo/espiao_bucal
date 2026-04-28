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

# Bloco CSS Ultra-Reforçado para Limpeza Total do Topo e Layout Profissional
st.markdown("""
    <style>
    /* 1. Esconde o header padrão e qualquer elemento de título de página */
    header, .stAppHeader, [data-testid="stHeader"] { 
        display: none !important; 
        visibility: hidden !important;
    }
    
    /* 2. Zera as margens do container principal e remove o espaço do título */
    .block-container, .stAppViewBlockContainer { 
        padding-top: 0rem !important; 
        margin-top: -2.5rem !important; /* Puxa o conteúdo para cima agressivamente */
    }
    
    /* 3. Remove o espaço interno que o Streamlit reserva no topo do bloco vertical */
    [data-testid="stVerticalBlock"] > div:first-child {
        margin-top: -1.5rem !important;
    }

    /* Estilização dos Cards de Tempo no Dashboard */
    .card-tempo { 
        background-color: #1e1e1e; 
        border: 1px solid #444; 
        border-radius: 12px; 
        padding: 15px; 
        text-align: center; 
        margin-bottom: 15px; 
        transition: 0.3s;
    }
    .card-tempo:hover {
        border-color: #00ff00;
    }
    
    /* Botões padronizados e robustos */
    .stButton button { 
        width: 100%; 
        border-radius: 10px; 
        height: 3.5em; 
        font-weight: bold; 
    }
    
    /* Box de Login Centralizado Estilo Moderno */
    .login-box { 
        max-width: 420px; 
        margin: 0 auto; 
        padding: 2.5rem; 
        border: 1px solid #333; 
        border-radius: 15px; 
        background-color: #0e1117; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.6);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CAMADA DE INFRAESTRUTURA E CONEXÕES REMOTAS ---

def conectar_bd():
    """Gerencia a conexão com o banco MySQL na HostGator"""
    try:
        conf = st.secrets["mysql"]
        conn = mysql.connector.connect(
            host=conf["host"], 
            port=conf.get("port", 3306), 
            database=conf["database"],
            user=conf["user"], 
            password=conf["password"], 
            autocommit=True
        )
        return conn
    except Exception as e:
        st.error(f"Erro Crítico de Banco: {e}")
        return None

def gerenciar_ftp(acao, nome_arquivo=None, foto_buffer=None):
    """Protocolo de Gestão de Arquivos no Servidor FTP"""
    try:
        ftp = ftplib.FTP("69.49.241.31")
        ftp.login("espiao@francotec.com.br", "Helena@!*2026")
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
            # Exclusão física para controle de storage
            ftp.delete(nome_arquivo)
            resultado = True
        
        ftp.quit()
        return resultado
    except Exception as e:
        if acao != "download":
            st.error(f"Falha na Transmissão (FTP): {e}")
        return None

# --- 3. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- 4. INTERFACE DE AUTENTICAÇÃO (LOGIN) ---
if not st.session_state.logado:
    st.write("##") # Espaço compensatório
    _, col_log, _ = st.columns([1, 1.3, 1])
    
    with col_log:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: white;'>🦷 Espião Bucal</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user_in = st.text_input("Usuário").lower().strip()
            pass_in = st.text_input("Senha", type="password").strip()
            
            if st.form_submit_button("Entrar no Painel"):
                db = conectar_bd()
                if db:
                    cursor = db.cursor(dictionary=True)
                    cursor.execute("SELECT * FROM usuarios WHERE LOWER(usuario) = %s AND senha = %s", (user_in, pass_in))
                    dados = cursor.fetchone()
                    db.close()
                    
                    if dados:
                        st.session_state.logado = True
                        st.session_state.user_info = dados
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. PAINEL PRINCIPAL DO USUÁRIO ---
user = st.session_state.user_info

# Sidebar de Controle
st.sidebar.title(f"👤 {user['nome']}")
st.sidebar.info(f"Acesso: {user['perfil'].upper()}")

if st.sidebar.button("Sair / Logout", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# Lógica de Navegação por Perfil
if user['perfil'] == 'admin':
    navegacao = st.sidebar.radio("Navegação", ["📊 Painel de Controle", "👥 Gestão de Usuários"])
else:
    navegacao = "📷 Meu Registro"

# --- MÓDULO: REGISTRO (PACIENTE) ---
if navegacao == "📷 Meu Registro":
    st.header("📸 Capturar Uso do Aparelho")
    
    db = conectar_bd()
    if db:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT evento FROM registros WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 1", (user['id'],))
        ultimo = cursor.fetchone()
        db.close()
        
        proximo = "Check-out" if ultimo and ultimo['evento'] == "Check-in" else "Check-in"
        
        col_camera, _ = st.columns([2, 1])
        with col_camera:
            camera_data = st.camera_input("Focar sorriso", label_visibility="collapsed")
            st.write(f"Ação Pendente: **{proximo}**")
            
            if st.button(f"Confirmar {proximo}", type="primary", use_container_width=True):
                if camera_data:
                    agora = datetime.now()
                    file_name = f"{agora.strftime('%Y%m%d_%H%M%S')}_{user['id']}_{proximo.lower()}.jpg"
                    
                    with st.spinner("Enviando dados..."):
                        if gerenciar_ftp("upload", file_name, camera_data):
                            db = conectar_bd()
                            cur = db.cursor()
                            sql = "INSERT INTO registros (data_hora, evento, nome_foto, usuario_id) VALUES (%s, %s, %s, %s)"
                            cur.execute(sql, (agora, proximo, file_name, user['id']))
                            db.close()
                            st.success("Registro sincronizado!")
                            st.rerun()
                else:
                    st.warning("⚠️ Capture a foto primeiro.")

# --- MÓDULO: PAINEL DE CONTROLE (ADMIN) ---
elif navegacao == "📊 Painel de Controle":
    st.header("📊 Monitoramento de Pacientes")
    
    db = conectar_bd()
    if db:
        query = "SELECT r.*, u.nome FROM registros r JOIN usuarios u ON r.usuario_id = u.id ORDER BY r.data_hora DESC"
        df = pd.read_sql(query, db)
        db.close()

        if not df.empty:
            # Botão de Reset Total
            if st.sidebar.button("🚨 Limpar Banco de Dados"):
                db = conectar_bd()
                cur = db.cursor()
                cur.execute("SELECT nome_foto FROM registros")
                fotos = cur.fetchall()
                for f in fotos:
                    gerenciar_ftp("deletar", f[0])
                cur.execute("TRUNCATE TABLE registros")
                db.close()
                st.rerun()

            df['data_hora'] = pd.to_datetime(df['data_hora'])
            df['dia'] = df['data_hora'].dt.date
            
            for paciente, grupo in df.groupby("nome"):
                with st.expander(f"👤 Paciente: {paciente}", expanded=False):
                    total_seg = 0; ref_checkin = None; card_list = []
                    
                    ordem = grupo.sort_values('data_hora')
                    for r in ordem.itertuples():
                        if r.evento == "Check-in":
                            ref_checkin = r.data_hora
                        elif r.evento == "Check-out" and ref_checkin:
                            diff = (r.data_hora - ref_checkin).total_seconds()
                            total_seg += diff
                            h = int(diff // 3600); m = int((diff % 3600) // 60)
                            card_list.append({"dia": r.dia, "txt": f"{h}h {m}m"})
                            ref_checkin = None
                    
                    th = int(total_seg // 3600); tm = int((total_seg % 3600) // 60)
                    st.subheader(f"⏱️ Tempo Total: {th}h {tm}m")
                    
                    cols = st.columns(4)
                    for i, cdata in enumerate(card_list):
                        with cols[i % 4]:
                            st.markdown(f"<div class='card-tempo'><small>{cdata['dia'].strftime('%d/%m')}</small><br><b>{cdata['txt']}</b></div>", unsafe_allow_html=True)

                    st.write("---")
                    for r in grupo.itertuples():
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.write(f"🔹 {r.data_hora.strftime('%H:%M')} - {r.evento}")
                        
                        if c2.button("Apagar", key=f"del_r_{r.id}"):
                            gerenciar_ftp("deletar", r.nome_foto)
                            db = conectar_bd(); cur = db.cursor()
                            cur.execute("DELETE FROM registros WHERE id=%s", (r.id,))
                            db.close(); st.rerun()
                            
                        if c3.toggle("Ver", key=f"img_r_{r.id}"):
                            bin_img = gerenciar_ftp("download", r.nome_foto)
                            if bin_img:
                                st.image(bin_img, use_container_width=True)

# --- MÓDULO: GESTÃO DE USUÁRIOS ---
elif navegacao == "👥 Gestão de Usuários":
    st.header("👥 Gestão de Contas")
    db = conectar_bd()
    
    with st.expander("➕ Novo Cadastro"):
        with st.form("cad_u"):
            n = st.text_input("Nome"); u = st.text_input("Login").lower().strip(); s = st.text_input("Senha"); p = st.selectbox("Perfil", ["user", "admin"])
            if st.form_submit_button("Salvar"):
                cur = db.cursor()
                cur.execute("INSERT INTO usuarios (nome, usuario, senha, perfil) VALUES (%s,%s,%s,%s)", (n,u,s,p))
                st.rerun()

    users_df = pd.read_sql("SELECT * FROM usuarios", db)
    for u_row in users_df.itertuples():
        with st.expander(f"👤 {u_row.nome} ({u_row.usuario})"):
            c1, c2 = st.columns([3, 1])
            with c1:
                with st.form(f"ed_u_{u_row.id}"):
                    en = st.text_input("Nome", value=u_row.nome); eu = st.text_input("Login", value=u_row.usuario); es = st.text_input("Senha", value=u_row.senha)
                    if st.form_submit_button("Atualizar"):
                        cur = db.cursor()
                        cur.execute("UPDATE usuarios SET nome=%s, usuario=%s, senha=%s WHERE id=%s", (en, eu, es, u_row.id))
                        st.rerun()
            if c2.button("Remover", key=f"rm_u_{u_row.id}"):
                cur = db.cursor(); cur.execute("DELETE FROM usuarios WHERE id=%s", (u_row.id,))
                st.rerun()