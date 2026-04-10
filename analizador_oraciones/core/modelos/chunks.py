from dataclasses import dataclass, field
from typing import List, Optional
from core.modelos.token_datos import Token
from config.settings import settings

"""se crean las frases nominales
apartir de las palabras o tokens
"""
@dataclass      #se usa para modelos, contenedores, ahora el __init__
class Actantes:
    """
    Representa una Actantes, eje:"los estudiantes"
    """
    texto: str
    genero: Optional[str] = None
    numero: Optional[str] = None
    es_propio: bool = False

    def to_token(self) -> Token:
        """
        Convierte Actantes a Token para poder usar ValidarConcordancia.
        """
        return Token(
            texto=self.texto,
            pos="NOUN",
            gen=self.genero,
            num=self.numero
        )
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para compatibilidad"""
        return {
            "texto": self.texto,
            "gen": self.genero if self.genero else "",
            "num": self.numero if self.numero else ""
        }
    

@dataclass
class Chunks:
    """
    Contenedor de fragmentos y de palabras clasificadas por categoría
        fn: Lista de frases nominales
        ...
        combinaciones_ambiguas: Lista de combinaciones posibles en casos ambiguos
    """
    fn: List[Actantes] = field(default_factory=list)
    verbo_pre: List[str] = field(default_factory=list)
    adj: List[str] = field(default_factory=list)
    adv: List[str] = field(default_factory=list)
    #nombres: List[str] = field(default_factory=list)
    pron_imp: List[str] = field(default_factory=list) # "se" no siempre es un pronomobre imp, pero no varía
    verbo_num: Optional[str] = None
    verbo_gen: Optional[str] = None
    adv_negacion: Optional[str] = None
    combinaciones_ambiguas: List[dict] = field(default_factory=list)
    
    def agregar_frase_nominal(self, texto: str, genero: Optional[str] = None, 
                              numero: Optional[str] = None, es_propio: bool = False):
        """Agrega una Actantes al chunk"""
        fn = Actantes(texto=texto, genero=genero, numero=numero, es_propio=es_propio)
        self.fn.append(fn)
    
    def agregar_verbo(self, verbo: str):
        """Agrega una palabra al sintagma verbal"""
        self.verbo_pre.append(verbo)
    
    def tiene_verbo(self) -> bool:
        """Verifica si hay al menos un verbo"""
        return len(self.verbo_pre) > 0
    
    def tiene_frases_nominales(self) -> bool:
        """Verifica si hay frases nominales"""
        return len(self.fn) > 0
    
    def tiene_ambiguedad(self) -> bool:
        """Verifica si hay ambigüedad sintáctica"""
        return len(self.combinaciones_ambiguas) > 0
    
    def tiene_participio(self) -> bool:
        if len(self.verbo_pre) < 2:
            return False
        for v in self.verbo_pre:
            if any(v.endswith(t) for t in settings.TERMINACIONES_PARTICIPIO):
                return True
        
        return False
    
    def to_dict(self) -> dict:
        """
        Convierte a diccionario toda la info.
        """
        return {
            "fn": [fn.to_dict() for fn in self.fn],
            "verbo_pre": self.verbo_pre,
            "ADJ": self.adj,
            "ADV": self.adv,
            #"Nombres": self.nombres,
            "Pron_imp": self.pron_imp,
            "Verbo_num": self.verbo_num if self.verbo_num else "",
            "Verbo_gen": self.verbo_gen if self.verbo_gen else "",
            "adv_negacion": self.adv_negacion,
            "Combinaciones_ambiguas": self.combinaciones_ambiguas
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Chunks':
        """Crea un Chunks desde un diccionario"""
        chunks = cls()
        
        # Convertir fn
        for fn_dict in data.get("fn", []):
            chunks.fn.append(Actantes(
                texto=fn_dict.get("texto", ""),
                genero=fn_dict.get("gen") or None,
                numero=fn_dict.get("num") or None
            ))
        
        chunks.verbo_pre = data.get("verbo_pre", [])
        chunks.adj = data.get("ADJ", [])
        chunks.adv = data.get("ADV", [])
        #chunks.nombres = data.get("Nombres", [])
        chunks.pron_imp = data.get("Pron_imp", [])
        chunks.verbo_num = data.get("Verbo_num") or None
        chunks.verbo_gen = data.get("Verbo_gen") or None
        chunks.adv_negacion = data.get("adv_negacion")
        chunks.combinaciones_ambiguas = data.get("Combinaciones_ambiguas", [])
        
        return chunks
    
    def __str__(self) -> str:
        return f"Chunks(fn={len(self.fn)}, verbo_pre={len(self.verbo_pre)}, ADJ={len(self.adj)})"