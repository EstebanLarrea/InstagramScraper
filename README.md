# Instagram Scraper con Playwright, Ley de Benford y Análisis Big Five con Gemini

Este es un proyecto didáctico desarrollado en Python para extraer información pública de perfiles de Instagram de forma automatizada, evadiendo los bloqueos y sistemas antibot de Meta. Además, analiza la red de seguidores del perfil con la **Ley de Benford** para detectar si es orgánica o anómala (posible bot) y, si resulta orgánica, estima el perfil de personalidad **Big Five** de la persona mediante la **API de Gemini**.

## Características

- **Evasión de Bloqueos:** Utiliza la inyección directa de cookies de sesión mediante contextos de navegador (`Browser Contexts`) para saltarse los formularios de inicio de sesión y simular una sesión legítima.
- **Análisis Profundo de Publicaciones:** Navega individualmente a las últimas 25 publicaciones para extraer el conteo de likes, comentarios de terceros y descripciones exactas extrayendo metadatos ocultos (`og:description`).
- **Limpieza de Datos (Regex):** Implementa expresiones regulares para filtrar y destruir ruido de la interfaz de usuario de React (fechas, botones, traducciones), conservando únicamente lenguaje humano útil para modelos de NLP.
- **Extracción Estructurada:** Obtiene métricas precisas del perfil principal y gestiona ventanas modales dinámicas para capturar muestras de seguidores y seguidos.
- **Extracción por Hover:** Pasa el mouse sobre hasta 200 seguidores del perfil y lee su número de seguidores desde la vista previa flotante, sin abrir el perfil de cada uno.
- **Detección de Redes Anómalas (Ley de Benford):** Cuenta el primer dígito de las cifras obtenidas, lo compara con la distribución de Benford mediante una prueba chi-cuadrada y clasifica el perfil como `HUMANO ORGÁNICO` o `BOT / ANÓMALO`. Genera una tabla CSV y una gráfica.
- **Decisión Previa al Análisis con IA:** El análisis Big Five solo se ejecuta si el perfil resulta orgánico, para no gastar llamadas al modelo en cuentas con una red artificial.
- **Estimación Big Five con IA:** Envía los datos recolectados a la API de Gemini y obtiene, en formato JSON, la puntuación (0 a 100), el nivel, la confianza, la justificación y las evidencias de cada uno de los cinco rasgos (apertura, responsabilidad, extraversión, amabilidad y neuroticismo).
- **Salida Estructurada y Validada:** El esquema de la respuesta se define con `pydantic` y se le exige a Gemini (`response_schema`); luego se valida antes de guardarla en `big_five.json`.
- **Exportación Segura:** Genera un archivo `datos_perfil.json` altamente estructurado y listo para ser consumido por microservicios o APIs de inteligencia artificial.

### Tecnologías Utilizadas

- **Python 3.x**
- **Playwright** (Motor Chromium y manipulación del Virtual DOM)
- **python-dotenv** (Gestión de seguridad y credenciales)
- **SciPy** (`scipy.stats.chisquare` para la prueba chi-cuadrada)
- **NumPy**, **pandas** y **Matplotlib** (tabla CSV y gráfica de Benford)
- **google-genai** (SDK oficial para consumir la API de Gemini)
- **pydantic** (Definición y validación del esquema de la respuesta)
- **Gemini** (modelo `gemini-3.8-flash`)

## Estructura del Proyecto

```text
.
├── scraper.py            # Recolección (Playwright), orquestación y análisis Big Five
├── benford_analisis.py   # Ley de Benford, chi-cuadrada, CSV y gráfica
├── requirements.txt
├── .env                  # Credenciales (no se sube al repositorio)
└── .gitignore
```

`benford_analisis.py` debe estar en la misma carpeta que `scraper.py`, porque este lo importa.

Archivos que genera el programa:

