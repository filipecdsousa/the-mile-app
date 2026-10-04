'use strict';

const ui = {
  root: document.getElementById('content'),
  lang: document.getElementById('language'),
  logout: document.getElementById('logout'),
  install: document.getElementById('install')
};

let lang = localStorage.getItem('mile-language') === 'en' ? 'en' : 'pt';
let user = null;
let csrf = null;
let selected = null;
let folder = null;
let players = [];
let admins = [];
let docs = [];
let mode = '';
let activationToken = new URLSearchParams(location.search).get('activate');
let installPrompt = null;
if (activationToken) history.replaceState(null, '', location.pathname);

const folders = ['nutrition', 'menus', 'other'];

const words = {
  pt: {
    private: 'Área privada', hello: 'Olá,', sub: 'Os teus documentos, num só lugar.',
    folders: ['Planos nutricionais', 'Menus', 'Outros documentos'], document: 'documento', documents: 'documentos',
    download: 'Abrir', documentTitle: 'Título apresentado ao jogador', editTitle: 'Editar título', titlePrompt: 'Título apresentado ao jogador:', back: '← Voltar', players: 'Jogadores', management: 'Administração',
    manageSub: 'Gere acessos, jogadores e documentos a partir de um único painel.', newPlayer: '+ Criar jogador',
    manage: 'Gerir', upload: '+ Carregar PDF', name: 'Nome', email: 'Email', password: 'Palavra-passe', enter: 'Entrar',
    loginSub: 'Acede à tua área privada.', create: 'Criar conta', foot: 'Nutrição. Performance. Detalhe.', logout: 'Sair', install: 'Instalar',
    installTitle: 'Adicionar The Mile ao telemóvel', installIOS: 'No iPhone: abre o menu Partilhar do Safari e escolhe “Adicionar ao ecrã principal”. Depois a The Mile abre como uma app.', installOther: 'Podes instalar a The Mile no ecrã principal para abrir em modo app.',
    activate: 'Definir palavra-passe', activateSub: 'Escolhe uma palavra-passe com pelo menos 12 caracteres.',
    confirm: 'Confirmar palavra-passe', save: 'Guardar', cancel: 'Cancelar', file: 'Ficheiro PDF', pdfNote: 'PDF até 20 MB.',
    empty: 'Ainda não há documentos nesta pasta.', noPlayers: 'Ainda não foram criados jogadores.', replace: 'Substituir',
    remove: 'Apagar', removeConfirm: 'Queres apagar este documento?', inactive: 'Desativado', pending: 'Por ativar', active: 'Ativo',
    deactivate: 'Desativar', reactivate: 'Reativar', statusConfirm: 'Alterar o acesso deste jogador?', reset: 'Link de acesso',
    linkTitle: 'Definir acesso', linkText: 'Partilha este link em privado. Permite definir ou recuperar a palavra-passe e é válido durante 24 horas. Não foi enviado nenhum email.',
    copy: 'Copiar link', copied: 'Copiado', forgot: 'Esqueci-me da palavra-passe', forgotText: 'Contacta Filipe Sousa ou Raquel Gomes para receberes um novo link de acesso.',
    search: 'Procurar jogador', administrators: 'Administradores', noMatches: 'Nenhum jogador encontrado.',
    adminSub: 'Contas com acesso total à administração.', generateLink: 'Gerar link', current: 'Tu',
    overview: 'Visão geral', totalPlayers: 'Jogadores', activePlayers: 'Ativos', pendingPlayers: 'Por ativar', inactivePlayers: 'Desativados', totalDocuments: 'Documentos',
    edit: 'Editar dados', update: 'Guardar alterações', deletePlayer: 'Eliminar jogador', deletePlayerConfirm: 'Eliminar este jogador e todos os seus documentos? Esta ação não pode ser anulada.',
    playerDetails: 'Dados do jogador', access: 'Acesso',
    errors: {
      credentials: 'Email ou palavra-passe incorretos.', login_required: 'A sessão terminou. Entra novamente.', csrf: 'Atualiza a página e tenta novamente.',
      origin: 'Pedido não permitido.', password_length: 'Usa pelo menos 12 caracteres.', activation: 'O link expirou ou já foi utilizado. Pede um novo link.',
      email_exists: 'Este email já tem uma conta.', pdf_only: 'Seleciona um ficheiro PDF válido.', file_size: 'O ficheiro ultrapassa 20 MB.',
      forbidden: 'Não tens acesso a este conteúdo.', user_fields: 'Verifica o nome e o email.', rate_limit: 'Demasiadas tentativas. Tenta novamente daqui a 15 minutos.',
      network: 'Não foi possível ligar. Tenta novamente.', password_mismatch: 'As palavras-passe não coincidem.', generic: 'Não foi possível concluir. Tenta novamente.'
    }
  },
  en: {
    private: 'Private area', hello: 'Hello,', sub: 'Your documents, all in one place.',
    folders: ['Nutrition plans', 'Menus', 'Other documents'], document: 'document', documents: 'documents',
    download: 'Open', documentTitle: 'Title shown to the player', editTitle: 'Edit title', titlePrompt: 'Title shown to the player:', back: '← Back', players: 'Players', management: 'Administration',
    manageSub: 'Manage access, players and documents from one dashboard.', newPlayer: '+ Add player',
    manage: 'Manage', upload: '+ Upload PDF', name: 'Name', email: 'Email', password: 'Password', enter: 'Sign in',
    loginSub: 'Access your private area.', create: 'Create account', foot: 'Nutrition. Performance. Detail.', logout: 'Sign out', install: 'Install',
    installTitle: 'Add The Mile to your phone', installIOS: 'On iPhone: open Safari’s Share menu and choose “Add to Home Screen”. The Mile will then open like an app.', installOther: 'You can install The Mile on your home screen to open it in app mode.',
    activate: 'Set password', activateSub: 'Choose a password with at least 12 characters.',
    confirm: 'Confirm password', save: 'Save', cancel: 'Cancel', file: 'PDF file', pdfNote: 'PDF up to 20 MB.',
    empty: 'There are no documents in this folder yet.', noPlayers: 'No players have been added yet.', replace: 'Replace',
    remove: 'Delete', removeConfirm: 'Delete this document?', inactive: 'Inactive', pending: 'Not activated', active: 'Active',
    deactivate: 'Deactivate', reactivate: 'Reactivate', statusConfirm: 'Change this player’s access?', reset: 'Access link',
    linkTitle: 'Set access', linkText: 'Share this link privately. It can set or recover the password and is valid for 24 hours. No email has been sent.',
    copy: 'Copy link', copied: 'Copied', forgot: 'Forgot password', forgotText: 'Contact Filipe Sousa or Raquel Gomes for a new access link.',
    search: 'Find player', administrators: 'Administrators', noMatches: 'No players found.',
    adminSub: 'Accounts with full administration access.', generateLink: 'Generate link', current: 'You',
    overview: 'Overview', totalPlayers: 'Players', activePlayers: 'Active', pendingPlayers: 'Pending', inactivePlayers: 'Inactive', totalDocuments: 'Documents',
    edit: 'Edit details', update: 'Save changes', deletePlayer: 'Delete player', deletePlayerConfirm: 'Delete this player and all their documents? This cannot be undone.',
    playerDetails: 'Player details', access: 'Access',
    errors: {
      credentials: 'Incorrect email or password.', login_required: 'Your session has ended. Sign in again.', csrf: 'Refresh this page and try again.',
      origin: 'Request not allowed.', password_length: 'Use at least 12 characters.', activation: 'This link has expired or has already been used. Request a new link.',
      email_exists: 'This email already has an account.', pdf_only: 'Select a valid PDF file.', file_size: 'This file exceeds 20 MB.',
      forbidden: 'You do not have access to this content.', user_fields: 'Check the name and email.', rate_limit: 'Too many attempts. Try again in 15 minutes.',
      network: 'Unable to connect. Try again.', password_mismatch: 'Passwords do not match.', generic: 'Unable to complete. Try again.'
    }
  }
};

