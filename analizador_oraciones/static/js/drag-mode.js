// =========================
// drag-mode.js – Modos Retroalimentación y Evaluación
// Depende de: dom.js, utils.js (deben cargarse antes en el HTML)
// Todas las referencias DOM viven en dom.js.
// Responsabilidad: drag & drop entre paneles + verificación con FastAPI.
// Feedback: visual en fichas
// =========================

// ── ESTADO ───────────────────────────────────────────────
let itemArrastrado = null; // ficha que está siendo arrastrada
let contadorIds = 0; // id único por ficha para evitar colisiones
let palabrasActuales = []; // palabras de la oración activa (para reiniciar)
let oracionCorrecta = []; // respuesta del backend – se guarda al primer envío
// los reintentos usan este valor sin llamar a la API

// =========================
// 1. ENTRADA – cargar palabras
// =========================

async function cargarPalabrasDrag() {
  const texto = elInput.value.trim();
  if (!texto) return;

  ocultarError(elErrorMsg);
  oracionCorrecta = []; // resetea respuesta anterior

  palabrasActuales = texto.split(/\s+/);
  contadorIds = 0;
  resetColores(); // utils.js

  _renderizarBanco(palabrasActuales);
  _limpiarPanel(
    elFichasDest,
    "Arrastra aquí las palabras para formar la oración.",
  );

  colapsarInput(elInputWrap); // utils.js

  // Llama a la API una sola vez al cargar – guarda la respuesta en estado.
  // verificarRespuesta() usará oracionCorrecta sin volver a llamar al backend.
  elBtnVerificar.disabled = true;
  mostrarEstado(elEstadoMsg, elEstadoTexto, "Preparando...");
  try {
    const data = await consultarAPI(texto); // utils.js
    oracionCorrecta = data.texto_corregido.trim().split(/\s+/);
    ocultarEstado(elEstadoMsg);
    // No activamos btnVerificar aquí – lo hace _actualizarVerificar() al mover fichas
    marcarEnvio(); // ui-controller.js
  } catch (error) {
    ocultarEstado(elEstadoMsg);
    mostrarError(
      elErrorMsg,
      "No se pudo conectar. ¿Está corriendo localhost:8000?",
    );
    expandirInput(elInputWrap, elInput);
  }
}

// =========================
// 2. RENDERIZADO
// =========================

function _renderizarBanco(palabras) {
  _limpiarPanel(elFichasOrig, "");

  palabras.forEach((palabra, idx) => {
    const ficha = _crearFichaDrag(palabra, idx);
    elFichasOrig.appendChild(ficha);
  });

  if (palabras.length === 0) {
    _ponerPlaceholder(elFichasOrig, "Aquí aparecen las palabras disponibles.");
  }
}

// Crea una ficha arrastrable – extiende crearFicha() de utils.js.
function _crearFichaDrag(texto, idx) {
  const ficha = crearFicha(texto, idx, true); // utils.js – draggable: true
  ficha.dataset.id = `ficha-${contadorIds++}`;

  ficha.addEventListener("dragstart", () => {
    itemArrastrado = ficha;
    setTimeout(() => ficha.classList.add("arrastrando"), 0);
  });

  ficha.addEventListener("dragend", () => {
    ficha.classList.remove("arrastrando");
    itemArrastrado = null;
    elFichasOrig.classList.remove("activa");
    elFichasDest.classList.remove("activa");
  });

  return ficha;
}

// =========================
// 3. DRAG & DROP
// =========================

// Inserta la ficha en la posición correcta según dónde suelta el usuario.
function _insertarFicha(panel, ficha, event) {
  _quitarPlaceholder(panel);

  // Considera fichas Y huecos para calcular la posición de inserción
  const hijos = [...panel.querySelectorAll(".ficha, .ficha-hueco")];
  let insertada = false;

  for (const actual of hijos) {
    const rect = actual.getBoundingClientRect();
    if (event.clientX < rect.left + rect.width / 2) {
      panel.insertBefore(ficha, actual);
      insertada = true;
      break;
    }
  }

  if (!insertada) panel.appendChild(ficha);

  // ── IMÁN ──────────────────────────────────────────────────────────────────
  // Si la ficha quedó pegada a un hueco (sibling inmediato izquierdo o derecho),
  // absorbe ese hueco: la ficha toma su lugar y el hueco desaparece.
  // Solo actúa cuando hay un hueco directamente adyacente, no a distancia.
  const huecoAnterior = ficha.previousElementSibling;
  const huecoSiguiente = ficha.nextElementSibling;

  if (huecoAnterior && huecoAnterior.classList.contains("ficha-hueco")) {
    huecoAnterior.remove();
  } else if (
    huecoSiguiente &&
    huecoSiguiente.classList.contains("ficha-hueco")
  ) {
    // Mueve la ficha al lugar del hueco (antes de él) y elimina el hueco
    panel.insertBefore(ficha, huecoSiguiente);
    huecoSiguiente.remove();
  }
  // ──────────────────────────────────────────────────────────────────────────
}

