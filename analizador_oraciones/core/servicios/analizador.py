import spacy
from typing import List
from core.modelos.token_datos import Token
from config.settings import settings

# no puedes usar dataclass por eso el constructor

class Analizador:
    def __init__(self):
        """
        Inicializa el analizador léxico cargando el modelo de spaCy.
        """
        print(f"🔄 Cargando modelo spaCy: {settings.SPACY_MODEL}...")
        self.nlp = spacy.load(settings.SPACY_MODEL, exclude=["parser", "ner"])
        print("✅ Modelo spaCy cargado correctamente")

    def extraer_token(self, palabra: str) -> Token:
        """
        Extrae información de una palabra individual usando spaCy.
        Trick: Agrega 'x' spaCy analice sin un contexto fijo
        """
        # Truco: agregar 'x' para contexto
        doc = self.nlp(f"x {palabra} x")
        token = doc[1]  # El token del medio y se extrae su información
        # Extraer información morfológica
        morph_dict = token.morph.to_dict()
        return Token(
            texto= token.text,
            pos= token.pos_,
            gen= morph_dict.get("Gender"),
            num= morph_dict.get("Number")
        )
    def _aplicar_correcciones_pos(self, token: Token) -> Token:
        """
        Aplica correcciones de POS tags según configuración.
        Algunas palabras son mal clasificadas por spaCy y necesitan corrección.
        recibe un token: Token original --> Token con correcciones aplicadas
        """
        palabra_lower = token.texto.lower()
        # Verificar si hay corrección configurada
        if palabra_lower in settings.CORRECCIONES_POS:
            c = settings.CORRECCIONES_POS[palabra_lower]
            return Token(
                texto= token.texto,
                pos= c["pos"],
                gen= c.get("gen"),
                num= c.get("num")
            )
        return token
    
    def analizar_oracion(self, oracion: str) -> List[Token]:
        """
        Analiza una oración completa y retorna lista de tokens.
        
        recibe oracion: Texto de la oración a analizar
        retorna: Lista de tokens con información morfológica
        """
        frase = oracion.split()
        tokens = []
        
        for palabra in frase:
            # Extraer token
            token = self.extraer_token(palabra)
            
            # Aplicar correcciones
            token = self._aplicar_correcciones_pos(token)
            
            tokens.append(token)
        
        return tokens
    # esto lo podemos convertir a una tabla
    def analizar_oracion_dict(self, oracion: str) -> List[dict]:
        """
        Retorna tokens como lista de diccionarios.
        oracion: Texto de la oración --- Lista de diccionarios
        """
        tokens = self.analizar_oracion(oracion)
        return [token.to_dict() for token in tokens]
    