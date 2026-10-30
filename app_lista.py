import os
import uuid
from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-de-desarrollo")
app.config["JSON_SORT_KEYS"] = False
try:
    app.json.sort_keys = False  # mantiene el orden de los campos
except AttributeError:
    pass

MAX_CAMPOS = 10
MAX_CAPACIDAD = 20
MAX_LARGO_VALOR = 100


# --- LÓGICA DE LISTA ENLAZADA ORDENADA ---
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None


class LinkedList:
    def __init__(self, max_capacity=6, order_key=None):
        self.head = None
        self.size = 0
        self.max_capacity = max_capacity
        self.order_key = order_key  # campo por el que se ordena

    def _val(self, data):
        return str(data.get(self.order_key, "")).lower()

    def insert(self, data):
        """Devuelve (ok, mensaje, posicion)."""
        if self.size >= self.max_capacity:
            return False, "Overflow: la lista está llena", -1
        nuevo = Node(data)
        val = self._val(data)

        if self.head is None:  # 1. lista vacía
            self.head = nuevo
            self.size += 1
            return True, "Insertado como Head", 0

        head_val = self._val(self.head.data)
        if val < head_val:  # 2. va antes que la Head
            nuevo.next = self.head
            self.head = nuevo
            self.size += 1
            return True, "Insertado como nueva Head", 0
        if val == head_val:
            return False, f"El elemento «{data.get(self.order_key)}» ya existe", -1

        # 3. buscar la posición en el medio o al final
        anterior, actual, pos = self.head, self.head.next, 1
        while actual is not None:
            actual_val = self._val(actual.data)
            if val < actual_val:
                break
            if val == actual_val:
                return False, f"El elemento «{data.get(self.order_key)}» ya existe", -1
            anterior, actual = actual, actual.next
            pos += 1

        nuevo.next = actual
        anterior.next = nuevo
        self.size += 1
        return True, "Insertado en orden", pos

    def delete(self, valor):
        """Devuelve (ok, mensaje, posicion, dato)."""
        if self.head is None:
            return False, "Underflow: la lista está vacía", -1, None
        buscado = str(valor).lower()

        if self._val(self.head.data) == buscado:
            dato = self.head.data
            self.head = self.head.next
            self.size -= 1
            return True, "Head eliminada", 0, dato

        anterior, actual, pos = self.head, self.head.next, 1
        while actual is not None:
            if self._val(actual.data) == buscado:
                anterior.next = actual.next  # el puntero salta el nodo eliminado
                self.size -= 1
                return True, "Nodo eliminado", pos, actual.data
            anterior, actual = actual, actual.next
            pos += 1
        return False, "Elemento no encontrado", -1, None

    def search(self, valor):
        """Devuelve la posición (0, 1, 2...) o -1 si no está."""
        buscado, actual, pos = str(valor).lower(), self.head, 0
        while actual is not None:
            if self._val(actual.data) == buscado:
                return pos
            actual = actual.next
            pos += 1
        return -1

    def clear(self):
        self.head = None
        self.size = 0

    def to_list(self):
        elementos, actual = [], self.head
        while actual:
            elementos.append(actual.data)
            actual = actual.next
        return elementos


# Cada visitante tiene su propia lista (cookie de sesión)
sesiones = {}


def mundo():
    sid = session.get("sid")
    if sid not in sesiones:
        sid = uuid.uuid4().hex
        session["sid"] = sid
        sesiones[sid] = {"campos": [], "lista": LinkedList()}
    return sesiones[sid]


def respuesta(m, **extra):
    li = m["lista"]
    return jsonify({"status": "success", "estructura": m["campos"], "capacidad": li.max_capacity,
                    "lista": li.to_list(), "tamano": li.size, **extra})


def error(msg):
    return jsonify({"error": msg}), 400