function _actualizarPlaceholders() {
  if (!elFichasOrig.querySelector(".ficha")) {
    _ponerPlaceholder(
      elFichasOrig,
      "Banco vacío. Puedes devolver fichas si quieres reorganizar.",
    );
  } else {
    _quitarPlaceholder(elFichasOrig);
  }

  if (!elFichasDest.querySelector(".ficha")) {
    _ponerPlaceholder(
      elFichasDest,
      "Arrastra aquí las palabras para formar la oración.",
    );
  } else {
    _quitarPlaceholder(elFichasDest);
  }

  _actualizarVerificar();
}

// Activa Verificar solo cuando todas las palabras están en el panel inferior
// (banco vacío) y hay una respuesta correcta cargada.
// Limpiar panel devuelve fichas al banco → botón se desactiva automáticamente.
// Solo Reiniciar o Editar+Enviar vuelven a cargar del modelo.
function _actualizarVerificar() {
  const bancioVacio = !elFichasOrig.querySelector(".ficha");
  const hayFichasAbajo = !!elFichasDest.querySelector(".ficha");
  const hayRespuesta = oracionCorrecta.length > 0;
  elBtnVerificar.disabled = !(bancioVacio && hayFichasAbajo && hayRespuesta);
}

function _configurarPanel(panel) {
  panel.addEventListener("dragover", (e) => {
    e.preventDefault();
    panel.classList.add("activa");
  });

  panel.addEventListener("dragleave", () => {
    panel.classList.remove("activa");
  });

  panel.addEventListener("drop", (e) => {
    e.preventDefault();
    panel.classList.remove("activa");
    if (!itemArrastrado) return;

    // Quita marcas de verificación previas al mover
    itemArrastrado.classList.remove("correcta", "incorrecta");

    _insertarFicha(panel, itemArrastrado, e);
    _actualizarPlaceholders();
  });
}

// =========================
// 4. VERIFICACIÓN
// =========================

// modo llega desde ui-controller.js – drag-mode.js no lee modoActivo directamente.
// Así este módulo no depende del estado interno de ui-controller.
function verificarRespuesta(modo) {
  // Limpia huecos del intento anterior
  elFichasDest.querySelectorAll(".ficha-hueco").forEach((h) => h.remove());

  const fichasAbajo = [...elFichasDest.querySelectorAll(".ficha")];
  if (fichasAbajo.length === 0) return;

  // Usa la respuesta guardada al cargar – sin llamar a la API de nuevo
  if (oracionCorrecta.length === 0) return;

  elBtnVerificar.disabled = true;

  if (modo === "retro") {
    _aplicarRetroalimentacion(fichasAbajo, oracionCorrecta);
  } else {
    _aplicarEvaluacion(fichasAbajo, oracionCorrecta);
  }
}

// =========================
// 5. MODO RETROALIMENTACIÓN
// =========================

// Correctas: se quedan, brillan en verde, quedan bloqueadas.
// Incorrectas: dejan un hueco gris en su posición y vuelven al banco.
// El hueco acepta drop – cuando el estudiante arrastra una ficha encima, desaparece.
function _aplicarRetroalimentacion(fichasAbajo, oracionCorrecta) {
  const incorrectas = [];
  let todasCorrectas = true;

  fichasAbajo.forEach((ficha, i) => {
    const esperada = oracionCorrecta[i]
      ? oracionCorrecta[i].toLowerCase()
      : null;
    const estaOk = esperada && ficha.dataset.palabra.toLowerCase() === esperada;

    if (estaOk) {
      ficha.classList.add("correcta");
      ficha.draggable = false;
      brillarFicha(ficha); // utils.js
    } else {
      incorrectas.push(ficha);
      todasCorrectas = false;
    }
  });

  incorrectas.forEach((ficha, i) => {
    setTimeout(() => {
      // Inserta hueco gris en la posición exacta de la ficha incorrecta
      const hueco = _crearHueco(ficha);
      elFichasDest.insertBefore(hueco, ficha);

      // Devuelve la ficha al banco
      ficha.classList.remove("incorrecta");
      ficha.draggable = true;
      _quitarPlaceholder(elFichasOrig);
      elFichasOrig.appendChild(ficha);
      _actualizarPlaceholders();

      // Al terminar de animar todas las incorrectas, recalcula el botón
      if (i === incorrectas.length - 1) {
        setTimeout(_actualizarVerificar, 50);
      }
    }, i * 120);
  });
  if (!todasCorrectas) {
    errorAnim(elPanelRes);
  }

  if (todasCorrectas) {
    elBtnVerificar.disabled = true;
    celebrar(elPanelRes);
  }
  // Si no todas correctas: _actualizarVerificar lo resolverá tras las animaciones
}