| Archivo | Contenido |
|---|---|
| `datos_perfil.json` | Biografía, muestra de contactos, cifras obtenidas por hover y datos de las publicaciones. |
| `benford_<usuario>.csv` | Frecuencias reales y esperadas de cada primer dígito. |
| `benford_<usuario>.png` | Gráfica con las barras reales y la curva teórica de Benford. |
| `big_five.json` | Estimación Big Five (solo si el perfil resulta orgánico). |

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
scipy
numpy
pandas
matplotlib
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

## Uso

Una vez configurado el archivo `.env`, ejecuta el script principal:

```bash
python scraper.py
```

El navegador se abrirá automáticamente, navegará al perfil objetivo y extraerá la información simulando el comportamiento humano. El programa trabaja en tres fases:

1. **Recolección:** extrae la biografía, una muestra de contactos, las cifras de seguidores por hover y los datos de las publicaciones, y guarda `datos_perfil.json`.
2. **Ley de Benford:** analiza las cifras obtenidas por hover, genera el CSV y la gráfica y muestra el diagnóstico.
3. **Decisión:** según el diagnóstico, se ejecuta o no el análisis Big Five.

| Resultado de Benford | Acción del programa |
|---|---|
| `HUMANO ORGÁNICO` | Llama a Gemini y genera `big_five.json`. |
| `BOT / ANÓMALO` | Muestra una alerta y cancela el análisis Big Five. |
| Sin cifras extraídas por hover | Lo informa y ejecuta directamente el análisis Big Five. |

En la consola verás el avance, el diagnóstico de Benford y, si corresponde, cada rasgo Big Five con su puntuación, nivel y confianza, junto con un resumen.

![Captura de pantalla 2026-10-16 110454.png](../../Pictures/Screenshots/Captura%20de%20pantalla%202026-10-16%20110454.png)

## Detección de Redes Anómalas con la Ley de Benford

### Qué es

La Ley de Benford establece que, en muchos conjuntos de datos reales que abarcan varios órdenes de magnitud, el primer dígito no se distribuye de forma uniforme: el 1 aparece cerca del 30 % de las veces y el 9 menos del 5 %. La probabilidad de que el primer dígito sea `d` es:

```text
P(d) = log10(1 + 1/d)
```

| Dígito | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| Probabilidad | 30,1 % | 17,6 % | 12,5 % | 9,7 % | 7,9 % | 6,7 % | 5,8 % | 5,1 % | 4,6 % |

Golbeck (2015) mostró que el primer dígito de las cantidades de amigos y seguidores en varias redes sociales sigue esta ley, y que las desviaciones respecto de ella pueden señalar actividad sospechosa. Este proyecto aplica esa idea a Instagram: toma el número de seguidores de cada seguidor del perfil analizado y comprueba si sus primeros dígitos siguen la distribución de Benford.

### Cómo funciona

1. **Extracción por hover (`extraer_numeros_hover`):** abre la lista de seguidores (y presiona "Ver todos los seguidores" si aparece la vista previa), pasa el mouse sobre cada usuario y lee el número de seguidores de la tarjeta flotante con una expresión regular. Desplaza la lista hasta reunir `MAX_HOVERS_BENFORD` muestras (200 por defecto) o hasta agotar 20 desplazamientos sin resultados nuevos.
2. **Primer dígito (`obtener_primer_digito`):** elimina comas y puntos y devuelve el primer dígito distinto de cero. Las cifras sin ese dígito (por ejemplo, `0`) se excluyen.
3. **Frecuencias:** cuenta cuántas veces aparece cada dígito del 1 al 9 y calcula las frecuencias esperadas con la fórmula de Benford.
4. **Chi-cuadrada:** compara lo observado con lo esperado usando `scipy.stats.chisquare` (9 categorías, 8 grados de libertad) y obtiene el p-valor.
5. **Decisión:** si el p-valor es menor que 0,05, el perfil se marca como anómalo.
6. **Salidas:** guarda el CSV y la gráfica.

Fragmento del hover:

```python
a.scroll_into_view_if_needed()
a.hover(timeout=3000)
pausa(1.5, 2.5)                    # espera la tarjeta flotante
body_text = page.locator("body").inner_text()
matches = re.findall(
    r"([\d\.,kKmM]+)\s*(?:seguidores|followers)", body_text, re.I)
if len(matches) > 1:
    candidato = matches[-1]        # cifra de la tarjeta flotante
    numeros_extraidos.append(candidato)
page.mouse.move(0, 200)            # cierra la tarjeta
```

