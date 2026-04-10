import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import time
import spacy
print("🔄 Cargando el modelo GPT-2 en español...")

# Especificar qué modelo vamos a usar (uno entrenado en español)
nombre_del_modelo = "DeepESP/gpt2-spanish"

# Cargar el "traductor" que convierte palabras a números
tokenizador = AutoTokenizer.from_pretrained(nombre_del_modelo)

# Cargar el "cerebro" del modelo (GPT-2 entrenado en español)
modelo = AutoModelForCausalLM.from_pretrained(nombre_del_modelo)
modelo.eval()

print("✅ ¡Modelo cargado y listo para usar!")



nlp = spacy.load("es_core_news_lg", exclude=["parser"])

# ANÁLISIS LÉXICO 
def extraer_token(frase: str):
    doc = nlp(f"x {frase} x")
    token = doc[1]  # siempre en el centro
    return token.text, token.pos_, token.morph.to_dict()

def analizar_oracion(oracion: str):
    oracion = oracion.split()
    resultados = []
    for palabra in oracion:
        texto, pos, morph = extraer_token(palabra)

        # Corrección de POS tags específicos
        if (texto.lower() in ["perro", "carpintero", "acertijo"] and pos == "PROPN" or 
            (texto.lower() in ["mar", "tejado", "ave", "pájaro", "clóset", "techo", "cuarto", "horno", "armario", "agua"] and pos == "NOUN") or 
            (texto.lower() in ["médico", "paciente", "español"] and pos == "ADJ")):
            pos = "NOUN"
            morph = {"Gender": "Masc", "Number": "Sing"}

        gen = morph.get("Gender", "")
        num = morph.get("Number", "")

        resultados.append({
            "token": texto, 
            "pos": pos,
            "gen": gen,
            "num": num
        })
    return resultados



# CONCORDANCIA, dar  presición 
def concordancia_valida(chunk_actual, nuevo_token):
    """Verifica si un nuevo token concuerda en género y número con el chunk actual"""
    genero_ref = None
    numero_ref = None
    
    # Primero buscar NOUN
    for token in chunk_actual:
        if token["pos"] == "NOUN" and token.get("gen") and token.get("num"):
            genero_ref = token["gen"]
            numero_ref = token["num"]
            break
    
    # Si no hay NOUN, buscar DET  
    if not numero_ref:
        for token in chunk_actual:
            if token["pos"] == "DET" and token.get("num"):
                genero_ref = token.get("gen")
                numero_ref = token["num"]
                break

    if not numero_ref:
        return False
    
    if not nuevo_token.get("num"):
        return False
    
    num_valido = nuevo_token["num"] == numero_ref
    
    if genero_ref and nuevo_token.get("gen"):
        gen_valido = nuevo_token["gen"] == genero_ref
    else:
        gen_valido = True
    
    return num_valido and gen_valido

