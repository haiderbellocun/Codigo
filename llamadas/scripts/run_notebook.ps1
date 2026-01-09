\
# Ejecutar notebook desde PowerShell (sin abrir Jupyter)
# Requiere: jupyter instalado (pip install jupyter)
# Opcional: archivo .env cargado manualmente (PowerShell no carga .env por defecto)

python -m pip install -U jupyter

jupyter nbconvert --to notebook --execute ^
  --ExecutePreprocessor.timeout=7200 ^
  --output executed_llamadas.ipynb ^
  llamadas.ipynb