Fragmento de la prueba estadística:

```python
chi2, p_valor = chisquare(f_obs=frecuencias_observadas,
                          f_exp=frecuencias_esperadas)
es_bot = p_valor < 0.05
diagnostico = "BOT / ANÓMALO" if es_bot else "HUMANO ORGÁNICO"
```

### Regla de decisión

| Condición | Diagnóstico | Significado |
|---|---|---|
| p-valor ≥ 0,05 | `HUMANO ORGÁNICO` | No hay evidencia suficiente para rechazar que los primeros dígitos siguen la distribución de Benford. |
| p-valor < 0,05 | `BOT / ANÓMALO` | La distribución observada difiere de la de Benford de forma estadísticamente significativa. |

Con 8 grados de libertad, el valor crítico de la chi-cuadrada al nivel de 0,05 es aproximadamente 15,51.

### Archivos de salida

**`benford_<usuario>.csv`**

| Columna | Contenido |
|---|---|
| `Dígito` | Dígito del 1 al 9. |
| `Frecuencia_Real` | Cantidad de muestras cuyo primer dígito es ese número. |
| `Porcentaje_Real(%)` | Porcentaje observado. |
| `Porcentaje_Benford(%)` | Porcentaje esperado según la Ley de Benford. |

**`benford_<usuario>.png`**

Gráfica de 300 ppp con las **barras azules** (porcentaje real de cada primer dígito, con su valor encima) y la **línea roja con marcadores** (curva teórica de Benford). El título muestra el diagnóstico y el p-valor. Si las barras siguen la forma de la curva, la red se comporta como una red orgánica; si se alejan, la chi-cuadrada resulta grande y el perfil se marca como anómalo.

### Alcance y límites del resultado

- Una desviación respecto de Benford es un **indicio**, no una prueba de que la cuenta sea un bot.
- La ley funciona mejor con muchas muestras y cifras que abarcan varios órdenes de magnitud. Si los seguidores de una persona real tienen tamaños muy parecidos (por ejemplo, compañeros de un mismo curso), puede aparecer un falso positivo.
- Si se obtienen menos de 50 muestras, el programa advierte que la prueba no es concluyente.
- Si la vista previa del hover cambia en Instagram o muestra las cifras con un formato que la expresión regular no reconoce (por ejemplo, con la palabra "mil"), esas cuentas no se cuentan y el resultado puede sesgarse.

## Análisis Big Five con la API de Gemini

### Cómo funciona

Cuando el perfil resulta orgánico, el programa lee los datos del scraper, los reduce a lo necesario, los inserta en un prompt y llama a la API.

La función `preparar_datos` conserva solo la biografía y, de cada publicación, la descripción, los likes, el total de comentarios y los comentarios. Se excluyen las URL y el nombre real, y, por defecto, los usuarios de seguidores y seguidos, porque son datos de terceros.

El prompt le indica a Gemini que actúe como analista de personalidad, que base cada puntuación **solo en evidencia** de los datos, que indique su **nivel de confianza**, que no haga diagnósticos clínicos y que aclare que es una estimación.

La llamada a la API se hace con el SDK `google-genai`:

```python
client = genai.Client(api_key=api_key)
respuesta = client.models.generate_content(
    model=modelo_seguro,           # "gemini-3.8-flash"
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
| `model` | Modelo de Gemini que procesa la solicitud (`gemini-3.8-flash`, definido en `analizar_big_five`). |
| `contents` | Prompt con las reglas y los datos del perfil. |
| `response_mime_type` | Pide que la respuesta sea JSON. |
| `response_schema` | Esquema de `pydantic` que la respuesta debe seguir. |
| `temperature` | Controla la aleatoriedad; `0.3` da respuestas más consistentes. |

**Reintentos:** si Google responde con un error de servidor (por ejemplo, `503` por saturación), el programa espera `10 s × número de intento` y vuelve a intentar, hasta 5 veces.

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

### Alcance y límites del resultado

- Es una **estimación aproximada** hecha por un modelo de lenguaje a partir de contenido público; **no es un test psicométrico** ni un diagnóstico.
- Con pocos datos, algunos rasgos tendrán confianza baja.
- Úsalo únicamente con el **consentimiento de la persona** analizada y no tomes decisiones sobre ella a partir del resultado.

## Opciones de Configuración

Al inicio de `scraper.py` hay constantes que puedes ajustar:

| Constante | Descripción |
|---|---|
| `USUARIO` | Nombre de la cuenta de Instagram a analizar. |
| `TOTAL_POSTS` | Cantidad de publicaciones a leer (25 por defecto). |
| `MAX_HOVERS_BENFORD` | Cantidad de seguidores a muestrear por hover para Benford (200 por defecto). |
| `INCLUIR_CONTACTOS` | Si es `True`, también envía a Gemini los usuarios de seguidores y seguidos. Por defecto es `False`. |
| `USAR_DATOS_GUARDADOS` | Si es `True`, omite el scraping y usa el `datos_perfil.json` ya existente (sin abrir el navegador). Útil para probar solo Benford y Gemini. |
| `ARCHIVO_DATOS` / `ARCHIVO_BIG_FIVE` | Nombres de los archivos de entrada y salida. |

El modelo de Gemini se define dentro de `analizar_big_five` (variable `modelo_seguro`). Para cambiarlo, edita esa línea.

## Errores Comunes

| Error | Causa probable | Solución |
|---|---|---|
| `no se encontró GEMINI_API_KEY` | La variable está mal escrita en el `.env` (por ejemplo, con `:` en lugar de `=`). | Usa el formato `GEMINI_API_KEY="tu_clave"`. |
| `cookies vencidas, Instagram pide login` | Las cookies de sesión caducaron. | Genera cookies nuevas y actualiza el `.env`. |
| `No se extrajeron números por hover` | Instagram cambió la vista previa, no se mostró la tarjeta o el perfil no permite ver la lista. | Revisa la consola. El programa continúa directamente con el análisis Big Five. |
| `Tienes muy pocas muestras...` | Se obtuvieron menos de 50 cifras. | Aumenta `MAX_HOVERS_BENFORD` o revisa que el hover esté funcionando. |
| `404 NOT_FOUND` del modelo | El modelo ya no está disponible para cuentas nuevas o cambió de nombre. | Cambia el valor de `modelo_seguro` en `analizar_big_five` por un modelo vigente (consulta Google AI Studio). |
| `503 UNAVAILABLE` | El modelo tiene alta demanda de forma temporal. | El programa reintenta automáticamente hasta 5 veces. Si sigue fallando, ejecuta más tarde; con `USAR_DATOS_GUARDADOS = True` no repites el scraping. |

## Seguridad

- Nunca subas el archivo `.env` al repositorio: contiene cookies de sesión de Instagram y tu clave de Gemini.
- Si una clave o cookie se expone, revócala: elimina la clave en Google AI Studio y cierra sesión en Instagram para invalidar las cookies.
- El CSV de Benford no guarda nombres de usuario: solo las frecuencias de cada dígito.
- Evita repetir el hover muchas veces seguidas: cada ejecución genera cientos de interacciones con Instagram y la plataforma puede limitar la cuenta.

## Referencias

- Benford, F. (1938). The law of anomalous numbers. *Proceedings of the American Philosophical Society, 78*(4), 551–572.
- Golbeck, J. (2015). Benford's law applies to online social networks. *PLOS ONE, 10*(8), e0135169. https://doi.org/10.1371/journal.pone.0135169

## Propósito
Proyecto desarrollado con fines netamente académicos y didácticos para la comprensión de arquitecturas web modernas (SPA/React), automatización de navegadores mediante WebSockets, extracción de datos, análisis estadístico con la Ley de Benford y consumo de APIs de inteligencia artificial generativa con salida estructurada.