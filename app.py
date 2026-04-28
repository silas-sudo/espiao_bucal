import streamlit as st
import mysql.connector
import ftplib
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# --- 1. CONFIGURAÇÕES DE INTERFACE ---
st.set_page_config(page_title="Espião Bucal", page_icon="🦷", layout="wide")

st.markdown("""
    <style>
    /* Estilização dos Cards de Tempo */
    .card-tempo { 
        background-color: #1e1e1e; 
        border: 1px solid #333; 
        border-radius: 12px; 
        padding: 15px; 
        text-align: center; 
        margin-bottom: 15px; 
    }
    .stButton button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    
    /* Centralização do Login */
    .login-box {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        border: 1px solid #333;
        border-radius: 15px;
        background-color: #0e1117;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INFRAESTRUTURA (CONEXÕES REMOTAS) ---

def conectar_bd():
    """Conexão segura via Secrets (HostGator)"""
    try:
        c = st.secrets["mysql"]
        return mysql.connector.connect(
            host=c["host"], port=c["port"], database=c["database"],
            user=c["user"], password=c["password"], autocommit=True
        )
    except Exception as e:
        st.error(f"Falha na conexão com o banco: {e}")
        return None

def gerenciar_ftp(acao, nome_arquivo=None, foto_buffer=None):
    """Lida com Upload e Download de imagens no servidor HostGator"""
    try:
        ftp = ftplib.FTP("69.49.241.31")
        ftp.login("espiao@francotec.com.br", "Helena@!*2026")
        ftp.set_pasv(True)
        
        resultado = None
        if acao == "upload":
            img = Image.open(foto_buffer)
            if img.mode != 'RGB': img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            ftp.storbinary(f'STOR {nome_arquivo}', io.BytesIO(buf.getvalue()))
            resultado = True
        elif acao == "download":
            buf = io.BytesIO()
            ftp.retrbinary(f'RETR {nome_arquivo}', buf.write)
            resultado = buf.getvalue()
        
        ftp.quit()
        return resultado
    except Exception as e:
        st.error(f"Erro no servidor de arquivos (FTP): {e}")
        return None

# --- 3. GESTÃO DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'user_info': None})

# --- 4. TELA DE LOGIN CENTRALIZADA ---
if not st.session_state.logado:
    st.write("#") # Espaçamento topo
    _, col_cent, _ = st.columns([1, 1.2, 1])
    with col_cent:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.title("🦷 Login")
        with st.form("login_form"):
            u = st.text_input("Usuário").lower().strip()
            p = st.text_input("Senha", type="password").strip()
            if st.form_submit_button("Acessar Sistema"):
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
                    else:
                        st.error("Usuário ou senha inválidos.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. INTERFACE PRINCIPAL ---
user = st.session_state.user_info
st.sidebar.title(f"👤 {user['nome']}")
if st.sidebar.button("Encerrar Sessão"):
    st.session_state.clear()
    st.rerun()

# Menu por Perfil
if user['perfil'] == 'admin':
    menu = st.sidebar.radio("Navegação", ["📷 Meu Registro", "📊 Painel de Controle", "👥 Gestão de Usuários"])
else:
    menu = "📷 Meu Registro"

# --- LÓGICA 1: MEU REGISTRO (CÂMERA) ---
if menu == "📷 Meu Registro":
    st.header("📸 Captura de Uso")
    db = conectar_bd()
    if db:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT evento FROM registros WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 1", (user['id'],))
        ultimo = cursor.fetchone()
        db.close()
    
    proximo = "Check-out" if ultimo and ultimo['evento'] == "Check-in" else "Check-in"
    
    col_c, _ = st.columns([2, 1])
    with col_c:
        foto = st.camera_input("Capturar", label_visibility="collapsed")
        st.write(f"Ação Atual: **{proximo}**")
        
        if st.button(f"Confirmar {proximo}", type="primary"):
            if foto:
                agora = datetime.now()
                nome_f = f"{agora.strftime('%Y%m%d_%H%M%S')}_{user['id']}_{proximo.lower()}.jpg"
                
                with st.spinner("Sincronizando imagens..."):
                    if gerenciar_ftp("upload", nome_f, foto):
                        db = conectar_bd()
                        cursor = db.cursor()
                        cursor.execute("INSERT INTO registros (data_hora, evento, nome_foto, usuario_id) VALUES (%s, %s, %s, %s)", 
                                     (agora, proximo, nome_f, user['id']))
                        db.close()
                        st.success("Salvo no servidor!")
                        st.rerun()
            else: st.warning("Por favor, tire a foto primeiro.")

# --- LÓGICA 2: PAINEL DE CONTROLE (ADMIN) ---
elif menu == "📊 Painel de Controle":
    st.header("📊 Dashboard de Monitoramento")
    db = conectar_bd()
    if db:
        # Puxa todos os registros cruzando com nomes de usuários
        query = "SELECT r.*, u.nome FROM registros r JOIN usuarios u ON r.usuario_id = u.id ORDER BY r.data_hora ASC"
        df = pd.read_sql(query, db)
        db.close()

        if not df.empty:
            df['data_hora'] = pd.to_datetime(df['data_hora'])
            df['dia'] = df['data_hora'].dt.date
            
            # Agrupar por usuário para criar os Expanders
            for usuario_n, grupo in df.groupby("nome"):
                with st.expander(f"👤 {usuario_n}", expanded=False):
                    seg_total = 0; check_t = None
                    dados_cards = []
                    
                    # Lógica de cálculo de tempo por par Check-in/Out
                    for r in grupo.itertuples():
                        if r.evento == "Check-in":
                            check_t = r.data_hora
                        elif r.evento == "Check-out" and check_t:
                            diff = (r.data_hora - check_t).total_seconds()
                            seg_total += diff
                            h_c = int(diff // 3600); m_c = int((diff % 3600) // 60)
                            dados_cards.append({"dia": r.dia, "tempo": f"{h_c}h {m_c}m"})
                            check_t = None
                    
                    # Exibe o Tempo Total do Usuário no Card
                    h_t = int(seg_total // 3600); m_t = int((seg_total % 3600) // 60)
                    st.subheader(f"Tempo Total: {h_t}h {m_t}m")
                    
                    # Grid de cards diários
                    cols = st.columns(4)
                    for i, card in enumerate(dados_cards):
                        with cols[i % 4]:
                            st.markdown(f"<div class='card-tempo'><small>{card['dia'].strftime('%d/%m')}</small><br><b>{card['tempo']}</b></div>", unsafe_allow_html=True)
                            if st.toggle("🖼️ Fotos", key=f"f_{usuario_n}_{i}"):
                                # Filtra fotos deste dia específico para este usuário
                                fotos_dia = grupo[grupo['dia'] == card['dia']]
                                for f in fotos_dia.itertuples():
                                    img_bin = gerenciar_ftp("download", f.nome_foto)
                                    if img_bin:
                                        st.image(img_bin, caption=f"{f.evento} {f.data_hora.strftime('%H:%M')}")

# --- LÓGICA 3: GESTÃO DE USUÁRIOS ---
elif menu == "👥 Gestão de Usuários":
    st.header("👥 Gerenciar Acessos")
    db = conectar_bd()
    
    # Formulário para novo usuário
    with st.expander("➕ Cadastrar Novo Paciente/Admin"):
        with st.form("novo_user"):
            n = st.text_input("Nome Completo")
            u = st.text_input("Login").lower().strip()
            s = st.text_input("Senha")
            p = st.selectbox("Perfil", ["user", "admin"])
            if st.form_submit_button("Salvar"):
                cursor = db.cursor()
                cursor.execute("INSERT INTO usuarios (nome, usuario, senha, perfil) VALUES (%s,%s,%s,%s)", (n,u,s,p))
                st.rerun()

    # Listagem de usuários existentes
    u_df = pd.read_sql("SELECT * FROM usuarios", db)
    for row in u_df.itertuples():
        # O título do expander agora exibe o nome corretamente após o cadastro
        with st.expander(f"👤 {row.nome} ({row.perfil})"):
            c_ed, c_del = st.columns([3, 1])
            with c_ed:
                with st.form(f"form_ed_{row.id}"):
                    en = st.text_input("Nome", value=row.nome)
                    es = st.text_input("Senha", value=row.senha)
                    if st.form_submit_button("Salvar Alterações"):
                        cursor = db.cursor()
                        cursor.execute("UPDATE usuarios SET nome=%s, senha=%s WHERE id=%s", (en, es, row.id))
                        st.rerun()
            with c_del:
                st.write("Ações")
                if st.button("Remover Usuário", key=f"btn_del_{row.id}", type="secondary"):
                    cursor = db.cursor()
                    cursor.execute("DELETE FROM usuarios WHERE id=%s", (row.id,))
                    st.warning(f"Usuário {row.nome} removido.")
                    st.rerun()