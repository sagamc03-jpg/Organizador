from dataclasses import dataclass
from typing import Optional

@dataclass
class FraseGenerada:
    """
    Representa una oración generada por el sistema.
    Attributes:
        texto: El texto de la oración
        puntaje_naturalidad: Puntaje de naturalidad (GPT-2)
        tiempo_evaluacion: Tiempo que tardó en evaluar (segundos)
        es_ambigua: Si la oración proviene de un caso ambiguo
    """
    texto: str
    puntaje_naturalidad: Optional[float] = None
    tiempo_evaluacion: Optional[float] = None
    es_ambigua: bool = False
    
    def __post_init__(self):
        """Validación básica"""
        if not self.texto or self.texto.strip() == "":
            raise ValueError("El texto de la oración no puede estar vacío")
    
    def fue_evaluada(self) -> bool:
        """Verifica si la oración fue evaluada con GPT-2"""
        return self.puntaje_naturalidad is not None
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para API"""
        return {
            "texto": self.texto,
            "puntaje_naturalidad": self.puntaje_naturalidad,
            "tiempo_evaluacion": self.tiempo_evaluacion,
            "es_ambigua": self.es_ambigua
        }
    
    def __str__(self) -> str:
        if self.fue_evaluada():
            return f"{self.texto} (puntaje: {self.puntaje_naturalidad:.4f})"
        return self.texto
    
    def __repr__(self) -> str:
        return f"FraseGenerada(texto='{self.texto}', puntaje={self.puntaje_naturalidad})"


@dataclass
class Resultados:
    """
    Resultado completo del análisis de una oración.
    
    Attributes:
        texto_original: Texto ingresado por el usuario
        oraciones_generadas: Lista de oraciones generadas
        mejor_oracion: La mejor oración según GPT-2
        chunks_info: Información sobre los chunks (opcional, para debugging)
    """
    texto_original: str
    oraciones_generadas: list[FraseGenerada]
    mejor_oracion: Optional[FraseGenerada] = None
    chunks_info: Optional[dict] = None
    
    def tiene_resultados(self) -> bool:
        """Verifica si se generaron oraciones"""
        return len(self.oraciones_generadas) > 0
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para API"""
        result = {
            "texto_original": self.texto_original,
            "oraciones_generadas": [s.to_dict() for s in self.oraciones_generadas],
            "mejor_oracion": self.mejor_oracion.to_dict() if self.mejor_oracion else None,
        }
        
        if self.chunks_info:
            result["chunks_info"] = self.chunks_info
        
        return result
    
    def __str__(self) -> str:
        if self.mejor_oracion:
            return f"Mejor: {self.mejor_oracion.texto}"
        elif self.tiene_resultados():
            return f"Generadas: {len(self.oraciones_generadas)} oraciones"
        return "Sin resultados"