# --- CONFIGURACIÓN: ¡ESTOS VALORES YA ESTÁN ACTUALIZADOS CON TUS IDs Y EL NOMBRE DE ARCHIVO JSON FINAL! ---
# Ruta al archivo JSON que descargaste de Google Cloud
# ¡ESTE ES EL NOMBRE Y RUTA EXACTA PARA TU ARCHIVO JSON BASADO EN TUS CAPTURAS DE PANTALLA!
SERVICE_ACCOUNT_FILE = 'braided-grammar-465202-t4-7894b7df3cb4.json'

# Alcances (permisos) que tu robot necesita
SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

# ID de tu Google Sheet 'Catálogo de Beats'
SPREADSHEET_ID = '19KvhoVYV0XIRZ3FfFTwBRPXjNSMyeAkFYUFl6I1kUEQ'
WORKSHEET_NAME = 'Hoja 1' # Si cambiaste el nombre de la hoja en tu Google Sheet (la pestaña de abajo), actualízalo aquí (ej. 'Catalogo')

# ID de tu carpeta 'Nuevos Beats' en Google Drive
NUEVOS_BEATS_FOLDER_ID = '1fwLKWkWvn8TY6SSL7kQgaVtZ5olZFuyw'

# ID de tu carpeta 'Beats organizados por género' en Google Drive
ORGANIZED_BEATS_PARENT_FOLDER_ID = '1nILKS4_YglgyLRuA_X6107N6ThMbsB8o'

# Carpeta temporal en tu computadora para descargar y procesar beats
DOWNLOAD_TEMP_DIR = 'temp_beats_processing'
if not os.path.exists(DOWNLOAD_TEMP_DIR):
    os.makedirs(DOWNLOAD_TEMP_DIR)

# --- FIN DE CONFIGURACIÓN ---

def authenticate_google():
    """
    Autentica con Google usando la cuenta de servicio.
    Verifica que el archivo de credenciales exista.
    """
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR: El archivo de credenciales '{SERVICE_ACCOUNT_FILE}' no se encontró.")
        print("VERIFICAR: Asegúrate de que el nombre del archivo es correcto y está en la misma carpeta que el script,")
        print("o que la ruta completa es la correcta si está en otra ubicación.")
        return None, None, None # Devolver None para indicar que la autenticación falló

    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPE)
        gc = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return gc, drive_service, creds
    except Exception as e:
        print(f"ERROR: Falló la autenticación con Google. Mensaje: {e}")
        print("VERIFICAR: Asegúrate de que el archivo JSON no esté corrupto y que la cuenta de servicio tiene los permisos correctos en Google Cloud y en las carpetas/hoja de Drive.")
        return None, None, None

def get_sheet_data(gc, spreadsheet_id, worksheet_name):
    """Obtiene todos los datos de la hoja de cálculo."""
    try:
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        return worksheet, worksheet.get_all_records(), worksheet.row_values(1)
    except Exception as e:
        print(f"ERROR: No se pudo acceder a la hoja de cálculo. Mensaje: {e}")
        print(f"VERIFICAR: ID de la hoja '{spreadsheet_id}' es correcto, el nombre de la hoja ('{worksheet_name}') es correcto, y la cuenta de servicio tiene permisos de Editor en la hoja.")
        return None, None, None

def update_sheet_row(worksheet, row_index, column_name, new_value, headers):
    """Actualiza una celda específica en la hoja de cálculo."""
    try:
        col_index = headers.index(column_name) + 1
        worksheet.update_cell(row_index, col_index, new_value)
    except ValueError:
        print(f"ADVERTENCIA: Columna '{column_name}' no encontrada en la hoja. Por favor, verifica los nombres exactos de las columnas en tu Google Sheet (incluyendo mayúsculas/minúsculas y espacios).")
    except Exception as e:
        print(f"ERROR: No se pudo actualizar la celda en la fila {row_index}, columna {column_name}. Mensaje: {e}")

def get_drive_file_info(drive_service, folder_id):
    """Obtiene información de los archivos en una carpeta de Google Drive."""
    try:
        files_info = {}
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        items = results.get('files', [])
        for item in items:
            files_info[item['name']] = {'id': item['id'], 'mimeType': item['mimeType']}
        return files_info
    except Exception as e:
        print(f"ERROR: No se pudo acceder a la carpeta de Drive con ID '{folder_id}'. Mensaje: {e}")
        print("VERIFICAR: ID de la carpeta es correcto y la cuenta de servicio tiene permisos de Editor en esa carpeta.")
        return {}

