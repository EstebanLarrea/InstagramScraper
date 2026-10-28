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
from google.genai import errors


import benford_analisis

load_dotenv()

USUARIO = "alondra_cgp"
TOTAL_POSTS = 25
MAX_HOVERS_BENFORD = 200

MODELO = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
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
    session_id = os.getenv("IG_SESSION_ID")
    if not session_id:
        return None
    return [
        {"name": "sessionid", "value": session_id, "domain": ".instagram.com", "path": "/", "secure": True, "httpOnly": True},
        {"name": "csrftoken", "value": os.getenv("IG_CSRF_TOKEN", ""), "domain": ".instagram.com", "path": "/"},
        {"name": "ds_user_id", "value": os.getenv("IG_DS_USER_ID", ""), "domain": ".instagram.com", "path": "/"},
        {"name": "ig_did", "value": os.getenv("IG_DID", ""), "domain": ".instagram.com", "path": "/"},
        {"name": "mid", "value": os.getenv("IG_MID", ""), "domain": ".instagram.com", "path": "/"}
    ]


def extraer_numeros_hover(page, max_muestras=200):
    """Abre la lista de seguidores, detecta si hay vista previa, y hace HOVER secuencial."""
    print(f"\nIniciando extracción por HOVER para Benford (Objetivo: {max_muestras} muestras)...")
    try:
        # 1. Asegurarnos de estar hasta arriba para que el botón exista
        page.evaluate("window.scrollTo(0, 0)")
        pausa(1, 2)


        candidatos = [
            page.locator("a[href*='/followers/']"),
            page.locator("header").get_by_text(re.compile(r"\b(seguidores|followers)\b", re.I)),
        ]
        boton = next((c.first for c in candidatos if c.count() > 0), None)

        if boton is None:
            print("  [!] Error: No se encontró el botón de seguidores en el perfil.")
            return []

        boton.click(timeout=5000)
        page.wait_for_selector("div[role='dialog'] a", timeout=10000)
        pausa(3, 5) # Esperamos bien a que la lista cargue

        dialog = page.locator("div[role='dialog']").first

        #Ver todos los seguidores
        try:
            # Buscamos el texto exacto (en español o inglés) dentro del cuadro
            btn_ver_todos = dialog.get_by_text(re.compile(r"Ver todos los seguidores|See all followers", re.I))
            if btn_ver_todos.count() > 0:
                print("  [*] Interfaz de 'Vista Previa' detectada. Haciendo clic en 'Ver todos'...")
                btn_ver_todos.first.click(timeout=3000)
                pausa(3, 5) # Esperamos a que Instagram cargue la lista real
        except Exception as e:
            pass

        numeros_extraidos = []
        enlaces_procesados = set()
        intentos_scroll = 0

        while len(numeros_extraidos) < max_muestras and intentos_scroll < 20:
            enlaces = dialog.locator("a[href^='/']").all()
            nuevos = 0

            for a in enlaces:
                if len(numeros_extraidos) >= max_muestras:
                    break

                href = a.get_attribute("href")
                # Ignorar hashtags, el mismo usuario, o repetidos
                if not href or href == f"/{USUARIO}/" or href in enlaces_procesados or "explore" in href:
                    continue

                try:
                    # Forzar a Playwright a bajar hasta donde está el nombre antes del hover
                    a.scroll_into_view_if_needed()
                    a.hover(timeout=3000)
                    pausa(1.5, 2.5)  # Esperar que cargue la tarjeta flotante

                    # Buscar texto de seguidores en todo el body
                    body_text = page.locator("body").inner_text()
                    matches = re.findall(r"([\d\.,kKmM]+)\s*(?:seguidores|followers)", body_text, re.I)

                    if len(matches) > 1:
                        candidato = matches[-1]
                        numeros_extraidos.append(candidato)
                        print(f"  [{len(numeros_extraidos)}/{max_muestras}] Hover en {href}: {candidato} seguidores")
                        nuevos += 1

                    enlaces_procesados.add(href)

                    # Retirar el mouse al lado izquierdo para cerrar la tarjeta y evitar bugs visuales
                    page.mouse.move(0, 200)
                    pausa(0.5, 1)

                except Exception as e:
                    pass

            if nuevos == 0:
                # Hacer scroll general en el cuadro flotante si nos quedamos sin enlaces nuevos
                dialog.hover()
                page.mouse.wheel(0, 1000)
                pausa(2, 4)
                intentos_scroll += 1

        page.keyboard.press("Escape")
        pausa(1, 2)
        return numeros_extraidos

    except Exception as e:
        print(f"  [!] Error general durante el hover: {e}")
        page.keyboard.press("Escape")
        return []


