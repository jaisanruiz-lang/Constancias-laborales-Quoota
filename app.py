import streamlit as st
import requests
import pandas as pd

# Configuración de la página web
st.set_page_config(page_title="Generador de Constancias", page_icon="📄", layout="centered")

st.title("📄 Generador Automático de Constancias de Trabajo")
st.write("Selecciona la empresa y el empleado, ingresa su sueldo y descarga la constancia en PDF al instante.")

# ==========================================
#               CONFIGURACIÓN
# ==========================================
# 0. Empresas disponibles (datos según RIF). Deben coincidir con el nodo
#    "Datos de la empresa" del workflow de n8n.
EMPRESAS = [
    {
        "alias": "ALUMINIOLOGO",
        "rif": "J-31154969-2",
        "razon_social": "DISTRIBUIDORA DE ALUMINIO EL ALUMINIOLOGO ZICA POLICARPO, C.A.",
        "direccion": "AV PRINCIPAL LOS MECEDORES EDIF BLOQUE 3 PISO 6 APT 26-A URB HIJOS DE DIOS CARACAS DISTRITO CAPITAL ZONA POSTAL 1010",
    },
    {
        "alias": "ALUTECH LA GUAIRA",
        "rif": "J-50197119-6",
        "razon_social": "ALUTECH J.J.M.N. LA GUAIRA, C.A.",
        "direccion": "AV CARLOS SOUBLETTE LOCAL 1160-014 NRO PB URB MIRAMAR MAIQUETIA LA GUAIRA ZONA POSTAL 1161",
    },
    {
        "alias": "AXIOMA",
        "rif": "J-50800235-0",
        "razon_social": "AXIOMA DESARROLLOS, C.A.",
        "direccion": "CALLE PRINCIPAL DE SOJO LOCAL GALPON NRO S/N SECTOR NIVEL AUTOPISTA ORIENTE GUATIRE MIRANDA ZONA POSTAL 1225",
    },
    {
        "alias": "ALUTECH CARACAS",
        "rif": "J-50134441-8",
        "razon_social": "GRUPO ALUTECH J.J.M. CARACAS, C.A.",
        "direccion": "AV SUCRE CON CALLE REAL DE LOS FLORES DE CATIA LOCAL CC SUCRE, LOCAL NRO 5,6 ZONA CATIA CARACAS DISTRITO CAPITAL ZONA POSTAL 1030",
    },
    {
        "alias": "PERSIANAS NORD",
        "rif": "J-50134439-6",
        "razon_social": "PERSIANAS J.J.F. NORD, C.A.",
        "direccion": "CTRA PETARE SANTA LUCIA LOCAL GALPON NRO S/N SECTOR EL LIMONCITO FILAS DE MARICHE MIRANDA ZONA POSTAL 1073",
    },
]
# 1. URL de tu Webhook de n8n
N8N_WEBHOOK_URL = "https://n8n-n8n.gfeuh8.easypanel.host/webhook/generar-constancia"

# 2. Conexión directa a Google Sheets (Apunta directamente a la pestaña de empleados con gid=10104786)
ID_GOOGLE_SHEET = "13VjBlYoagr2OC0DMoTLt9bpmPS9Mu6LOqS_HSxU2dlg"
URL_DATOS = f"https://docs.google.com/spreadsheets/d/{ID_GOOGLE_SHEET}/export?format=csv&gid=10104786"

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
    # Selector de empresa: define razón social, RIF y dirección que llevará la constancia
    empresa = st.selectbox(
        "Empresa que emite la constancia:",
        EMPRESAS,
        format_func=lambda e: e["razon_social"],
    )
    st.caption(f"**RIF:** {empresa['rif']}  ·  **Domicilio fiscal:** {empresa['direccion']}")

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
                    "sueldo": sueldo_manual.strip(),
                    "empresa_rif": empresa["rif"]
                }

                try:
                    respuesta = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=60)
                    if respuesta.status_code == 200:
                        st.success("¡Constancia procesada exitosamente por el servidor de n8n!")
                        st.download_button(
                            label="⬇️ Descargar Archivo PDF",
                            data=respuesta.content,
                            file_name=f"Constancia_Trabajo_{cedula_seleccionada}_{empresa['alias'].replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        st.error(f"Error devuelto por n8n: Código {respuesta.status_code}.")
                except Exception as e:
                    st.error(f"No se pudo conectar con el Webhook: {e}")
else:
    st.warning("No se pudieron cargar los datos. Verifica que el enlace de Google Sheets sea correcto.")
