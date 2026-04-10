from dataclasses import dataclass
from typing import Optional

"""Aquí se representa todo lo que tiene que ver con un token"""
@dataclass
class Token:
    texto: str
    pos: str             #categoria gramatical
    gen: Optional[str] = None   #género
    num: Optional[str] = None   #número
    
    def __post_init__(self):
        """Validación básica después de inicialización"""
        if not self.texto:
            raise ValueError("El texto del token no puede estar vacío")
        if not self.pos:
            raise ValueError("El POS tag es obligatorio")
        
    #retorna un booleano verdadero o falso -> bool
    def tiene_gen(self) -> bool:
        """Verifica si el token tiene género definido"""
        return self.gen is not None and self.gen != ""
    
    def tiene_num(self) -> bool:
        """Verifica si el token tiene número definido"""
        return self.num is not None and self.num != ""
    
    def concuerda_con(self, otro: 'Token') -> bool: 
        """
        Verifica si este token concuerda en género y número con otro token.
        """
        # Verificar número (obligatorio para concordancia)
        if not self.tiene_num() or not otro.tiene_num():
            return False
        
        if self.num != otro.num:
            return False
        
        # Verificar género (si ambos lo tienen)
        if self.tiene_gen() and otro.tiene_gen():
            return self.gen == otro.gen
        
        return True
    
    def crear_diccionario(self) -> dict:
        """Convierte el token a diccionario"""
        return print({
            "token": self.texto,
            "pos": self.pos,
            "gen": self.gen if self.gen else "",
            "num": self.num if self.num else ""
        })
    def to_dict(self) -> dict:
        return self.crear_diccionario()
    
    @classmethod
    def para_diccionario(cls, data: dict) -> 'Token':
        """Crea un Token desde un diccionario"""
        return cls(
            texto= data.get("token", ""),
            pos= data.get("pos", ""),
            gen= data.get("gen") if data.get("gen") else None,
            num= data.get("num") if data.get("num") else None
        )
    
    def __str__(self) -> str:
        return f"{self.texto} ({self.pos})"
    
    def __repr__(self) -> str:
        return f"Token(texto='{self.texto}', pos='{self.pos}', gen={self.gen}, num={self.num})"