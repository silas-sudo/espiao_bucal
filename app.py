import streamlit as st
import mysql.connector
import ftplib
import os
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# --- 1. CONFIGURAÇÕES DE INTERFACE (LAYOUT PRO) ---
st.set_page_config(page_title="Espião Bucal Pro", page_icon="🦷", layout="wide")

st.markdown("""
    <style>
    .card-tempo { background-color: #1e1e1e; border: 1px solid #333; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 15px; }
    .galeria-img-container { border: 2px solid #444; border-radius: 8px; padding: 5px; background: #111; margin-bottom: 10px; }
    .stButton button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    /* Ajustes para Responsividade Mobile */
    @media (max-width: 600px) {
        .stMetric { font-size: 0.8rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INFRAESTRUTURA (CONEXÕES HOSTGATOR) ---

def conectar_bd():
    """Conexão com Banco Remoto da HostGator"""
    try:
        c = st.secrets["mysql"]
        return mysql.connector.connect(
            host=c["host"], port=c["port"], database=c["database"],
            user=c["user"], password=c["password"], autocommit=True
        )
    except Exception as e:
        st.error(f"Erro de Conexão DB: {e}")
        return None

def enviar_ftp_hostgator(foto_buffer, nome_arquivo):
    """Upload via FTP Passivo para HostGator"""
    try:
        # Redimensionamento para economizar banda
        img = Image.open(foto_buffer)
        if img.mode != 'RGB': img = img.convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        
        ftp = ftplib.FTP("69.49.241.31")
        ftp.login("espiao@francotec.com.br", "Helena@!*2026")
        ftp.set_pasv(True)
        ftp.storbinary(f'STOR {nome_arquivo}', io.BytesIO(buffer.getvalue()))
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Erro FTP: {e}")
        return False

# --- 3. GESTÃO DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.user_info = None

# --- 4. TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🦷 Login - Espião Bucal")
    with st.form("login_form"):
        u = st.text_input("Usuário").lower().strip()
        p = st.text_input("Senha", type="password").strip()
        if st.form_submit_button("Entrar"):
            db = conectar_bd()
            if db:
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT * FROM usuarios WHERE LOWER(usuario) = %s AND senha = %s", (u, p))
                res = cursor.fetchone()
                db.close()
                if res:
                    st.session_state.logado = True
                    st.session_state.user_info = res
                    st.rerun()
                else: st.error("Acesso Negado.")
    st.stop()

# --- 5. INTERFACE LOGADA ---
user = st.session_state.user_info
st.sidebar.title(f"👤 {user['nome']}")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.session_state.user_info = None
    st.rerun()

# Menu dinâmico por perfil
if user['perfil'] == 'admin':
    menu = st.sidebar.radio("Navegação", ["📊 Painel de Controle", "👥 Gestão de Usuários", "📷 Meu Registro"])
else:
    menu = "📷 Meu Registro"

# ---------------------------------------------------------
# LÓGICA 1: MEU REGISTRO (CÂMERA + CHECK-IN/OUT)
# ---------------------------------------------------------
if menu == "📷 Meu Registro":
    st.header("📸 Captura de Uso")
    
    db = conectar_bd()
    if db:
        cursor = db.cursor(dictionary=True)
        # Consulta o último evento para alternar entre check-in e check-out
        cursor.execute("SELECT evento FROM registros WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 1", (user['id'],))
        ultimo = cursor.fetchone()
        db.close()

    proximo = "Check-out" if ultimo and ultimo['evento'] == "Check-in" else "Check-in"

    col_cam, col_info = st.columns([2, 1])
    with col_cam:
        foto = st.camera_input("Tire a foto para validar", label_visibility="collapsed")
        st.write(f"Ação Pendente: **{proximo}**")
        
        if st.button(f"Confirmar {proximo}", type="primary"):
            if foto:
                agora = datetime.now()
                # Nome do arquivo otimizado para o FTP
                nome_f = f"{agora.strftime('%Y%m%d_%H%M%S')}_{user['id']}_{proximo.lower()}.jpg"
                
                with st.spinner("Sincronizando com servidor..."):
                    if enviar_ftp_hostgator(foto, nome_f):
                        db = conectar_bd()
                        if db:
                            cur = db.cursor()
                            # Importante: colunas batendo com seu banco image_8575d8.png
                            sql = "INSERT INTO registros (data_hora, evento, nome_foto, usuario_id) VALUES (%s, %s, %s, %s)"
                            cur.execute(sql, (agora, proximo, nome_f, user['id']))
                            db.close()
                            st.success("Registro Salvo com sucesso!")
                            st.rerun()
            else: st.warning("Capture a foto primeiro!")

# ---------------------------------------------------------
# LÓGICA 2: PAINEL DE CONTROLE (DASHBOARD ADMIN)
# ---------------------------------------------------------
elif menu == "📊 Painel de Controle":
    st.header("📊 Dashboard Administrativo")
    
    db = conectar_bd()
    if db:
        query = "SELECT r.*, u.nome FROM registros r JOIN usuarios u ON r.usuario_id = u.id ORDER BY u.nome, r.data_hora ASC"
        df = pd.read_sql(query, db)
        db.close()

        if not df.empty:
            df['data_hora'] = pd.to_datetime(df['data_hora'])
            df['data_dia'] = df['data_hora'].dt.date
            
            total_s = 0
            dados_lista = []

            # Agrupamento para cálculo de horas (Check-in -> Check-out)
            for (nome_u, dia), gp in df.groupby(['nome', 'data_dia']):
                seg_dia = 0; check_t = None
                for r in gp.itertuples():
                    if r.evento == "Check-in": check_t = r.data_hora
                    elif r.evento == "Check-out" and check_t:
                        seg_dia += (r.data_hora - check_t).total_seconds()
                        check_t = None
                
                total_s += seg_dia
                h = int(seg_dia // 3600); m = int((seg_dia % 3600) // 60)
                dados_lista.append({"usuario": nome_u, "data": dia, "tempo": f"{h}h {m}m", "s": seg_dia})

            # Métricas Superiores
            c1, c2 = st.columns(2)
            c1.metric("Total de Uso Geral", f"{int(total_s // 3600)}h {int((total_s % 3600) // 60)}m")
            c2.metric("Dias com Registros", len(df['data_dia'].unique()))

            st.divider()

            resumo = pd.DataFrame(dados_lista)
            for usuario_n, grupo in resumo.groupby("usuario"):
                with st.expander(f"👤 {usuario_n}", expanded=True):
                    cols = st.columns(4)
                    for idx, r in enumerate(grupo.itertuples()):
                        with cols[idx % 4]:
                            st.markdown(f"<div class='card-tempo'><small>{r.data.strftime('%d/%m')}</small><br><b>{r.tempo}</b></div>", unsafe_allow_html=True)
                            
                            if st.toggle("🖼️ Ver Fotos", key=f"t_{idx}_{r.usuario}"):
                                # Aqui, como as fotos estão no FTP, em produção você precisaria da URL pública.
                                # Por enquanto, mostramos o nome do arquivo.
                                st.info(f"Ref: {r.usuario}")

# ---------------------------------------------------------
# LÓGICA 3: GESTÃO DE USUÁRIOS
# ---------------------------------------------------------
elif menu == "👥 Gestão de Usuários":
    st.header("👥 Gerenciar Acessos")
    with st.expander("➕ Novo Usuário"):
        with st.form("add"):
            n = st.text_input("Nome completo")
            u = st.text_input("Login (usuário)").lower()
            s = st.text_input("Senha")
            p = st.selectbox("Perfil", ["user", "admin"])
            if st.form_submit_button("Salvar Usuário"):
                db = conectar_bd()
                if db:
                    cur = db.cursor()
                    cur.execute("INSERT INTO usuarios (nome, usuario, senha, perfil) VALUES (%s,%s,%s,%s)", (n,u,s,p))
                    db.close()
                    st.rerun()

    db = conectar_bd()
    if db:
        u_df = pd.read_sql("SELECT * FROM usuarios", db)
        db.close()
        for row in u_df.itertuples():
            with st.expander(f"{row.nome} ({row.perfil})"):
                with st.form(f"ed_{row.id}"):
                    en = st.text_input("Nome", value=row.nome)
                    es = st.text_input("Senha", value=row.senha)
                    ep = st.selectbox("Perfil", ["user", "admin"], index=0 if row.perfil=="user" else 1)
                    if st.form_submit_button("Atualizar"):
                        db = conectar_bd()
                        if db:
                            cur = db.cursor()
                            cur.execute("UPDATE usuarios SET nome=%s, senha=%s, perfil=%s WHERE id=%s", (en,es,ep,row.id))
                            db.close()
                            st.rerun()