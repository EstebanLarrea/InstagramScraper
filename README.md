# Instagram Scraper con Playwright y Análisis Big Five con Gemini

Este es un proyecto didáctico desarrollado en Python para extraer información pública de perfiles de Instagram de forma automatizada, evadiendo los bloqueos y sistemas antibot de Meta, y para estimar el perfil de personalidad **Big Five** de la persona mediante la **API de Gemini**.

## Características

- **Evasión de Bloqueos:** Utiliza la inyección directa de cookies de sesión mediante contextos de navegador (`Browser Contexts`) para saltarse los formularios de inicio de sesión y simular una sesión legítima.
- **Análisis Profundo de Publicaciones:** Navega individualmente a las últimas 25 publicaciones para extraer el conteo de likes, comentarios de terceros y descripciones exactas extrayendo metadatos ocultos (`og:description`).
- **Limpieza de Datos (Regex):** Implementa expresiones regulares para filtrar y destruir ruido de la interfaz de usuario de React (fechas, botones, traducciones), conservando únicamente lenguaje humano útil para modelos de NLP.
- **Extracción Estructurada:** Obtiene métricas precisas del perfil principal y gestiona ventanas modales dinámicas para capturar muestras de seguidores y seguidos.
- **Exportación Segura:** Genera un archivo `datos_perfil.json` altamente estructurado y listo para ser consumido por microservicios o APIs de inteligencia artificial.
- **Estimación Big Five con IA:** Envía los datos recolectados a la API de Gemini y obtiene, en formato JSON, la puntuación (0 a 100), el nivel, la confianza, la justificación y las evidencias de cada uno de los cinco rasgos (apertura, responsabilidad, extraversión, amabilidad y neuroticismo).
- **Salida Estructurada y Validada:** El esquema de la respuesta se define con `pydantic` y se le exige a Gemini (`response_schema`); luego se valida antes de guardarla en `big_five.json`.

### Tecnologías Utilizadas

- **Python 3.x**
- **Playwright** (Motor Chromium y manipulación del Virtual DOM)
- **python-dotenv** (Gestión de seguridad y credenciales)
- **google-genai** (SDK oficial para consumir la API de Gemini)
- **pydantic** (Definición y validación del esquema de la respuesta)
- **Gemini** (modelo `gemini-3.8-flash` por defecto, configurable)

## Instalación y Configuración

Sigue estos pasos para ejecutar el proyecto en cualquier entorno local:

**1. Clonar el repositorio**
```bash
git clone https://github.com/TU-USUARIO/TU-REPOSITORIO.git
cd TU-REPOSITORIO
```

**2. Instalar las dependencias**
```bash
pip install -r requirements.txt
```

Asegúrate de que `requirements.txt` incluya, como mínimo:
```text
playwright
python-dotenv
google-genai
pydantic
```

**3. Instalar los binarios del navegador (Obligatorio)**
Playwright necesita descargar su propio motor interno de Chromium:
```bash
playwright install chromium
```

**4. Configurar Credenciales (Seguridad)**
Por directrices de seguridad, las credenciales jamás se suben al repositorio. Debes crear un archivo llamado `.env` en la raíz del proyecto.

Usa las herramientas de desarrollador de tu navegador (F12 > Application > Cookies) en una cuenta descartable de Instagram y pega los 5 valores esenciales en el archivo `.env`. Además, agrega tu clave de la API de Gemini (ver el paso 5), con esta estructura exacta:

```bash
IG_SESSION_ID="TU_SESSION_ID_AQUI"
IG_CSRF_TOKEN="TU_CSRF_TOKEN_AQUI"
IG_DS_USER_ID="TU_USER_ID_AQUI"
IG_DID="TU_IG_DID_AQUI"
IG_MID="TU_MID_AQUI"
GEMINI_API_KEY="TU_API_KEY_DE_GEMINI_AQUI"
```

> **Importante:** cada línea usa el signo igual (`=`), no dos puntos. Si escribes `GEMINI_API_KEY:"..."`, el programa no encontrará la clave.

> **Advertencia:** Asegúrate de que el archivo `.env` esté incluido en tu `.gitignore`. No utilices tu cuenta personal principal de Instagram para ejecutar flujos de automatización.