// Crea un hueco gris del mismo tamaño visual que una ficha.
// Acepta drop: cuando el estudiante suelta una ficha encima, el hueco desaparece
// y la ficha queda en esa posición.
function _crearHueco(fichaRef) {
  const hueco = document.createElement("div");
  hueco.className = "ficha-hueco";
  hueco.dataset.hueco = "true";

  // Mismo ancho aproximado que la ficha que reemplaza
  hueco.style.minWidth = fichaRef.offsetWidth + "px";

  // Acepta drag over
  hueco.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    hueco.classList.add("hueco-activo");
  });

  hueco.addEventListener("dragleave", () => {
    hueco.classList.remove("hueco-activo");
  });

  hueco.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation(); // evita que el panel capture el drop antes que el hueco
    hueco.classList.remove("hueco-activo");
    if (!itemArrastrado) return;

    // Coloca la ficha en la posición del hueco y elimina el hueco
    itemArrastrado.classList.remove("correcta", "incorrecta");
    elFichasDest.insertBefore(itemArrastrado, hueco);
    hueco.remove();
    _actualizarPlaceholders();
  });

  return hueco;
}

// =========================
// 6. MODO EVALUACIÓN
// =========================

// Correcto: todas brillan en verde y se bloquean.
// Incorrecto: todas vuelven al banco sin pistas de posición.
function _aplicarEvaluacion(fichasAbajo, oracionCorrecta) {
  const respuestaUsuario = fichasAbajo.map((f) =>
    f.dataset.palabra.toLowerCase(),
  );
  const correcta = oracionCorrecta.map((p) => p.toLowerCase());
  const esCorrecto = respuestaUsuario.join(" ") === correcta.join(" ");

  if (esCorrecto) {
    fichasAbajo.forEach((ficha) => {
      ficha.classList.add("correcta");
      ficha.draggable = false;
      brillarFicha(ficha); // utils.js
    });
    elBtnVerificar.disabled = true;
    celebrar(elPanelRes);
  } else {
    errorAnim(elPanelRes);
    fichasAbajo.forEach((ficha, i) => {
      setTimeout(() => {
        ficha.classList.remove("correcta", "incorrecta");
        ficha.draggable = true;
        _quitarPlaceholder(elFichasOrig);
        elFichasOrig.appendChild(ficha);
        _actualizarPlaceholders();

        if (i === fichasAbajo.length - 1) {
          setTimeout(_actualizarVerificar, 50);
        }
      }, i * 80);
    });
  }
}

// =========================
// 7. ACCIONES AUXILIARES
// =========================

// Devuelve todas las fichas del panel inferior al superior.
// También elimina los huecos grises que pudieran haber quedado.
function limpiarPanelInferior() {
  // Elimina huecos primero
  elFichasDest.querySelectorAll(".ficha-hueco").forEach((h) => h.remove());

  const fichasAbajo = [...elFichasDest.querySelectorAll(".ficha")];
  if (fichasAbajo.length === 0) {
    _ponerPlaceholder(
      elFichasDest,
      "Arrastra aquí las palabras para formar la oración.",
    );
    return;
  }

  fichasAbajo.forEach((ficha) => {
    ficha.classList.remove("correcta", "incorrecta");
    ficha.draggable = true;
    _quitarPlaceholder(elFichasOrig);
    elFichasOrig.appendChild(ficha);
  });

  _ponerPlaceholder(
    elFichasDest,
    "Arrastra aquí las palabras para formar la oración.",
  );
  _actualizarVerificar(); // banco ya no está vacío → desactiva Verificar
}

// Reinicia completamente el modo drag al estado inicial.
// Solo limpia lo propio – ui-controller.js coordina el resto tras llamar aquí.
function reiniciarDrag() {
  palabrasActuales = [];
  oracionCorrecta = [];
  contadorIds = 0;
  itemArrastrado = null;

  expandirInput(elInputWrap, elInput);
  elInput.value = "";

  _limpiarPanel(elFichasOrig, "Aquí aparecen las palabras disponibles.");
  _limpiarPanel(
    elFichasDest,
    "Arrastra aquí las palabras para formar la oración.",
  );

  elBtnVerificar.disabled = true;
}

// Llamada desde ui-controller.js al entrar a un modo drag.
function iniciarDrag() {
  itemArrastrado = null;
  _limpiarPanel(elFichasOrig, "Aquí aparecen las palabras disponibles.");
  _limpiarPanel(
    elFichasDest,
    "Arrastra aquí las palabras para formar la oración.",
  );
  elBtnVerificar.disabled = true;
}

// =========================
// 8. UTILIDADES PRIVADAS
// =========================

function _limpiarPanel(panel, placeholder) {
  panel.innerHTML = "";
  if (placeholder) _ponerPlaceholder(panel, placeholder);
}

function _ponerPlaceholder(panel, texto) {
  if (panel.querySelector(".ph")) return; // evita duplicados
  const ph = document.createElement("span");
  ph.className = "ph";
  ph.textContent = texto;
  panel.appendChild(ph);
}

function _quitarPlaceholder(panel) {
  const ph = panel.querySelector(".ph");
  if (ph) ph.remove();
}

// =========================
// 9. INICIALIZACIÓN
// =========================

// Configura ambos paneles como zonas de drop al cargar la página.
_configurarPanel(elFichasOrig);
_configurarPanel(elFichasDest);