def download_file(drive_service, file_id, file_name, destination_folder):
    """Descarga un archivo de Google Drive a una carpeta local."""
    filepath = os.path.join(destination_folder, file_name)
    try:
        request = drive_service.files().get_media(fileId=file_id)
        response = requests.get(request.url, headers={'Authorization': f'Bearer {drive_service.credentials.token}'}, stream=True)
        response.raise_for_status() # Lanza un error si la descarga falla
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: # filtrar keep-alive new chunks
                    f.write(chunk)
        return filepath
    except Exception as e:
        print(f"ERROR: Falló la descarga de '{file_name}' (ID: {file_id}). Mensaje: {e}")
        return None

def analyze_audio(filepath):
    """Analiza un archivo de audio para BPM y clave usando Librosa."""
    if not filepath: # Si el archivo no se pudo descargar, no intentes analizar
        return "N/A", "N/A"
    try:
        y, sr = librosa.load(filepath)
        
        onset_env = librosa.onset.onset_detect(y=y, sr=sr) # CORREGIDO
        tempo, _ = librosa.beat.beat_track(onset_env=onset_env, sr=sr)
        
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        key_mode = librosa.key_to_notes(librosa.feature.tonnetz(y=y, sr=sr).mean(axis=1))
        
        return round(tempo), key_mode[0] if key_mode else "N/A"
    except Exception as e:
        print(f"ERROR: Error al analizar audio '{filepath}'. Asegúrate de que el archivo no está corrupto o es de un formato soportado por Librosa. Mensaje: {e}")
        return "N/A", "N/A"

