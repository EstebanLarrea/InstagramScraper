# Instagram Scraper con Playwright 

Este es un proyecto didáctico desarrollado en Python para extraer información pública de perfiles de Instagram de forma automatizada, evadiendo los bloqueos y sistemas antibot de Meta.

##  Características

- **Evasión de Bloqueos:** Utiliza la inyección directa de cookies de sesión mediante contextos de navegador (`Browser Contexts`) para saltarse los formularios de inicio de sesión y simular una sesión legítima.
- **Análisis Profundo de Publicaciones:** Navega individualmente a las últimas 25 publicaciones para extraer el conteo de likes, comentarios de terceros y descripciones exactas extrayendo metadatos ocultos (`og:description`).
- **Limpieza de Datos (Regex):** Implementa expresiones regulares para filtrar y destruir ruido de la interfaz de usuario de React (fechas, botones, traducciones), conservando únicamente lenguaje humano útil para modelos de NLP.
- **Extracción Estructurada:** Obtiene métricas precisas del perfil principal y gestiona ventanas modales dinámicas para capturar muestras de seguidores y seguidos.
- **Exportación Segura:** Genera un archivo `datos_perfil.json` altamente estructurado y listo para ser consumido por microservicios o APIs de inteligencia artificial.

### Tecnologías Utilizadas

- **Python 3.x**
- **Playwright** (Motor Chromium y manipulación del Virtual DOM)
- **python-dotenv** (Gestión de seguridad y credenciales)


## Instalación y Configuración

Sigue estos pasos para ejecutar el proyecto en cualquier entorno local:

1. **Clonar el repositorio**
```bash
git clone [https://github.com/TU-USUARIO/TU-REPOSITORIO.git](https://github.com/TU-USUARIO/TU-REPOSITORIO.git)
cd TU-REPOSITORIO
```

```bash
pip install -r requirements.txt
```

**3. Instalar los binarios del navegador (Obligatorio)**
Playwright necesita descargar su propio motor interno de Chromium:
```bash
playwright install chromium
```

**4. Configurar Credenciales (Seguridad)**
Por directrices de seguridad, las credenciales jamás se suben al repositorio. Debes crear un archivo llamado .env en la raíz del proyecto.

Usa las herramientas de desarrollador de tu navegador (F12 > Application > Cookies) en una cuenta descartable de Instagram y pega los 5 valores esenciales en el archivo .env con esta estructura exacta:

```bash
IG_SESSION_ID="TU_SESSION_ID_AQUI"
IG_CSRF_TOKEN="TU_CSRF_TOKEN_AQUI"
IG_DS_USER_ID="TU_USER_ID_AQUI"
IG_DID="TU_IG_DID_AQUI"
IG_MID="TU_MID_AQUI"
```
>  **Advertencia:** Asegúrate de que el archivo .env esté incluido en tu .gitignore. No utilices tu cuenta personal principal de Instagram para ejecutar flujos de automatización.



##  Uso

Una vez configurado el archivo de cookies, ejecuta el script principal:

```bash
python scraper.py
```

El navegador se abrirá automáticamente, navegará al perfil objetivo, extraerá la información simulando el comportamiento humano, y finalmente generará el archivo `datos_perfil.json` con los resultados.

![Captura de pantalla 2026-10-16 110454.png](../../Pictures/Screenshots/Captura%20de%20pantalla%202026-10-16%20110454.png)



##  Propósito
Proyecto desarrollado con fines netamente académicos y didácticos para la comprensión de arquitecturas web modernas (SPA/React), automatización de navegadores mediante WebSockets y extracción de datos.