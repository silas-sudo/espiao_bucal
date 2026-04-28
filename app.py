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
    initial_sidebar_state="expanded",
    menu_items=None  # Remove menu padrão do Streamlit
)

# CSS Customizado para remover cabeçalho e ajustar layout
st.markdown("""
<style>
/* Remove completamente o cabeçalho padrão do Streamlit */
.stAppHeader {
    display: none !important;
    visibility: hidden !important;
    background: transparent !important;
    height: 0 !important;
}

/* Remove o header padrão */
header {
    display: none !important;
    visibility: hidden !important;
    background: transparent !important;
}

/* Remove o espaço reservado pelo header */
.stApp > header {
    display: none !important;
}

/* Remove toolbar e elementos extras */
[data-testid="stHeader"] {
    display: none !important;
}

[data-testid="stToolbar"] {
    display: none !important;
}

/* Ajusta o padding superior do conteúdo principal */
.main .block-container {
    padding-top: 0.5rem !important;
}

/* Remove qualquer borda ou sombra superior */
.stApp {
    border-top: none !important;
}

/* Cards de tempo no Dashboard */
.card-tempo { 
    background-color: #1e1e1e; 
    border: 1px solid #333; 
    border-radius: 12px; 
    padding: 15px; 
    text-align: center; 
    margin-bottom: 15px; 
}

/* Botões padronizados */
.stButton button { 
    width: 100%; 
    border-radius: 10px; 
    height: 3.5em; 
    font-weight: bold; 
}

/* Box de Login Centralizado */
.login-box { 
    max-width: 400px; 
    margin: 0 auto; 
    padding: 2.5rem; 
    border: 1px solid #333; 
    border-radius: 15px; 
    background-color: #0e1117; 
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
}

/* Remove padding superior da sidebar */
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# --- 2. CAMADA DE INFRAESTRUTURA (CONEXÕES HOSTGATOR) ---

def conectar_bd():
    """Gerencia conexão remota com MySQL"""
    try:
        c = st.secrets["mysql"]
        conn = mysql.connector.connect(
            host=c["host"], 
            port=c["port"], 
            database=c["database"],
            user=c["user"], 
            password=c["password"], 
            autocommit=True
        )
        return conn
    except Exception as e:
        st.error(f"Falha Crítica na Conexão com Banco: {e}")
        return None

def gerenciar_ftp(acao, nome_arquivo=None, foto_buffer=None):
    """Lida com Sincronização de Arquivos no Servidor"""
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
            buf.seek(0)
            ftp.storbinary(f'STOR {nome_arquivo}', buf)
            resultado = True
            
        elif acao == "download":
            buf = io.BytesIO()
            ftp.retrbinary(f'RETR {nome_arquivo}', buf.write)
            buf.seek(0)
            resultado = buf.getvalue()
            
        elif acao == "deletar":
            ftp.delete(nome_arquivo)
            resultado = True
        
        ftp.quit()
        return resultado
    except Exception as e:
        if acao != "download":
            st.error(f"Erro no Servidor de Arquivos (FTP): {e}")
        return None

# --- 3. GESTÃO DE ESTADO DA SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- 4. TELA DE LOGIN (CENTRALIZADA E LIMPA) ---
if not st.session_state.logado:
    st.write("")  # Espaço vazio para compensar o topo
    _, col_login, _ = st.columns([1, 1.2, 1])
    
    with col_login:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: white;'>🦷 Espião Bucal</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("Usuário").lower().strip()
            p = st.text_input("Senha", type="password").strip()
            
            submit = st.form_submit_button("Acessar Painel")
            if submit:
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
                        st.error("Credenciais inválidas. Tente novamente.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. INTERFACE PRINCIPAL LOGADA ---
user = st.session_state.user_info
st.sidebar.title(f"👤 {user['nome']}")
st.sidebar.write(f"Nível: {user['perfil'].upper()}")

if st.sidebar.button("Encerrar Sessão"):
    st.session_state.clear()
    st.rerun()

# Menu baseado no perfil
if user['perfil'] == 'admin':
    menu = st.sidebar.radio("Navegação", ["📊 Painel de Controle", "👥 Gestão de Usuários"])
else:
    menu = "📷 Meu Registro"

# --- MÓDULO: MEU REGISTRO (PACIENTES) ---
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
            foto = st.camera_input("Capturar Foto", label_visibility="collapsed")
            st.info(f"Status Atual: **{proximo}**")
            
            if st.button(f"Confirmar Registro de {proximo}", type="primary"):
                if foto:
                    agora = datetime.now()
                    nome_f = f"{agora.strftime('%Y%m%d_%H%M%S')}_{user['id']}_{proximo.lower()}.jpg"
                    
                    with st.spinner("Enviando dados..."):
                        if gerenciar_ftp("upload", nome_f, foto):
                            db = conectar_bd()
                            cur = db.cursor()
                            sql = "INSERT INTO registros (data_hora, evento, nome_foto, usuario_id) VALUES (%s, %s, %s, %s)"
                            cur.execute(sql, (agora, proximo, nome_f, user['id']))
                            db.close()
                            st.success("Sincronizado com Sucesso!")
                            st.rerun()
                else:
                    st.warning("Por favor, capture uma imagem para validar.")

# --- MÓDULO: PAINEL DE CONTROLE (ADMIN) ---
elif menu == "📊 Painel de Controle":
    st.header("📊 Gestão de Monitoramento")
    
    db = conectar_bd()
    if db:
        query = "SELECT r.*, u.nome FROM registros r JOIN usuarios u ON r.usuario_id = u.id ORDER BY r.data_hora DESC"
        df = pd.read_sql(query, db)
        db.close()

        if not df.empty:
            if st.sidebar.button("🚨 Zerar Todos os Registros"):
                db = conectar_bd()
                cur = db.cursor()
                cur.execute("SELECT nome_foto FROM registros")
                todas_fotos = cur.fetchall()
                for f in todas_fotos:
                    gerenciar_ftp("deletar", f[0])
                cur.execute("TRUNCATE TABLE registros")
                db.close()
                st.rerun()

            df['data_hora'] = pd.to_datetime(df['data_hora'])
            df['dia'] = df['data_hora'].dt.date
            
            for usuario_n, grupo in df.groupby("nome"):
                with st.expander(f"👤 {usuario_n}", expanded=False):
                    seg_total = 0
                    check_t = None
                    cards_data = []
                    
                    grupo_ord = grupo.sort_values('data_hora')
                    for r in grupo_ord.itertuples():
                        if r.evento == "Check-in":
                            check_t = r.data_hora
                        elif r.evento == "Check-out" and check_t:
                            diff = (r.data_hora - check_t).total_seconds()
                            seg_total += diff
                            h_c = int(diff // 3600)
                            m_c = int((diff % 3600) // 60)
                            cards_data.append({"dia": r.dia, "tempo": f"{h_c}h {m_c}m"})
                            check_t = None
                    
                    h_t = int(seg_total // 3600)
                    m_t = int((seg_total % 3600) // 60)
                    st.subheader(f"⏱️ Tempo Total Acumulado: {h_t}h {m_t}m")
                    
                    c_cols = st.columns(4)
                    for i, card in enumerate(cards_data):
                        with c_cols[i % 4]:
                            st.markdown(f"<div class='card-tempo'><small>{card['dia'].strftime('%d/%m')}</small><br><b>{card['tempo']}</b></div>", unsafe_allow_html=True)

                    st.write("#### Detalhamento de Fotos e Eventos")
                    for r in grupo.itertuples():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        col1.write(f"🔹 {r.data_hora.strftime('%d/%m %H:%M')} - {r.evento}")
                        
                        if col2.button("🗑️ Apagar", key=f"del_{r.id}"):
                            gerenciar_ftp("deletar", r.nome_foto)
                            db = conectar_bd()
                            cur = db.cursor()
                            cur.execute("DELETE FROM registros WHERE id=%s", (r.id,))
                            db.close()
                            st.rerun()
                            
                        if col3.toggle("🖼️ Ver Foto", key=f"img_{r.id}"):
                            img_bin = gerenciar_ftp("download", r.nome_foto)
                            if img_bin:
                                st.image(img_bin, use_container_width=True)

# --- MÓDULO: GESTÃO DE USUÁRIOS ---
elif menu == "👥 Gestão de Usuários":
    st.header("👥 Administração de Contas")
    db = conectar_bd()
    
    # Novo Cadastro
    with st.expander("➕ Cadastrar Novo Usuário/Paciente"):
        with st.form("cad_user"):
            n = st.text_input("Nome Completo")
            u = st.text_input("Login/Usuário").lower().strip()
            s = st.text_input("Senha")
            p = st.selectbox("Nível de Acesso", ["user", "admin"])
            if st.form_submit_button("Salvar Cadastro"):
                cur = db.cursor()
                cur.execute("INSERT INTO usuarios (nome, usuario, senha, perfil) VALUES (%s,%s,%s,%s)", (n,u,s,p))
                db.commit()
                st.rerun()

    # Listagem para Edição
    u_df = pd.read_sql("SELECT * FROM usuarios", db)
    for row in u_df.itertuples():
        with st.expander(f"👤 {row.nome} (Login: {row.usuario})"):
            c1, c2 = st.columns([3, 1])
            with c1:
                with st.form(f"edit_{row.id}"):
                    en = st.text_input("Nome", value=row.nome)
                    eu = st.text_input("Usuário", value=row.usuario)
                    es = st.text_input("Senha", value=row.senha)
                    if st.form_submit_button("Confirmar Alteração"):
                        cur = db.cursor()
                        cur.execute("UPDATE usuarios SET nome=%s, usuario=%s, senha=%s WHERE id=%s", (en, eu, es, row.id))
                        db.commit()
                        st.rerun()
            with c2:
                st.write("---")
                if st.button("❌ Excluir", key=f"u_del_{row.id}"):
                    cur = db.cursor()
                    cur.execute("DELETE FROM usuarios WHERE id=%s", (row.id,))
                    db.commit()
                    st.rerun()
    
    db.close()