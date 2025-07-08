# -*- coding: utf-8 -*-
import gspread
from google.oauth2.service_account import Credentials
import os 
import librosa
import soundfile as sf
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError, ID3, TIT2, TPE1, TCON, TXXX
import requests
from googleapiclient.discovery import build

# --- CONFIGURACIÓN CRÍTICA: ¡VERIFICAR CADA VALOR! ---
# Ruta al archivo JSON de tus credenciales de Google Cloud
# ¡ESTE ES EL NOMBRE EXACTO QUE ME DISTE, SIN EL .json AL FINAL, PARA VER SI ASÍ LO ENCUENTRA!
SERVICE_ACCOUNT_FILE = 'braided-grammar-465202-t4-7894b7df3cb4.json' # <--- ¡CORRECCIÓN AQUÍ!

# ID de tu Google Sheet 'Catálogo de Beats'
# ¡Este ID es MUY SENSIBLE! Debe ser solo la parte del ID de la URL (entre /d/ y /edit).
SPREADSHEET_ID = '19KvhoVYV0XIRZ3FfFTwBRPXjNSMyeAkFYUFl6I1kUEQ'
# Nombre EXACTO de la pestaña/hoja dentro de tu Google Sheet. Normalmente es 'Hoja 1'.
WORKSHEET_NAME = 'Hoja 1' 

# ID de tu carpeta 'Nuevos Beats' en Google Drive (donde subes los beats a organizar)
NUEVOS_BEATS_FOLDER_ID = '1fwLKWkWvn8TY6SSL7kQgaVtZ5olZFuyw'

# ID de tu carpeta 'Beats organizados por género' en Google Drive (donde se crearán las subcarpetas de género)
ORGANIZED_BEATS_PARENT_FOLDER_ID = '1nILKS4_YglgyLRuA_X6107N6ThMbsB8o'

# --- CONFIGURACIÓN DE RUTAS LOCALES Y PERMISOS ---
# Alcances (permisos) que tu robot necesita en Google
SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

# Carpeta temporal en tu computadora para descargar y procesar beats
# Se creará automáticamente si no existe.
DOWNLOAD_TEMP_DIR = 'temp_beats_processing'
if not os.path.exists(DOWNLOAD_TEMP_DIR):
    try:
        os.makedirs(DOWNLOAD_TEMP_DIR)
    except OSError as e:
        print(f"ERROR FATAL: No se pudo crear la carpeta temporal '{DOWNLOAD_TEMP_DIR}'. Mensaje: {e}")
        print("VERIFICAR: Permisos de escritura en el escritorio o ruta del script.")
        exit(1) # Salir del script si no se puede crear la carpeta temporal.

# --- FIN DE CONFIGURACIÓN Y DECLARACIONES ---


def authenticate_google():
    """
    Autentica con Google usando la cuenta de servicio.
    Verifica que el archivo de credenciales exista y que los permisos sean correctos.
    """
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR CRÍTICO DE AUTENTICACIÓN: El archivo de credenciales '{SERVICE_ACCOUNT_FILE}' NO SE ENCONTRÓ.")
        print("POSIBLE SOLUCIÓN: ")
        print("  1. Verifica que el nombre del archivo en 'SERVICE_ACCOUNT_FILE' (línea 15 del script) es EXACTO.")
        print("  2. Asegúrate de que el archivo JSON está en la MISMA CARPETA que este script.")
        print("  3. Si lo guardaste en otro lugar, pon la RUTA COMPLETA al archivo en la línea 15.")
        return None, None, None

    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPE)
        gc = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return gc, drive_service, creds
    except Exception as e:
        print(f"ERROR CRÍTICO DE AUTENTICACIÓN: Falló la conexión con Google. Mensaje: {e}")
        print("POSIBLE SOLUCIÓN: ")
        print("  1. El archivo JSON puede estar corrupto o incorrecto.")
        print("  2. La CUENTA DE SERVICIO (el email que termina en @gserviceaccount.com) NO TIENE PERMISOS de 'Editor' en:")
        print(f"     - La Google Sheet (ID: {SPREADSHEET_ID})")
        print(f"     - La carpeta 'Nuevos Beats' (ID: {NUEVOS_BEATS_FOLDER_ID})")
        print(f"     - La carpeta 'Beats organizados por género' (ID: {ORGANIZED_BEATS_PARENT_FOLDER_ID})")
        print("  3. Las APIs de 'Google Drive API' y 'Google Sheets API' NO están HABILITADAS en tu proyecto de Google Cloud.")
        return None, None, None