def update_audio_metadata(filepath, title, artist, genre, bpm, key):
    """Actualiza los metadatos (ID3 tags) de un archivo MP3."""
    if not filepath or not filepath.lower().endswith('.mp3'):
        # Este script no re-sube el archivo a Drive después de actualizar tags.
        # Por lo tanto, esta función es más una demostración de capacidad.
        return

    try:
        audio = MP3(filepath, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()

        audio.tags.add(TIT2(encoding=3, text=[title]))
        audio.tags.add(TPE1(encoding=3, text=[artist]))
        audio.tags.add(TCON(encoding=3, text=[genre]))

        audio.tags.delall('TXXX') 
        audio.tags.add(TXXX(encoding=3, desc='BPM', text=[str(bpm)]))
        audio.tags.add(TXXX(encoding=3, desc='Key', text=[key]))
        
        audio.save()
        # print(f"Metadatos actualizados para {filepath}") # Comentado para minimizar output
    except ID3NoHeaderError:
        pass
    except Exception as e:
        print(f"ERROR: Error al actualizar metadatos de {filepath}. Mensaje: {e}")

def move_drive_file(drive_service, file_id, old_parent_id, new_parent_id):
    """Mueve un archivo de Google Drive de una carpeta a otra."""
    try:
        file = drive_service.files().get(fileId=file_id, fields='parents').execute()
        current_parents = file.get('parents', [])
        
        if old_parent_id not in current_parents:
            print(f"ADVERTENCIA: Archivo {file_id} ('{file.get('name', 'N/A')}') no se encuentra en la carpeta de origen {old_parent_id}. Posiblemente ya movido o en otra ubicación. No se intentará mover.")
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
        print(f"ERROR: Falló el movimiento del archivo {file_id} en Google Drive. Mensaje: {e}")
        return False

def main():
    gc, drive_service, creds = authenticate_google()
    if gc is None: return

    worksheet, records, headers = get_sheet_data(gc, SPREADSHEET_ID, WORKSHEET_NAME)
    if worksheet is None: return
    
    required_cols = ['Nombre del Archivo Original', 'Género', 'Ruta en Drive (ID)', 'Enlace de Google Drive', 'BPM', 'Clave Armónica', 'Estado (PENDIENTE/ORGANIZADO)']
    if not all(col in headers for col in required_cols):
        print("ERROR: Faltan una o más columnas requeridas en tu Google Sheet o los nombres no coinciden.")
        print("VERIFICAR: Asegúrate de que tienes estas columnas (exactamente con estos nombres, incluyendo mayúsculas/minúsculas y espacios):")
        for col in required_cols:
            print(f"- {col}")
        print("El script no puede continuar.")
        return

    print("--- Proceso de Actualización de Catálogo y Análisis ---")
    
    drive_files_in_new_folder = get_drive_file_info(drive_service, NUEVOS_BEATS_FOLDER_ID)
    existing_sheet_names = {rec.get('Nombre del Archivo Original') for rec in records}

    new_beats_added_to_sheet = 0
    for file_name, info in drive_files_in_new_folder.items():
        if file_name not in existing_sheet_names:
            row_data = {
                'Nombre del Archivo Original': file_name, 'Género': '', 'Ruta en Drive (ID)': info['id'],
                'Enlace de Google Drive': f"https://drive.google.com/file/d/{info['id']}/view",
                'BPM': '', 'Clave Armónica': '', 'Estado (PENDIENTE/ORGANIZADO)': 'PENDIENTE_ANALISIS_Y_MOVIMIENTO'
            }
            new_row_values = [row_data.get(header, '') for header in headers]
            worksheet.append_row(new_row_values)
            records.append(row_data)
            new_beats_added_to_sheet += 1
            print(f"Añadido nuevo beat a hoja: {file_name}")

    if new_beats_added_to_sheet > 0:
        print(f"Se han añadido {new_beats_added_to_sheet} nuevos beats a la hoja.")
        print("ACCIÓN REQUERIDA: Asigna un género a los beats recién añadidos en tu Google Sheet (columna 'Género').")
        worksheet, records, headers = get_sheet_data(gc, SPREADSHEET_ID, WORKSHEET_NAME)
        if worksheet is None: return

    print("\n--- Proceso de Análisis y Organización de Beats ---")
    for i, record in enumerate(records):
        row_num = i + 2 
        file_name = record.get('Nombre del Archivo Original')
        drive_file_id = record.get('Ruta en Drive (ID)')
        genre = record.get('Género', '').strip()
        status = record.get('Estado (PENDIENTE/ORGANIZADO)')

        if not file_name or not drive_file_id:
            print(f"Saltando fila {row_num}: faltan nombre o ID.")
            continue

        if (status == 'PENDIENTE_ANALISIS_Y_MOVIMIENTO' or (not record.get('BPM') or not record.get('Clave Armónica'))
            or status == 'ERROR_DESCARGA' or status == 'ERROR_ANALISIS') and status != 'ORGANIZADO':
            print(f"Analizando: {file_name}...")
            local_filepath = None
            try:
                local_filepath = download_file(drive_service, drive_file_id, file_name, DOWNLOAD_TEMP_DIR)
                if local_filepath:
                    bpm, key = analyze_audio(local_filepath)
                    update_sheet_row(worksheet, row_num, 'BPM', bpm, headers)
                    update_sheet_row(worksheet, row_num, 'Clave Armónica', key, headers)
                    print(f"Analizado {file_name}: BPM={bpm}, Clave={key}")
                    if not genre:
                        update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ANALIZADO_PENDIENTE_GENERO', headers)
                    else:
                        update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'PENDIENTE_MOVIMIENTO', headers)
                else:
                    update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_DESCARGA', headers)
            except Exception as e:
                print(f"ERROR: Falló análisis de {file_name}. Mensaje: {e}")
                update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_ANALISIS', headers)
            finally:
                if local_filepath and os.path.exists(local_filepath): os.remove(local_filepath)
            continue

        if genre and (status == 'ANALIZADO_PENDIENTE_GENERO' or status == 'PENDIENTE_MOVIMIENTO' or \
                      status == 'ERROR_MOVIMIENTO' or status == 'ERROR_MOVIMIENTO_CARPETA'):
            print(f"Moviendo: {file_name} (Género: {genre})...")
            try:
                query_folder = f"name = '{genre}' and mimeType = 'application/vnd.google-apps.folder' and '{ORGANIZED_BEATS_PARENT_FOLDER_ID}' in parents and trashed = false"
                results_folder = drive_service.files().list(q=query_folder, fields="files(id, name)").execute()
                items_folder = results_folder.get('files', [])
                target_genre_folder_id = None
                if items_folder:
                    target_genre_folder_id = items_folder[0]['id']
                else:
                    file_metadata = {'name': genre, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [ORGANIZED_BEATS_PARENT_FOLDER_ID]}
                    new_folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                    target_genre_folder_id = new_folder.get('id')
                    print(f"Carpeta '{genre}' creada en Drive: {target_genre_folder_id}.")
                
                if target_genre_folder_id:
                    success = move_drive_file(drive_service, drive_file_id, NUEVOS_BEATS_FOLDER_ID, target_genre_folder_id)
                    if success:
                        update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ORGANIZADO', headers)
                    else:
                        update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_MOVIMIENTO', headers)
                else:
                    update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_MOVIMIENTO_CARPETA', headers)
            except Exception as e:
                print(f"ERROR: Falló movimiento de {file_name}. Mensaje: {e}")
                update_sheet_row(worksheet, row_num, 'Estado (PENDIENTE/ORGANIZADO)', 'ERROR_GENERAL_MOVIMIENTO', headers)
        elif status == 'ORGANIZADO':
            pass
        else:
            print(f"Beat {file_name} en estado '{status}'. Saltando por ahora.")

    print("\n--- Proceso Completado ---")

if __name__ == "__main__":
    main()