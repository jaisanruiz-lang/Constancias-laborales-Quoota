import streamlit as st
import requests
import pandas as pd
import os

# Configuración de la página web
st.set_page_config(page_title="Generador de Constancias", page_icon="📄", layout="centered")

st.title("📄 Generador Automático de Constancias de Trabajo")
st.write("Selecciona un empleado de la lista para generar y descargar su constancia en PDF al instante.")

# ==========================================
#               CONFIGURACIÓN
# ==========================================
# 1. URL de tu Webhook de n8n
N8N_WEBHOOK_URL = "https://n8n-n8n.gfeuh8.easypanel.host/webhook/generar-constancia"

# 2. Nombre del archivo local (asegúrate de que se llame exactamente así en tu carpeta)
ARCHIVO_LOCAL = "empleados.csv"

# ==========================================
#          CARGA DE DATOS LOCALES
# ==========================================
def cargar_datos_empleados():
    if not os.path.exists(ARCHIVO_LOCAL):
        st.error(f"⚠️ No se encontró el archivo '{ARCHIVO_LOCAL}' en la carpeta actual. Por favor, verifica el nombre.")
        return None
        
    try:
        # Usamos encoding='latin-1' para que Windows Excel lea correctamente la 'é' de Cédula y tildes sin romperse
        df = pd.read_csv(ARCHIVO_LOCAL, header=6, sep=None, engine='python', encoding='latin-1')
        
        # Limpiamos espacios invisibles en los títulos de las columnas
        df.columns = df.columns.astype(str).str.strip()
        
        # Accedemos por POSICIÓN absoluta en las columnas del archivo para blindar el flujo:
        # Columna 0 = Cédula, Columna 4 = Nombres, Columna 5 = Apellidos
        col_cedula = df.columns[0]
        col_nombres = df.columns[4]
        col_apellidos = df.columns[5]
        
        # Filtramos eliminando filas que tengan datos vacíos en estas columnas clave
        df = df.dropna(subset=[col_cedula, col_nombres, col_apellidos], how='any')
        
        # Limpiamos espacios en blanco al inicio o final de los textos de cada celda
        df[col_cedula] = df[col_cedula].astype(str).str.strip()
        df[col_nombres] = df[col_nombres].astype(str).str.strip()
        df[col_apellidos] = df[col_apellidos].astype(str).str.strip()
        
        # Eliminamos filas basura o textos de cabeceras repetidas
        df = df[df[col_cedula] != 'nan']
        df = df[~df[col_cedula].str.contains("Cédula|Cedula", case=False)]
        
        # Creamos la visualización limpia para el selector desplegable
        df['Empleado_Display'] = df[col_nombres] + " " + df[col_apellidos] + " (" + df[col_cedula] + ")"
        
        # Renombramos las columnas internas para estandarizar la interfaz
        df = df.rename(columns={col_cedula: 'Cédula', col_nombres: 'Nombres', col_apellidos: 'Apellidos'})
        return df
        
    except Exception as e:
        st.error(f"Error al procesar el archivo local: {e}")
        return None

# Ejecutar la carga de la nómina
df_empleados = cargar_datos_empleados()

# ==========================================
#           INTERFAZ DE USUARIO
# ==========================================
if df_empleados is not None and not df_empleados.empty:
    # Generamos la lista ordenada para el buscador desplegable
    lista_empleados = df_empleados['Empleado_Display'].tolist()
    seleccion = st.selectbox("Buscar y seleccionar empleado:", lista_empleados)
    
    # Extraemos la fila del empleado seleccionado
    fila_empleado = df_empleados[df_empleados['Empleado_Display'] == seleccion].iloc[0]
    cedula_seleccionada = str(fila_empleado['Cédula']).strip()
    
    st.divider()
    
    # Tarjeta informativa de validación visual
    st.subheader("Datos del talento seleccionado:")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Nombre Completo:**\n{fila_empleado['Nombres']} {fila_empleado['Apellidos']}")
    with col2:
        st.info(f"**Documento de Identidad:**\n{cedula_seleccionada}")

    # Botón para disparar la solicitud a n8n
    if st.button("Generar Constancia en PDF", type="primary", use_container_width=True):
        with st.spinner("Enviando requerimiento a n8n y procesando PDF corporativo..."):
            payload = {"cedula": cedula_seleccionada}
            
            try:
                respuesta = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)
                if respuesta.status_code == 200:
                    st.success("¡Constancia procesada exitosamente por el servidor de n8n!")
                    st.download_button(
                        label="⬇️ Descargar Archivo PDF",
                        data=respuesta.content,
                        file_name=f"Constancia_Trabajo_{cedula_seleccionada}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.error(f"Error devuelto por n8n: Código {respuesta.status_code}.")
            except Exception as e:
                st.error(f"No se pudo conectar con el Webhook: {e}")
else:
    st.warning("No se pudieron estructurar los datos de los empleados. Verifica que el archivo 'empleados.csv' esté en la misma carpeta.")