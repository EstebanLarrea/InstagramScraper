from playwright.sync_api import sync_playwright
import json
import re
import time
import random

USUARIO = "alondra_cgp"
TOTAL_POSTS = 25


UI = {"Responder", "Reply", "Ver traducción", "See translation", "Me gusta", "Like",
      "Seguir", "Follow", "Inicio", "Reels", "Mensajes", "Búsqueda", "Notificaciones",
      "Explorar", "Crear", "Perfil", "Más", "Panel", "Ver respuestas", USUARIO}
# Fechas tipo "3 sem", "2 d", "5 h", "1 año"
FECHA = re.compile(r"^\d+\s?(s|min|m|h|d|sem|w|a|año|años|y)\b", re.I)


def pausa(a, b):
    time.sleep(random.uniform(a, b))


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

        # 1) usernames desde los href de los enlaces del diálogo
        hrefs = page.locator("div[role='dialog'] a").evaluate_all(
            "els => els.map(e => e.getAttribute('href') || '')"
        )
        usuarios = []
        for h in hrefs:
            p = [x for x in h.split("/") if x]
            if len(p) == 1 and p[0] != USUARIO and p[0] not in usuarios:
                usuarios.append(p[0])

        # 2) respaldo: el método original con los span
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
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()

    try:
        with open("cookies.json", "r") as f:
            context.add_cookies(json.load(f))
    except FileNotFoundError:
        print("Error: Falta el archivo cookies.json")
        return

    page = context.new_page()
    print(f"Navegando al perfil de {USUARIO}...")
    page.goto(f"https://www.instagram.com/{USUARIO}/")
    pausa(4, 7)

    if "accounts/login" in page.url:
        print("Error: cookies vencidas, Instagram pide login.")
        return

    # 1. Biografía y métricas (todo sale del <header> del perfil)
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

    # 2 y 3. Seguidores y seguidos
    print("Obteniendo seguidores y seguidos...")
    seguidores = muestra_contactos(page, "followers")
    seguidos = muestra_contactos(page, "following")

    # 4. Enlaces del grid
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

    # 5. Detalle de cada publicación
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

            # If solo para buscar comentarios si los tiene realmente
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
    with open("datos_perfil.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

    print("\n¡Éxito! Los datos fueron guardados en 'datos_perfil.json'")
    context.close()
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)