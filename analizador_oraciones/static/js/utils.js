// =========================
// utils.js
// colores, animaciones, fichas y feddback
// pueden separarse pero por ahora se mantienen en utils. 
// =========================

// ── COLORES ──────────────────────────────────────────────────────────────────
//
// Sin rojo — genera fatiga visual en sesiones largas.
// Saturación moderada — señala relevancia sin sobrecargar.
const COLORES = [
  '#2563a8', // azul medio
  '#2d7d4f', // verde bosque
  '#6d3fa8', // violeta suave
  '#b06820', // ámbar oscuro
  '#1a7a7a', // teal
  '#7a6020', // dorado oscuro
  '#5c4ab0', // índigo
  '#6B7C93',
  '#C97A5A',
];

// Asocia cada palabra a un color durante la sesión.
// Si la palabra ya tiene color asignado, reutiliza el mismo.
// ¿Por qué un mapa y no solo idx % COLORES.length?
// Porque la misma palabra puede aparecer en posiciones distintas al corregir.
// El mapa garantiza que "casa" siempre sea el mismo color en ambos paneles.
let mapaColor = {};

function resetColores() {
  // Limpia el mapa al inicio de cada oración nueva.
  // Sin esto, los colores de una sesión anterior "contaminarían" la siguiente.
  mapaColor = {};
}

function getColor(palabra, idx) {
  const clave = palabra.toLowerCase();
  if (!mapaColor[clave]) {
    mapaColor[clave] = COLORES[idx % COLORES.length];
  }
  return mapaColor[clave];
}


// ── FICHAS ───────────────────────────────────────────────────────────────────
//
// Crea un elemento visual a partir de una palabra.
// Es compartida por app.js (fichas estáticas) y drag-mode.js (fichas arrastrables).
// ¿Por qué está aquí y no en cada módulo?
// Porque duplicar esta lógica en dos sitios significa que un cambio visual
// (padding, clase CSS, color) hay que hacerlo dos veces — fuente garantizada de bugs.
function crearFicha(texto, idx, draggable = false) {
  const ficha = document.createElement('div');
  ficha.className = 'ficha anim-aparecer';
  ficha.textContent = texto;
  ficha.dataset.palabra = texto;
  ficha.style.background = getColor(texto, idx);
  ficha.style.animationDelay = `${idx * 70}ms`;

  if (draggable) {
    ficha.draggable = true;
    ficha.style.cursor = 'grab';
  }

  return ficha;
}


// ── ANIMACIONES ──────────────────────────────────────────────────────────────

// wait(ms) — pausa asíncrona legible.
// Alternativa a setTimeout anidados: permite escribir "await wait(300)"
// dentro de funciones async en vez de callbacks dentro de callbacks.
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

// Agita todas las fichas de un contenedor para llamar la atención.
async function agitarFichas(contenedor) {
  contenedor.querySelectorAll('.ficha').forEach(ficha => {
    ficha.classList.remove('anim-shake');
    void ficha.offsetWidth; // fuerza reflow para reiniciar la animación CSS
    ficha.classList.add('anim-shake');
  });
  await wait(450);
}

// Hace brillar una ficha en verde para confirmar posición correcta.
function brillarFicha(ficha) {
  ficha.classList.remove('anim-glow');
  void ficha.offsetWidth; // mismo truco: reflow para reiniciar la animación
  ficha.classList.add('anim-glow');
}