def get_sheet_data(gc, spreadsheet_id, worksheet_name):
    """Obtiene todos los datos de la hoja de cálculo. Maneja errores de acceso."""
    try:
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        return worksheet, worksheet.get_all_records(), worksheet.row_values(1)
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"ERROR: La Google Sheet con ID '{spreadsheet_id}' NO FUE ENCONTRADA.")
        print("POSIBLE SOLUCIÓN: Verifica que el 'SPREADSHEET_ID' en la línea 12 del script sea CORRECTO y la hoja exista.")
        print("  Asegúrate de que la CUENTA DE SERVICIO tiene permisos de 'Editor' en esa Google Sheet.")
        return None, None, None
    except gspread.exceptions.WorksheetNotFound:
        print(f"ERROR: La hoja '{worksheet_name}' NO FUE ENCONTRADA dentro de la Google Sheet.")
        print("POSIBLE SOLUCIÓN: Verifica que el 'WORKSHEET_NAME' en la línea 13 del script sea el nombre EXACTO de la pestaña de tu hoja (ej. 'Hoja 1' o 'MiCatalogo').")
        return None, None, None
    except Exception as e:
        print(f"ERROR: No se pudo acceder a la hoja de cálculo. Mensaje: {e}")
        print("POSIBLE SOLUCIÓN: Podría ser un problema de permisos. Asegúrate de que la CUENTA DE SERVICIO tiene permisos de 'Editor' en la Google Sheet.")
        return None, None, None

def update_sheet_row(worksheet, row_index, column_name, new_value, headers):
    """Actualiza una celda específica en la hoja de cálculo. Maneja errores de columna y API."""
    try:
        col_index = headers.index(column_name) + 1 # gspread usa 1-based indexing
        worksheet.update_cell(row_index, col_index, new_value)
    except ValueError:
        print(f"ADVERTENCIA: Columna '{column_name}' no encontrada en la hoja para la fila {row_index}. La información no se guardó para esta columna.")
        print("POSIBLE SOLUCIÓN: Verifica que el nombre de la columna en tu Google Sheet es EXACTO (incluyendo mayúsculas/minúsculas y espacios).")
    except Exception as e:
        print(f"ERROR: No se pudo actualizar la celda en la fila {row_index}, columna '{column_name}'. Mensaje: {e}")
        print("POSIBLE SOLUCIÓN: Podría ser un problema de conexión o cuota de la API de Google Sheets.")

def get_drive_file_info(drive_service, folder_id):
    """Obtiene información de los archivos en una carpeta de Google Drive. Maneja errores de acceso."""
    try:
        files_info = {}
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        items = results.get('files', [])
        for item in items:
            files_info[item['name']] = {'id': item['id'], 'mimeType': item['mimeType']}
        return files_info
    except Exception as e:
        print(f"ERROR: No se pudo acceder a la carpeta de Google Drive con ID '{folder_id}'. Mensaje: {e}")
        print("POSIBLE SOLUCIÓN: Verifica que el ID de la carpeta es CORRECTO y la CUENTA DE SERVICIO tiene permisos de 'Editor' en esa carpeta.")
        return {}

def download_file(drive_service, file_id, file_name, destination_folder):
    """Descarga un archivo de Google Drive a una carpeta local. Maneja errores de descarga."""
    filepath = os.path.join(destination_folder, file_name)
    try:
        # Usamos requests para una descarga más robusta que la de googleapiclient.get_media() directamente
        download_url = drive_service.files().get_media(fileId=file_id).uri
        response = requests.get(download_url, headers={'Authorization': f'Bearer {drive_service.credentials.token}'}, stream=True)
        response.raise_for_status() # Lanza un HTTPError si la descarga falla (ej. 404, 500)
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: # filtrar keep-alive new chunks
                    f.write(chunk)
        return filepath
    except requests.exceptions.HTTPError as err:
        print(f"ERROR DE DESCARGA HTTP para '{file_name}' (ID: {file_id}). Código: {err.response.status_code}. Mensaje: {err.response.text}")
        print("POSIBLE SOLUCIÓN: El archivo no existe en Drive (ID incorrecto) o hay un problema temporal de Google Drive.")
        return None
    except requests.exceptions.ConnectionError as err:
        print(f"ERROR DE CONEXIÓN al descargar '{file_name}'. Mensaje: {err}")
        print("POSIBLE SOLUCIÓN: Problemas de conexión a internet o firewall bloqueando la conexión.")
        return None
    except Exception as e:
        print(f"ERROR GENERAL al descargar '{file_name}'. Mensaje: {e}")
        print("POSIBLE SOLUCIÓN: Verificar permisos de escritura en la carpeta temporal.")
        return None