# construir Chunks de forma ordenada, primero el verbo (dependencias)
def agregar_verbo(chunks, resultados, indices_usados):
    """Agrega verbos y construcciones verbales
    Agrega verbos y construcciones verbales.
    Se Modificam chunks e indices usados
    """
    # Procesar AUX + participio
    aux_idx = None
    for i, palabra in enumerate(resultados):
        if palabra["pos"] == "AUX" and i not in indices_usados:
            chunks["VP"].append(palabra["token"])
            indices_usados.add(i)
            chunks["Verbo_num"] = palabra.get("num", "")
            aux_idx = i
            break

    if aux_idx is not None:
        terminaciones_participio = [ "oto", "lto", "ado", "ido", "sto",
        "cho", "rto", "sta", "das", "dos", "ada", "do", "ito"]
        
        # Buscar participio como NOUN
        for i, palabra in enumerate(resultados):
            if i in indices_usados:
                continue
            if any(palabra["token"].endswith(t) for t in terminaciones_participio) and palabra["pos"] == "NOUN":
                chunks["VP"].append(palabra["token"])
                chunks["Verbo_gen"] = palabra.get("gen", "")
                indices_usados.add(i)
                return
        else:
            # Buscar participio como ADJ
            for i, palabra in enumerate(resultados):
                if i in indices_usados:
                    continue
                if any(palabra["token"].endswith(t) for t in terminaciones_participio) and palabra["pos"] == "ADJ":
                    chunks["VP"].append(palabra["token"])
                    chunks["Verbo_gen"] = palabra.get("gen", "")
                    indices_usados.add(i)
                    return
    
    # Procesar verbos principales
    for i, palabra in enumerate(resultados):
        if palabra["pos"] == "VERB" and i not in indices_usados:
            chunks["VP"].append(palabra["token"])
            chunks["Verbo_num"] = palabra.get("num", "")
            indices_usados.add(i)
            return
    
    # Buscar sustantivos verbales si no hay verbos
    sustantivos_verbales = {'baila', 'copia', 'manda', 'guarda', 'cura', 'compra', 'canto', 'uso', 
                           'copio', 'pelea', 'bebe', 'mira', 'ama', 'odia', 'baja', 'caza', 'pesca', 
                           'cosecha', 'siembra', 'barniza', 'borda', 'rema', 'patina', 'brinca', 
                           'trota', 'escala', 'resbala', 'gira', 'ata', 'suelta', 'agarra', 'pega', 
                           'empuña', 'lanza', 'tira', 'custodia', 'combate', 'debate', 'corta', 
                           'rota', 'afloja', 'martilla', 'atornilla', 'pilota', 'bucea', 'surfea', 
                           'trepa', 'empuja', 'nada', 'es', 'ladra', "vino", 'entrevista', 'muerde'}
    
    if len(chunks["VP"]) == 0:
        for i, palabra in enumerate(resultados):
            if i in indices_usados:
                continue
            if palabra["token"].lower() in sustantivos_verbales:
                chunks["VP"].append(palabra["token"])
                indices_usados.add(i)
                palabra["pos"] = "VERB"
                chunks["Verbo_num"] = "Sing"
                return

def agregar_preposiciones(chunks, resultados, indices_usados):
    """Agrega preposiciones al chunk verbal"""
    preposiciones_especiales = {"a", "desde", "entre", "hacia", "según", "hasta", "contra"}
    for i, palabra in enumerate(resultados):
        if i in indices_usados:
            continue
        es_prepo = (palabra["pos"] == "ADP" or 
                   (palabra["pos"] == "NOUN" and palabra["token"].lower() in preposiciones_especiales))
        if es_prepo:
            chunks["VP"].append(palabra["token"])
            indices_usados.add(i)
            break
def extraer_determinantes(resultados, indices_usados):
    """
    Extrae y clasifica determinantes en definidos e indefinidos.
    """
    # Identificar determinantes
    dets_indices = []
    for i, palabra in enumerate(resultados):
        if palabra["pos"] == "DET" and i not in indices_usados:
            dets_indices.append((i, palabra))
    
    # Separar DET definidos e indefinidos
    dets_definidos = []
    dets_indefinidos = []
    
    for i, det in dets_indices:
        genero = det.get("gen")
        if genero in ["Masc", "Fem"]:
            dets_definidos.append((i, det))
        else:
            dets_indefinidos.append((i, det))
    
    # Ordenar: definidos primero
    dets_ordenados = dets_definidos + dets_indefinidos
    total_dets = len(dets_indices)
    
    return dets_ordenados, total_dets

def detectar_ambiguedad(resultados, indices_usados):
    """
    Detecta si hay ambigüedad: UN solo DET que concuerda con varios nouns.
    Retorna ambiguedad y las palabras que se usaron
    """
    # Usar tu función existente
    dets_ordenados, total_dets = extraer_determinantes(resultados, indices_usados)
    
    # debe haber un det
    if total_dets != 1:
        return False, None, [], []  
    
    # Tomar el único DET
    i_det, det = dets_ordenados[0]
    
    # buscar nouns compatibles
    nouns_compatibles = []  
    for i_noun, noun in enumerate(resultados):
        if noun["pos"] != "NOUN" or i_noun in indices_usados:
            continue
        if concordancia_valida([det], noun):
            nouns_compatibles.append((i_noun, noun))  
    
    # deben haber dos nouns compatibles
    if len(nouns_compatibles) <= 1:
        return False, None, [], []  
    
    # PASO 3: Buscar ADJs disponibles
    adjs_compatibles = []  
    for i_adj, adj in enumerate(resultados):
        if adj["pos"] != "ADJ" or i_adj in indices_usados:
            continue
        for i_noun, noun in nouns_compatibles:
                if concordancia_valida([noun], adj):
                    adjs_compatibles.append((i_adj, adj))
                    break
    
    # si hay ambiguedad
    return True, (i_det, det), nouns_compatibles, adjs_compatibles

