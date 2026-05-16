// =========================
// dom.js
// Responsabilidad única: resolver IDs del HTML a referencias vivas.
// Ningún módulo declara getElementById por su cuenta — todos leen de aquí.
// Si un ID cambia en el HTML, se corrige en un solo lugar.
//
// EXCEPCIÓN: los botones de modo (.modo-btn) se resuelven dinámicamente
// en ui-controller.js con 'modo' + capitalize(modo) — no son fijos.
// =========================

// ── INPUT ─────────────────────────────────────────────
const elInput       = document.getElementById('inputTexto');
const elBtnEnviar   = document.getElementById('btnEnviar');
const elInputWrap   = document.getElementById('inputWrap');

// ── MENSAJES ──────────────────────────────────────────
const elEstadoMsg   = document.getElementById('estadoMsg');
const elEstadoTexto = document.getElementById('estadoTexto');
const elErrorMsg    = document.getElementById('errorMsg');

// ── PANELES ───────────────────────────────────────────
const elFichasOrig  = document.getElementById('fichasOrig');
const elFichasDest  = document.getElementById('fichasDest');
const elPanelRes    = document.getElementById('panelResultado');

// ── BOTONES DE ACCIÓN ─────────────────────────────────
const elBtnRevelar  = document.getElementById('btnRevelar');
const elBtnVerificar= document.getElementById('btnVerificar');
const elAccionesDrag= document.getElementById('accionesDrag');

// ── OPCIONES (modo animación) ─────────────────────────
const elOpcionesWrap = document.getElementById('opcionesWrap');
const elOpcionesLista= document.getElementById('opcionesLista');

// ── TEXTOS DE UI ──────────────────────────────────────
const elTituloApp     = document.getElementById('tituloApp');
const elLabelSuperior = document.getElementById('labelSuperior');
const elLabelInferior = document.getElementById('labelInferior');