# --- INTERFAZ GRÁFICA (FRONTEND) ---
PAGINA_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Simulador de Listas Enlazadas</title>
<style>
:root{--bg:#eef7f3;--panel:#fff;--ink:#12332b;--muted:#587a6f;--line:#cfe4dc;--acc:#0b8a68;--acc2:#12b886;--soft:#e3f5ee;--warn:#f59f00;--err:#c92a4b;--ok:#0b8a68}
*{box-sizing:border-box}
body{margin:0;padding:24px 20px 44px;color:var(--ink);font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;line-height:1.45;
background:radial-gradient(900px 380px at 15% -10%,rgba(18,184,134,.18),transparent),var(--bg)}
.wrap{max-width:1250px;margin:0 auto;display:grid;gap:20px}
h1{margin:0 0 4px;font-size:clamp(1.7rem,4vw,2.4rem);letter-spacing:-.02em}
.sub{margin:0;color:var(--muted)}
.coach{display:flex;flex-direction:column;padding:14px 18px;min-height:80px;background:var(--panel);border:1px solid var(--line);border-left:8px solid var(--acc2);border-radius:14px;box-shadow:0 4px 14px rgba(18,80,60,.07)}
.coach b{font-size:1.1rem}.coach span{color:var(--muted)}
.coach.ok{border-left-color:var(--ok)}.coach.err{border-left-color:var(--err)}.coach.warn{border-left-color:var(--warn)}.coach.flash{animation:flash .5s ease-out}
.panel{background:var(--panel);padding:22px;border-radius:16px;border:2px solid var(--line);box-shadow:0 4px 14px rgba(18,80,60,.07);transition:border-color .3s,opacity .3s}
.panel.active{border-color:var(--acc2)}.panel.locked{opacity:.55}
h2{margin:0 0 6px;font-size:1.1rem;display:flex;align-items:center;gap:10px}
.step{display:grid;place-items:center;flex-shrink:0;width:26px;height:26px;border-radius:50%;background:var(--acc);color:#fff;font-size:.85rem;font-weight:700}
.hint{margin:0 0 12px;color:var(--muted);font-size:.9rem}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
label{display:block;margin:14px 0 4px;font-size:.85rem;font-weight:700;color:var(--muted)}
input{width:100%;padding:12px;background:#f8fcfa;border:2px solid var(--line);border-radius:10px;color:var(--ink);font:inherit;transition:border-color .2s,box-shadow .2s}
input:focus{outline:none;border-color:var(--acc2);box-shadow:0 0 0 3px rgba(18,184,134,.25)}
button{width:100%;margin-top:12px;padding:12px;border:0;border-radius:10px;color:#fff;font:inherit;font-weight:700;cursor:pointer;box-shadow:0 4px 0 rgba(0,0,0,.18);transition:transform .12s,box-shadow .12s,filter .15s}
button:hover:not(:disabled){filter:brightness(1.08);transform:translateY(-2px)}
button:active:not(:disabled){transform:translateY(3px);box-shadow:0 1px 0 rgba(0,0,0,.18)}
button:disabled{opacity:.4;cursor:not-allowed;box-shadow:none}
button small{display:block;font-weight:400;font-size:.72rem;opacity:.9}
.b-main{background:var(--ink)}.b-ins{background:var(--acc)}.b-del{background:var(--err)}.b-find{background:#1c7ed6}.b-clear{background:#e67700}
.b-add{background:transparent;border:2px dashed var(--acc2);color:var(--acc);width:auto;padding:8px 16px;margin-top:2px;font-size:.88rem;box-shadow:none}
.def-box{display:flex;gap:10px;align-items:center;margin-bottom:10px;padding:10px;background:var(--soft);border:1px solid var(--line);border-radius:10px;animation:slidein .3s ease-out}
.def-box input{border:0;background:#fff}
.def-box .tagk{font-size:.68rem;font-weight:700;color:var(--acc);white-space:nowrap}
.x{width:auto;margin:0;padding:10px 14px;background:var(--err);box-shadow:none}
#dynamicInputs{padding:2px 16px 14px;background:var(--soft);border-radius:10px;min-height:70px}
.row{display:flex;gap:10px}.row button{margin-top:10px}

.top-row{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px}
.segs{display:flex;gap:3px;margin:8px 0 14px}.seg{flex:1;height:10px;border-radius:4px;background:var(--line);transition:background .3s}
.track{display:flex;align-items:center;min-height:230px;padding:42px 20px 24px;overflow-x:auto;border-radius:14px;background:repeating-linear-gradient(0deg,#f8fcfa,#f8fcfa 28px,#f0f9f5 28px,#f0f9f5 29px);border:2px solid var(--line)}
.chip{flex:0 0 auto;padding:8px 14px;border-radius:10px;font-weight:800;font-size:.85rem}
.chip.head{background:var(--acc);color:#fff}.chip.null{background:#dfe9e5;color:var(--muted)}
.arrow{flex:0 0 46px;height:3px;background:var(--acc2);position:relative;border-radius:2px}
.arrow::after{content:"";position:absolute;right:-2px;top:-6px;border-left:11px solid var(--acc2);border-top:7.5px solid transparent;border-bottom:7.5px solid transparent}
.node{flex:0 0 172px;background:#fff;border:2px solid var(--acc2);border-radius:14px;overflow:hidden;box-shadow:0 4px 0 rgba(11,138,104,.25)}
.node.first{border-color:var(--acc);box-shadow:0 4px 0 rgba(11,138,104,.5)}
.nh{display:flex;justify-content:space-between;align-items:center;padding:5px 10px;background:var(--soft);font-size:.72rem;font-weight:700;color:var(--acc)}
.nh .badge{padding:1px 8px;border-radius:99px;background:var(--acc);color:#fff}
.nb{padding:8px 12px}
.kv{margin-bottom:4px}.kv small{display:block;font-size:.66rem;color:var(--muted)}.kv b{overflow-wrap:anywhere}
.kv.key b{color:var(--acc);font-size:1.05rem}
.nx{padding:6px 12px;border-top:2px dashed var(--line);font-size:.78rem;color:var(--muted)}.nx b{color:var(--ink)}
.node.visit{border-color:var(--warn);box-shadow:0 0 0 4px rgba(245,159,0,.35)}
.node.found{border-color:var(--ok);box-shadow:0 0 0 5px rgba(18,184,134,.45)}
.enter{animation:drop .7s cubic-bezier(.3,1.4,.5,1)}
.log{margin:0;padding:0;list-style:none;max-height:110px;overflow-y:auto;font-size:.85rem}
.log li{padding:4px 0;border-bottom:1px solid var(--line);color:var(--muted)}.log li:first-child{color:var(--ink);font-weight:700}
.log:empty::after{content:"Sin operaciones todavía.";color:var(--muted)}
@keyframes drop{0%{transform:translateY(-130px) scale(.9);opacity:0}55%{transform:none;opacity:1}72%{transform:scale(1.05,.94)}100%{transform:none}}
@keyframes flash{from{transform:translateY(-8px);opacity:.3}to{transform:none;opacity:1}}
@keyframes slidein{from{transform:translateX(-24px);opacity:0}to{transform:none;opacity:1}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<div class="wrap">
<div><h1>Simulador de listas enlazadas</h1><p class="sub">Una lista enlazada es una cadena de nodos. Cada nodo guarda sus datos y un puntero <b>next</b> al nodo siguiente. Esta lista se mantiene siempre ordenada.</p></div>
<div class="coach" id="coach" role="status" aria-live="polite"><b id="coachTitle"></b><span id="coachText"></span></div>

<section class="panel">
  <div class="top-row"><h2 style="margin:0">Lista gráfica</h2><span><b id="count">0 / 6</b> <span id="keyInfo" style="color:var(--muted)"></span></span></div>
  <div class="segs" id="segs"></div>
  <div class="track" id="listVisual"></div>
  <h2 style="margin:18px 0 4px;font-size:.95rem">Registro</h2>
  <ul class="log" id="log"></ul>
</section>

<div class="steps">
  <section class="panel active" id="s1">
    <h2><span class="step">1</span> Estructura de la lista</h2>
    <p class="hint">El <b>primer campo</b> es la llave: la lista se ordena alfabéticamente por él y no admite llaves repetidas.</p>
    <div id="defFieldsContainer"></div>
    <button class="b-add" id="btnAdd">+ Agregar otro campo</button>
    <label for="capacidadInput">Capacidad máxima (1 a 20)</label>
    <input type="number" id="capacidadInput" min="1" max="20" value="6">
    <button class="b-main" id="btnSet">Guardar estructura</button>
  </section>
  <section class="panel locked" id="s2">
    <h2><span class="step">2</span> Insertar un nodo</h2>
    <p class="hint">Se coloca solo en la posición que le corresponde.</p>
    <div id="dynamicInputs"></div>
    <button class="b-ins" id="btnInsert" disabled>Insertar nodo<small>queda ordenado</small></button>
  </section>
  <section class="panel locked" id="s3">
    <h2><span class="step">3</span> Eliminar o buscar</h2>
    <p class="hint">Escribí el valor de la llave.</p>
    <input type="text" id="deleteInput" placeholder="Valor de la llave..." autocomplete="off">
    <div class="row">
      <button class="b-del" id="btnDelete" disabled>Delete<small>quita el nodo</small></button>
      <button class="b-find" id="btnSearch" disabled>Buscar<small>recorre la lista</small></button>
    </div>
    <button class="b-clear" id="btnClear" disabled>Clear All<small>vacía la lista</small></button>
  </section>
</div>
</div>

<script>
const $ = id => document.getElementById(id);
const REDUCE = matchMedia('(prefers-reduced-motion: reduce)').matches;
const SHAKE = [{transform:'translateX(0)'},{transform:'translateX(-12px)'},{transform:'translateX(12px)'},{transform:'translateX(-7px)'},{transform:'translateX(7px)'},{transform:'translateX(0)'}];
let state = { estructura: [], capacidad: 6, lista: [] };
let busy = false;
const llave = () => state.estructura[0];
const kOf = it => String(it[llave()]).toLowerCase();
const sleep = ms => new Promise(r => setTimeout(r, REDUCE ? 0 : ms));

async function api(url, method = 'POST', body = null) {
  try {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    return await (await fetch(url, opts)).json();
  } catch (e) {
    return { error: 'No se pudo conectar con el servidor.' };
  }
}

function anim(el, kf, opt) {
  if (REDUCE || !el) return Promise.resolve();
  return el.animate(kf, opt).finished.catch(() => {});
}

function coach(kind, title, text) {
  const c = $('coach');
  c.className = 'coach ' + kind;
  $('coachTitle').textContent = title;
  $('coachText').textContent = text;
  void c.offsetWidth;
  c.classList.add('flash');
}

function log(text) {
  const li = document.createElement('li');
  li.textContent = text;
  $('log').prepend(li);
  while ($('log').children.length > 30) $('log').lastChild.remove();
}

function fail(msg) {
  const hit = ['Overflow', 'Underflow', 'ya existe', 'no encontrado'].find(w => msg.includes(w));
  const titles = { Overflow: 'Overflow: la lista está llena', Underflow: 'Underflow: la lista está vacía',
    'ya existe': 'Llave repetida', 'no encontrado': 'No encontrado' };
  const texts = { Overflow: 'No cabe otro nodo. Eliminá alguno y probá de nuevo.',
    Underflow: 'No hay nodos. Insertá uno primero.',
    'ya existe': msg + '. En esta lista cada llave debe ser única.',
    'no encontrado': 'Ningún nodo tiene esa llave. Se llega a NULL sin encontrarlo.' };
  coach('err', hit ? titles[hit] : 'Revisá los datos', hit ? texts[hit] : msg);
  if (hit) anim($('listVisual'), SHAKE, { duration: 450 });
}

function chip(text, cls) {
  const d = document.createElement('div');
  d.className = 'chip ' + cls;
  d.textContent = text;
  return d;
}
const arrow = () => { const a = document.createElement('div'); a.className = 'arrow'; return a; };

function node(it, i, nextIt) {
  const d = document.createElement('div');
  d.className = 'node' + (i === 0 ? ' first' : '');
  d.dataset.k = kOf(it);
  const hd = document.createElement('div');
  hd.className = 'nh';
  const s = document.createElement('span');
  s.textContent = 'Nodo ' + i;
  hd.appendChild(s);
  if (i === 0) {
    const b = document.createElement('span');
    b.className = 'badge';
    b.textContent = 'HEAD';
    hd.appendChild(b);
  }
  const nb = document.createElement('div');
  nb.className = 'nb';
  state.estructura.forEach((k, j) => {
    const kv = document.createElement('div');
    kv.className = 'kv' + (j === 0 ? ' key' : '');
    const a = document.createElement('small');
    a.textContent = j === 0 ? k + ' (llave)' : k;
    const b = document.createElement('b');
    b.textContent = it[k];
    kv.append(a, b);
    nb.appendChild(kv);
  });
  const nx = document.createElement('div');
  nx.className = 'nx';
  nx.append('next → ');
  const nb2 = document.createElement('b');
  nb2.textContent = nextIt ? nextIt[llave()] : 'NULL';
  nx.appendChild(nb2);
  d.append(hd, nb, nx);
  return d;
}

function makeRow(value = '', removable = true, isKey = false) {
  const row = document.createElement('div');
  row.className = 'def-box';
  const inp = document.createElement('input');
  inp.type = 'text';
  inp.className = 'def-campo';
  inp.placeholder = isKey ? 'Ej: Nombre (llave)' : 'Ej: Edad';
  inp.autocomplete = 'off';
  inp.value = value;
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') setStructure(); });
  row.appendChild(inp);
  if (isKey) {
    const t = document.createElement('span');
    t.className = 'tagk';
    t.textContent = 'LLAVE';
    row.appendChild(t);
  }
  if (removable) {
    const x = document.createElement('button');
    x.className = 'x';
    x.textContent = 'X';
    x.addEventListener('click', () => {
      anim(row, [{ opacity: 1, transform: 'none' }, { opacity: 0, transform: 'translateX(30px)' }], { duration: 200 }).then(() => row.remove());
    });
    row.appendChild(x);
  }
  return row;
}

function addDefField() {
  const box = $('defFieldsContainer');
  if (box.children.length >= 10) return coach('err', 'Máximo 10 campos', 'Ya no caben más datos en cada nodo.');
  const row = makeRow('', true);
  box.appendChild(row);
  row.firstChild.focus();
}

function buildInputs() {
  const box = $('dynamicInputs');
  box.innerHTML = '';
  if (!state.estructura.length) {
    const p = document.createElement('p');
    p.className = 'hint';
    p.style.cssText = 'color:#c92a4b;text-align:center;margin:14px 0 0';
    p.textContent = 'Primero guardá la estructura en el paso 1.';
    box.appendChild(p);
    return;
  }
  state.estructura.forEach((campo, i) => {
    const lab = document.createElement('label');
    lab.htmlFor = 'val_' + i;
    lab.textContent = campo + (i === 0 ? ' (llave de orden)' : '');
    const inp = document.createElement('input');
    inp.id = 'val_' + i;
    inp.autocomplete = 'off';
    inp.placeholder = 'Valor para ' + campo;
    inp.addEventListener('keydown', e => {
      if (e.key !== 'Enter') return;
      const next = $('val_' + (i + 1));
      next ? next.focus() : insertItem();
    });
    box.append(lab, inp);
  });
}

function renderList(enterKey = null) {
  const c = $('listVisual'), L = state.lista, cap = state.capacidad, has = state.estructura.length > 0;
  c.innerHTML = '';
  c.appendChild(chip('HEAD', 'head'));
  c.appendChild(arrow());
  L.forEach((it, i) => {
    const n = node(it, i, L[i + 1]);
    if (enterKey !== null && kOf(it) === enterKey) n.classList.add('enter');
    c.append(n, arrow());
  });
  c.appendChild(chip('NULL', 'null'));
  $('segs').innerHTML = '';
  for (let i = 0; i < cap; i++) {
    const s = document.createElement('div');
    s.className = 'seg';
    if (i < L.length) s.style.background = 'var(--acc2)';
    $('segs').appendChild(s);
  }
  $('count').textContent = L.length + ' / ' + cap;
  $('keyInfo').textContent = has ? '· ordenada por «' + llave() + '»' : '';
  ['btnInsert', 'btnDelete', 'btnSearch', 'btnClear'].forEach(id => { $(id).disabled = !has; });
  $('s1').classList.toggle('active', !has);
  ['s2', 's3'].forEach(id => { $(id).classList.toggle('locked', !has); $(id).classList.toggle('active', has); });
}

function sync(data, enterKey = null) {
  state = { estructura: data.estructura, capacidad: data.capacidad, lista: data.lista };
  renderList(enterKey);
}

const posiciones = () => new Map([...$('listVisual').querySelectorAll('.node')].map(el => [el.dataset.k, el.getBoundingClientRect().left]));
function deslizar(antes) {
  $('listVisual').querySelectorAll('.node').forEach(el => {
    if (!antes.has(el.dataset.k)) return;
    const dx = antes.get(el.dataset.k) - el.getBoundingClientRect().left;
    if (dx) anim(el, [{ transform: 'translateX(' + dx + 'px)' }, { transform: 'none' }], { duration: 450, easing: 'cubic-bezier(.2,.8,.2,1)' });
  });
}

async function setStructure() {
  if (busy) return;
  const campos = Array.from(document.querySelectorAll('.def-campo')).map(i => i.value.trim()).filter(Boolean);
  if (!campos.length) return fail('Agregá al menos un campo con nombre.');
  const data = await api('/set_structure', 'POST', { campos, capacidad: $('capacidadInput').value });
  if (data.error) return fail(data.error);
  sync(data);
  buildInputs();
  $('deleteInput').placeholder = 'Valor de ' + llave() + '...';
  log('Estructura: ' + data.estructura.join(', ') + ' (llave: ' + data.estructura[0] + ')');
  coach('ok', 'Estructura lista',
    'La lista se ordenará por «' + llave() + '» y admite hasta ' + data.capacidad + ' nodos. Insertá el primero.');
  $('val_0').focus();
}

async function insertItem() {
  if (busy || !state.estructura.length) return;
  const elemento = {};
  for (let i = 0; i < state.estructura.length; i++) {
    const val = $('val_' + i).value.trim();
    if (!val) { $('val_' + i).focus(); return fail('Completá el campo «' + state.estructura[i] + '».'); }
    elemento[state.estructura[i]] = val;
  }
  const data = await api('/insert', 'POST', { elemento });
  if (data.error) return fail(data.error);
  const antes = posiciones();
  const key = String(elemento[llave()]).toLowerCase();
  sync(data, key);
  deslizar(antes);
  const pos = data.posicion, ultimo = pos === data.lista.length - 1;
  log('Insert: ' + elemento[llave()] + ' (posición ' + pos + ')');
  coach('ok', pos === 0 ? 'Insertado como nueva Head' : 'Insertado en la posición ' + pos,
    pos === 0 ? (data.lista.length === 1 ? 'La lista estaba vacía: el nodo es la Head y su next es NULL.'
      : 'Va antes que todos (alfabéticamente), así que pasa a ser la Head y su next apunta a la Head anterior.')
    : 'Se recorrió la lista hasta encontrar su lugar. El nodo anterior ahora apunta al nuevo, y el nuevo apunta a ' + (ultimo ? 'NULL.' : 'su siguiente.'));
  state.estructura.forEach((_, i) => { $('val_' + i).value = ''; });
  $('val_0').focus();
}

async function deleteItem() {
  if (busy || !state.estructura.length) return;
  const v = $('deleteInput').value.trim();
  if (!v) { $('deleteInput').focus(); return fail('Escribí el valor de la llave a eliminar.'); }
  const data = await api('/delete', 'POST', { valor: v });
  if (data.error) return fail(data.error);
  busy = true;
  const el = $('listVisual').querySelectorAll('.node')[data.posicion];
  await anim(el, [{ transform: 'none', opacity: 1 }, { transform: 'translateY(-34px) scale(1.05)', opacity: .8, offset: .4 }, { transform: 'translateY(-34px) scale(.8)', opacity: 0 }],
    { duration: 550, easing: 'ease-in', fill: 'forwards' });
  const antes = posiciones();
  sync(data);
  deslizar(antes);
  log('Delete: ' + data.eliminado[llave()] + ' (posición ' + data.posicion + ')');
  coach('ok', data.posicion === 0 ? 'Head eliminada' : 'Nodo eliminado',
    data.posicion === 0 ? 'La Head ahora apunta al segundo nodo, que pasa a ser la nueva Head.'
      : 'El nodo anterior "salta" al eliminado y apunta directo al siguiente. Nada más se mueve en la lista.');
  $('deleteInput').value = '';
  busy = false;
}

async function searchItem() {
  if (busy || !state.estructura.length) return;
  const v = $('deleteInput').value.trim();
  if (!v) { $('deleteInput').focus(); return fail('Escribí el valor de la llave a buscar.'); }
  const data = await api('/search', 'POST', { valor: v });
  if (data.error) return fail(data.error);
  busy = true;
  coach('warn', 'Buscando...', 'Hay que recorrer los nodos de a uno, empezando desde la Head.');
  const nodos = [...$('listVisual').querySelectorAll('.node')];
  const limite = data.posicion >= 0 ? data.posicion + 1 : nodos.length;
  for (let i = 0; i < limite; i++) {
    nodos[i].classList.add('visit');
    await sleep(450);
    nodos[i].classList.remove('visit');
  }
  if (data.posicion >= 0) {
    nodos[data.posicion].classList.add('found');
    coach('ok', 'Encontrado en la posición ' + data.posicion, 'Se visitaron ' + limite + ' nodo(s) en orden, desde la Head.');
    log('Buscar: ' + v + ' → posición ' + data.posicion);
    await sleep(1400);
    nodos[data.posicion].classList.remove('found');
  } else {
    fail('Elemento no encontrado');
    coach('err', 'No encontrado', 'Se recorrieron los ' + limite + ' nodos hasta llegar a NULL y ninguno tiene esa llave.');
    log('Buscar: ' + v + ' → no está');
  }
  busy = false;
}

async function clearList() {
  if (busy || !state.estructura.length) return;
  const data = await api('/clear');
  if (data.error) return fail(data.error);
  if (!data.eliminados) return coach('', 'Ya estaba vacía', 'La Head ya apunta a NULL.');
  busy = true;
  coach('ok', 'Clear: lista vacía', 'Se descartaron ' + data.eliminados + ' nodos. La Head vuelve a apuntar a NULL.');
  const nodos = [...$('listVisual').querySelectorAll('.node')];
  await Promise.all(nodos.map((el, i) => anim(el, [
    { transform: 'none', opacity: 1 },
    { transform: 'translateY(90px) rotate(' + (i % 2 ? -8 : 8) + 'deg)', opacity: 0 }
  ], { duration: 450, delay: i * 70, easing: 'ease-in', fill: 'forwards' })));
  sync(data);
  log('Clear: ' + data.eliminados + ' nodo(s)');
  busy = false;
}

$('btnAdd').addEventListener('click', addDefField);
$('btnSet').addEventListener('click', setStructure);
$('btnInsert').addEventListener('click', insertItem);
$('btnDelete').addEventListener('click', deleteItem);
$('btnSearch').addEventListener('click', searchItem);
$('btnClear').addEventListener('click', clearList);
$('deleteInput').addEventListener('keydown', e => { if (e.key === 'Enter') deleteItem(); });

(async function init() {
  const data = await api('/state', 'GET');
  const box = $('defFieldsContainer');
  if (!data.error && data.estructura.length) {
    sync(data);
    $('capacidadInput').value = data.capacidad;
    data.estructura.forEach((c, i) => box.appendChild(makeRow(c, i > 0, i === 0)));
    $('deleteInput').placeholder = 'Valor de ' + llave() + '...';
    coach('', 'Seguimos donde lo dejaste', 'Tu lista sigue acá. Probá insertar, buscar o eliminar.');
  } else {
    box.appendChild(makeRow('Nombre', false, true));
    coach('', 'Empecemos', 'Definí los datos de cada nodo. El primero será la llave que ordena la lista.');
  }
  buildInputs();
  renderList();
})();
</script>
</body>
</html>"""


# --- RUTAS DE FLASK ---
@app.route("/")
def index():
    return PAGINA_HTML


@app.route("/state", methods=["GET"])
def get_state():
    return respuesta(mundo())


@app.route("/set_structure", methods=["POST"])
def set_structure():
    m = mundo()
    data = request.get_json(silent=True) or {}
    campos = [str(c).strip() for c in data.get("campos", []) if str(c).strip()]
    if not campos:
        return error("Ingresá al menos un campo.")
    if len(campos) > MAX_CAMPOS:
        return error(f"Máximo {MAX_CAMPOS} campos por nodo.")
    vistos = set()
    for c in campos:
        if c.lower() in vistos:
            return error(f"El campo «{c}» está repetido.")
        vistos.add(c.lower())
    try:
        cap = int(data.get("capacidad", 6))
    except (TypeError, ValueError):
        return error("La capacidad debe ser un número entero.")
    if not 1 <= cap <= MAX_CAPACIDAD:
        return error(f"La capacidad debe estar entre 1 y {MAX_CAPACIDAD}.")
    m["campos"] = campos
    m["lista"] = LinkedList(cap, campos[0])
    return respuesta(m)


@app.route("/insert", methods=["POST"])
def insert():
    m = mundo()
    if not m["campos"]:
        return error("Definí la estructura primero.")
    elemento = (request.get_json(silent=True) or {}).get("elemento")
    if not isinstance(elemento, dict):
        return error("Faltan datos para insertar.")
    limpio = {}
    for campo in m["campos"]:
        valor = str(elemento.get(campo, "")).strip()
        if not valor:
            return error(f"Completá el campo «{campo}».")
        limpio[campo] = valor[:MAX_LARGO_VALOR]
    ok, mensaje, pos = m["lista"].insert(limpio)
    if not ok:
        return error(mensaje)
    return respuesta(m, mensaje=mensaje, posicion=pos)


@app.route("/delete", methods=["POST"])
def delete():
    m = mundo()
    valor = (request.get_json(silent=True) or {}).get("valor", "")
    ok, mensaje, pos, dato = m["lista"].delete(valor)
    if not ok:
        return error(mensaje)
    return respuesta(m, mensaje=mensaje, posicion=pos, eliminado=dato)


@app.route("/search", methods=["POST"])
def search():
    m = mundo()
    if m["lista"].head is None:
        return error("Underflow: la lista está vacía")
    valor = (request.get_json(silent=True) or {}).get("valor", "")
    return respuesta(m, posicion=m["lista"].search(valor))


@app.route("/clear", methods=["POST"])
def clear():
    m = mundo()
    n = m["lista"].size
    m["lista"].clear()
    return respuesta(m, eliminados=n)


if __name__ == "__main__":
    app.run(debug=True)