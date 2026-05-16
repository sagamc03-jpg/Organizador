// =========================
// ui-controller.js
// Responsabilidad única: gestionar el estado de modo y actualizar la UI.
// Depende de: utils.js, app.js, drag-mode.js (deben cargarse antes).
// El HTML no tiene lógica — solo llama a funciones definidas aquí.
// Para agregar un modo: añadir una entrada en TITULOS, LABELS y ACCION_ENVIO.
// =========================

// ── ESTADO DE MODO ────────────────────────────────────
let modoActivo = 'animacion';

// Flag compartido con app.js y drag-mode.js.
// Se activa cuando el usuario envía una oración y recibe respuesta.
// cambiarModo() lo consulta para decidir si resetea los paneles.
let yaSeEnvio = false;
function marcarEnvio()   { yaSeEnvio = true;  }
function resetearEnvio() { yaSeEnvio = false; }

// ── CONFIGURACIÓN POR MODO ────────────────────────────
// Agregar un modo nuevo = una entrada en cada tabla, nada más.
// Ninguna función de abajo necesita saber qué modos existen.
const TITULOS = {
  animacion : 'Corrector de Oraciones',
  retro     : 'Retroalimentación',
  eval      : 'Evaluación'
};

const LABELS = {
  animacion : { superior: 'Oración ingresada',    inferior: 'Oración corregida' },
  retro     : { superior: 'Palabras disponibles', inferior: 'Tu oración'        },
  eval      : { superior: 'Palabras disponibles', inferior: 'Tu oración'        }
};

// Qué función ejecutar al enviar según el modo activo.
// app.js y drag-mode.js deben cargarse antes para que estas referencias resuelvan.
const ACCION_ENVIO = {
  animacion : mostrarYProcesar,    // app.js
  retro     : cargarPalabrasDrag,  // drag-mode.js
  eval      : cargarPalabrasDrag,  // drag-mode.js
};

// Si el modo usa drag & drop — controla visibilidad de paneles y botones.
const ES_DRAG = {
  animacion : false,
  retro     : true,
  eval      : true,
};

// ── CAMBIO DE MODO ────────────────────────────────────
function cambiarModo(modo) {
  modoActivo = modo;

  // Actualiza botones del selector
  document.querySelectorAll('.modo-btn').forEach(b => b.classList.remove('activo'));
  document.getElementById('modo' + _capitalize(modo)).classList.add('activo'); // dinámico — no puede ir a dom.js

  // Actualiza título y labels
  elTituloApp.textContent     = TITULOS[modo];
  elLabelSuperior.textContent = LABELS[modo].superior;
  elLabelInferior.textContent = LABELS[modo].inferior;

  const esDrag = ES_DRAG[modo];

  // Si ya se envió una oración, resetea los paneles al cambiar de modo.
  // El input se conserva siempre — el profesor puede reutilizar la oración.
  if (yaSeEnvio) {
    _resetearPaneles();
    resetearEnvio();
  }

  // Visibilidad de elementos exclusivos por modo
  // hayResultadoPendiente() — app.js expone su estado sin revelar la variable interna
  const hayPendiente = !esDrag && hayResultadoPendiente();
  elBtnRevelar.classList.toggle('visible', hayPendiente);
  elOpcionesWrap.style.display = 'none';
  elAccionesDrag.classList.toggle('visible', esDrag);

  // Panel inferior: siempre activo en drag, inactivo en animación hasta recibir respuesta
  elPanelRes.classList.toggle('panel-drag', esDrag);
  elPanelRes.classList.toggle('panel-resultado', !esDrag);
  if (!esDrag) elPanelRes.classList.remove('listo');

  if (esDrag) iniciarDrag(); // drag-mode.js
}

// ── RESET DE PANELES ──────────────────────────────────
// Limpia ambos paneles al cambiar de modo tras un envío previo.
// El input se expande para que el profesor pueda reenviar si quiere.
function _resetearPaneles() {
  elFichasOrig.innerHTML = '<span class="ph">Aquí aparecerá tu oración...</span>';
  elFichasDest.innerHTML = '<span class="ph">Esperando resultado...</span>';
  expandirInput(elInputWrap, elInput);
  elBtnEnviar.disabled = false;
  elBtnRevelar.classList.remove('visible');
  limpiarPendiente(); // app.js — no tocamos estadoPendiente directamente
}

// ── ACCIONES ──────────────────────────────────────────
// El HTML llama siempre a estas funciones.
// No saben nada de app.js ni drag-mode.js — solo consultan las tablas.

function enviar() {
  ACCION_ENVIO[modoActivo]();
}

function verificar() {
  verificarRespuesta(modoActivo); // le pasa el modo — drag-mode.js no lo lee solo
}

function editar() {
  expandirInput(elInputWrap, elInput);
  elBtnEnviar.disabled = false;
}

// Coordina el reinicio completo del modo drag.
// drag-mode.js limpia su estado interno — ui-controller hace el resto.
function reiniciar() {
  reiniciarDrag();       // drag-mode.js — limpia fichas, banco, estado interno
  resetearEnvio();       // ui-controller — resetea su propio flag
  renderizarEjemplos();  // ui-controller — rota los ejemplos del input
}

function usarEjemplo(texto) {
  elInput.value = texto;
  enviar();
}

// ── HELPERS PRIVADOS ──────────────────────────────────

function _capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ── EJEMPLOS ALEATORIOS ───────────────────────────────
function renderizarEjemplos() {
  const fila = document.querySelector('.ejemplos-row');
  fila.innerHTML = '';
  obtenerEjemplosAleatorios(4).forEach(texto => {
    const btn = document.createElement('button');
    btn.className = 'ej-btn';
    btn.textContent = texto.length > 24 ? texto.slice(0, 24) + '...' : texto;
    btn.title = texto; // muestra el texto completo en hover
    btn.onclick = () => usarEjemplo(texto);
    fila.appendChild(btn);
  });
}

// Carga ejemplos al iniciar la página
renderizarEjemplos();