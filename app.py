import streamlit as st
import requests
import pandas as pd

# Configuración de la página web
st.set_page_config(page_title="Generador de Constancias", page_icon="📄", layout="centered")

st.title("📄 Generador Automático de Constancias de Trabajo")
st.write("Selecciona un empleado de la lista e ingresa su sueldo para generar y descargar su constancia en PDF al instante.")

# ==========================================
#               CONFIGURACIÓN
# ==========================================
# 1. URL de tu Webhook de n8n
N8N_WEBHOOK_URL = "https://n8n-n8n.gfeuh8.easypanel.host/webhook/generar-constancia"

# 2. Conexión directa a Google Sheets
# Utilizamos el enlace directo de exportación a CSV de tu hoja
ID_GOOGLE_SHEET = "13VjBlYoagr2OC0DMoTLt9bpmPS9Mu6LOqS_HSxU2dlg"
URL_DATOS = f"https://docs.google.com/spreadsheets/d/{ID_GOOGLE_SHEET}/export?format=csv"

# ==========================================
#          CARGA DE DATOS DESDE G-SHEETS
# ==========================================
# Aplicamos un caché de 2 minutos para evitar consultas repetidas al servidor si el usuario interactúa con los botones
@st.cache_data(ttl=120) 
def cargar_datos_empleados():
    try:
        # Al descargar directo de G-Sheets, el formato por defecto es UTF-8 y separado por comas
        df = pd.read_csv(URL_DATOS, header=6, sep=",", engine='python', encoding='utf-8')
        
        # Limpiamos espacios invisibles en los títulos de las columnas
        df.columns = df.columns.astype(str).str.strip()
        
        # Accedemos por POSICIÓN absoluta en las columnas del archivo para blindar el flujo
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
        st.error(f"Error al procesar la base de datos de Google Sheets: {e}")
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

    # ==== NUEVO CAMPO: SUELDO MANUAL ====
    st.subheader("Información de Remuneración:")
    sueldo_manual = st.text_input(
        "Ingresa el monto del sueldo para la constancia:", 
        placeholder="Ej. $150, 5.000 Bs., etc.",
        help="Este monto exacto será el que se imprima en el documento."
    )

    st.divider()

    # Botón para disparar la solicitud a n8n
    if st.button("Generar Constancia en PDF", type="primary", use_container_width=True):
        
        # Validación: Evitar generar si el sueldo está vacío
        if not sueldo_manual.strip():
            st.warning("⚠️ Por favor, ingresa el monto del sueldo antes de generar la constancia.")
        else:
            with st.spinner("Enviando requerimiento a n8n y procesando PDF corporativo..."):
                
                # Payload con la nueva estructura
                payload = {
                    "cedula": cedula_seleccionada,
                    "sueldo": sueldo_manual.strip()
                }
                
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
    st.warning("No se pudieron cargar los datos. Verifica que el enlace de Google Sheets sea correcto.")
