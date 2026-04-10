from typing import List, Optional
from config import settings
from core.modelos.chunks import Chunks
from core.modelos.enunciado import FraseGenerada
#from core.servicios.construir_chunks import ConstructorDeChunks


class GeneradorOraciones:
    """
    Generador de frases/oraciones a partir de chunks sintácticos.

    Genera frases válidas siguiendo el orden sintáctico del español:
    Sujeto + Negación + Pronombre + Verbo + Objeto + Adjetivo
    """
    
    def generar_frases(self, chunks: Chunks) -> List[FraseGenerada]:
        """
        Decide si hay ambigüedad y llama al método correspondiente.
        """
        # Verificar si hay ambigüedad
        
        if chunks.tiene_ambiguedad():
            return self._generar_frases_ambiguas(chunks)
        else:
            return self._generar_frases_normales(chunks)
    
    # GENERACIÓN DE FRASES NORMALES
    
    def _generar_frases_normales(self, chunks: Chunks) -> List[FraseGenerada]:
        """
        Genera frases siguiendo reglas de concordancia y orden.
        chunks: Objeto Chunks
            Lista de FraseGenerada
        """
        frases = []
        
        # Construir verbo completo
        verbo_completo = ' '.join(chunks.verbo_pre) if chunks.verbo_pre else None
        adv_negacion = chunks.adv_negacion
        pron_imp = ' '.join(chunks.pron_imp) if chunks.pron_imp else None
        
        if not verbo_completo:
            frase_error = FraseGenerada(texto="No se pudo construir oración (falta verbo)")
            return [frase_error]
        
        # Identificar posibles sujetos (que concuerden con el verbo)
        sujetos_posibles = []
        otras_fn = []
        # 1. Detectar si hay participio (usando el método del modelo Chunks)
        tiene_participio = chunks.tiene_participio()

        for fn in chunks.fn:
            # Por defecto, nadie es sujeto seguro a menos que se demuestre lo contrario
            es_sujeto_seguro = False
            
            # REGLA DE ORO: Solo filtramos si hay participio
            if tiene_participio:
                # 2. Validación EXCLUSIVA y TOTAL (Sin Nones)
                # Ambos deben tener datos de género y número
                datos_completos = all([
                    fn.genero, fn.numero, 
                    chunks.verbo_gen, chunks.verbo_num
                ])
                
                if datos_completos:
                    # 3. Deben coincidir en AMBOS parámetros
                    concuerda_gen = (fn.genero == chunks.verbo_gen)
                    concuerda_num = (fn.numero == chunks.verbo_num)
                    
                    if concuerda_gen and concuerda_num:
                        es_sujeto_seguro = True

            # Clasificación
            if es_sujeto_seguro:
                sujetos_posibles.append(fn)
            else:
                # Si no hay participio, o hay un None, o no coinciden: 
                # va a otras_fn para que se generen permutaciones (GPT-2)
                otras_fn.append(fn)
        
        # LÓGICA DE CONSTRUCCIÓN
        
        # CASO 1: Hay nombres propios
        if len(otras_fn) >= 2:
            actante1 = otras_fn[0]
            actante2 = otras_fn[1]  #.texto if chunks.fn else None
            frase = self._construir_frase(
                sujeto=actante1.texto,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=actante2.texto,
                adj=None
            )
            frases.append(FraseGenerada(texto=frase))
            # Permutación 2: objeto1 + verbo + sujeto1
            frase2 = self._construir_frase(
                sujeto=actante2.texto,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=actante1.texto,
                adj=None
            )
            frases.append(FraseGenerada(texto=frase2))
        #caso 1B
        elif len(otras_fn) == 1 and len(sujetos_posibles) == 0 and chunks.adj:
            sujeto = otras_fn[0].texto
            adj = chunks.adj[0]
            frase = self._construir_frase(
                sujeto=sujeto,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=None,
                adj=adj
            )
            frases.append(FraseGenerada(texto=frase))
         
        # CASO 2: Hay 2 o más sujetos posibles (generar permutaciones)
        elif len(sujetos_posibles) >= 2:
            sujeto1 = sujetos_posibles[0].texto
            objeto1 = sujetos_posibles[1].texto
            
            # Permutación 1: sujeto1 + verbo + objeto1
            frase1 = self._construir_frase(
                sujeto=sujeto1,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=objeto1,
                adj=None
            )
            frases.append(FraseGenerada(texto=frase1))
            
            # Permutación 2: objeto1 + verbo + sujeto1
            frase2 = self._construir_frase(
                sujeto=objeto1,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=sujeto1,
                adj=None
            )
            frases.append(FraseGenerada(texto=frase2))
        
        # CASO 3: Hay 1 sujeto posible
        elif len(sujetos_posibles) == 1:
            sujeto = sujetos_posibles[0].texto
            objeto = otras_fn[0].texto if otras_fn else None
            adj = chunks.adj[0] if chunks.adj else None
            
            frase = self._construir_frase(
                sujeto=sujeto,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=objeto,
                adj=adj
            )
            frases.append(FraseGenerada(texto=frase))

        # Caso: 4 hay un fn pero con impersonal(posible tácito)
        elif len(otras_fn) == 1 and len(sujetos_posibles) == 0 and pron_imp:
            actante = otras_fn[0].texto
            adj = chunks.adj[0] if chunks.adj else None
            
            frase = self._construir_frase(
                sujeto=None,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=actante,
                adj=adj
            )
            frases.append(FraseGenerada(texto=frase))

            frase2 = self._construir_frase(
                sujeto=actante,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=None,
                adj=adj
            )
            frases.append(FraseGenerada(texto=frase2))
        
        # CASO 5: 
        # Genera 2 frases: fn como sujeto directo + fn como objeto (sujeto tácito)
        elif len(otras_fn) == 1 and len(sujetos_posibles) == 0:
            actante = otras_fn[0].texto
 
            # Frase 1: fn actúa como sujeto (sujeto + verbo, objeto implícito)
            frase1 = self._construir_frase(
                sujeto=actante,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=None,
                adj=None
            )
            frases.append(FraseGenerada(texto=frase1))
 
            # Frase 2: fn actúa como objeto (sujeto tácito en la conjugación verbal)
            frase2 = self._construir_frase(
                sujeto=None,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=actante,
                adj=None
            )
            frases.append(FraseGenerada(texto=frase2))

        """# Caso 5b: poco probable, verbo y un adjetivo
        elif len(otras_fn) == 0 and len(sujetos_posibles) == 0:
            adj = chunks.adj[0] if chunks.adj else None
            frase1 = self._construir_frase(
                sujeto=None,
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=None,
                adj= adj
            )
            frases.append(FraseGenerada(texto=frase1))"""

        return frases
    
    def _construir_frase(self, sujeto: Optional[str], adv_negacion: Optional[str],
        pron_imp: Optional[str],verbo_completo: str, objeto: Optional[str],
        adj: Optional[str] = None) -> str:
        """
        Construye la frase en el orden sintáctico correcto.
        Orden sintáctico del español:
        Sujeto + Negación + Pronombre + Verbo + Objeto + Adjetivo
        Returns: Frase completa como string
        """
        partes = []
        
        # ORDEN: Sujeto + Negación + Pronombre + Verbo + Objeto + Adjetivo
        
        if sujeto:
            partes.append(sujeto)
        
        if adv_negacion:
            partes.append(adv_negacion)
        
        if pron_imp:
            partes.append(pron_imp)
        
        partes.append(verbo_completo)
        
        if objeto:
            partes.append(objeto)
        
        if adj:
            partes.append(adj)
        
        return ' '.join(partes)
    

    # GENERACIÓN DE FRASES AMBIGUAS
    
    def _generar_frases_ambiguas(self, chunks: Chunks) -> List[FraseGenerada]:
        """
        Genera frases para casos ambiguos.
        Caso ambiguo: UN DET que concuerda con MÚLTIPLES NOUNs.

        chunks: Objeto Chunks con combinaciones_ambiguas
        Lista de FraseGenerada (una por cada combinación)
        """
        if not chunks.combinaciones_ambiguas:
            return []
        
        verbo_completo = ' '.join(chunks.verbo_pre) if chunks.verbo_pre else ""
        adv_negacion = chunks.adv_negacion
        pron_imp = chunks.pron_imp[0] if chunks.pron_imp else None
        
        frases = []
        
        for combo in chunks.combinaciones_ambiguas:
            frase = self._construir_frase(
                sujeto=combo["sujeto"],
                adv_negacion=adv_negacion,
                pron_imp=pron_imp,
                verbo_completo=verbo_completo,
                objeto=combo["objeto"],
                adj=None
            )
            
            frase_generada = FraseGenerada(
                texto=frase,
                es_ambigua=True
            )
            frases.append(frase_generada)
        
        return frases
    
    def generar_frases_dict(self, chunks_dict: dict) -> List[str]:
        """
        Versión compatible con diccionarios (tu código original).
            chunks_dict: Diccionario de chunks con formato:
            Lista de strings (frases generadas)
        """
        # Convertir diccionario a Chunks
        chunks = Chunks.from_dict(chunks_dict)
        
        # Generar frases
        frases = self.generar_frases(chunks)
        
        # Convertir a lista de strings
        return [frase.texto for frase in frases]