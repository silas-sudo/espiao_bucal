import streamlit as st
import mysql.connector
import ftplib
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import os
import pytz

# --- 1. CONFIGURAÇÕES DE INTERFACE ---
st.set_page_config(
    page_title="Espião Bucal Pro", 
    page_icon="🦷", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

# CSS Customizado - Remove o botão de colapso da sidebar
st.markdown("""
<style>
/* Remove cabeçalho padrão */
.stAppHeader, header, .stApp > header, [data-testid="stHeader"], [data-testid="stToolbar"] {
    display: none !important;
    visibility: hidden !important;
    background: transparent !important;
    height: 0 !important;
}

/* Ajusta padding */
.main .block-container {
    padding-top: 0.5rem !important;
}

/* REMOVE O BOTÃO DE COLAPSO DA SIDEBAR - SIDEBAR FIXA */
[data-testid="collapsedControl"] {
    display: none !important;
}

/* Garante que a sidebar sempre fique visível */
section[data-testid="stSidebar"] {
    min-width: 300px !important;
    width: 300px !important;
    transform: translateX(0px) !important;
}

/* Estilo dos cards */
.card-tempo { 
    background-color: #1e1e1e; 
    border: 1px solid #333; 
    border-radius: 12px; 
    padding: 15px; 
    text-align: center; 
    margin-bottom: 15px; 
}

.stButton button { 
    width: 100%; 
    border-radius: 10px; 
    height: 3.5em; 
    font-weight: bold; 
}
</style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÃO PARA HORÁRIO DE BRASÍLIA ---
def obter_horario_brasilia():
    """Retorna a data/hora atual no fuso horário de Brasília"""
    fuso_brasilia = pytz.timezone('America/Sao_Paulo')
    agora_utc = datetime.now(pytz.UTC)
    agora_brasilia = agora_utc.astimezone(fuso_brasilia)
    return agora_brasilia

# --- 3. CONEXÕES ---
def conectar_bd():
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
        st.error(f"Falha na Conexão: {e}")
        return None

def gerenciar_ftp(acao, nome_arquivo=None, foto_buffer=None):
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
            st.error(f"Erro FTP: {e}")
        return None

# --- 4. SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- 5. TELA DE LOGIN ---
if not st.session_state.logado:
    _, col_login, _ = st.columns([1, 1.2, 1])
    
    with col_login:
        st.markdown("<h2 style='text-align: center;'>🦷 Espião Bucal</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("Usuário").lower().strip()
            p = st.text_input("Senha", type="password").strip()
            
            submit = st.form_submit_button("Acessar Painel", use_container_width=True)
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
                        st.error("Credenciais inválidas")
    st.stop()

# --- 6. INTERFACE PRINCIPAL - SIDEBAR FIXA ---
user = st.session_state.user_info

# SIDEBAR FIXA (sem botão de colapso)
with st.sidebar:
    st.markdown("---")
    st.markdown(f"### 👤 {user['nome']}")
    st.caption(f"**Nível:** {user['perfil'].upper()}")
    
    st.markdown("---")
    
    # Exibe hora atual de Brasília
    hora_atual = obter_horario_brasilia()
    st.caption(f"🕐 {hora_atual.strftime('%d/%m/%Y')}")
    st.caption(f"⏰ {hora_atual.strftime('%H:%M:%S')} (Brasília)")
    
    st.markdown("---")
    
    # Menu de navegação
    st.markdown("### 📋 Navegação")
    if user['perfil'] == 'admin':
        menu = st.radio(
            "Selecione uma opção:",
            ["📊 Painel de Controle", "👥 Gestão de Usuários"],
            label_visibility="collapsed"
        )
    else:
        menu = "📷 Meu Registro"
        st.info("📷 Modo de Captura")
    
    st.markdown("---")
    
    if st.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    st.caption("Espião Bucal Pro v1.0")

# --- MÓDULO: MEU REGISTRO ---
if menu == "📷 Meu Registro":
    st.header("📸 Captura de Uso")
    
    db = conectar_bd()
    if db:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT evento, data_hora FROM registros WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 1", (user['id'],))
        ultimo = cursor.fetchone()
        db.close()
        
        proximo = "Check-out" if ultimo and ultimo['evento'] == "Check-in" else "Check-in"
        
        col_c, _ = st.columns([2, 1])
        with col_c:
            foto = st.camera_input("Capturar Foto", label_visibility="collapsed")
            
            agora_brasilia = obter_horario_brasilia()
            st.info(f"**Status:** {proximo} | **Hora:** {agora_brasilia.strftime('%d/%m/%Y %H:%M:%S')}")
            
            if st.button(f"✅ Confirmar {proximo}", type="primary", use_container_width=True):
                if foto:
                    agora = obter_horario_brasilia()
                    nome_f = f"{agora.strftime('%Y%m%d_%H%M%S')}_{user['id']}_{proximo.lower()}.jpg"
                    
                    with st.spinner("Enviando..."):
                        if gerenciar_ftp("upload", nome_f, foto):
                            db = conectar_bd()
                            cur = db.cursor()
                            data_hora_str = agora.strftime('%Y-%m-%d %H:%M:%S')
                            sql = "INSERT INTO registros (data_hora, evento, nome_foto, usuario_id) VALUES (%s, %s, %s, %s)"
                            cur.execute(sql, (data_hora_str, proximo, nome_f, user['id']))
                            db.close()
                            st.success(f"✅ Registrado com sucesso!")
                            st.rerun()
                else:
                    st.warning("⚠️ Capture uma imagem primeiro")

# --- MÓDULO: PAINEL DE CONTROLE ---
elif menu == "📊 Painel de Controle":
    st.header("📊 Gestão de Monitoramento")
    
    db = conectar_bd()
    if db:
        query = "SELECT r.*, u.nome FROM registros r JOIN usuarios u ON r.usuario_id = u.id ORDER BY r.data_hora DESC"
        df = pd.read_sql(query, db)
        db.close()

        if not df.empty:
            col_btn1, col_btn2 = st.columns([1, 3])
            with col_btn1:
                if st.button("🚨 Zerar Todos", use_container_width=True):
                    db = conectar_bd()
                    cur = db.cursor()
                    cur.execute("SELECT nome_foto FROM registros")
                    todas_fotos = cur.fetchall()
                    for f in todas_fotos:
                        gerenciar_ftp("deletar", f[0])
                    cur.execute("TRUNCATE TABLE registros")
                    db.close()
                    st.rerun()

            def converter_para_datetime(valor):
                try:
                    if isinstance(valor, str):
                        return datetime.strptime(valor, '%Y-%m-%d %H:%M:%S')
                    return valor
                except:
                    return None
            
            df['data_hora'] = df['data_hora'].apply(converter_para_datetime)
            df = df[df['data_hora'].notna()]
            
            if not df.empty:
                df['dia'] = df['data_hora'].apply(lambda x: x.date())
                
                for usuario_n in df['nome'].unique():
                    grupo = df[df['nome'] == usuario_n].copy()
                    
                    with st.expander(f"👤 {usuario_n}", expanded=True):
                        seg_total = 0
                        check_t = None
                        cards_data = []
                        
                        grupo = grupo.sort_values('data_hora')
                        
                        for idx, row in grupo.iterrows():
                            if row['evento'] == "Check-in":
                                check_t = row['data_hora']
                            elif row['evento'] == "Check-out" and check_t:
                                diff = (row['data_hora'] - check_t).total_seconds()
                                seg_total += diff
                                h_c = int(diff // 3600)
                                m_c = int((diff % 3600) // 60)
                                cards_data.append({"dia": row['dia'], "tempo": f"{h_c}h {m_c}m"})
                                check_t = None
                        
                        h_t = int(seg_total // 3600)
                        m_t = int((seg_total % 3600) // 60)
                        st.subheader(f"⏱️ Total: {h_t}h {m_t}m")
                        
                        if cards_data:
                            st.write("#### 📅 Resumo por Dia")
                            num_cols = min(4, len(cards_data))
                            c_cols = st.columns(num_cols)
                            for i, card in enumerate(cards_data):
                                with c_cols[i % num_cols]:
                                    st.markdown(f"<div class='card-tempo'><small>{card['dia'].strftime('%d/%m/%Y')}</small><br><b>{card['tempo']}</b></div>", unsafe_allow_html=True)

                        st.write("#### 📋 Detalhes")
                        for idx, row in grupo.iterrows():
                            col1, col2, col3 = st.columns([3, 1, 1])
                            hora_str = row['data_hora'].strftime('%d/%m/%Y %H:%M:%S')
                            col1.write(f"🔹 {hora_str} - {row['evento']}")
                            
                            if col2.button("🗑️", key=f"del_{row['id']}"):
                                gerenciar_ftp("deletar", row['nome_foto'])
                                db = conectar_bd()
                                cur = db.cursor()
                                cur.execute("DELETE FROM registros WHERE id=%s", (row['id'],))
                                db.close()
                                st.rerun()
                                
                            if col3.toggle("🖼️", key=f"img_{row['id']}"):
                                img_bin = gerenciar_ftp("download", row['nome_foto'])
                                if img_bin:
                                    st.image(img_bin, use_container_width=True)
            else:
                st.info("📭 Nenhum registro válido encontrado.")
        else:
            st.info("📭 Nenhum registro encontrado.")

# --- MÓDULO: GESTÃO DE USUÁRIOS ---
elif menu == "👥 Gestão de Usuários":
    st.header("👥 Administração de Contas")
    db = conectar_bd()
    
    if db:
        with st.expander("➕ Novo Usuário", expanded=False):
            with st.form("cad_user"):
                col1, col2 = st.columns(2)
                with col1:
                    n = st.text_input("Nome Completo")
                    u = st.text_input("Login").lower().strip()
                with col2:
                    s = st.text_input("Senha", type="password")
                    p = st.selectbox("Perfil", ["user", "admin"])
                
                if st.form_submit_button("💾 Salvar", use_container_width=True):
                    if n and u and s:
                        cur = db.cursor()
                        cur.execute("INSERT INTO usuarios (nome, usuario, senha, perfil) VALUES (%s,%s,%s,%s)", (n,u,s,p))
                        db.commit()
                        st.success("✅ Cadastrado!")
                        st.rerun()
                    else:
                        st.warning("Preencha todos os campos!")

        st.subheader("📋 Usuários")
        u_df = pd.read_sql("SELECT id, nome, usuario, perfil FROM usuarios ORDER BY nome", db)
        
        for row in u_df.itertuples():
            with st.expander(f"👤 {row.nome} (@{row.usuario})", expanded=False):
                c1, c2 = st.columns([3, 1])
                with c1:
                    with st.form(f"edit_{row.id}"):
                        en = st.text_input("Nome", value=row.nome)
                        eu = st.text_input("Usuário", value=row.usuario)
                        es = st.text_input("Nova Senha", type="password", placeholder="Deixe em branco")
                        ep = st.selectbox("Perfil", ["user", "admin"], index=0 if row.perfil == "user" else 1)
                        
                        if st.form_submit_button("✏️ Alterar", use_container_width=True):
                            cur = db.cursor()
                            if es:
                                cur.execute("UPDATE usuarios SET nome=%s, usuario=%s, senha=%s, perfil=%s WHERE id=%s", 
                                          (en, eu, es, ep, row.id))
                            else:
                                cur.execute("UPDATE usuarios SET nome=%s, usuario=%s, perfil=%s WHERE id=%s", 
                                          (en, eu, ep, row.id))
                            db.commit()
                            st.success("✅ Alterado!")
                            st.rerun()
                
                with c2:
                    if st.button("🗑️ Excluir", key=f"u_del_{row.id}"):
                        if row.id == user['id']:
                            st.error("❌ Não pode excluir a própria conta!")
                        else:
                            cur = db.cursor()
                            cur.execute("DELETE FROM usuarios WHERE id=%s", (row.id,))
                            db.commit()
                            st.success("✅ Excluído!")
                            st.rerun()
        
        db.close()