**5. Obtener la clave de la API de Gemini**
1. Entra a [Google AI Studio](https://aistudio.google.com/apikey) con tu cuenta de Google.
2. Crea una clave de API.
3. Pégala en el `.env` como `GEMINI_API_KEY`.

Opcionalmente, puedes elegir otro modelo agregando esta línea al `.env`:
```bash
GEMINI_MODEL="nombre-del-modelo"
```

## Uso

Una vez configurado el archivo `.env`, ejecuta el script principal:

```bash
python scraper.py
```

El navegador se abrirá automáticamente, navegará al perfil objetivo y extraerá la información simulando el comportamiento humano. Al terminar, generará el archivo `datos_perfil.json` y, a continuación, enviará los datos a Gemini para generar el archivo `big_five.json` con la estimación de personalidad. En la consola verás cada rasgo con su puntuación, nivel y confianza, junto con un resumen.

![Captura de pantalla 2026-10-16 110454.png](../../Pictures/Screenshots/Captura%20de%20pantalla%202026-10-16%20110454.png)

## Análisis Big Five con la API de Gemini

### Cómo funciona

El programa se divide en dos etapas comunicadas por un archivo JSON:

1. **Scraper (Playwright):** guarda `datos_perfil.json`.
2. **Análisis (Gemini):** lee esos datos, los reduce a lo necesario, los inserta en un prompt y llama a la API.

La función `preparar_datos` conserva solo la biografía y, de cada publicación, la descripción, los likes, el total de comentarios y los comentarios. Se excluyen las URL y el nombre real, y, por defecto, los usuarios de seguidores y seguidos, porque son datos de terceros.

El prompt le indica a Gemini que actúe como analista de personalidad, que base cada puntuación **solo en evidencia** de los datos, que indique su **nivel de confianza**, que no haga diagnósticos clínicos y que aclare que es una estimación.

La llamada a la API se hace con el SDK `google-genai`:

```python
client = genai.Client(api_key=api_key)
respuesta = client.models.generate_content(
    model=MODELO,
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=InformeBigFive,
        temperature=0.3,
    ),
)
```

| Parámetro | Función |
|---|---|
| `model` | Modelo de Gemini que procesa la solicitud (`gemini-3.8-flash` por defecto). |
| `contents` | Prompt con las reglas y los datos del perfil. |
| `response_mime_type` | Pide que la respuesta sea JSON. |
| `response_schema` | Esquema de `pydantic` que la respuesta debe seguir. |
| `temperature` | Controla la aleatoriedad; `0.3` da respuestas más consistentes. |

La respuesta se valida con `pydantic`. Si no cumple el esquema, no se pierde: se guarda el texto recibido en el campo `respuesta_cruda`.

### Estructura de `big_five.json`

```json
{
  "rasgos": [
    {
      "rasgo": "Apertura a la experiencia",
      "puntuacion": 0,
      "nivel": "bajo | medio | alto",
      "confianza": "baja | media | alta",
      "justificacion": "...",
      "evidencias": ["..."]
    }
  ],
  "resumen": "...",
  "limitaciones": "..."
}
```

El campo `rasgo` toma uno de estos cinco valores: `Apertura a la experiencia`, `Responsabilidad`, `Extraversión`, `Amabilidad` y `Neuroticismo`.

### Opciones de configuración

Al inicio de `scraper.py` hay constantes que puedes ajustar:

| Constante | Descripción |
|---|---|
| `MODELO` | Modelo de Gemini. Se lee de `GEMINI_MODEL` en el `.env`; si no existe, usa `gemini-3.8-flash`. |
| `INCLUIR_CONTACTOS` | Si es `True`, también envía a Gemini los usuarios de seguidores y seguidos. Por defecto es `False`. |
| `USAR_DATOS_GUARDADOS` | Si es `True`, omite el scraping y usa el `datos_perfil.json` ya existente. Útil para probar solo la parte de Gemini. |
| `ARCHIVO_DATOS` / `ARCHIVO_BIG_FIVE` | Nombres de los archivos de entrada y salida. |

### Errores comunes

| Error | Causa probable | Solución |
|---|---|---|
| `no se encontró GEMINI_API_KEY` | La variable está mal escrita en el `.env` (por ejemplo, con `:` en lugar de `=`). | Usa el formato `GEMINI_API_KEY="tu_clave"`. |
| `404 NOT_FOUND` del modelo | El modelo ya no está disponible para cuentas nuevas o cambió de nombre. | Pon un modelo vigente en `GEMINI_MODEL` (consulta Google AI Studio). |
| `503 UNAVAILABLE` | El modelo tiene alta demanda de forma temporal. | Espera unos minutos y vuelve a ejecutar. Con `USAR_DATOS_GUARDADOS = True` no repites el scraping. |

### Alcance y límites del resultado

- Es una **estimación aproximada** hecha por un modelo de lenguaje a partir de contenido público; **no es un test psicométrico** ni un diagnóstico.
- Con pocos datos, algunos rasgos tendrán confianza baja.
- Úsalo únicamente con el **consentimiento de la persona** analizada y no tomes decisiones sobre ella a partir del resultado.

## Seguridad

- Nunca subas el archivo `.env` al repositorio: contiene cookies de sesión de Instagram y tu clave de Gemini.
- Si una clave o cookie se expone, revócala: elimina la clave en Google AI Studio y cierra sesión en Instagram para invalidar las cookies.

## Propósito
Proyecto desarrollado con fines netamente académicos y didácticos para la comprensión de arquitecturas web modernas (SPA/React), automatización de navegadores mediante WebSockets, extracción de datos y consumo de APIs de inteligencia artificial generativa con salida estructurada.