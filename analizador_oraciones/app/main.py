import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

# Configuración de rutas
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

# TUS IMPORTACIONES DE SERVICIOS
from core.servicios.analizador import Analizador
from core.servicios.construir_chunks import ConstructorDeChunks
from core.servicios.generar_frases import GeneradorOraciones
from core.servicios.evaluador_oraciones import EvaluadorNaturalidad

# ============ MODELOS DE DATOS ============
class CorreccionRequest(BaseModel):   # lo que envía el usuario
    texto: str

class CorreccionResponse(BaseModel):  # lo que responde la api
    texto_original: str
    texto_corregido: str
    opciones: List[str]

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
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos
static_path = os.path.join(root_path, "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_path, "index.html"))

# ============ ENDPOINT ============
@app.post("/corregir", response_model=CorreccionResponse)
async def corregir(request: CorreccionRequest):
    # Procesar la oración
    tokens = analizador.analizar_oracion(request.texto)
    chunks = constructor_chunks.generar_chunks(tokens)
    frases = generador.generar_frases(chunks)
    
    texto_corregido = request.texto
    if len(frases) > 0:
        if len(frases) > 1:
            # GPT-2 ya está en memoria, será instantáneo
            mejor = evaluador.elegir_mejor_frase(frases)
            texto_corregido = mejor.texto if mejor else frases[0].texto
        else:
            texto_corregido = frases[0].texto
    
    return CorreccionResponse(
        texto_original=request.texto,
        texto_corregido=texto_corregido,
        opciones=[f.texto for f in frases[:5]]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)