def procesar_datos_ambiguos(chunks, det_info, nouns_compatibles, adjs_compatibles, indices_usados):
    """
    2 nouns máximo, 1 ADJ máximo.
    """
    i_det, det = det_info

    # 1. Extraer datos básicos
    det_token = det["token"]
    
    # Siempre hay 2 nouns 
    (i_noun1, noun1), (i_noun2, noun2) = nouns_compatibles[0], nouns_compatibles[1]
    sus1, sus2 = noun1["token"], noun2["token"]
    
    # 2. LAS 2 COMBINACIONES BASE
    combinaciones = []
    if not adjs_compatibles:

        combinaciones = [
            {"sujeto": f"{det_token} {sus1}", "objeto": sus2},  # DET+NOUN1 + NOUN2
            {"sujeto": f"{det_token} {sus2}", "objeto": sus1}   # DET+NOUN2 + NOUN1
        ]
    
    else:
        i_adj, adj = adjs_compatibles[0]
        adj_u = adj["token"]
        
        # AGREGAR LAS 4 COMBINACIONES CON ADJ 
        combinaciones.append({
            "sujeto": f"{det_token} {sus1} {adj_u}",
            "objeto": sus2
        })
        
        # 2. DET+NOUN2+ADJ + NOUN1
        combinaciones.append({
            "sujeto": f"{det_token} {sus2} {adj_u}",
            "objeto": sus1
        })
        
        # 3. DET+NOUN1 + NOUN2+ADJ
        combinaciones.append({
            "sujeto": f"{det_token} {sus1}",
            "objeto": f"{sus2} {adj_u}"
        })
        
        # 4. DET+NOUN2 + NOUN1+ADJ
        combinaciones.append({
            "sujeto": f"{det_token} {sus2}",
            "objeto": f"{sus1} {adj_u}"
        })
    
    # 3. Guardar
    chunks["Combinaciones_ambiguas"] = combinaciones
    
    # 4. Marcar índices usados
    indices_usados.update([i_det, i_noun1, i_noun2])
    if adjs_compatibles:
        indices_usados.add(i_adj)
    
    return len(combinaciones)

def agregar_frases_nominales(chunks, resultados, indices_usados):
    """Construye frases nominales (DET + NOUN + ADJ)"""
    dets_ordenados, total_dets = extraer_determinantes(resultados, indices_usados)

    for i_det, det in dets_ordenados:
        if i_det in indices_usados:
            continue
        
        # PASO 1: Separar NOUNs con género/número registrado vs sin registrar
        nouns_con_gennum = []  # NOUNs con gen y num
        nouns_sin_gennum = []  # NOUNs con gen='' o num=''
        
        for i_noun, noun in enumerate(resultados):
            if noun["pos"] != "NOUN" or i_noun in indices_usados:
                continue
            
            tiene_gen = noun.get("gen", "") != ""
            tiene_num = noun.get("num", "") != ""
            
            if tiene_gen and tiene_num:
                nouns_con_gennum.append((i_noun, noun))
            else:
                nouns_sin_gennum.append((i_noun, noun))
        
        # PASO 2: Intentar primero con NOUNs que tienen género/número
        encontrado = False
        for i_noun, noun in nouns_con_gennum:
            if concordancia_valida([det], noun):
                fn_datos = {
                    "texto": det["token"] + " " + noun["token"],
                    "num": noun.get("num", ""),
                    "gen": noun.get("gen", "")
                }
                np_indices = [i_det, i_noun]
                chunk_actual = [det, noun]
                
                # Agregar ADJ si hay más de un DET
                if total_dets > 1:
                    for i_adj, adj in enumerate(resultados):
                        if adj["pos"] != "ADJ":
                            continue
                        if i_adj in indices_usados:
                            continue
                        
                        if concordancia_valida(chunk_actual, adj):
                            fn_datos["texto"] += " " + adj["token"]
                            np_indices.append(i_adj)
                            break
                
                chunks["NP"].append(fn_datos)
                for idx in np_indices:
                    indices_usados.add(idx)
                encontrado = True
                break  # Encontrado, salir del bucle de NOUNs con gen/num
        
        # PASO 3: Si no se encontró con NOUNs con gen/num, intentar con NOUNs sin gen/num
        if not encontrado:
            for i_noun, noun in nouns_sin_gennum:
                # Inferir número del NOUN basado en terminación
                num_inferido = ""
                if noun["token"].endswith("s"):
                    num_inferido = "Plur"
                else:
                    num_inferido = "Sing"
                
                # Verificar si el DET concuerda con el número inferido
                det_num = det.get("num", "")
                if det_num == num_inferido:
                    # Usar el género del DET si está disponible
                    gen_asignado = det.get("gen", "")
                    
                    fn_datos = {
                        "texto": det["token"] + " " + noun["token"],
                        "num": num_inferido,
                        "gen": gen_asignado
                    }
                    np_indices = [i_det, i_noun]
                    
                    # Crear chunk_actual con morfología actualizada para concordancia ADJ
                    noun_actualizado = noun.copy()
                    noun_actualizado["num"] = num_inferido
                    if gen_asignado:
                        noun_actualizado["gen"] = gen_asignado
                    chunk_actual = [det, noun_actualizado]
                    
                    # Agregar ADJ si hay más de un DET
                    if total_dets > 1:
                        for i_adj, adj in enumerate(resultados):
                            if adj["pos"] != "ADJ":
                                continue
                            if i_adj in indices_usados:
                                continue
                            
                            if concordancia_valida(chunk_actual, adj):
                                fn_datos["texto"] += " " + adj["token"]
                                np_indices.append(i_adj)
                                break
                    
                    chunks["NP"].append(fn_datos)
                    for idx in np_indices:
                        indices_usados.add(idx)
                    break  # Encontrado, salir del bucle de NOUNs sin gen/num
                
