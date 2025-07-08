# -*- coding: utf-8 -*-
import gspread
from google.oauth2.service_account import Credentials
import os

# --- TUS DATOS CRÍTICOS ---
SERVICE_ACCOUNT_FILE = 'braided-gramma-465202-t4-7894b7df3cb4.json' # ¡Nombre exacto del JSON!
SPREADSHEET_ID = '19KvhoVYV0XIRZ3FfFTwBRPXjNSMyeAkFYUFl6I1kUEQ' # ¡ID exacto de tu Google Sheet!

SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]
# --- FIN TUS DATOS CRÍTICOS ---

print("Intentando autenticar con Google...")
try:
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR: Archivo de credenciales NO encontrado: '{SERVICE_ACCOUNT_FILE}'")
        exit()

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPE)
    gc = gspread.authorize(creds)
    print("Autenticación exitosa.")

    print(f"Intentando abrir la hoja de cálculo con ID: '{SPREADSHEET_ID}'...")
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    print(f"¡ÉXITO! Hoja de cálculo '{spreadsheet.title}' abierta correctamente.")

    # Opcional: intentar acceder a una hoja específica
    # worksheet = spreadsheet.worksheet('Hoja 1')
    # print(f"¡ÉXITO! Hoja de trabajo '{worksheet.title}' accesible.")

except gspread.exceptions.SpreadsheetNotFound:
    print(f"ERROR: Hoja de cálculo NO ENCONTRADA. ID: '{SPREADSHEET_ID}'.")
    print("Verifica el ID y los permisos de la cuenta de servicio como 'Editor' en la hoja.")
except Exception as e:
    print(f"ERROR GENERAL al intentar la conexión: {type(e).__name__} - {e}")
    print("Posibles causas: Problemas con el archivo JSON, permisos insuficientes, o conflicto de librerías.")