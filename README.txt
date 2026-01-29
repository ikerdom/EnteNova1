ORBE ERP - INSTRUCCIONES (SOLO CARPETA ENV)
==========================================

Este paquete contiene todo lo necesario para ejecutar el ERP desde ENV.

1) Preparar entorno (primera vez)
---------------------------------
- Ejecuta setup_env.bat.
- Si falta Python, el script lo indica con un enlace.
- Si falta configuracion, solicita el archivo .env a IT.

2) Arranque
-----------
- run_all.bat: backend (8000) + frontend (8501) en paralelo.
- run_backend.bat: solo backend.
- run_streamlit.bat: solo frontend.

3) Acceso
---------
- UI: http://localhost:8501
- API docs: http://localhost:8000/docs

4) Login
--------
- Usa tu correo corporativo.
- Los permisos se gestionan en el sistema central.

5) Puertos
----------
- Si hay conflicto, edita los .bat y cambia --port o --server.port.
