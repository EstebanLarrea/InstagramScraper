import os
import json
import re
import time
import random
from typing import List, Literal

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


load_dotenv()

USUARIO = "alondra_cgp"
TOTAL_POSTS = 25


MODELO = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
INCLUIR_CONTACTOS = False
USAR_DATOS_GUARDADOS = False
ARCHIVO_DATOS = "datos_perfil.json"
ARCHIVO_BIG_FIVE = "big_five.json"

UI = {"Responder", "Reply", "Ver traducción", "See translation", "Me gusta", "Like",
      "Seguir", "Follow", "Inicio", "Reels", "Mensajes", "Búsqueda", "Notificaciones",
      "Explorar", "Crear", "Perfil", "Más", "Panel", "Ver respuestas", USUARIO}

FECHA = re.compile(r"^\d+\s?(s|min|m|h|d|sem|w|a|año|años|y)\b", re.I)


def pausa(a, b):
    time.sleep(random.uniform(a, b))



def cargar_cookies_desde_env():
    """Construye la lista de cookies de Playwright leyendo del .env"""
    session_id = os.getenv("IG_SESSION_ID")
    if not session_id:
        return None

    return [
        {
            "name": "sessionid",
            "value": session_id,
            "domain": ".instagram.com",
            "path": "/",
            "secure": True,
            "httpOnly": True
        },
        {
            "name": "csrftoken",
            "value": os.getenv("IG_CSRF_TOKEN", ""),
            "domain": ".instagram.com",
            "path": "/"
        },
        {
            "name": "ds_user_id",
            "value": os.getenv("IG_DS_USER_ID", ""),
            "domain": ".instagram.com",
            "path": "/"
        },
        {
            "name": "ig_did",
            "value": os.getenv("IG_DID", ""),
            "domain": ".instagram.com",
            "path": "/"
        },
        {
            "name": "mid",
            "value": os.getenv("IG_MID", ""),
            "domain": ".instagram.com",
            "path": "/"
        }
    ]


def muestra_contactos(page, ruta):
    """Abre el diálogo de followers/following y devuelve hasta 5 usuarios."""
    try:
        palabra = "seguidores|followers" if ruta == "followers" else "seguidos|following"
        candidatos = [
            page.locator(f"a[href*='/{ruta}/']"),
            page.locator("header").get_by_text(re.compile(rf"\b({palabra})\b", re.I)),
        ]
        boton = next((c.first for c in candidatos if c.count() > 0), None)
        if boton is None:
            raise Exception("no encontré el enlace en el perfil (¿cuenta privada?)")
        boton.click(timeout=5000)
        page.wait_for_selector("div[role='dialog'] a", timeout=10000)
        pausa(2, 4)


        hrefs = page.locator("div[role='dialog'] a").evaluate_all(
            "els => els.map(e => e.getAttribute('href') || '')"
        )
        usuarios = []
        for h in hrefs:
            p = [x for x in h.split("/") if x]
            if len(p) == 1 and p[0] != USUARIO and p[0] not in usuarios:
                usuarios.append(p[0])


        if not usuarios:
            textos = page.locator("div[role='dialog'] span[dir='auto']").all_inner_texts()
            usuarios = list(dict.fromkeys(t for t in textos if t.strip()))

        page.keyboard.press("Escape")
        pausa(1, 2)
        return usuarios[:5]
    except Exception as e:
        print(f"No se pudo obtener {ruta}: {e}")
        try:
            print("  Enlaces del header:", page.locator("header a").evaluate_all(
                "els => els.map(e => e.getAttribute('href'))"))
        except Exception:
            pass
        page.keyboard.press("Escape")
        return []


def run(playwright):
    """Hace el scraping, guarda datos_perfil.json y devuelve los datos (o None si falla)."""
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()


    cookies = cargar_cookies_desde_env()
    if not cookies:
        print("Error: No se encontró IG_SESSION_ID en el archivo .env")
        return None

    context.add_cookies(cookies)

    page = context.new_page()
    print(f"Navegando al perfil de {USUARIO}...")
    page.goto(f"https://www.instagram.com/{USUARIO}/")
    pausa(4, 7)

    if "accounts/login" in page.url:
        print("Error: cookies vencidas, Instagram pide login.")
        return None


    perfil = {"usuario": USUARIO, "nombre_real": "", "biografia": ""}
    try:
        metricas = page.locator("header ul li").all_inner_texts()  # solo para filtrar la bio
        lineas = [l.strip() for l in page.locator("header").inner_text().split("\n") if l.strip()]
        if len(lineas) > 1:
            perfil["nombre_real"] = lineas[1]
        ignoradas = metricas + [USUARIO, perfil["nombre_real"], "Seguir", "Mensaje"]
        perfil["biografia"] = " | ".join(l for l in lineas if l not in ignoradas)
    except Exception as e:
        print(f"Falló la biografía/métricas: {e}")


    print("Obteniendo seguidores y seguidos...")
    seguidores = muestra_contactos(page, "followers")
    seguidos = muestra_contactos(page, "following")


    enlaces = []
    print(f"Cargando {TOTAL_POSTS} enlaces de la cuadrícula...")
    for _ in range(15):
        for a in page.locator("a[href*='/p/']").all():
            href = a.get_attribute("href")
            if href:
                url = f"https://www.instagram.com{href}"
                if url not in enlaces:
                    enlaces.append(url)
        if len(enlaces) >= TOTAL_POSTS:
            break
        page.mouse.wheel(0, 1500)
        pausa(2, 5)
    enlaces = enlaces[:TOTAL_POSTS]


    publicaciones = []
    for idx, url in enumerate(enlaces, 1):
        print(f"Analizando post {idx}/{len(enlaces)}...")
        page.goto(url)
        pausa(4, 5)

        likes, n_coment, caption, comentarios = "No disponible", "0", "", []
        try:
            desc = page.locator("meta[property='og:description']").first.get_attribute(
                "content", timeout=3000
            ) or ""
            cabecera = desc.split(" - ")[0]  # "36 Me gusta, 0 comentarios"

            m = re.search(r"([\d.,KMkm]+)\s+(?:likes?|me gusta)", cabecera, re.I)
            if m:
                likes = m.group(1)
            m = re.search(r"([\d.,KMkm]+)\s+(?:comments?|comentarios?)", cabecera, re.I)
            if m:
                n_coment = m.group(1)

            c = re.search(r":\s*[“\"«](.*)[”\"»]\.?\s*$", desc, re.S)
            caption = c.group(1).strip() if c else desc


            if n_coment != "0":
                textos = page.locator("main span[dir='auto']").evaluate_all(
                    "els => els.filter(e => !e.closest('a, nav')).map(e => e.innerText.trim())"
                )
                for t in textos:
                    if (len(t) > 2 and t not in UI and not FECHA.match(t)
                            and t not in caption and t not in comentarios):
                        comentarios.append(t)
                comentarios = comentarios[:5]
        except Exception as e:
            print(f"Error en {url}: {e}")

        publicaciones.append({
            "url_post": url,
            "descripcion": caption,
            "interacciones": {
                "likes": likes,
                "total_comentarios": n_coment,
            },
            "comentarios": comentarios,
        })

    # Exportar Json
    datos = {
        "cuenta": perfil,
        "contactos_recientes": {"seguidores_muestra": seguidores, "seguidos_muestra": seguidos},
        "extraccion": {"total_posts_analizados": len(publicaciones), "publicaciones": publicaciones},
    }
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

    print(f"\n¡Éxito! Los datos fueron guardados en '{ARCHIVO_DATOS}'")
    context.close()
    browser.close()
    return datos