def muestra_contactos(page, ruta):
    """Mantiene tu lógica original para extraer los 5 nombres de usuario."""

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
        hrefs = page.locator("div[role='dialog'] a").evaluate_all("els => els.map(e => e.getAttribute('href') || '')")
        usuarios = []
        for h in hrefs:
            p = [x for x in h.split("/") if x]
            if len(p) == 1 and p[0] != USUARIO and p[0] not in usuarios:
                usuarios.append(p[0])
        page.keyboard.press("Escape")
        pausa(1, 2)
        return usuarios[:5]
    except Exception as e:
        page.keyboard.press("Escape")
        return []


def run(playwright):

    browser = playwright.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )

    # Le inyectamos una identidad humana (User-Agent) y un tamaño de pantalla normal
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720}
    )

    cookies = cargar_cookies_desde_env()
    if not cookies:
        print("Error: No se encontró IG_SESSION_ID en el archivo .env")
        return None

    context.add_cookies(cookies)

    page = context.new_page()
    print(f"Navegando al perfil de {USUARIO}...")

    # Ahora la conexión no debería ser rechazada
    page.goto(f"https://www.instagram.com/{USUARIO}/")
    pausa(4, 7)

    if "accounts/login" in page.url:
        print("Error: cookies vencidas, Instagram pide login.")
        return None

    # 1. Extracción de Bio
    perfil = {"usuario": USUARIO, "nombre_real": "", "biografia": ""}
    try:
        metricas = page.locator("header ul li").all_inner_texts()
        lineas = [l.strip() for l in page.locator("header").inner_text().split("\n") if l.strip()]
        if len(lineas) > 1:
            perfil["nombre_real"] = lineas[1]
        ignoradas = metricas + [USUARIO, perfil["nombre_real"], "Seguir", "Mensaje"]
        perfil["biografia"] = " | ".join(l for l in lineas if l not in ignoradas)
    except Exception as e:
        print(f"Falló la biografía/métricas: {e}")

    # 2. Extracción de seguidores para Benford (NUEVO)
    metricas_benford = extraer_numeros_hover(page, max_muestras=MAX_HOVERS_BENFORD)

    # 3. Seguidores/Seguidos Muestra (Tu código original)
    print("\nObteniendo muestra de nombres de seguidores y seguidos...")
    seguidores = muestra_contactos(page, "followers")
    seguidos = muestra_contactos(page, "following")

    # 4. Extracción de Posts (Grid)
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

    # 5. Análisis Individual de Posts
    publicaciones = []
    for idx, url in enumerate(enlaces, 1):
        print(f"Analizando post {idx}/{len(enlaces)}...")
        page.goto(url)
        pausa(4, 5)

        likes, n_coment, caption, comentarios = "No disponible", "0", "", []
        try:
            desc = page.locator("meta[property='og:description']").first.get_attribute("content", timeout=3000) or ""
            cabecera = desc.split(" - ")[0]
            m = re.search(r"([\d.,KMkm]+)\s+(?:likes?|me gusta)", cabecera, re.I)
            if m: likes = m.group(1)
            m = re.search(r"([\d.,KMkm]+)\s+(?:comments?|comentarios?)", cabecera, re.I)
            if m: n_coment = m.group(1)

            c = re.search(r":\s*[“\"«](.*)[”\"»]\.?\s*$", desc, re.S)
            caption = c.group(1).strip() if c else desc

            if n_coment != "0":
                textos = page.locator("main span[dir='auto']").evaluate_all(
                    "els => els.filter(e => !e.closest('a, nav')).map(e => e.innerText.trim())"
                )
                for t in textos:
                    if (len(t) > 2 and t not in UI and not FECHA.match(t) and t not in caption and t not in comentarios):
                        comentarios.append(t)
                comentarios = comentarios[:5]
        except Exception as e:
            pass

        publicaciones.append({
            "url_post": url, "descripcion": caption,
            "interacciones": {"likes": likes, "total_comentarios": n_coment},
            "comentarios": comentarios
        })

    # 6. Empaquetar y Guardar Todo
    datos = {
        "cuenta": perfil,
        "contactos_recientes": {"seguidores_muestra": seguidores, "seguidos_muestra": seguidos},
        "metricas_seguidores_hover": metricas_benford,  # <--- Agregamos los datos de Benford aquí
        "extraccion": {"total_posts_analizados": len(publicaciones), "publicaciones": publicaciones},
    }
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

    context.close()
    browser.close()
    return datos


