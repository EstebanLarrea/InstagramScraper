import math
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import chisquare
import pandas as pd

def obtener_primer_digito(numero):
    """Toma un número (entero o texto como '12.4k') y devuelve su primer dígito válido (1-9)."""
    texto = str(numero).replace(",", "").replace(".", "").strip()
    for char in texto:
        if char.isdigit() and char != '0':
            return int(char)
    return None

def analizar_ley_benford(lista_seguidores, nombre_usuario):
    """
    Aplica Benford y Chi-cuadrada. Genera CSV y Gráfica.
    Retorna "HUMANO ORGÁNICO" o "BOT / ANÓMALO".
    """
    print(f"\n[BENFORD] Iniciando análisis para @{nombre_usuario} con {len(lista_seguidores)} muestras...")

    # 1. Extraer primer dígito
    digitos = [obtener_primer_digito(n) for n in lista_seguidores if obtener_primer_digito(n) is not None]
    total_muestras = len(digitos)

    if total_muestras < 50:
        print("[!] Advertencia: Tienes muy pocas muestras para que Chi-cuadrada sea concluyente.")

    # 2. Frecuencias Reales
    conteos_reales = {i: 0 for i in range(1, 10)}
    for d in digitos:
        conteos_reales[d] += 1

    frecuencias_observadas = [conteos_reales[i] for i in range(1, 10)]
    porcentajes_observados = [(c / total_muestras) * 100 if total_muestras > 0 else 0 for c in frecuencias_observadas]

    # 3. Frecuencias Esperadas (Ley de Benford)
    porcentajes_esperados = [(math.log10(1 + 1/i) * 100) for i in range(1, 10)]
    frecuencias_esperadas = [(p / 100) * total_muestras for p in porcentajes_esperados]

    # 4. Chi-cuadrada
    # Si f_exp tiene algún valor en 0, chisquare fallará, así que añadimos un pequeño margen de error si es necesario
    frecuencias_esperadas = [max(e, 0.0001) for e in frecuencias_esperadas]
    chi2, p_valor = chisquare(f_obs=frecuencias_observadas, f_exp=frecuencias_esperadas)

    es_bot = p_valor < 0.05
    diagnostico = "BOT / ANÓMALO" if es_bot else "HUMANO ORGÁNICO"

    print(f"  - Chi-cuadrada: {chi2:.2f}")
    print(f"  - p-valor: {p_valor:.5f}")
    print(f"  - Diagnóstico: {diagnostico}")

    # 5. Generar CSV
    df = pd.DataFrame({
        "Dígito": list(range(1, 10)),
        "Frecuencia_Real": frecuencias_observadas,
        "Porcentaje_Real(%)": porcentajes_observados,
        "Porcentaje_Benford(%)": porcentajes_esperados
    })
    archivo_csv = f"benford_{nombre_usuario}.csv"
    df.to_csv(archivo_csv, index=False)

    # 6. Generar Gráfica Superpuesta (MEJORADA)
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(1, 10)

    # Barras para los datos reales (Azul claro con borde)
    barras = ax.bar(x, porcentajes_observados, color='#3498db', alpha=0.8, edgecolor='black', label='Datos Reales (Los 200 seguidores)')

    # Curva (línea roja) para la Ley de Benford ideal (Más gruesa y vistosa)
    ax.plot(x, porcentajes_esperados, color='#e74c3c', marker='o', markersize=8, linewidth=3, linestyle='-', label='Curva Perfecta Teórica (Benford)')

    # Añadir los números (porcentajes) encima de cada barra
    for barra in barras:
        alto = barra.get_height()
        ax.text(barra.get_x() + barra.get_width()/2., alto + 0.5,
                f'{alto:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#2c3e50')

    # Estilos y textos de la gráfica
    ax.set_title(f"Análisis Forense: Ley de Benford - @{nombre_usuario}\nDiagnóstico: {diagnostico} (p={p_valor:.4f})", fontsize=14, fontweight='bold')
    ax.set_xlabel("Primer Dígito del Número de Seguidores", fontsize=12, fontweight='bold')
    ax.set_ylabel("Frecuencia de Aparición (%)", fontsize=12, fontweight='bold')
    ax.set_xticks(x)

    # Dar un poco de espacio en la parte de arriba para que los números no se corten
    ax.set_ylim(0, max(max(porcentajes_observados), max(porcentajes_esperados)) + 5)

    ax.legend(loc="upper right", fontsize=11, framealpha=1)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Guardar gráfica como PNG
    archivo_img = f"benford_{nombre_usuario}.png"
    plt.savefig(archivo_img, dpi=300, bbox_inches='tight')
    plt.close()

    return diagnostico