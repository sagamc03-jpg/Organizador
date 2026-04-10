from typing import List
from core.modelos.token_datos import Token

"""
Servicio de Validación de Concordancia.
Verifica la concordancia gramatical entre tokens.

Principio SOLID aplicado:
- Single Responsibility: Solo valida concordancia
- Open/Closed: Fácil extender reglas sin modificar código base
"""

class ValidarConcordancia:
    """
    Verifica que los tokens concuerden en género y número.
    """
    
    def validar_concordancia(self, chunk_actual: List[Token], nuevo_token: Token) -> bool:
        """
        Verifica si un nuevo token concuerda con un chunk actual.
            chunk_actual: Lista de tokens del chunk
            nuevo_token: Token a validar       
        """
        genero_ref = None
        numero_ref = None
        
        # PASO 1: Buscar NOUN como referencia
        for token in chunk_actual:
            if token.pos == "NOUN" and token.tiene_gen() and token.tiene_num():
                genero_ref = token.gen
                numero_ref = token.num
                break
        
        # PASO 2: Si no hay NOUN, buscar DET
        if not numero_ref:
            for token in chunk_actual:
                if token.pos == "DET" and token.tiene_num():
                    genero_ref = token.gen
                    numero_ref = token.num
                    break
        
        # PASO 3: Validar que haya referencia
        if not numero_ref:
            return False
        
        # PASO 4: Validar que el nuevo token tenga número
        if not nuevo_token.tiene_num():
            return False
        
        # PASO 5: Validar número (obligatorio)
        num_valido = nuevo_token.num == numero_ref
        
        # PASO 6: Validar género (si ambos lo tienen)
        if genero_ref and nuevo_token.tiene_gen():
            gen_valido = nuevo_token.gen == genero_ref
        else:
            gen_valido = True  # Si no hay género, se acepta
        
        return num_valido and gen_valido
    
    def validar_concordancia_dict(self, chunk_actual: List[dict], nuevo_token: dict) -> bool:
        """
        Versión compatible con diccionarios.
        """
        # Convertir diccionarios a Tokens
        tokens_chunk = [Token.para_diccionario(t) for t in chunk_actual]
        token_nuevo = Token.para_diccionario(nuevo_token)
        
        return self.validar_concordancia(tokens_chunk, token_nuevo)