def agregar_nombres_sin_articulos(chunks, resultados, indices_usados):
    """Agrega nombres sin artículos"""
    for i, palabra in enumerate(resultados):
        if i in indices_usados:
            continue
        if palabra["pos"] == "NOUN":
            chunks["NP"].append({
                "texto": palabra["token"],
                "num": palabra.get("num", ""),
                "gen": palabra.get("gen", "")
            })
            indices_usados.add(i)

def agregar_nombres_propios_pronombres(chunks, resultados, indices_usados):
    """Agrega nombres propios y pronombres"""
    for i, palabra in enumerate(resultados):
        if i in indices_usados:
            continue
        if palabra["pos"] == "PROPN" or palabra["pos"] == "PRON":
            chunks["Nombres"].append(palabra["token"])
            indices_usados.add(i)

def agregar_pronombres_impersonales(chunks, resultados, indices_usados):
    """Agrega pronombres impersonales"""
    for i, palabra in enumerate(resultados):
        if i in indices_usados:
            continue
        if palabra["pos"] == "PRON" and palabra["token"].lower() == "se":
            chunks["Pron_imp"].append(palabra["token"])
            indices_usados.add(i)
            break

def agregar_adjetivos(chunks, resultados, indices_usados):
    """Agrega adjetivos sueltos"""
    for i, palabra in enumerate(resultados):
        if i in indices_usados:
            continue
        if palabra["pos"] == "ADJ":
            chunks["ADJ"].append(palabra["token"])
            indices_usados.add(i)

def agregar_adverbios(chunks, resultados, indices_usados):
    """Agrega adverbios de negación"""
    adverbios_negacion = {"no", "nunca", "jamás", "tampoco", "ni"}
    for i, palabra in enumerate(resultados):
        if i in indices_usados:
            continue
        if palabra["pos"] == "ADV" and palabra["token"].lower() in adverbios_negacion:
            chunks["adv_negacion"] = palabra["token"]
            chunks["ADV"].append(palabra["token"])
            indices_usados.add(i)
            break

def generar_chunks(resultados):
    """Función principal que coordina la construcción de todos los chunks"""
    chunks = {
        "NP": [],
        "Nombres": [],
        "VP": [],
        "ADJ": [],
        "ADV": [],
        "Pron_imp": [],
        "Verbo_num": "",
        "Verbo_gen": "",
        "Combinaciones_ambiguas": []
    }
    
    indices_usados = set()
    
    # Orden de procesamiento (puedes ajustarlo)
    agregar_verbo(chunks, resultados, indices_usados)
    agregar_preposiciones(chunks, resultados, indices_usados)
    hay_amb, det_info, nouns_compat, adjs_disp = detectar_ambiguedad(resultados, indices_usados)
    if hay_amb:
        procesar_datos_ambiguos(chunks, det_info, nouns_compat, adjs_disp, indices_usados)
    else:
        agregar_frases_nominales(chunks, resultados, indices_usados)
        agregar_nombres_sin_articulos(chunks, resultados, indices_usados)
    agregar_pronombres_impersonales(chunks, resultados, indices_usados)
    agregar_nombres_propios_pronombres(chunks, resultados, indices_usados)
    agregar_adjetivos(chunks, resultados, indices_usados)
    agregar_adverbios(chunks, resultados, indices_usados)
    
    return chunks

