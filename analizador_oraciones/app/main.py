import os
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Configuración de rutas
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

# TUS IMPORTACIONES DE SERVICIOS
from core.servicios.analizador import Analizador
from core.servicios.construir_chunks import ConstructorDeChunks
from core.servicios.evaluador_oraciones import EvaluadorNaturalidad
from core.servicios.generar_frases import GeneradorOraciones


# ============ MODELOS DE DATOS ============
class CorreccionRequest(BaseModel):  # lo que envía el usuario
    texto: str


class TokenResponse(BaseModel):  # token serializado para el frontend
    texto: str
    pos: str
    gen: Optional[str] = ""
    num: Optional[str] = ""


class CorreccionResponse(BaseModel):  # lo que responde la api
    texto_original: str
    texto_corregido: str
    opciones: List[str]
    tokens: List[TokenResponse]


# ============ INICIALIZACIÓN GLOBAL (Carga única) ============
print("🚀 Cargando modelos y servicios... (esto solo ocurre una vez)")

# Inicializamos los servicios
analizador = Analizador()  # Esto ya carga spaCy internamente
constructor_chunks = ConstructorDeChunks()
generador = GeneradorOraciones()
evaluador = EvaluadorNaturalidad(mostrar_logs=True)

# FORZAMOS LA CARGA DE GPT-2 AHORA MISMO
print("🔄 Forzando carga de GPT-2 en memoria...")
evaluador._cargar_modelo_si_es_necesario()  # <--- Llamada explícita para cargar GPT-2
print("✅ GPT-2 cargado y listo en memoria")

print("✅ Todo listo. Servidor esperando peticiones.")

# ============ CONFIGURACIÓN FASTAPI ============
app = FastAPI(title="Corrector Gramatical")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos
# El mount va DESPUES de los endpoints para no interceptar / ni /corregir
static_path = os.path.join(root_path, "static")


@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_path, "index.html"))


# ============ ENDPOINT ============
@app.post("/corregir", response_model=CorreccionResponse)
async def corregir(request: CorreccionRequest):
    # Procesar la oración
    tokens_obj = analizador.analizar_oracion(request.texto)

    chunks = constructor_chunks.generar_chunks(tokens_obj)
    frases = generador.generar_frases(chunks)

    texto_corregido = request.texto
    if len(frases) > 0:
        if len(frases) > 1:
            # GPT-2 ya está en memoria
            mejor = evaluador.elegir_mejor_frase(frases, chunks)
            texto_corregido = mejor.texto if mejor else frases[0].texto
        else:
            texto_corregido = frases[0].texto

    return CorreccionResponse(
        texto_original=request.texto,
        texto_corregido=texto_corregido,
        opciones=[f.texto for f in frases[:5]],
        # tokens: disponible cuando el frontend lo necesite.
        # analizar_oracion_dict() sigue activo en el analizador,
        # solo se omite de la respuesta por ahora.
        tokens=[],
    )


# Mount en / al final -- los endpoints declarados antes tienen prioridad
app.mount("/", StaticFiles(directory=static_path), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
