 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/README.md b/README.md
index c235dc1648aefd654168bc2462a6736516239ecf..82d96cf94586e81ae6a751ee87a574d56fd006b5 100644
--- a/README.md
+++ b/README.md
@@ -1,20 +1,73 @@
-# WavFinder Landing Page
+# WavFinder
 
-This simple static page now includes optional Stripe Checkout integration using a minimal Node.js server.
+WavFinder es una página estática con un pequeño servidor Node.js para gestionar pagos con Stripe y una utilidad en Python para analizar archivos de audio.
 
-## Development
+## Requisitos
 
-1. Install dependencies:
-   ```bash
-   npm install express stripe
-   ```
+- Node.js 18 o superior
+- Python 3.10 o superior
 
-2. Set your Stripe secret key in the environment before starting the server:
-   ```bash
-   export STRIPE_SECRET_KEY=sk_test_...
-   node server.js
-   ```
+## Instalación
 
-3. Open `http://localhost:4242` in your browser.
+1. Instala las dependencias de Node.js:
 
-Each purchase button has a `data-price-id` attribute which should match a Price ID from your Stripe dashboard.
+```bash
+npm install
+```
+
+2. Instala las dependencias de Python:
+
+```bash
+pip install -r requirements.txt
+```
+
+3. Copia `config.example.env` a `.env` y establece tu clave de Stripe:
+
+```bash
+cp config.example.env .env
+# Edita .env y define STRIPE_SECRET_KEY
+```
+
+### Configuración de Stripe
+
+Asegúrate de definir `STRIPE_SECRET_KEY` en tu archivo `.env`. Los botones de
+compra de `Index.html` contienen atributos `data-price-id` con los Price IDs de
+tus productos en Stripe. Puedes editar esos valores en el HTML para que
+coincidan con los precios configurados en tu cuenta.
+
+## Uso del servidor
+
+Inicia el servidor de desarrollo:
+
+```bash
+npm start
+```
+
+Abre <http://localhost:4242> en tu navegador. Los botones de compra incluyen un atributo `data-price-id` que debe coincidir con un Price ID de tu panel de Stripe.
+
+## Análisis de audio con Librosa
+
+La utilidad `analyze_audio.py` analiza todos los archivos `.wav` de un directorio y genera un archivo `analysis.csv` con la siguiente información:
+
+- `file`: ruta completa del archivo
+- `duration`: duración en segundos
+- `sr`: frecuencia de muestreo
+- `md5`: hash del contenido
+- `duplicate_of`: si existe, indica qué archivo tiene el mismo hash
+- `spectral_centroid`: media del centroide espectral
+
+Puedes ejecutarla así:
+
+```bash
+python analyze_audio.py <directorio> -o analysis.csv
+```
+
+El CSV resultante se puede abrir en cualquier hoja de cálculo para revisar los duplicados y las características de cada archivo.
+
+## Configuración
+
+Los valores de configuración se cargan desde variables de entorno definidas en `.env`. No incluyas este archivo en el control de versiones. Consulta `config.example.env` para ver un ejemplo.
+
+## Licencia
+
+MIT
 
EOF
)