class Rasgo(BaseModel):
    rasgo: Literal["Apertura a la experiencia", "Responsabilidad", "Extraversión",
    "Amabilidad", "Neuroticismo"]
    puntuacion: int = Field(description="Entero de 0 a 100")
    nivel: Literal["bajo", "medio", "alto"]
    confianza: Literal["baja", "media", "alta"]
    justificacion: str = Field(description="Explicación breve basada solo en los datos")
    evidencias: List[str] = Field(description="Fragmentos o hechos concretos del perfil")


class InformeBigFive(BaseModel):
    rasgos: List[Rasgo]
    resumen: str
    limitaciones: str


PROMPT = """Eres un analista de psicología de la personalidad. A partir de los datos públicos de un perfil
de Instagram (biografía, descripciones de publicaciones, interacciones y comentarios), estima
el perfil Big Five (modelo OCEAN) de la persona.

Reglas:
- Basa cada puntuación SOLO en evidencia presente en los datos; cita esa evidencia.
- Puntúa de 0 a 100 (50 = promedio poblacional). Nivel: bajo (<40), medio (40-60), alto (>60).
- Indica tu confianza en cada rasgo; si hay poca evidencia, usa confianza "baja" y puntuación cercana a 50.
- No hagas diagnósticos clínicos ni afirmaciones sobre salud mental.
- Es una estimación aproximada a partir de contenido público, no un test psicométrico.
- Responde en español.

Datos del perfil (JSON):
{datos}
"""


def preparar_datos(datos):
    """Deja solo lo útil para el análisis y reduce el tamaño del prompt."""
    resumen = {
        "biografia": datos["cuenta"].get("biografia", ""),
        "publicaciones": [
            {
                "descripcion": p.get("descripcion", ""),
                "likes": p["interacciones"].get("likes"),
                "total_comentarios": p["interacciones"].get("total_comentarios"),
                "comentarios": p.get("comentarios", []),
            }
            for p in datos["extraccion"]["publicaciones"]
        ],
    }
    if INCLUIR_CONTACTOS:
        resumen["contactos"] = datos.get("contactos_recientes", {})
    return resumen


def analizar_big_five(datos):
    """Envía los datos del scraper a Gemini y guarda big_five.json."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: no se encontró GEMINI_API_KEY en el archivo .env")
        return

    prompt = PROMPT.format(
        datos=json.dumps(preparar_datos(datos), ensure_ascii=False, indent=2)
    )

    client = genai.Client(api_key=api_key)
    print(f"\nEnviando datos a Gemini ({MODELO})...")
    respuesta = client.models.generate_content(
        model=MODELO,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=InformeBigFive,
            temperature=0.3,
        ),
    )


    try:
        resultado = InformeBigFive.model_validate_json(respuesta.text).model_dump()
    except Exception as e:
        print(f"La respuesta no coincidió con el esquema ({e}); se guarda tal cual.")
        resultado = {"respuesta_cruda": respuesta.text}

    with open(ARCHIVO_BIG_FIVE, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=4)

    if "rasgos" in resultado:
        print("\nResultado Big Five:")
        for r in resultado["rasgos"]:
            print(f"  {r['rasgo']}: {r['puntuacion']}/100 ({r['nivel']}, confianza {r['confianza']})")
        print(f"\nResumen: {resultado['resumen']}")
    print(f"\nGuardado en '{ARCHIVO_BIG_FIVE}'")



if __name__ == "__main__":
    if USAR_DATOS_GUARDADOS and os.path.exists(ARCHIVO_DATOS):
        print(f"Usando los datos guardados en '{ARCHIVO_DATOS}' (sin repetir el scraping)")
        with open(ARCHIVO_DATOS, encoding="utf-8") as f:
            datos = json.load(f)
    else:
        with sync_playwright() as playwright:
            datos = run(playwright)

    if datos:
        analizar_big_five(datos)