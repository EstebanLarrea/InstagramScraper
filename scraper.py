from playwright.sync_api import sync_playwright
import json
import time
import random

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
    print("Navegando al perfil...")
    page.goto("https://www.instagram.com/alondra_cgp/")
    time.sleep(random.uniform(4, 7)) # Pausa antibots


    try:
        biografia = page.locator("header").inner_text()
        print("Biografía extraída correctamente.")
    except Exception:
        biografia = "No se pudo extraer"
        print("No se pudo extraer la biografía.")


    posts = set()
    print("Cargando publicaciones...")

    while len(posts) < 50:

        for enlace in page.locator("a[href*='/p/']").all():
            href = enlace.get_attribute("href")
            if href:

                posts.add(f"https://www.instagram.com{href}")
            if len(posts) >= 50:
                break

        if len(posts) < 50:
            page.mouse.wheel(0, 1500)
            time.sleep(random.uniform(2, 5))

    # 4. Guardar datos en un archivo JSON
    datos_exportar = {
        "usuario": "alondra_cgp",
        "biografia": biografia,
        "enlaces_extraidos": len(posts),
        "publicaciones": list(posts)[:50]
    }

    with open("datos_perfil.json", "w", encoding="utf-8") as f:
        json.dump(datos_exportar, f, ensure_ascii=False, indent=4)

    print("¡Éxito! Los datos fueron guardados en 'datos_perfil.json'")

    context.close()
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)