# -*- coding: utf-8 -*-
import gspread
from google.oauth2.service_account import Credentials # Se mantiene para la autenticación de Drive API
import os
import time # Para añadir una marca de tiempo al nombre de la nueva hoja

# --- TUS DATOS CRÍTICOS ---
SERVICE_ACCOUNT_FILE = 'braided-gramma-465202-t4-7894b7df3cb4.json' # ¡Nombre exacto del JSON!
# ¡NUEVO ID DE LA HOJA DE CÁLCULO! Es el ID de tu 'Catálogo de Beats_NUEVO'
SPREADSHEET_ID = '1bHbVKr7B4DptPCWsL4HFdg4Qy9So5rC88T3hrQf5P68' 

SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]
# --- FIN TUS DATOS CRÍTICOS ---

print("--- TEST DE CONEXIÓN Y CREACIÓN DE HOJA ---")
print("Intentando autenticar con Google...")
try:
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR: Archivo de credenciales NO encontrado: '{SERVICE_ACCOUNT_FILE}'")
        print("Verifica el nombre y ruta del JSON.")
        exit()

    # Autenticación para gspread (la forma más directa para cuentas de servicio)
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    
    # Autenticación para la API de Drive (si la necesitáramos aquí, aunque para crear hoja, gspread.create es suficiente)
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPE)
    drive_service = build('drive', 'v3', credentials=creds) # Necesario si el script principal usa drive_service
    
    print("Autenticación exitosa.")

    # Intentar crear una nueva hoja de cálculo
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    new_sheet_name = f"Test_Robot_Hoja_{timestamp}"
    
    print(f"Intentando crear una nueva hoja de cálculo: '{new_sheet_name}'...")
    new_spreadsheet = gc.create(new_sheet_name)
    print(f"¡ÉXITO! Nueva hoja '{new_spreadsheet.title}' creada correctamente con ID: {new_spreadsheet.id}")
    print("Por favor, verifica en tu Google Drive si aparece esta nueva hoja. Puedes borrarla luego.")

except gspread.exceptions.APIError as e:
    print(f"ERROR: Falló la API de Google Sheets al intentar crear la hoja. Mensaje: {e}")
    print("POSIBLE CAUSA:")
    print("  - Permisos insuficientes para CREAR hojas (verificar roles de cuenta de servicio en Google Cloud Console, no solo compartir una hoja).")
    print("  - Políticas de Google Workspace (si es una cuenta de empresa/educativa) que impiden la creación de hojas.")
    print("  - Problema temporal con la API de Google.")
except Exception as e:
    print(f"ERROR GENERAL al intentar la conexión o creación: {type(e).__name__} - {e}")
    print("Posibles causas: Problemas con el archivo JSON, conflicto de librerías, o red.")

print("--- FIN DEL TEST DE CONEXIÓN Y CREACIÓN ---")