class Rasgo(BaseModel):
    rasgo: Literal["Apertura a la experiencia", "Responsabilidad", "Extraversión", "Amabilidad", "Neuroticismo"]
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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: no se encontró GEMINI_API_KEY en el archivo .env")
        return

    # Forzamos un modelo válido por si en el .env está mal escrito
    modelo_seguro = "gemini-3.8-flash"
    prompt = PROMPT.format(datos=json.dumps(preparar_datos(datos), ensure_ascii=False, indent=2))
    client = genai.Client(api_key=api_key)

    print(f"\n[GEMINI] Enviando datos a Gemini ({modelo_seguro})...")

    respuesta = None
    reintentos = 5

    # SISTEMA DE REINTENTOS PARA EVITAR CAÍDAS POR EL ERROR 503
    for intento in range(1, reintentos + 1):
        try:
            respuesta = client.models.generate_content(
                model=modelo_seguro,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=InformeBigFive,
                    temperature=0.3
                ),
            )
            break  # Si la petición fue exitosa, rompe el bucle

        except errors.ServerError as e:
            espera = 10 * intento
            print(f"  [!] Servidores de Google saturados (503). Intento {intento}/{reintentos}. Esperando {espera}s...")
            if intento == reintentos:
                print("  [X] No se pudo conectar con Gemini tras varios intentos. Intenta más tarde.")
                return
            time.sleep(espera)

    # Si hubo respuesta, procesamos el JSON
    if respuesta:
        try:
            resultado = InformeBigFive.model_validate_json(respuesta.text).model_dump()
        except Exception as e:
            print(f"La respuesta de Gemini no cumplió el esquema: {e}")
            resultado = {"respuesta_cruda": respuesta.text}

        with open(ARCHIVO_BIG_FIVE, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=4)

        if "rasgos" in resultado:
            print("\nResultado Big Five:")
            for r in resultado["rasgos"]:
                print(f"  {r['rasgo']}: {r['puntuacion']}/100 ({r['nivel']}, confianza {r['confianza']})")
            print(f"\nResumen: {resultado['resumen']}")
        print(f"\nGuardado en '{ARCHIVO_BIG_FIVE}'")
# =======================================================
# ORQUESTADOR (El Semáforo Inteligente)
# =======================================================
if __name__ == "__main__":
    datos = None

    # FASE 1: SCRAPING
    if USAR_DATOS_GUARDADOS and os.path.exists(ARCHIVO_DATOS):
        print(f"Usando datos locales en '{ARCHIVO_DATOS}' (Sin abrir navegador)...")
        with open(ARCHIVO_DATOS, encoding="utf-8") as f:
            datos = json.load(f)
    else:
        with sync_playwright() as playwright:
            datos = run(playwright)

    if datos:
        # FASE 2: LEY DE BENFORD
        muestras_hover = datos.get("metricas_seguidores_hover", [])

        if not muestras_hover:
            print("\n[!] No se extrajeron números por hover. Procediendo directamente a Big Five...")
            analizar_big_five(datos)
        else:
            diagnostico_bot = benford_analisis.analizar_ley_benford(muestras_hover, datos["cuenta"]["usuario"])

            # FASE 3: DECISIÓN DE IA (Gemini)
            if diagnostico_bot == "HUMANO ORGÁNICO":
                print("\n[✓] Comportamiento orgánico verificado. Llamando a la IA para análisis psicológico...")
                analizar_big_five(datos)
            else:
                print("\n[X] ALERTA: Red de seguidores artificial detectada.")
                print("    El análisis psicológico Big Five HA SIDO CANCELADO para no desperdiciar tokens de Gemini en bots.")