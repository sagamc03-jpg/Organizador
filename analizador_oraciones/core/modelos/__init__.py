"""
Modelos de datos del proyecto.
"""

from core.modelos.token_datos import Token
from core.modelos.chunks import Chunks, Actantes
from core.modelos.enunciado import FraseGenerada, Resultados

__all__ = [
    'Token',
    'Chunks',
    'FraseNominal',
    'FraseGenerada',
    'ResultadoAnalisis'
]