// Anima una ficha volando entre dos posiciones absolutas en pantalla.
// Usada en modo animación para el vuelo de corrección.
// Recibe rectángulos del DOM (getBoundingClientRect) para saber de dónde a dónde volar.
function volarFicha(palabra, color, rectO, rectD) {
  return new Promise(resolve => {
    const fichaVoladora = document.createElement('div');
    fichaVoladora.className = 'ficha-voladora';
    fichaVoladora.textContent = palabra;
    fichaVoladora.style.background = color;
    fichaVoladora.style.left  = rectO.left + 'px';
    fichaVoladora.style.top   = rectO.top  + 'px';
    fichaVoladora.style.width = rectO.width + 'px';
    document.body.appendChild(fichaVoladora);

    const dx = rectD.left - rectO.left;
    const dy = rectD.top  - rectO.top;

    fichaVoladora.animate([
      { transform: 'translate(0,0) scale(1)',                                           opacity: 1 },
      { transform: `translate(${dx*0.5}px,${dy*0.4 - 45}px) scale(1.10)`, opacity: 1, offset: 0.45 },
      { transform: `translate(${dx}px,${dy}px) scale(1)`,                              opacity: 1 },
    ], {
      duration: 560,
      easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      fill: 'forwards'
    }).onfinish = () => {
      fichaVoladora.remove();
      resolve();
    };
  });
}

// ── UI FEEDBACK ──────────────────────────────────────────────────────────────
//
// Estas funciones reciben los elementos como parámetros en vez de acceder
// a variables globales directamente.
// ¿Por qué? Porque así son más fáciles de reutilizar y de testear:
// puedes llamarlas con cualquier elemento, no solo los específicos del HTML.

function mostrarEstado(elEstadoMsg, elEstadoTexto, msg) {
  elEstadoTexto.textContent = msg;
  elEstadoMsg.style.display = 'flex';
}

function ocultarEstado(elEstadoMsg) {
  elEstadoMsg.style.display = 'none';
}

function mostrarError(elErrorMsg, msg) {
  elErrorMsg.textContent = msg;
  elErrorMsg.style.display = 'block';
}

function ocultarError(elErrorMsg) {
  elErrorMsg.style.display = 'none';
}

function colapsarInput(elInputWrap) {
  elInputWrap.classList.add('colapsado');
}

function expandirInput(elInputWrap, elInput) {
  elInputWrap.classList.remove('colapsado');
  elInput.focus();
}

// ── CELEBRACIÓN Y ERROR VISUAL ───────────────────────────────────────────────

function celebrar(panelEl) {
  // Brillo del panel
  panelEl.classList.remove('panel-correcto');
  void panelEl.offsetWidth;
  panelEl.classList.add('panel-correcto');
  // { once: true } garantiza que el listener no se acumule entre llamadas (SRP de limpieza)
  panelEl.addEventListener('animationend', () => {
    panelEl.classList.remove('panel-correcto');
  }, { once: true });

  // Confeti
  const colores = ['#3b82f6','#60a5fa','#93c5fd','#facc15','#34d399','#f472b6'];
  for (let i = 0; i < 72; i++) {
    const el = document.createElement('div');
    el.className = 'confeti-pieza';
    el.style.left            = Math.random() * 100 + 'vw';
    el.style.backgroundColor = colores[Math.floor(Math.random() * colores.length)];
    el.style.width           = (7 + Math.random() * 6) + 'px';
    el.style.height          = (7 + Math.random() * 6) + 'px';
    el.style.borderRadius    = Math.random() > 0.5 ? '50%' : '2px';
    el.style.animationDuration = (1.4 + Math.random() * 1.2) + 's';
    el.style.animationDelay    = (Math.random() * 0.4) + 's';
    document.body.appendChild(el);
    el.addEventListener('animationend', () => el.remove());
  }
}

function errorAnim(panelEl) {
  // Shake del panel
  panelEl.classList.remove('panel-error');
  void panelEl.offsetWidth;
  panelEl.classList.add('panel-error');
  panelEl.addEventListener('animationend', () => {
    panelEl.classList.remove('panel-error');
  }, { once: true });

  // Emoji flotante desde el centro del panel
  const rect    = panelEl.getBoundingClientRect();
  const emojis  = ['💪', '🔄','🔂'];
  const elegido = emojis[Math.floor(Math.random() * emojis.length)];

  const el = document.createElement('div');
  el.className  = 'emoji-flotante';
  el.textContent = elegido;
  el.style.left = (rect.left + rect.width / 2 - 20) + 'px';
  el.style.top  = (rect.top  + rect.height / 2)     + 'px';
  document.body.appendChild(el);
  el.addEventListener('animationend', () => el.remove());
}