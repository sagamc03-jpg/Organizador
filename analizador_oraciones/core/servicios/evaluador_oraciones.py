import time
from typing import List, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from core.modelos.enunciado import FraseGenerada
from config.settings import settings
from core.modelos import Chunks

BONUS_VOZ_PASIVA = 1.0
BONUS_COPULATIVA = 2.5
BONUS_PRON_IMPERSONAL = 1.0
 
class EvaluadorNaturalidad:
    """
    Evalúa y elige la mejor frase usando GPT-2 de forma perezosa (Lazy Loading).
    Aplica reglas sintácticas para ajustar puntajes cuando hay PROPN/PRON.
    """
    
    def __init__(self, mostrar_logs: bool = True):
        self.mostrar_logs = mostrar_logs
        self.tokenizador = None
        self.modelo = None
 
    # -------------------------------------------------------------------------
    # CARGA DEL MODELO
    # -------------------------------------------------------------------------
 
    def _cargar_modelo_si_es_necesario(self) -> None:
        """
        Carga GPT-2 solo la primera vez que se necesita (Lazy Loading).
        """
        if self.modelo is None:
            if self.mostrar_logs:
                print(f"🔄 Cargando modelo GPT-2 por primera vez: {settings.GPT2_MODEL}...")
            
            self.tokenizador = AutoTokenizer.from_pretrained(settings.GPT2_MODEL)
            self.modelo = AutoModelForCausalLM.from_pretrained(settings.GPT2_MODEL)
            self.modelo.eval()
            
            if self.mostrar_logs:
                print(f"✅ Modelo GPT-2 cargado en memoria correctamente.")
 
    # -------------------------------------------------------------------------
    # PUNTO DE ENTRADA PRINCIPAL
    # -------------------------------------------------------------------------
 
    def elegir_mejor_frase(self, frases: List[FraseGenerada], chunks: Chunks) -> Optional[FraseGenerada]:
        """
        Elige la mejor frase. Si solo hay una, la devuelve sin cargar GPT-2.
        Si hay varias, GPT-2 puntúa y se aplican reglas sintácticas si hay PROPN/PRON.
        """
        if not frases:
            return None
        
        if len(frases) == 1:
            if self.mostrar_logs:
                print("💡 Solo hay una opción disponible. Saltando evaluación de GPT-2.")
            return frases[0]
        
        # Puntuar todas las frases con GPT-2
        self._cargar_modelo_si_es_necesario()
        self._puntuar_frases(frases)
 
        # Aplicar bonus si hay PROPN/PRON y alguna regla aplica
        if self._hay_nombre_propio(chunks):
            self._aplicar_bonus_si_aplica_regla(frases, chunks)
 
        mejor_frase = max(frases, key=lambda f: f.puntaje_naturalidad)
        return mejor_frase
 
    # -------------------------------------------------------------------------
    # PUNTUACIÓN GPT-2
    # -------------------------------------------------------------------------
 
    def _puntuar_frases(self, frases: List[FraseGenerada]) -> None:
        """
        Asigna puntaje de naturalidad GPT-2 a cada frase.
        """
        for frase in frases:
            puntaje, _ = self._medir_naturalidad(frase.texto)
            frase.puntaje_naturalidad = puntaje
 
            if self.mostrar_logs:
                texto_corto = frase.texto[:50].ljust(50)
                print(f"📝 '{texto_corto}' → Score: {puntaje:.4f}")
 
    def _medir_naturalidad(self, texto: str) -> tuple[float, float]:
        """
        Mide la naturalidad de un texto con GPT-2.
        Retorna (puntaje, tiempo). Puntaje más alto = más natural.
        """
        tiempo_inicio = time.time()
        
        entrada_tokenizada = self.tokenizador(texto, return_tensors="pt")
        
        with torch.no_grad():
            resultados = self.modelo(
                **entrada_tokenizada,
                labels=entrada_tokenizada["input_ids"]
            )
            puntaje_naturalidad = -resultados.loss.item()
        
        tiempo_total = time.time() - tiempo_inicio
        return puntaje_naturalidad, tiempo_total
 
    # -------------------------------------------------------------------------
    # DETECCIÓN DE PROPN/PRON
    # -------------------------------------------------------------------------
 
    def _hay_nombre_propio(self, chunks: Chunks) -> bool:
        """
        Verifica si hay algún PROPN o PRON en las frases nominales.
        """
        return any(fn.es_propio for fn in chunks.fn)
 
    def _obtener_textos_propios(self, chunks: Chunks) -> List[str]:
        """
        Retorna los textos de las FNs que son PROPN o PRON.
        """
        return [fn.texto for fn in chunks.fn if fn.es_propio]
 
    # -------------------------------------------------------------------------
    # ORQUESTADOR DE REGLAS
    # -------------------------------------------------------------------------
 
    def _aplicar_bonus_si_aplica_regla(self, frases: List[FraseGenerada], chunks: Chunks) -> None:
        """
        Detecta qué regla aplica y suma bonus a la frase donde el PROPN/PRON
        está al final (posición de objeto/agente).
        Solo se aplica una regla por evaluación (la primera que coincida).
        """
        reglas = [
            self._regla_voz_pasiva,
            self._regla_copulativa,
            self._regla_pronombre_impersonal,
        ]
 
        for regla in reglas:
            if regla(frases, chunks):
                return  # Solo aplica una regla
 
    # -------------------------------------------------------------------------
    # REGLAS SINTÁCTICAS
    # -------------------------------------------------------------------------
 
    def _regla_voz_pasiva(self, frases: List[FraseGenerada], chunks: Chunks) -> bool:
        """
        Regla 1: AUX + participio + "por"
        Ejemplo: "el perro fue encontrado por José"
        → El PROPN/PRON es el agente de la pasiva, va al final.
        """
        verbo = chunks.verbo_pre
        tiene_aux_participio = len(verbo) >= 2
        tiene_por = "por" in verbo
 
        if not (tiene_aux_participio and tiene_por):
            return False
 
        self._bonificar_frase_con_propio_al_final(frases, chunks, BONUS_VOZ_PASIVA)
        return True

    def _regla_copulativa(self, frases: List[FraseGenerada], chunks: Chunks) -> bool:
        """
        Regla 2: Verbo copulativo ("es", "parece") + preposición "de"
        Ejemplo: "el libro es de Juan"
        → El PROPN/PRON es el complemento, va al final.
        """
        verbos_copulativos = {"es", "parece"}
        verbo = chunks.verbo_pre
 
        tiene_copulativo = any(v.lower() in verbos_copulativos for v in verbo)
        tiene_de = "de" in verbo
 
        if not (tiene_copulativo and tiene_de):
            return False
 
        self._bonificar_frase_con_propio_al_final(frases, chunks, BONUS_COPULATIVA)
        return True

    def _regla_pronombre_impersonal(self, frases: List[FraseGenerada], chunks: Chunks) -> bool:
        """
        Regla 3: pron_imp + preposición "a"
        Ejemplo: "le di el libro a María"
        → El PROPN/PRON es el destinatario, va al final.
        """
        tiene_pron_imp = len(chunks.pron_imp) > 0
        tiene_a = "a" in chunks.verbo_pre
 
        if not (tiene_pron_imp and tiene_a):
            return False
 
        self._bonificar_frase_con_propio_al_final(frases, chunks, BONUS_PRON_IMPERSONAL)
        return True
 
    # -------------------------------------------------------------------------
    # APLICACIÓN DEL BONUS
    # -------------------------------------------------------------------------
 
    def _bonificar_frase_con_propio_al_final(self, frases: List[FraseGenerada], chunks: Chunks, bonus: float) -> None:
        """
        Suma el bonus al puntaje de la frase donde el PROPN/PRON
        aparece como última palabra (posición de objeto/agente).
        """
        textos_propios = self._obtener_textos_propios(chunks)

        for frase in frases:
            palabras = frase.texto.strip().split()
            ultima_palabra = palabras[-1] if palabras else ""

            if ultima_palabra in textos_propios:
                frase.puntaje_naturalidad += bonus
                if self.mostrar_logs:
                    print(f"✅ Bonus ({bonus}) aplicado a: '{frase.texto}'")