def construir_oracion(sujeto, adv_negacion, pron_imp, verbo_completo, objeto, adj= None):
    """Construye la oración en el orden correcto"""
    partes = []
    
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

def generar_oraciones(chunks):

    """Función principal que decide qué tipo de oraciones generar"""
    Combinaciones_ambiguas = chunks.get("Combinaciones_ambiguas", [])
    
    if Combinaciones_ambiguas:
        # Generar oraciones ambiguas
        oraciones = generar_oraciones_ambiguas(chunks)
        
        # 🔥 FILTRO GPT-2: Si hay más de una, elegir la mejor
        if len(oraciones) > 1:
            mejor = elegir_mejor_oracion(oraciones)
            return [mejor]  # Retornar solo la mejor
        else:
            return oraciones
    else:
        # Generar oraciones normales
        oraciones = generar_oraciones_n(chunks)
        
        # 🔥 FILTRO GPT-2: Si hay más de una, elegir la mejor
        if len(oraciones) > 1:
            mejor = elegir_mejor_oracion(oraciones)
            return [mejor]  # Retornar solo la mejor
        else:
            return oraciones

def generar_oraciones_n(chunks):
    """Genera oraciones siguiendo las reglas de concordancia y orden"""
    oraciones = []
    
    verbo_completo = ' '.join(chunks["VP"]) if chunks["VP"] else None
    
    if not verbo_completo:
        return ["No se pudo construir oración (falta verbo)"]
    
    # Identificar posibles sujetos (MODIFICADO: verificar si tiene determinante)
    sujetos_posibles = []
    otras_fn = []
    verbo_num = chunks.get("Verbo_num", "")
    
    for fn in chunks["NP"]:
        fn_num = fn.get("num", "")
        # NUEVA VALIDACIÓN: Solo considerar como sujeto posible si tiene determinante
        tiene_det = len(fn["texto"].split()) > 1
        
        if tiene_det and fn_num and verbo_num and fn_num == verbo_num:
            sujetos_posibles.append(fn)
        else:
            otras_fn.append(fn)
    
    # Elementos adicionales
    adv_negacion = chunks.get("adv_negacion", None)
    pron_imp = chunks["Pron_imp"][0] if chunks["Pron_imp"] else None
    
    # Lógica de construcción
    if len(chunks.get("Nombres", [])) > 0:
        sujeto = chunks["Nombres"][0]
        objeto = chunks["NP"][0]["texto"] if chunks["NP"] else None
        oraciones.append(construir_oracion(sujeto, adv_negacion, pron_imp, verbo_completo, objeto, None))
    
    elif len(sujetos_posibles) >= 2:
        sujeto1 = sujetos_posibles[0]["texto"]
        objeto1 = sujetos_posibles[1]["texto"]
        oraciones.append(construir_oracion(sujeto1, adv_negacion, pron_imp, verbo_completo, objeto1, None))
        oraciones.append(construir_oracion(objeto1, adv_negacion, pron_imp, verbo_completo, sujeto1, None))
    
    elif len(sujetos_posibles) == 1:
        sujeto = sujetos_posibles[0]["texto"]
        objeto = otras_fn[0]["texto"] if otras_fn else None
        adj = chunks["ADJ"][0] if chunks["ADJ"] else None
        oraciones.append(construir_oracion(sujeto, adv_negacion, pron_imp, verbo_completo, objeto, adj))
    
    elif len(chunks["NP"]) > 0:
        # MODIFICADO: Si no hay sujetos con determinante, considerar todas las NPs
        sujeto = chunks["NP"][0]["texto"]
        objeto = chunks["NP"][1]["texto"] if len(chunks["NP"]) > 1 else None
        oraciones.append(construir_oracion(sujeto, adv_negacion, pron_imp, verbo_completo, objeto, None))
    
    else:
        oraciones.append(construir_oracion(None, adv_negacion, pron_imp, verbo_completo, None))
    
    return oraciones

