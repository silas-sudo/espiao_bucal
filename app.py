import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime
import ftplib
import os
from PIL import Image

# --- CONFIGURAÇÕES DE CONEXÃO (Lendo do Secrets) ---
def conectar_bd():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        port=st.secrets["mysql"]["port"]
    )

# --- FUNÇÃO DE UPLOAD FTP (HostGator) ---
def upload_foto_ftp(caminho_local, nome_arquivo):
    try:
        # Dados do seu painel
        ftp_host = "69.49.241.31" 
        ftp_user = "espiao@francotec.com.br"
        ftp_pass = "Helena@!*2026"
        
        ftp = ftplib.FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        
        # Caminho absoluto confirmado
        ftp.cwd('fotos_registro')
        
        with open(caminho_local, 'rb') as f:
            ftp.storbinary(f'STOR {nome_arquivo}', f)
        
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Erro no Upload FTP: {e}")
        return False

# --- INTERFACE E LÓGICA ---
st.set_page_config(page_title="Espião Bucal - FrancoTec", layout="wide")

st.title("🦷 Sistema de Monitoramento Bucal")

# Menu Lateral simplificado
menu = st.sidebar.selectbox("Navegação", ["Check-in/Out", "Painel Administrativo"])

if menu == "Check-in/Out":
    st.header("📸 Registro de Uso")
    
    # Campo para identificar o usuário (Isabela ou Rafael)
    usuario = st.selectbox("Selecione o Usuário", ["Isabela Alves da Conceição", "Rafael Alves Araújo"])
    
    foto = st.camera_input("Tire uma foto para registrar")

    if foto:
        nome_foto = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{usuario.split()[0]}.jpg"
        caminho_temp = os.path.join("temp_foto.jpg")
        
        # Salva localmente para enviar
        img = Image.open(foto)
        img.save(caminho_temp)
        
        if st.button("Confirmar Registro"):
            with st.spinner("Salvando dados e enviando foto..."):
                # 1. Envia Foto via FTP
                if upload_foto_ftp(caminho_temp, nome_foto):
                    # 2. Salva no Banco de Dados da HostGator
                    try:
                        conn = conectar_bd()
                        cursor = conn.cursor()
                        
                        # Lógica de inserção (ajuste conforme suas colunas do banco exportado)
                        sql = "INSERT INTO registros (usuario, data_hora, nome_foto) VALUES (%s, %s, %s)"
                        cursor.execute(sql, (usuario, datetime.now(), nome_foto))
                        
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        st.success(f"Registro realizado com sucesso para {usuario}!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco: {e}")
                
                # Remove arquivo temporário
                if os.path.exists(caminho_temp):
                    os.remove(caminho_temp)

elif menu == "Painel Administrativo":
    st.header("📊 Dashboard de Uso")
    
    try:
        conn = conectar_bd()
        df = pd.read_sql("SELECT * FROM registros ORDER BY data_hora DESC", conn)
        conn.close()

        # Exibição dos dados
        if not df.empty:
            st.subheader("Últimos Registros")
            for index, row in df.iterrows():
                with st.expander(f"{row['usuario']} - {row['data_hora']}"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        # Link direto da FrancoTec
                        url_foto = f"https://francotec.com.br/fotos_registro/{row['nome_foto']}"
                        st.image(url_foto, width=200)
                    with col2:
                        st.write(f"Data: {row['data_hora'].strftime('%d/%m/%Y')}")
                        st.write(f"Hora: {row['data_hora'].strftime('%H:%M:%S')}")
        else:
            st.info("Nenhum registro encontrado no banco da HostGator.")
            
    except Exception as e:
        st.error(f"Erro ao carregar Dashboard: {e}")