def analyze_audio(filepath):
    """Analiza un archivo de audio para BPM y clave usando Librosa. Maneja errores de Librosa."""
    if not filepath: # Si la descarga falló, filepath será None
        return "N/A", "N/A"
    try:
        y, sr = librosa.load(filepath, sr=None) # sr=None para usar la tasa de muestreo original
        
        onset_env = librosa.onset.onset_detect(y=y, sr=sr)
        tempo, _ = librosa.beat.beat_track(onset_env=onset_env, sr=sr)
        
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        key_mode = librosa.key_to_notes(librosa.feature.tonnetz(y=y, sr=sr).mean(axis=1))
        
        return round(tempo), key_mode[0] if key_mode else "N/A"
    except Exception as e:
        print(f"ERROR DE ANÁLISIS DE AUDIO: Falló el análisis de '{filepath}'. Mensaje: {e}")
        print("POSIBLE SOLUCIÓN: Asegúrate de que el archivo no está corrupto o es de un formato soportado por Librosa (MP3, WAV, FLAC).")
        return "N/A", "N/A"

def update_audio_metadata(filepath, title, artist, genre, bpm, key):
    """
    Actualiza los metadatos (ID3 tags) de un archivo MP3.
    Esta función solo actualiza el archivo LOCAL. El script no lo re-sube a Drive.
    """
    if not filepath or not filepath.lower().endswith('.mp3'):
        return

    try:
        audio = MP3(filepath, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()

        # Añadir o actualizar tags ID3 estándar
        audio.tags.add(TIT2(encoding=3, text=[title])) # Título
        audio.tags.add(TPE1(encoding=3, text=[artist])) # Artista
        audio.tags.add(TCON(encoding=3, text=[genre])) # Género

        # Usar TXXX (campo de texto personalizado) para BPM y Clave
        audio.tags.delall('TXXX') # Eliminar tags TXXX existentes para evitar duplicados
        audio.tags.add(TXXX(encoding=3, desc='BPM', text=[str(bpm)]))
        audio.tags.add(TXXX(encoding=3, desc='Key', text=[key]))
        
        audio.save()
        # print(f"Metadatos actualizados para {filepath} localmente.") # Comentado para minimizar output
    except ID3NoHeaderError:
        print(f"ADVERTENCIA: No se encontraron tags ID3 válidos en '{filepath}'. No se pudieron actualizar los metadatos.")
    except Exception as e:
        print(f"ERROR: Falló la actualización de metadatos de '{filepath}'. Mensaje: {e}")

def move_drive_file(drive_service, file_id, old_parent_id, new_parent_id):
    """Mueve un archivo de Google Drive de una carpeta a otra. Maneja errores de la API de Drive."""
    try:
        file_metadata = drive_service.files().get(fileId=file_id, fields='parents,name').execute()
        current_parents = file_metadata.get('parents', [])
        
        if old_parent_id not in current_parents:
            print(f"ADVERTENCIA: Archivo '{file_metadata.get('name', 'N/A')}' (ID: {file_id}) NO se encontró en la carpeta de origen '{old_parent_id}'.")
            print("POSIBLE SOLUCIÓN: El archivo ya fue movido manualmente, eliminado, o el ID de la carpeta de origen es incorrecto. No se intentará mover.")
            return False

        drive_service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=old_parent_id,
            fields='id, parents'
        ).execute()
        # print(f"Archivo {file_id} movido exitosamente en Google Drive.") # Comentado para minimizar output
        return True
    except Exception as e:
        print(f"ERROR: Falló el movimiento del archivo '{file_metadata.get('name', 'N/A')}' (ID: {file_id}) en Google Drive. Mensaje: {e}")
        print("POSIBLE SOLUCIÓN: Problema de permisos de la cuenta de servicio en la carpeta de destino, ID de carpeta incorrecto, o error temporal de Google Drive.")
        return False