function t() { return words[lang]; }
function esc(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function statusLabel(p, w) { return p.active ? (p.activated ? w.active : w.pending) : w.inactive; }
function statusClass(p) { return p.active ? (p.activated ? 'active' : 'pending') : 'inactive'; }

async function api(path, {method='GET', body=null, binary=false}={}) {
  const options = {method, credentials: 'same-origin', headers: {}};
  if (method !== 'GET' && csrf) options.headers['X-CSRF-Token'] = csrf;
  if (body !== null) {
    options.body = binary ? body : JSON.stringify(body);
    options.headers['Content-Type'] = binary ? 'application/pdf' : 'application/json';
  }
  let r;
  try { r = await fetch('/api' + path, options); } catch { throw Error('network'); }
  let data = {};
  try { data = await r.json(); } catch { data = {}; }
  if (!r.ok) {
    if (r.status === 401 && user) { user=null; selected=null; folder=null; mode=''; render(); }
    throw Error(data.error || 'generic');
  }
  return data;
}

function notify(title, text, link) {
  document.getElementById('notice-title').textContent = title;
  document.getElementById('notice-text').textContent = text;
  const input = document.getElementById('notice-link');
  const copy = document.getElementById('copy-link');
  input.hidden = copy.hidden = !link;
  input.value = link || '';
  copy.textContent = t().copy;
  copy.onclick = async () => {
    try { await navigator.clipboard.writeText(input.value); copy.textContent = t().copied; }
    catch { input.select(); }
  };
  document.getElementById('notice').showModal();
}

function error(e) {
  const el = ui.root.querySelector('.error');
  const message = t().errors[e.message] || t().errors.generic;
  if (el) el.textContent = message; else notify('The Mile', message);
}
function bind(id, fn) {
  const el = document.getElementById(id);
  if (el) el.onclick = () => Promise.resolve().then(fn).catch(error);
}
function submit(fn) {
  const form = ui.root.querySelector('form');
  if (!form) return;
  form.onsubmit = async e => {
    e.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;
    const err = ui.root.querySelector('.error');
    if (err) err.textContent = '';
    try { await fn(new FormData(form)); } catch (e) { error(e); }
    finally { if (button) button.disabled = false; }
  };
}

async function refresh() {
  const session = await api('/me');
  user = session.user;
  csrf = session.csrf;
  if (user) {
    if (user.role === 'admin') {
      const results = await Promise.all([api('/players'), api('/admins')]);
      players = results[0].players;
      admins = results[1].admins;
    } else {
      docs = (await api('/documents')).documents;
    }
  }
  render();
}

async function openPlayer(id) {
  selected = players.find(p => p.id === id);
  docs = (await api('/documents?player=' + encodeURIComponent(id))).documents;
  folder = null;
  mode = '';
  render();
}

function renderDashboard(w) {
  if (mode === 'create') {
    ui.root.innerHTML = `<button class="back" id="back">${w.back}</button><p class="eyebrow">${w.management}</p><h1>${w.newPlayer.slice(2)}</h1><form class="inline-form"><label for="name">${w.name}</label><input id="name" name="name" maxlength="120" required><label for="email">${w.email}</label><input id="email" name="email" type="email" maxlength="254" required><p class="error" role="alert"></p><button class="primary" type="submit">${w.create}</button></form>`;
    bind('back', () => { mode=''; render(); });
    submit(async f => {
      const result = await api('/players', {method:'POST', body:{name:f.get('name'), email:f.get('email')}});
      mode=''; await refresh(); notify(w.linkTitle, w.linkText, result.activation_url);
    });
    return;
  }

  const active = players.filter(p => p.active && p.activated).length;
  const pending = players.filter(p => p.active && !p.activated).length;
  const inactive = players.filter(p => !p.active).length;
  const totalDocs = players.reduce((n,p) => n + Number(p.documents || 0), 0);

  ui.root.innerHTML = `
    <p class="eyebrow">${w.management} · ${esc(user.name)}</p>
    <div class="topline"><div><h1>${w.players}</h1><p class="subtitle compact">${w.manageSub}</p></div><button class="primary" id="create">${w.newPlayer}</button></div>
    <section class="overview" aria-label="${w.overview}">
      <div class="metric"><strong>${players.length}</strong><span>${w.totalPlayers}</span></div>
      <div class="metric"><strong>${active}</strong><span>${w.activePlayers}</span></div>
      <div class="metric"><strong>${pending}</strong><span>${w.pendingPlayers}</span></div>
      <div class="metric"><strong>${inactive}</strong><span>${w.inactivePlayers}</span></div>
      <div class="metric"><strong>${totalDocs}</strong><span>${w.totalDocuments}</span></div>
    </section>
    <section class="panel-section">
      <div class="section-head"><h2>${w.players}</h2></div>
      ${players.length ? `<label for="search">${w.search}</label><input id="search" type="search" autocomplete="off"><div id="player-list"></div>` : `<p class="empty">${w.noPlayers}</p>`}
    </section>
    <section class="panel-section administrators">
      <div class="section-head"><div><h2>${w.administrators}</h2><p>${w.adminSub}</p></div></div>
      <div id="admin-list">${admins.map(a => `<div class="row admin-row"><div><strong>${esc(a.name)}${a.id===user.id?` <span class="you">${w.current}</span>`:''}</strong><p>${esc(a.email)}</p></div><div class="actions"><span class="badge ${statusClass(a)}">${statusLabel(a,w)}</span><button class="secondary" data-admin-link="${a.id}">${w.generateLink}</button></div></div>`).join('')}</div>
    </section>`;

  bind('create', () => { mode='create'; render(); });

  if (players.length) {
    const list = document.getElementById('player-list');
    function show(q='') {
      const filtered = players.filter(p => (p.name+' '+p.email).toLowerCase().includes(q.toLowerCase()));
      list.innerHTML = filtered.map(p => `<div class="row player-row"><div><strong>${esc(p.name)}</strong><p>${esc(p.email)}</p><div class="row-meta"><span class="badge ${statusClass(p)}">${statusLabel(p,w)}</span><span>${p.documents} ${w.documents}</span></div></div><button class="secondary" data-player="${p.id}">${w.manage}</button></div>`).join('') || `<p class="empty">${w.noMatches}</p>`;
      list.querySelectorAll('[data-player]').forEach(b => b.onclick = () => openPlayer(b.dataset.player).catch(error));
    }
    show();
    document.getElementById('search').oninput = e => show(e.target.value);
  }

  ui.root.querySelectorAll('[data-admin-link]').forEach(b => b.onclick = async () => {
    try {
      b.disabled = true;
      const result = await api('/admins/' + b.dataset.adminLink + '/activation', {method:'POST', body:{}});
      notify(w.linkTitle, w.linkText, result.activation_url);
    } catch (e) { error(e); }
    finally { b.disabled = false; }
  });
}

function renderPlayer(w) {
  const isAdmin = user.role === 'admin';
  const owner = isAdmin ? selected : user;

  if (isAdmin && mode === 'edit') {
    ui.root.innerHTML = `<button class="back" id="back">${w.back}</button><p class="eyebrow">${w.playerDetails}</p><h1>${esc(owner.name)}</h1><form class="inline-form"><label for="name">${w.name}</label><input id="name" name="name" maxlength="120" value="${esc(owner.name)}" required><label for="email">${w.email}</label><input id="email" name="email" type="email" maxlength="254" value="${esc(owner.email)}" required><p class="error" role="alert"></p><div class="actions"><button class="primary" type="submit">${w.update}</button><button class="secondary" type="button" id="cancel">${w.cancel}</button></div></form>`;
    bind('back', () => { mode=''; render(); });
    bind('cancel', () => { mode=''; render(); });
    submit(async f => {
      await api('/players/' + owner.id, {method:'PUT', body:{name:f.get('name'), email:f.get('email')}});
      selected = null; mode=''; await refresh();
    });
    return;
  }

  const title = folder === null ? (isAdmin ? owner.name : w.hello + ' ' + owner.name.split(' ')[0] + '.') : w.folders[folders.indexOf(folder)];
  ui.root.innerHTML = `${isAdmin || folder!==null ? `<button class="back" id="back">${w.back}</button>` : ''}
    ${folder===null ? `<p class="eyebrow">${isAdmin ? esc(owner.email) : w.private}</p>` : ''}
    <div class="topline"><h1>${esc(title)}</h1>${isAdmin && folder!==null && mode!=='upload' ? `<button class="primary" id="upload">${w.upload}</button>` : ''}</div>
    ${folder===null ? `<p class="subtitle">${w.sub}</p><div class="folders">${folders.map((f,i)=>{const count=docs.filter(d=>d.folder===f).length;return `<button class="folder" data-folder="${f}"><span class="folder-icon" aria-hidden="true"></span><div><strong>${w.folders[i]}</strong><small>${count} ${count===1?w.document:w.documents}</small></div></button>`}).join('')}</div>${isAdmin ? `<div class="player-control"><div><span class="badge ${statusClass(owner)}">${statusLabel(owner,w)}</span></div><div class="actions player-actions"><button class="secondary" id="edit">${w.edit}</button><button class="secondary" id="reset" ${!owner.active?'disabled':''}>${w.reset}</button><button class="secondary" id="status">${owner.active?w.deactivate:w.reactivate}</button><button class="secondary danger" id="delete-player">${w.deletePlayer}</button></div></div>` : ''}` :
      mode==='upload' ? `<form class="inline-form"><label for="doc-title">${w.documentTitle}</label><input id="doc-title" name="title" type="text" maxlength="180" required><label for="pdf">${w.file}</label><input id="pdf" name="pdf" type="file" accept="application/pdf,.pdf" required><p class="note">${w.pdfNote}</p><p class="error" role="alert"></p><div class="actions"><button class="primary" type="submit">${w.save}</button><button class="secondary" type="button" id="cancel">${w.cancel}</button></div></form>` :
      docs.filter(d=>d.folder===folder).map(d=>`<div class="row"><div><strong>${esc(d.title)}</strong><p>PDF · ${new Intl.DateTimeFormat(lang==='pt'?'pt-PT':'en-GB').format(new Date(d.updated*1000))} · ${(d.size/1024/1024).toFixed(1)} MB</p></div><div class="actions"><a class="primary download" href="/api/documents/${d.id}">${w.download}</a>${isAdmin?`<button class="secondary" data-title="${d.id}">${w.editTitle}</button><button class="secondary" data-replace="${d.id}">${w.replace}</button><button class="secondary danger" data-delete="${d.id}">${w.remove}</button>`:''}</div></div>`).join('') || `<p class="empty">${w.empty}</p>`}`;

  bind('back', async () => { if(mode){mode='';render();} else if(folder!==null){folder=null;render();} else {selected=null;await refresh();} });
  ui.root.querySelectorAll('[data-folder]').forEach(b => b.onclick = () => {folder=b.dataset.folder; mode=''; render();});
  bind('upload', () => {mode='upload';render();});
  bind('cancel', () => {mode='';render();});
  bind('edit', () => {mode='edit';render();});
  bind('reset', async () => {const result=await api('/players/'+owner.id+'/activation',{method:'POST',body:{}});notify(w.linkTitle,w.linkText,result.activation_url);});
  bind('status', async () => {if(!confirm(w.statusConfirm))return;await api('/players/'+owner.id+'/status',{method:'POST',body:{active:!owner.active}});selected=null;await refresh();});
  bind('delete-player', async () => {if(!confirm(w.deletePlayerConfirm))return;await api('/players/'+owner.id,{method:'DELETE'});selected=null;folder=null;mode='';await refresh();});

  if (mode==='upload') submit(async f => {
    const file=f.get('pdf');
    if(!file||!file.size)throw Error('pdf_only');
    if(file.size>20*1024*1024)throw Error('file_size');
    const title=String(f.get('title')||'').trim();
    if(!title)throw Error('document_fields');
    await api('/documents?player='+encodeURIComponent(owner.id)+'&folder='+folder+'&title='+encodeURIComponent(title),{method:'POST',body:file,binary:true});
    docs=(await api('/documents?player='+encodeURIComponent(owner.id))).documents;mode='';render();
  });

  ui.root.querySelectorAll('[data-title]').forEach(b=>b.onclick=async()=>{
    const d=docs.find(x=>x.id===b.dataset.title);
    const title=prompt(w.titlePrompt,d?d.title:'');
    if(title===null)return;
    const clean=title.trim();
    if(!clean)return;
    try{
      await api('/documents/'+b.dataset.title,{method:'PATCH',body:{title:clean}});
      docs=(await api('/documents?player='+encodeURIComponent(owner.id))).documents;
      render();
    }catch(e){error(e)}
  });

  ui.root.querySelectorAll('[data-replace]').forEach(b=>b.onclick=()=>{
    const input=document.createElement('input'); input.type='file'; input.accept='application/pdf,.pdf';
    input.onchange=async()=>{const file=input.files[0];if(!file)return;try{if(file.size>20*1024*1024)throw Error('file_size');b.disabled=true;await api('/documents/'+b.dataset.replace,{method:'PUT',body:file,binary:true});docs=(await api('/documents?player='+encodeURIComponent(owner.id))).documents;render()}catch(e){error(e)}finally{b.disabled=false}};
    input.click();
  });
  ui.root.querySelectorAll('[data-delete]').forEach(b=>b.onclick=async()=>{if(!confirm(w.removeConfirm))return;try{await api('/documents/'+b.dataset.delete,{method:'DELETE'});docs=(await api('/documents?player='+encodeURIComponent(owner.id))).documents;render()}catch(e){error(e)}});
}

function render() {
  const w=t();
  document.documentElement.lang=lang==='pt'?'pt-PT':'en';
  ui.lang.textContent=lang==='pt'?'EN':'PT';
  ui.logout.hidden=!user;
  ui.logout.textContent=w.logout;
  ui.install.textContent=w.install;
  document.getElementById('tagline').textContent=w.foot;

  if (!user || activationToken) {
    const activating=!!activationToken;
    ui.root.innerHTML=`<div class="login"><p class="eyebrow">The Mile</p><h1>${activating?w.activate:w.enter}</h1><p class="subtitle">${activating?w.activateSub:w.loginSub}</p><form>${!activating?`<label for="email">${w.email}</label><input id="email" name="email" type="email" autocomplete="username" required>`:''}<label for="password">${w.password}</label><input id="password" name="password" type="password" autocomplete="${activating?'new-password':'current-password'}" ${activating?'minlength="12"':''} maxlength="256" required>${activating?`<label for="confirm">${w.confirm}</label><input id="confirm" name="confirm" type="password" autocomplete="new-password" minlength="12" maxlength="256" required>`:''}<p class="error" role="alert"></p><button class="primary" type="submit">${activating?w.save:w.enter}</button></form>${!activating?`<button id="forgot" class="subtle">${w.forgot}</button>`:''}</div>`;
    submit(async f=>{if(activating&&f.get('password')!==f.get('confirm'))throw Error('password_mismatch');await api(activating?'/activate':'/login',{method:'POST',body:{email:f.get('email'),password:f.get('password'),token:activationToken}});activationToken=null;await refresh();});
    bind('forgot',()=>notify(w.forgot,w.forgotText));
    return;
  }

  if (user.role==='admin' && !selected) { renderDashboard(w); return; }
  renderPlayer(w);
}

ui.lang.onclick=()=>{lang=lang==='pt'?'en':'pt';localStorage.setItem('mile-language',lang);render();};
ui.logout.onclick=async()=>{try{await api('/logout',{method:'POST',body:{}});user=null;csrf=null;selected=null;folder=null;mode='';players=[];admins=[];docs=[];render()}catch(e){error(e)}};

function isStandalone() {
  return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
}
function isiOS() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}
function updateInstallButton() {
  ui.install.hidden = isStandalone() || (!installPrompt && !isiOS());
}
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  installPrompt = e;
  updateInstallButton();
});
window.addEventListener('appinstalled', () => {
  installPrompt = null;
  updateInstallButton();
});
ui.install.onclick = async () => {
  const w = t();
  if (installPrompt) {
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    updateInstallButton();
    return;
  }
  notify(w.installTitle, isiOS() ? w.installIOS : w.installOther);
};
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}));
}
updateInstallButton();
refresh().catch(e=>{render();error(e)});
