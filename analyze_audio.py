 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/analyze_audio.py
index 0000000000000000000000000000000000000000..11fe049dfc8c7bfafb2ff1a234eb5c39b5c827b6 100755
--- a//dev/null
+++ b/analyze_audio.py
@@ -0,0 +1,55 @@
+#!/usr/bin/env python3
+"""Analiza archivos WAV usando librosa y exporta resultados a CSV."""
+
+import argparse
+import hashlib
+import os
+import librosa
+import pandas as pd
+
+
+def analyze(directory: str) -> pd.DataFrame:
+    rows = []
+    seen = {}
+    for root, _, files in os.walk(directory):
+        for name in files:
+            if not name.lower().endswith('.wav'):
+                continue
+            path = os.path.join(root, name)
+            try:
+                y, sr = librosa.load(path, sr=None, mono=True)
+                duration = librosa.get_duration(y=y, sr=sr)
+                centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
+            except Exception as exc:
+                print(f'Skipping {path}: {exc}')
+                continue
+            with open(path, 'rb') as fh:
+                md5 = hashlib.md5(fh.read()).hexdigest()
+            duplicate_of = seen.get(md5)
+            if duplicate_of is None:
+                seen[md5] = path
+            rows.append(
+                {
+                    'file': path,
+                    'duration': duration,
+                    'sr': sr,
+                    'md5': md5,
+                    'duplicate_of': duplicate_of,
+                    'spectral_centroid': centroid,
+                }
+            )
+    return pd.DataFrame(rows)
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(description='Analiza archivos WAV')
+    parser.add_argument('directory', help='Directorio que contiene los WAV')
+    parser.add_argument('-o', '--output', default='analysis.csv', help='Archivo CSV de salida')
+    args = parser.parse_args()
+    df = analyze(args.directory)
+    df.to_csv(args.output, index=False)
+    print(f'Resultados guardados en {args.output}')
+
+
+if __name__ == '__main__':
+    main()
 
EOF
)