def main():
    print("\n--- INICIANDO PROCESO DE ORGANIZACIÓN DE BEATS ---")
    gc, drive_service, creds = authenticate_google()
    if gc is None: 
        print("SCRIPT DETENIDO: No se pudo autenticar con Google.")
        return

    worksheet, records, headers = get_sheet_data(gc, SPREADSHEET_ID, WORKSHEET_NAME)
    if worksheet is None: 
        print("SCRIPT DETENIDO: No se pudo acceder a la hoja de cálculo.")
        return
    
    # Verificar que las columnas requeridas existan en la hoja
    required_cols = ['Nombre del Archivo Original', 'Género', 'Ruta en Drive (ID)', 'Enlace de Google Drive', 'BPM', 'Clave Armónica', 'Estado (PENDIENTE/ORGANIZADO)']
    if not all(col in headers for col in required_cols):
        print("ERROR CRÍTICO: Faltan una o más columnas requeridas en tu Google Sheet o los nombres no coinciden.")
        print("VERIFICAR: La PRIMERA FILA de tu Google Sheet debe tener estas columnas (nombres EXACTOS, incluyendo mayúsculas/minúsculas y espacios):")
        for col in required_cols:
            print(f"- '{col}'")
        print("SCRIPT DETENIDO: Por favor, corrige los nombres de las columnas en tu Google Sheet.")
        return

    print("\n--- Paso 1: Actualizando Catálogo de Beats en Google Sheet ---")
    
    drive_files_in_new_folder = get_drive_file_info(drive_service, NUEVOS_BEATS_FOLDER_ID)
    if not drive_files_in_new_folder and drive_files_in_new_folder != {}: # Si hubo un error en get_drive_file_info y no es un diccionario vacío
        print("SCRIPT DETENIDO: No se pudo obtener información de archivos en la carpeta 'Nuevos Beats'.")
        return

    existing_sheet_names = {rec.get('Nombre del Archivo Original') for rec in records if rec.get('Nombre del Archivo Original')} # Filtrar None o vacíos

    new_beats_added_to_sheet = 0
    for file_name, info in drive_files_in_new_folder.items():
        if file_name not in existing_sheet_names:
            row_data = {
                'Nombre del Archivo Original': file_name, 
                'Género': '', 
                'Ruta en Drive (ID)': info['id'],
                'Enlace de Google Drive': f"https://drive.google.com/file/d/{info['id']}/view",
                'BPM': '', 
                'Clave Armónica': '', 
                'Estado (PENDIENTE/ORGANIZADO)': 'PENDIENTE_ANALISIS_Y_MOVIMIENTO'
            }
            # Asegurar que el orden de los datos coincida con los headers para append_row
            new_row_values = [row_data.get(header, '') for header in headers]
            try:
                worksheet.append_row(new_row_values)
                records.append(row_data) # Actualizar records localmente
                new_beats_added_to_sheet += 1
                print(f" -> Añadido a la hoja: {file_name}")
            except Exception as e:
                print(f"ERROR: No se pudo añadir la fila para '{file_name}' a la hoja. Mensaje: {e}")
                print("POSIBLE SOLUCIÓN: Problema de escritura en Google Sheet o cuota API.")

    if new_beats_added_to_sheet > 0:
        print(f"\n--- Se han añadido {new_beats_added_to_sheet} nuevos beats a la hoja. ---")
        print("ACCIÓN REQUERIDA: Abre tu Google Sheet y ASIGNA UN GÉNERO a los beats con estado 'PENDIENTE_ANALISIS_Y_MOVIMIENTO' o 'ANALIZADO_PENDIENTE_GENERO' (columna 'Género').")
        # Refrescar los records y headers después de añadir nuevas filas para asegurar que las referencias sean correctas
        worksheet, records, headers = get_sheet_data(gc, SPREADSHEET_ID, WORKSHEET_NAME)
        if worksheet is None: 
            print("SCRIPT DETENIDO: Falló la recarga de datos de la hoja después de añadir nuevos beats.")
            return

    print("\n--- Paso 2: Analizando y Moviendo Beats ---")
    processed_count = 0
    for i, record in enumerate(records):
        row_num = i + 2 # Fila en la hoja de cálculo (1-based)
        
        file_name = record.get('Nombre del Archivo Original')
        drive_file_id = record.get('Ruta en Drive (ID)')
        genre = record.get('Género', '').strip()
        status = record.get('Estado (PENDIENTE/ORGANIZADO)')

        if not file_name or not drive_file_id:
            # print(f"Saltando fila {row_num}: faltan Nombre del Archivo Original o Ruta en Drive (ID).") # Comentado para minimizar output
            continue # Saltar filas incompletas

        if (status == 'PENDIENTE_ANALISIS_Y_MOVIMIENTO' or (not record.get('BPM') or not record.get('Clave Armónica')) or \
           status == 'ERROR_DESCARGA' or status == 'ERROR_ANALISIS') and status != 'ORGANIZADO':
            if status == 'ORGANIZADO': continue # No re-analizar si ya está organizado

            print(f" -> Analizando beat: {file_name}...")
            local_filepath = None
            try:
                local_filepath = download_file(drive_service, drive_file_id, file_name, DOWNLOAD_TEMP_DIR)
                if local_filepath:
                    bpm, key = analyze_audio(local_filepath)
                    update_sheet_row(worksheet, row_num, 'BPM', bpm, headers)
                    update_sheet_row(worksheet, row_num, 'Clave Armónica', key, headers)
                    print(f"    - Análisis completado: BPM={bpm}, Clave={key}")
                    if not genre: # Si el género aún no ha sido asignado por el usuario
                        update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ANALIZADO_PENDIENTE_GENERO', headers)
                    else: # Si el género ya fue asignado (quizás en una ejecución previa o manualmente)
                        update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'PENDIENTE_MOVIMIENTO', headers)
                else: # Falló la descarga
                    update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_DESCARGA', headers)
            except Exception as e:
                print(f"    - ERROR FATAL al analizar/descargar '{file_name}'. Mensaje: {e}")
                update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_ANALISIS', headers)
            finally:
                if local_filepath and os.path.exists(local_filepath):
                    try: os.remove(local_filepath) # Limpiar archivo temporal
                    except OSError as e: print(f"ADVERTENCIA: No se pudo eliminar archivo temporal '{local_filepath}'. Mensaje: {e}")
            continue # Continuar al siguiente beat o esperar la próxima ejecución si este necesita género manual

        # --- Sub-Paso: Movimiento del Archivo (si es necesario) ---
        if genre and (status == 'ANALIZADO_PENDIENTE_GENERO' or status == 'PENDIENTE_MOVIMIENTO' or \
                      status == 'ERROR_MOVIMIENTO' or status == 'ERROR_MOVIMIENTO_CARPETA' or status == 'ERROR_GENERAL_MOVIMIENTO'):
            if status == 'ORGANIZADO': continue # No mover si ya está organizado

            print(f" -> Moviendo beat: {file_name} (Género: {genre})...")
            try:
                # Buscar o crear la carpeta de género de destino en Drive
                query_folder = f"name = '{genre}' and mimeType = 'application/vnd.google-apps.folder' and '{ORGANIZED_BEATS_PARENT_FOLDER_ID}' in parents and trashed = false"
                results_folder = drive_service.files().list(q=query_folder, fields="files(id, name)").execute()
                items_folder = results_folder.get('files', [])

                target_genre_folder_id = None
                if items_folder:
                    target_genre_folder_id = items_folder[0]['id']
                else:
                    # Si no existe, crea la carpeta de género
                    file_metadata = {'name': genre, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [ORGANIZED_BEATS_PARENT_FOLDER_ID]}
                    new_folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                    target_genre_folder_id = new_folder.get('id')
                    print(f"    - Carpeta de género '{genre}' creada en Drive con ID: {target_genre_folder_id}.")
                
                if target_genre_folder_id:
                    success = move_drive_file(drive_service, drive_file_id, NUEVOS_BEATS_FOLDER_ID, target_genre_folder_id)
                    if success:
                        update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ORGANIZADO', headers)
                        print(f"    - Movido exitosamente a '{genre}' en Drive.")
                        processed_count += 1
                    else: # Falló el movimiento (posiblemente ya no está en la carpeta origen)
                        update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_MOVIMIENTO', headers)
                else: # No se pudo obtener o crear la carpeta de género
                    update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_MOVIMIENTO_CARPETA', headers)
            except Exception as e:
                print(f"    - ERROR FATAL al mover '{file_name}'. Mensaje: {e}")
                update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_GENERAL_MOVIMIENTO', headers)
        elif status == 'ORGANIZADO':
            pass # Beat ya organizado, no hacer nada
        else:
            # print(f"Beat {file_name} en estado '{status}'. Saltando por ahora.") # Comentado para minimizar output
            pass

    print(f"\n--- Proceso Completado. Beats procesados en esta ejecución: {processed_count} ---")
    print("VERIFICAR: Revisa la terminal para ver si hubo errores y tu Google Sheet para el estado de los beats.")

if __name__ == "__main__":
    main()