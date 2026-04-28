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

# Bloco CSS Expandido para Estilização e Remoção do Topo
st.markdown("""
    <style>
    /* Ajuste de Layout: Remoção total do cabeçalho branco */
    .stAppHeader { 
        display: none !important; 
    }
    .block-container { 
        padding-top: 0rem !important; 
        padding-bottom: 1rem !important;
    }
    header { 
        visibility: hidden; 
    }
    
    /* Estilização dos Cards de Tempo Diário */
    .card-tempo { 
        background-color: #1e1e1e; 
        border: 1px solid #444; 
        border-radius: 15px; 
        padding: 20px; 
        text-align: center; 
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .card-tempo:hover {
        border-color: #00ff00;
        transform: scale(1.02);
    }
    
    /* Botões de Ação Padronizados */
    .stButton button { 
        width: 100%; 
        border-radius: 12px; 
        height: 3.8em; 
        font-weight: bold;
        text-transform: uppercase;
    }
    
    /* Box de Login Centralizado Estilo Dark */
    .login-box { 
        max-width: 450px; 
        margin: 0 auto; 
        padding: 3rem; 
        border: 1px solid #333; 
        border-radius: 20px; 
        background-color: #0e1117; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.7);
    }
    
    /* Ajustes de tabelas e expanders */
    .stExpander {
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CAMADA DE INFRAESTRUTURA E CONEXÕES ---

def conectar_bd():
    """Conexão segura com o MySQL da HostGator via st.secrets"""
    try:
        config = st.secrets["mysql"]
        connection = mysql.connector.connect(
            host=config["host"], 
            port=config.get("port", 3306), 
            database=config["database"],
            user=config["user"], 
            password=config["password"], 
            autocommit=True
        )
        if connection.is_connected():
            return connection
    except mysql.connector.Error as err:
        st.error(f"Erro de Banco de Dados: {err}")
    except Exception as e:
        st.error(f"Erro inesperado na conexão: {e}")
    return None

def gerenciar_ftp(acao, nome_arquivo=None, foto_buffer=None):
    """Protocolo de transferência de arquivos (Upload, Download e Delete)"""
    try:
        ftp_host = "69.49.241.31"
        ftp_user = "espiao@francotec.com.br"
        ftp_pass = "Helena@!*2026"
        
        ftp = ftplib.FTP(ftp_host)
        ftp.login(ftp_user, ftp_pass)
        ftp.set_pasv(True)
        
        resultado = None
        
        if acao == "upload":
            # Otimização de imagem antes do envio
            img = Image.open(foto_buffer)
            if img.mode != 'RGB': 
                img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70) # Reduzido p/ 70% p/ economizar espaço
            buf.seek(0)
            ftp.storbinary(f'STOR {nome_arquivo}', buf)
            resultado = True
            
        elif acao == "download":
            buf = io.BytesIO()
            ftp.retrbinary(f'RETR {nome_arquivo}', buf.write)
            buf.seek(0)
            resultado = buf.getvalue()
            
        elif acao == "deletar":
            # Exclusão física para manter o servidor limpo
            ftp.delete(nome_arquivo)
            resultado = True
            
        ftp.quit()
        return resultado
    except Exception as e:
        if acao != "download":
            st.error(f"Falha na operação FTP ({acao}): {e}")
        return None

# --- 3. GESTÃO DE ESTADO DA SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- 4. FLUXO DE LOGIN (CENTRALIZADO) ---
if not st.session_state.logado:
    st.write("##") # Pequeno respiro no topo
    _, col_login, _ = st.columns([1, 1.5, 1])
    
    with col_login:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #00ff00;'>🦷 Espião Bucal Pro</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Acesse sua conta para continuar</p>", unsafe_allow_html=True)
        
        with st.form("form_acesso"):
            usuario_input = st.text_input("Usuário").lower().strip()
            senha_input = st.text_input("Senha", type="password").strip()
            
            btn_login = st.form_submit_button("Entrar no Sistema")
            
            if btn_login:
                db_conn = conectar_bd()
                if db_conn:
                    cursor = db_conn.cursor(dictionary=True)
                    query = "SELECT * FROM usuarios WHERE LOWER(usuario) = %s AND senha = %s"
                    cursor.execute(query, (usuario_input, senha_input))
                    usuario_data = cursor.fetchone()
                    db_conn.close()
                    
                    if usuario_data:
                        st.session_state.logado = True
                        st.session_state.user_info = usuario_data
                        st.success("Login realizado! Redirecionando...")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. DASHBOARD PRINCIPAL (LOGADO) ---
current_user = st.session_state.user_info

# Sidebar Customizada
with st.sidebar:
    st.image("https://francotec.com.br/wp-content/uploads/2024/03/cropped-logo-francotec.png", width=100) # Exemplo de logo
    st.title(f"Bem-vindo, {current_user['nome']}")
    st.write(f"💼 Perfil: **{current_user['perfil'].upper()}**")
    st.divider()
    
    # Navegação baseada em Perfil (Admin não vê câmera)
    if current_user['perfil'] == 'admin':
        menu_opcoes = ["📊 Painel de Controle", "👥 Gestão de Usuários"]
    else:
        menu_opcoes = ["📷 Meu Registro"]
        
    escolha = st.radio("Selecione o Módulo:", menu_opcoes)
    
    st.divider()
    if st.button("Sair do Sistema", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- MÓDULO 1: MEU REGISTRO (VISÃO DO PACIENTE) ---
if escolha == "📷 Meu Registro":
    st.header("📸 Registro de Uso do Aparelho")
    
    db_conn = conectar_bd()
    if db_conn:
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT evento FROM registros WHERE usuario_id = %s ORDER BY data_hora DESC LIMIT 1", (current_user['id'],))
        ultimo_registro = cursor.fetchone()
        db_conn.close()
        
        # Lógica de alternância automática
        proxima_acao = "Check-out" if ultimo_registro and ultimo_registro['evento'] == "Check-in" else "Check-in"
        
        st.write(f"Sua próxima ação é: **{proxima_acao}**")
        
        container_cam = st.container()
        with container_cam:
            foto_capturada = st.camera_input("Focar no sorriso para validar", label_visibility="collapsed")
            
            if st.button(f"Confirmar {proxima_acao}", type="primary"):
                if foto_capturada:
                    timestamp = datetime.now()
                    arquivo_nome = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{current_user['id']}_{proxima_acao.lower()}.jpg"
                    
                    with st.spinner("Sincronizando com servidor remoto..."):
                        if gerenciar_ftp("upload", arquivo_nome, foto_capturada):
                            db_conn = conectar_bd()
                            cursor = db_conn.cursor()
                            sql_insert = "INSERT INTO registros (data_hora, evento, nome_foto, usuario_id) VALUES (%s, %s, %s, %s)"
                            cursor.execute(sql_insert, (timestamp, proxima_acao, arquivo_nome, current_user['id']))
                            db_conn.close()
                            st.toast(f"{proxima_acao} realizado com sucesso!", icon="✅")
                            st.rerun()
                else:
                    st.warning("⚠️ Capture a foto antes de confirmar o registro.")

# --- MÓDULO 2: PAINEL DE CONTROLE (VISÃO DO DENTISTA) ---
elif escolha == "📊 Painel de Controle":
    st.header("📊 Monitoramento de Pacientes")
    
    db_conn = conectar_bd()
    if db_conn:
        sql_full = "SELECT r.*, u.nome FROM registros r JOIN usuarios u ON r.usuario_id = u.id ORDER BY r.data_hora DESC"
        df_registros = pd.read_sql(sql_full, db_conn)
        db_conn.close()

        if not df_registros.empty:
            # Opção de limpeza total
            if st.sidebar.warning("Zona de Perigo"):
                if st.sidebar.button("🚨 Apagar TUDO (Reset)"):
                    db_conn = conectar_bd()
                    cursor = db_conn.cursor()
                    cursor.execute("SELECT nome_foto FROM registros")
                    lista_fotos = cursor.fetchall()
                    for foto_item in lista_fotos:
                        gerenciar_ftp("deletar", foto_item[0])
                    cursor.execute("TRUNCATE TABLE registros")
                    db_conn.close()
                    st.rerun()

            df_registros['data_hora'] = pd.to_datetime(df_registros['data_hora'])
            df_registros['dia_formatado'] = df_registros['data_hora'].dt.date
            
            # Loop por Paciente
            for nome_paciente, grupo_paciente in df_registros.groupby("nome"):
                with st.expander(f"👤 Paciente: {nome_paciente}", expanded=False):
                    
                    # Cálculo de Horas
                    segundos_acumulados = 0
                    checkin_referencia = None
                    dados_grid = []
                    
                    # Ordenar ascendente para cálculo de tempo
                    grupo_ordenado = grupo_paciente.sort_values('data_hora', ascending=True)
                    
                    for row in grupo_ordenado.itertuples():
                        if row.evento == "Check-in":
                            checkin_referencia = row.data_hora
                        elif row.evento == "Check-out" and checkin_referencia:
                            duracao = (row.data_hora - checkin_referencia).total_seconds()
                            segundos_acumulados += duracao
                            
                            h_card = int(duracao // 3600)
                            m_card = int((duracao % 3600) // 60)
                            dados_grid.append({"dia": row.dia_formatado, "valor": f"{h_card}h {m_card}m"})
                            checkin_referencia = None
                    
                    total_h = int(segundos_acumulados // 3600)
                    total_m = int((segundos_acumulados % 3600) // 60)
                    
                    st.markdown(f"### ⏱️ Tempo Total Acumulado: `{total_h}h {total_m}m`")
                    
                    # Grid de Cards
                    col_grid = st.columns(4)
                    for idx, item in enumerate(dados_grid):
                        with col_grid[idx % 4]:
                            st.markdown(f"""
                                <div class='card-tempo'>
                                    <small>{item['dia'].strftime('%d/%m/%Y')}</small><br>
                                    <b style='font-size: 1.2em; color: #00ff00;'>{item['valor']}</b>
                                </div>
                            """, unsafe_allow_html=True)

                    st.divider()
                    st.write("📋 **Histórico de Registros:**")
                    
                    for r_hist in grupo_paciente.itertuples():
                        c_info, c_del, c_foto = st.columns([3, 1, 1])
                        c_info.write(f"🔹 {r_hist.data_hora.strftime('%d/%m - %H:%M')} | **{r_hist.evento}**")
                        
                        if c_del.button("🗑️", key=f"btn_del_{r_hist.id}"):
                            gerenciar_ftp("deletar", r_hist.nome_foto)
                            db_conn = conectar_bd()
                            cursor = db_conn.cursor()
                            cursor.execute("DELETE FROM registros WHERE id=%s", (r_hist.id,))
                            db_conn.close()
                            st.rerun()
                            
                        if c_foto.toggle("📷", key=f"tgl_img_{r_hist.id}"):
                            imagem_servidor = gerenciar_ftp("download", r_hist.nome_foto)
                            if imagem_servidor:
                                st.image(imagem_servidor, caption=f"Registro: {r_hist.evento}", use_container_width=True)

# --- MÓDULO 3: GESTÃO DE USUÁRIOS (ADMIN) ---
elif escolha == "👥 Gestão de Usuários":
    st.header("👥 Administração de Usuários e Pacientes")
    
    # Cadastro de Novo Usuário
    with st.expander("➕ Adicionar Novo Usuário ao Sistema"):
        with st.form("form_novo_usuario"):
            cad_nome = st.text_input("Nome Completo")
            cad_login = st.text_input("Login de Acesso (Usuário)").lower().strip()
            cad_senha = st.text_input("Senha Temporária")
            cad_perfil = st.selectbox("Perfil de Acesso", ["user", "admin"])
            
            if st.form_submit_button("Criar Conta"):
                if cad_nome and cad_login and cad_senha:
                    db_conn = conectar_bd()
                    cursor = db_conn.cursor()
                    cursor.execute("INSERT INTO usuarios (nome, usuario, senha, perfil) VALUES (%s,%s,%s,%s)", 
                                 (cad_nome, cad_login, cad_senha, cad_perfil))
                    db_conn.close()
                    st.success(f"Usuário {cad_nome} criado com sucesso!")
                    st.rerun()
                else:
                    st.error("Preencha todos os campos.")

    st.divider()
    
    # Listagem e Edição
    db_conn = conectar_bd()
    df_users = pd.read_sql("SELECT * FROM usuarios", db_conn)
    db_conn.close()
    
    for u_row in df_users.itertuples():
        with st.expander(f"👤 {u_row.nome} | Login: `{u_row.usuario}`"):
            col_ed, col_rem = st.columns([3, 1])
            
            with col_ed:
                with st.form(f"edit_user_{u_row.id}"):
                    ed_nome = st.text_input("Nome", value=u_row.nome)
                    ed_login = st.text_input("Usuário", value=u_row.usuario)
                    ed_senha = st.text_input("Senha", value=u_row.senha)
                    
                    if st.form_submit_button("Atualizar Dados"):
                        db_conn = conectar_bd()
                        cursor = db_conn.cursor()
                        cursor.execute("UPDATE usuarios SET nome=%s, usuario=%s, senha=%s WHERE id=%s", 
                                     (ed_nome, ed_login, ed_senha, u_row.id))
                        db_conn.close()
                        st.rerun()
            
            with col_rem:
                st.write("Cuidado!")
                if st.button("Remover", key=f"rem_u_{u_row.id}", type="secondary"):
                    db_conn = conectar_bd()
                    cursor = db_conn.cursor()
                    cursor.execute("DELETE FROM usuarios WHERE id=%s", (u_row.id,))
                    db_conn.close()
                    st.rerun()