def generar_oraciones_ambiguas(chunks):
    """
    Genera oraciones para casos ambiguos usando construir_oracion().
    """
    if "Combinaciones_ambiguas" not in chunks:
        return []
    
    verbo_completo = ' '.join(chunks["VP"]) if chunks["VP"] else ""
    adv_negacion = chunks.get("adv_negacion", None)
    pron_imp = chunks["Pron_imp"][0] if chunks["Pron_imp"] else None
    
    oraciones = []
    
    for combo in chunks["Combinaciones_ambiguas"]:
        # Usar construir_oracion() que ya tienes
        oracion = construir_oracion(
            sujeto=combo["sujeto"],
            adv_negacion=adv_negacion,
            pron_imp=pron_imp,
            verbo_completo=verbo_completo,
            objeto=combo["objeto"]
        )
        oraciones.append(oracion)
    
    return oraciones
#GPT
def medir_naturalidad(texto_a_analizar):
    """
    Analiza qué tan natural suena un texto en español usando GPT-2.
    
    Args:
        texto_a_analizar (str): La oración que queremos evaluar
    
    Returns:
        tuple: (puntaje_naturalidad, tiempo_ejecucion)
            - puntaje_naturalidad: número más alto = más natural (menos pérdida)
            - tiempo_ejecucion: segundos que tardó el análisis
    """
    tiempo_inicio = time.time()
    
    # Convertir texto a tokens
    entrada_tokenizada = tokenizador(
        texto_a_analizar, 
        return_tensors="pt"
    )
    
    # Evaluar con el modelo (sin gradientes para ser más rápido)
    with torch.no_grad():
        resultados = modelo(
            **entrada_tokenizada,
            labels=entrada_tokenizada["input_ids"]
        )
        
        # Convertir pérdida en puntaje (negativo porque pérdida baja = mejor)
        puntaje_naturalidad = -resultados.loss.item()
    
    tiempo_fin = time.time()
    tiempo_total = tiempo_fin - tiempo_inicio
    
    return puntaje_naturalidad, tiempo_total


def elegir_mejor_oracion(lista_oraciones):
    """
    Dada una lista de oraciones, usa GPT-2 para elegir la más natural.
    
    Args:
        lista_oraciones (list): Lista de strings (oraciones candidatas)
    
    Returns:
        str: La oración con mayor puntaje de naturalidad
    """
    if len(lista_oraciones) == 0:
        return None
    
    if len(lista_oraciones) == 1:
        return lista_oraciones[0]
    
    print(f"\n{'='*60}")
    print(f"🔍 FILTRO GPT-2: Evaluando {len(lista_oraciones)} oraciones candidatas")
    print(f"{'='*60}")
    
    resultados = []
    
    for oracion in lista_oraciones:
        puntaje, tiempo = medir_naturalidad(oracion)
        resultados.append((oracion, puntaje, tiempo))
        print(f"📝 '{oracion:50}' → Puntaje: {puntaje:.4f} | Tiempo: {tiempo:.3f}s")
    
    # Encontrar la mejor
    mejor_oracion = max(resultados, key=lambda x: x[1])
    
    print(f"\n{'='*60}")
    print(f"🏆 GANADORA: '{mejor_oracion[0]}'")
    print(f"📊 Puntaje: {mejor_oracion[1]:.4f}")
    print(f"{'='*60}\n")
    
    return mejor_oracion[0]

# Test
if __name__ == "__main__":
    text = "mi su este ese va mí mío esta"
    print(f"Texto original: {text}")
    
    tokens = analizar_oracion(text)
    print(f"\nTokens analizados: {tokens}")
    
    chunks = generar_chunks(tokens)
    
    print("\n=== CHUNKS GENERADOS ===")
    print(f"Frases nominales (NP): {chunks['NP']}")
    print(f"Nombres: {chunks['Nombres']}")
    print(f"Verbo: {chunks['VP']}")
    print(f"Adjetivo: {chunks['ADJ']}")
    print(f"Adverbio: {chunks['ADV']}")
    print(f"Imper: {chunks['Pron_imp']}")
    print(f"Verbo num: {chunks['Verbo_num']}")
    print(f"Verbo gen: {chunks['Verbo_gen']}")
    print(f"ambiguedad: {chunks['Combinaciones_ambiguas']}")
    
    oraciones = generar_oraciones(chunks)
    
    print("\n=== ORACIONES GENERADAS ===")
    for i, oracion in enumerate(oraciones, 1):
        print(f"{i}: {oracion}")