// Painel administrativo — usuários, faculdades, cursos, vestibulares e dados
// do sistema. Navegação entre seções em painel.js; todas as rotas usadas
// aqui exigem admin no backend (@admin_required).
let deleteUserId = null;
let deleteFaculdadeId = null;
let usuariosCarregados = [];

const PAGINA_ADMIN = 20;
const estadoCursos = { pagina: 1, busca: '' };
const estadoVestibulares = { pagina: 1, busca: '' };
const secoesCarregadas = {};

// ── Utilitários ──
function esc(texto) {
    const div = document.createElement('div');
    div.textContent = texto == null ? '' : String(texto);
    return div.innerHTML;
}

function urlSegura(url) {
    return /^https?:\/\//i.test(url || '') ? esc(url) : '';
}

function alerta(elOuId, tipo, mensagem) {
    const el = typeof elOuId === 'string' ? document.getElementById(elOuId) : elOuId;
    if (!el) return;
    el.innerHTML = mensagem ? `<div class="alert ${tipo || ''}">${esc(mensagem)}</div>` : '';
}

function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function dataBR(valor) {
    if (!valor) return '—';
    const [a, m, d] = String(valor).slice(0, 10).split('-');
    return d && m && a ? `${d}/${m}/${a}` : esc(valor);
}

function dataHoraBR(valor) {
    if (!valor) return '—';
    const texto = String(valor).replace(' ', 'T');
    const d = new Date(texto.endsWith('Z') ? texto : `${texto}Z`); // SQLite grava em UTC
    return isNaN(d) ? esc(valor) : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function renderizarPaginacao(containerId, pagina, totalPaginas, aoMudar) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = '';
    if (totalPaginas <= 1) return;
    const botao = (rotulo, destino, desabilitado, aria) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.innerHTML = rotulo;
        b.disabled = desabilitado;
        b.setAttribute('aria-label', aria);
        b.addEventListener('click', () => aoMudar(destino));
        el.appendChild(b);
    };
    botao('<i class="fas fa-chevron-left"></i>', pagina - 1, pagina <= 1, 'Página anterior');
    const info = document.createElement('span');
    info.className = 'admin-pagina-info';
    info.textContent = `${pagina} / ${totalPaginas}`;
    el.appendChild(info);
    botao('<i class="fas fa-chevron-right"></i>', pagina + 1, pagina >= totalPaginas, 'Próxima página');
}

// Compatibilidade: a navegação antiga era por abas (openTab('users')).
function openTab(tabName) {
    const mapa = { users: 'usuarios', settings: 'sistema' };
    if (window.SuaFaculPainel) window.SuaFaculPainel.mostrar(mapa[tabName] || tabName);
}

// Carrega os dados de cada seção só quando ela é aberta.
document.addEventListener('painel:secao', (e) => {
    const id = e.detail.id;
    if (secoesCarregadas[id]) return;
    secoesCarregadas[id] = true;
    if (id === 'usuarios') carregarUsuarios();
    if (id === 'faculdades') carregarFaculdades();
    if (id === 'cursos') carregarCursos();
    if (id === 'vestibulares') carregarVestibularesCadastrados();
});

document.addEventListener('DOMContentLoaded', function () {
    carregarStats();
});

// ── Estatísticas (todas vêm de /api/admin/stats) ──
function carregarStats() {
    fetch('/api/admin/stats')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            const s = data.stats;
            document.querySelectorAll('[data-stat]').forEach(el => {
                const valor = s[el.dataset.stat];
                el.textContent = valor == null ? '–' : Number(valor).toLocaleString('pt-BR');
            });
            renderizarAutomacoes(data.automacoes || []);
        })
        .catch(() => {});
}

function renderizarAutomacoes(automacoes) {
    const lista = document.getElementById('automacoes-lista');
    if (!lista) return;
    if (!automacoes.length) {
        lista.innerHTML = `
            <li class="painel-vazio">
                <i class="fas fa-robot"></i>
                <strong>Nenhuma execução registrada</strong>
                <p>A validação de vestibulares roda automaticamente uma vez por dia; o histórico aparece aqui.</p>
            </li>`;
        return;
    }
    const nomes = { validacao_vestibulares: 'Validação de vestibulares' };
    lista.innerHTML = automacoes.map(a => {
        const r = a.resumo || {};
        const detalhe = a.sucesso
            ? (r.total != null ? `${r.total} vestibulares · ${r.ativos || 0} ativos · ${r.encerrados || 0} encerrados` : 'Concluída')
            : 'Falhou — veja o log da aplicação';
        return `
            <li class="painel-lista-item">
                <span class="painel-lista-icone ${a.sucesso ? 'painel-lista-icone--ok' : 'painel-lista-icone--erro'}" aria-hidden="true">
                    <i class="fas ${a.sucesso ? 'fa-check' : 'fa-xmark'}"></i>
                </span>
                <div class="painel-lista-texto">
                    <span class="painel-lista-titulo">${esc(nomes[a.tipo] || a.tipo)}</span>
                    <span class="painel-lista-meta">${esc(detalhe)}</span>
                </div>
                <span class="painel-chip">${dataHoraBR(a.executado_em)}</span>
            </li>`;
    }).join('');
}

// ── Usuários ──
function carregarUsuarios() {
    const loading = document.getElementById('users-loading');
    const table = document.getElementById('users-table');
    const alertEl = document.getElementById('users-alert');

    loading.style.display = 'flex';
    table.style.display = 'none';
    alertEl.textContent = '';

    fetch('/api/usuario/listar')
        .then(response => response.json())
        .then(data => {
            loading.style.display = 'none';
            if (data.success) {
                table.style.display = 'table';
                usuariosCarregados = data.usuarios;
                buscarUsuarios();
            } else {
                alerta(alertEl, 'error', data.message);
            }
        })
        .catch(() => {
            loading.style.display = 'none';
            alerta(alertEl, 'error', 'Erro ao carregar usuários.');
        });
}

function renderizarUsuarios(usuarios) {
    const tbody = document.getElementById('users-list');
    tbody.innerHTML = '';

    if (!usuarios.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="admin-vazio">Nenhum usuário encontrado.</td></tr>';
    }

    usuarios.forEach(user => {
        const row = document.createElement('tr');
        const ehAdmin = user.tipo === 'admin';
        const ehVoce = String(user.id) === String(window._adminUsuarioId);
        row.innerHTML = `
            <td>${esc(user.id)}</td>
            <td>
                <div class="admin-usuario">
                    <span class="admin-usuario-avatar" aria-hidden="true">${esc((user.nome_usuario || '?').charAt(0).toUpperCase())}</span>
                    <strong>${esc(user.nome_usuario)}</strong>${ehVoce ? ' <span class="painel-chip">você</span>' : ''}
                </div>
            </td>
            <td>${esc(user.email)}</td>
            <td><span class="badge ${ehAdmin ? 'badge-admin' : 'badge-aluno'}">${ehAdmin ? 'Admin' : 'Aluno'}</span></td>
            <td class="user-actions"></td>
        `;
        const acoes = row.querySelector('.user-actions');
        const editar = document.createElement('button');
        editar.type = 'button';
        editar.className = 'btn-icone';
        editar.title = 'Editar usuário';
        editar.setAttribute('aria-label', `Editar ${user.nome_usuario}`);
        editar.innerHTML = '<i class="fas fa-pen"></i>';
        editar.addEventListener('click', () => editarUsuario(user.id, user.nome_usuario, user.email, user.tipo));
        acoes.appendChild(editar);
        if (!ehVoce) {
            const excluir = document.createElement('button');
            excluir.type = 'button';
            excluir.className = 'btn-icone btn-icone--perigo';
            excluir.title = 'Excluir usuário';
            excluir.setAttribute('aria-label', `Excluir ${user.nome_usuario}`);
            excluir.innerHTML = '<i class="fas fa-trash"></i>';
            excluir.addEventListener('click', () => excluirUsuario(user.id));
            acoes.appendChild(excluir);
        }
        tbody.appendChild(row);
    });
}

// Filtra a lista já carregada por nome ou e-mail (o campo de busca antes
// era ignorado e só recarregava a lista inteira).
function buscarUsuarios() {
    const termo = (document.getElementById('search-input').value || '').trim().toLowerCase();
    const filtrados = !termo ? usuariosCarregados : usuariosCarregados.filter(u =>
        (u.nome_usuario || '').toLowerCase().includes(termo) || (u.email || '').toLowerCase().includes(termo));
    renderizarUsuarios(filtrados);
    const total = document.getElementById('users-total');
    if (total) {
        total.textContent = termo
            ? `${filtrados.length} de ${usuariosCarregados.length} usuários`
            : `${usuariosCarregados.length} usuário${usuariosCarregados.length === 1 ? '' : 's'}`;
    }
}

function abrirModal(id) {
    const modal = document.getElementById(id);
    modal.style.display = 'block';
    const primeiro = modal.querySelector('input:not([type="hidden"]), select, textarea');
    if (primeiro) setTimeout(() => primeiro.focus(), 50);
}

function abrirModalAdicionar() {
    document.getElementById('modal-title').textContent = 'Adicionar Usuário';
    document.getElementById('user-form').reset();
    document.getElementById('user-id').value = '';
    document.getElementById('modal-alert').innerHTML = '';
    document.getElementById('tipo-group').style.display = 'none';
    document.getElementById('password').required = true;
    abrirModal('user-modal');
}

function editarUsuario(id, username, email, tipo) {
    document.getElementById('modal-title').textContent = 'Editar Usuário';
    document.getElementById('user-id').value = id;
    document.getElementById('username').value = username;
    document.getElementById('email').value = email;
    document.getElementById('password').value = '';
    document.getElementById('password').required = false;
    document.getElementById('modal-alert').innerHTML = '';
    document.getElementById('tipo-group').style.display = 'block';
    document.getElementById('user-tipo').value = tipo || 'aluno';
    abrirModal('user-modal');
}

function fecharModal() {
    document.getElementById('user-modal').style.display = 'none';
}

function fecharConfirmModal() {
    document.getElementById('confirm-modal').style.display = 'none';
    deleteUserId = null;
    deleteFaculdadeId = null;
}

function confirmarExclusao() {
    if (deleteFaculdadeId) {
        const id = deleteFaculdadeId;
        const formData = new FormData();
        formData.append('id', id);
        fetch('/api/faculdades/deletar', { method: 'POST', body: formData })
            .then(r => r.json())
            .then(data => {
                fecharConfirmModal();
                alerta('faculdades-alert', data.success ? 'success' : 'error', data.message);
                if (data.success) { carregarFaculdades(); carregarStats(); }
            })
            .catch(() => {
                fecharConfirmModal();
                alerta('faculdades-alert', 'error', 'Erro ao excluir faculdade.');
            });
        return;
    }
    if (!deleteUserId) return;

    const formData = new FormData();
    formData.append('id', deleteUserId);

    fetch('/api/usuario/deletar', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            fecharConfirmModal();
            alerta('users-alert', data.success ? 'success' : 'error', data.message);
            if (data.success) { carregarUsuarios(); carregarStats(); }
        })
        .catch(() => {
            fecharConfirmModal();
            alerta('users-alert', 'error', 'Erro ao excluir usuário.');
        });
}

function excluirUsuario(id) {
    deleteUserId = id;
    deleteFaculdadeId = null;
    document.getElementById('confirm-message').textContent = 'Tem certeza que deseja excluir este usuário? Os favoritos dele também serão removidos.';
    document.getElementById('confirm-modal').style.display = 'block';
}

function handleLogout() {
    window.location.href = '/logout';
}

function irParaDashboard() {
    window.location.href = '/dashboard';
}

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('search-input').addEventListener('input', debounce(buscarUsuarios, 150));
    document.getElementById('faculdade-search-input').addEventListener('input', debounce(buscarFaculdades, 350));
    document.getElementById('faculdade-search-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); buscarFaculdades(); }
    });
    document.getElementById('curso-search-input').addEventListener('input', debounce(() => {
        estadoCursos.busca = document.getElementById('curso-search-input').value.trim();
        estadoCursos.pagina = 1;
        carregarCursos();
    }, 350));
    document.getElementById('vestibular-search-input').addEventListener('input', debounce(() => {
        estadoVestibulares.busca = document.getElementById('vestibular-search-input').value.trim();
        estadoVestibulares.pagina = 1;
        carregarVestibularesCadastrados();
    }, 350));

    document.getElementById('user-form').addEventListener('submit', function (e) {
        e.preventDefault();

        const userId = document.getElementById('user-id').value;
        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const tipo = document.getElementById('user-tipo').value;

        const formData = new FormData();
        formData.append('username', username);
        formData.append('email', email);
        if (password) formData.append('password', password);

        const url = userId ? '/api/usuario/atualizar' : '/api/usuario/registrar';
        if (userId) formData.append('id', userId);

        fetch(url, { method: 'POST', body: formData })
            .then(response => response.json())
            .then(async data => {
                if (data.success) {
                    // Se estiver editando e o tipo foi alterado, aplica separadamente
                    if (userId) {
                        const tipoForm = new FormData();
                        tipoForm.append('id', userId);
                        tipoForm.append('tipo', tipo);
                        const r = await fetch('/api/usuario/definir-tipo', { method: 'POST', body: tipoForm });
                        const tipoRes = await r.json().catch(() => ({ success: true }));
                        if (!tipoRes.success) {
                            alerta('modal-alert', 'error', tipoRes.message);
                            carregarUsuarios();
                            return;
                        }
                    }
                    fecharModal();
                    alerta('users-alert', 'success', data.message);
                    carregarUsuarios();
                    carregarStats();
                } else {
                    alerta('modal-alert', 'error', data.message);
                }
            })
            .catch(() => {
                alerta('modal-alert', 'error', 'Erro ao salvar usuário.');
            });
    });

    document.getElementById('faculdade-form').addEventListener('submit', function (e) {
        e.preventDefault();
        salvarFaculdade();
    });

    document.getElementById('curso-form').addEventListener('submit', function (e) {
        e.preventDefault();
        salvarCurso();
    });

    document.getElementById('vestibular-form').addEventListener('submit', function (e) {
        e.preventDefault();
        salvarVestibular();
    });

    const modais = {
        'user-modal': fecharModal,
        'confirm-modal': fecharConfirmModal,
        'faculdade-modal': fecharModalFaculdade,
        'curso-modal': fecharModalCurso,
        'vestibular-modal': fecharModalVestibular,
    };
    window.onclick = function (event) {
        if (modais[event.target.id]) modais[event.target.id]();
    };
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        Object.entries(modais).forEach(([id, fechar]) => {
            if (document.getElementById(id).style.display === 'block') fechar();
        });
    });
});

// ── Faculdades ──
function carregarFaculdades(busca) {
    const loading = document.getElementById('faculdades-loading');
    const table = document.getElementById('faculdades-table');

    loading.style.display = 'flex';
    table.style.display = 'none';

    const params = new URLSearchParams();
    if (busca) params.append('busca', busca);
    params.append('limit', '100');

    fetch('/api/faculdades/listar?' + params.toString())
        .then(r => r.json())
        .then(data => {
            loading.style.display = 'none';
            if (data.success) {
                table.style.display = 'table';
                renderizarFaculdades(data.faculdades);
                const total = document.getElementById('faculdades-total');
                if (total) {
                    total.textContent = data.total > data.faculdades.length
                        ? `Mostrando ${data.faculdades.length} de ${data.total} faculdades — refine a busca para ver outras`
                        : `${data.total} faculdade${data.total === 1 ? '' : 's'}`;
                }
            } else {
                alerta('faculdades-alert', 'error', data.message);
            }
        })
        .catch(() => {
            loading.style.display = 'none';
            alerta('faculdades-alert', 'error', 'Erro ao carregar faculdades.');
        });
}

function renderizarFaculdades(faculdades) {
    const tbody = document.getElementById('faculdades-list');
    tbody.innerHTML = '';

    if (!faculdades.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="admin-vazio">Nenhuma faculdade encontrada.</td></tr>';
    }

    faculdades.forEach(f => {
        const row = document.createElement('tr');
        const contato = [f.telefone, f.email].filter(Boolean).map(esc).join(' / ') || '<em class="admin-pendente">a completar</em>';
        const site = urlSegura(f.url);
        row.innerHTML = `
            <td><strong>${esc(f.nome)}</strong>${f.sigla ? ' (' + esc(f.sigla) + ')' : ''}${site ? `<br><a href="${site}" target="_blank" rel="noopener">${site}</a>` : ''}</td>
            <td>${esc([f.cidade, f.uf].filter(Boolean).join('/') || '-')}</td>
            <td>${esc(f.tipo_instituicao)}</td>
            <td>${f.fonte === 'emec' ? '<span class="badge badge-ok">e-MEC</span>' : '<span class="badge badge-pendente">Manual</span>'}</td>
            <td>${contato}</td>
            <td class="user-actions"></td>
        `;
        const acoes = row.querySelector('.user-actions');
        const editar = document.createElement('button');
        editar.type = 'button';
        editar.className = 'btn-icone';
        editar.title = 'Editar faculdade';
        editar.setAttribute('aria-label', `Editar ${f.nome}`);
        editar.innerHTML = '<i class="fas fa-pen"></i>';
        editar.addEventListener('click', () => editarFaculdade(f));
        const excluir = document.createElement('button');
        excluir.type = 'button';
        excluir.className = 'btn-icone btn-icone--perigo';
        excluir.title = 'Excluir faculdade';
        excluir.setAttribute('aria-label', `Excluir ${f.nome}`);
        excluir.innerHTML = '<i class="fas fa-trash"></i>';
        excluir.addEventListener('click', () => excluirFaculdade(f.id));
        acoes.append(editar, excluir);
        tbody.appendChild(row);
    });
}

function buscarFaculdades() {
    carregarFaculdades(document.getElementById('faculdade-search-input').value.trim());
}

function abrirModalFaculdade() {
    document.getElementById('faculdade-modal-title').textContent = 'Cadastrar Faculdade';
    document.getElementById('faculdade-form').reset();
    document.getElementById('faculdade-id').value = '';
    document.getElementById('faculdade-modal-alert').innerHTML = '';
    abrirModal('faculdade-modal');
}

function editarFaculdade(f) {
    document.getElementById('faculdade-modal-title').textContent = 'Editar Faculdade';
    document.getElementById('faculdade-id').value = f.id;
    document.getElementById('f-nome').value = f.nome || '';
    document.getElementById('f-sigla').value = f.sigla || '';
    document.getElementById('f-tipo').value = f.tipo_instituicao || 'Pública';
    document.getElementById('f-url').value = f.url || '';
    document.getElementById('f-endereco').value = f.endereco || '';
    document.getElementById('f-cidade').value = f.cidade || '';
    document.getElementById('f-uf').value = f.uf || '';
    document.getElementById('f-telefone').value = f.telefone || '';
    document.getElementById('f-email').value = f.email || '';
    document.getElementById('faculdade-modal-alert').innerHTML = '';
    abrirModal('faculdade-modal');
}

function fecharModalFaculdade() {
    document.getElementById('faculdade-modal').style.display = 'none';
}

function salvarFaculdade() {
    const id = document.getElementById('faculdade-id').value;
    const formData = new FormData();
    formData.append('nome', document.getElementById('f-nome').value);
    formData.append('sigla', document.getElementById('f-sigla').value);
    formData.append('tipo_instituicao', document.getElementById('f-tipo').value);
    formData.append('url', document.getElementById('f-url').value);
    formData.append('endereco', document.getElementById('f-endereco').value);
    formData.append('cidade', document.getElementById('f-cidade').value);
    formData.append('uf', document.getElementById('f-uf').value);
    formData.append('telefone', document.getElementById('f-telefone').value);
    formData.append('email', document.getElementById('f-email').value);

    const url = id ? '/api/faculdades/atualizar' : '/api/faculdades/criar';
    if (id) formData.append('id', id);

    fetch(url, { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                fecharModalFaculdade();
                alerta('faculdades-alert', 'success', data.message);
                if (window.SuaFaculPainel) window.SuaFaculPainel.mostrar('faculdades');
                carregarFaculdades();
                carregarStats();
            } else {
                alerta('faculdade-modal-alert', 'error', data.message);
            }
        })
        .catch(() => {
            alerta('faculdade-modal-alert', 'error', 'Erro ao salvar faculdade.');
        });
}

function excluirFaculdade(id) {
    deleteFaculdadeId = id;
    deleteUserId = null;
    document.getElementById('confirm-message').textContent = 'Tem certeza que deseja excluir esta faculdade?';
    document.getElementById('confirm-modal').style.display = 'block';
}

function importarEmec() {
    const codigo = document.getElementById('emec-codigo').value.trim();
    if (!codigo) {
        alerta('faculdades-alert', 'error', 'Informe o código e-MEC da instituição.');
        return;
    }
    alerta('faculdades-alert', '', 'Importando do e-MEC, aguarde...');
    const formData = new FormData();
    formData.append('codigo', codigo);
    fetch('/api/faculdades/emec/importar', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            alerta('faculdades-alert', data.success ? 'success' : 'error',
                data.message || (data.success ? 'Importado com sucesso.' : 'Falha na importação.'));
            if (data.success) {
                document.getElementById('emec-codigo').value = '';
                carregarFaculdades();
                carregarStats();
            }
        })
        .catch(() => {
            alerta('faculdades-alert', 'error', 'Erro ao importar do e-MEC.');
        });
}

function importarEmecPorUF() {
    const uf = document.getElementById('emec-uf').value;
    if (!uf) {
        alerta('faculdades-alert', 'error', 'Selecione uma UF.');
        return;
    }
    alerta('faculdades-alert', '', `Importando todas as instituições de ${uf} do e-MEC, isso pode levar um tempo...`);
    const formData = new FormData();
    formData.append('uf', uf);
    fetch('/api/faculdades/emec/importar-uf', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alerta('faculdades-alert', 'success', `UF ${data.uf}: ${data.total_encontradas} instituições encontradas — ${data.criadas} criadas, ${data.atualizadas} atualizadas${data.falhas ? `, ${data.falhas} falharam` : ''}.`);
                carregarFaculdades();
                carregarStats();
            } else {
                alerta('faculdades-alert', 'error', data.message || 'Falha na importação.');
            }
        })
        .catch(() => {
            alerta('faculdades-alert', 'error', 'Erro ao importar instituições da UF.');
        });
}

function importarEmecCsv() {
    const input = document.getElementById('emec-csv-file');
    const arquivo = input.files[0];
    if (!arquivo) {
        alerta('faculdades-alert', 'error', 'Selecione o arquivo CSV baixado de dadosabertos.mec.gov.br.');
        return;
    }
    alerta('faculdades-alert', '', 'Processando o CSV, isso pode levar um instante (o arquivo tem milhares de linhas)...');
    const formData = new FormData();
    formData.append('arquivo', arquivo);
    fetch('/api/faculdades/emec/importar-csv', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alerta('faculdades-alert', 'success', `CSV processado: ${data.total_no_arquivo} instituições no arquivo — ${data.criadas} criadas, ${data.atualizadas} atualizadas${data.falhas ? `, ${data.falhas} falharam` : ''}.`);
                input.value = '';
                carregarFaculdades();
                carregarStats();
            } else {
                alerta('faculdades-alert', 'error', data.message || 'Falha ao processar o CSV.');
            }
        })
        .catch(() => {
            alerta('faculdades-alert', 'error', 'Erro ao enviar o arquivo CSV.');
        });
}

function importarEmecBrasil() {
    if (!confirm('Isso vai importar as instituições de TODAS as 27 UFs do Brasil e pode levar vários minutos. Deseja continuar?')) {
        return;
    }
    alerta('faculdades-alert', '', 'Importando instituições de todo o Brasil, isso pode levar vários minutos — não feche esta página...');
    fetch('/api/faculdades/emec/importar-brasil', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alerta('faculdades-alert', 'success', `${data.ufs_processadas} UFs processadas: ${data.total_criadas} faculdades criadas, ${data.total_atualizadas} atualizadas.`);
                carregarFaculdades();
                carregarStats();
            } else {
                alerta('faculdades-alert', 'error', data.message || 'Falha na importação.');
            }
        })
        .catch(() => {
            alerta('faculdades-alert', 'error', 'Erro ao importar instituições do Brasil.');
        });
}

// ── Cursos ──
function carregarCursos() {
    const loading = document.getElementById('cursos-loading');
    const table = document.getElementById('cursos-table');
    loading.style.display = 'flex';
    table.style.display = 'none';

    const params = new URLSearchParams({ page: estadoCursos.pagina, limit: PAGINA_ADMIN });
    if (estadoCursos.busca) params.append('busca', estadoCursos.busca);

    fetch('/api/cursos/listar?' + params.toString())
        .then(r => r.json())
        .then(data => {
            loading.style.display = 'none';
            if (!data.success) {
                alerta('cursos-alert', 'error', data.message || 'Erro ao carregar cursos.');
                return;
            }
            table.style.display = 'table';
            renderizarCursos(data.cursos);
            document.getElementById('cursos-total').textContent =
                `${data.total} curso${data.total === 1 ? '' : 's'}${estadoCursos.busca ? ' encontrados' : ''}`;
            renderizarPaginacao('cursos-paginacao', estadoCursos.pagina, data.total_pages, (p) => {
                estadoCursos.pagina = p;
                carregarCursos();
            });
            preencherAreasConhecidas(data.cursos);
        })
        .catch(() => {
            loading.style.display = 'none';
            alerta('cursos-alert', 'error', 'Erro ao carregar cursos.');
        });
}

function renderizarCursos(cursos) {
    const tbody = document.getElementById('cursos-list');
    if (!cursos.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="admin-vazio">Nenhum curso encontrado.</td></tr>';
        return;
    }
    const modalidades = { presencial: 'Presencial', ead: 'EaD', semipresencial: 'Semipresencial' };
    tbody.innerHTML = cursos.map(c => `
        <tr>
            <td><strong>${esc(c.nome)}</strong></td>
            <td>${esc(c.instituicao || '—')}</td>
            <td>${esc(c.area || '—')}</td>
            <td><span class="badge badge-modalidade">${esc(modalidades[c.modalidade] || c.modalidade || '—')}</span></td>
            <td>${esc([c.grau, c.duracao].filter(Boolean).join(' · ') || '—')}</td>
        </tr>`).join('');
}

function preencherAreasConhecidas(cursos) {
    const lista = document.getElementById('c-areas');
    if (!lista) return;
    const existentes = new Set(Array.from(lista.options).map(o => o.value));
    cursos.map(c => c.area).filter(Boolean).forEach(area => {
        if (!existentes.has(area)) {
            existentes.add(area);
            const op = document.createElement('option');
            op.value = area;
            lista.appendChild(op);
        }
    });
}

let faculdadesDoSelect = null;
function carregarFaculdadesNoSelect() {
    const select = document.getElementById('c-faculdade');
    if (faculdadesDoSelect) return Promise.resolve();
    return fetch('/api/faculdades/listar?limit=5000')
        .then(r => r.json())
        .then(data => {
            faculdadesDoSelect = data.success ? data.faculdades : [];
            select.innerHTML = '<option value="">Selecione a faculdade...</option>' + faculdadesDoSelect.map(f =>
                `<option value="${esc(f.id)}">${esc(f.nome)}${f.sigla && !f.nome.includes(f.sigla) ? ` (${esc(f.sigla)})` : ''}</option>`).join('');
            if (!faculdadesDoSelect.length) {
                select.innerHTML = '<option value="">Nenhuma faculdade cadastrada — cadastre uma primeiro</option>';
            }
        })
        .catch(() => {
            select.innerHTML = '<option value="">Erro ao carregar faculdades</option>';
        });
}

function abrirModalCurso() {
    document.getElementById('curso-form').reset();
    document.getElementById('curso-modal-alert').innerHTML = '';
    abrirModal('curso-modal');
    carregarFaculdadesNoSelect();
}

function fecharModalCurso() {
    document.getElementById('curso-modal').style.display = 'none';
}

function salvarCurso() {
    const faculdadeId = document.getElementById('c-faculdade').value;
    const faculdade = (faculdadesDoSelect || []).find(f => String(f.id) === faculdadeId);
    const nome = document.getElementById('c-nome').value.trim();
    if (!nome || !faculdade) {
        alerta('curso-modal-alert', 'error', 'Informe o nome do curso e selecione a faculdade.');
        return;
    }
    const formData = new FormData();
    formData.append('nome', nome);
    formData.append('faculdade_id', faculdade.id);
    formData.append('instituicao', faculdade.sigla && !faculdade.nome.includes(faculdade.sigla)
        ? `${faculdade.sigla} - ${faculdade.nome}` : faculdade.nome);
    formData.append('tipo_instituicao', faculdade.tipo_instituicao || 'Pública');
    formData.append('modalidade', document.getElementById('c-modalidade').value);
    formData.append('area', document.getElementById('c-area').value.trim());
    formData.append('grau', document.getElementById('c-grau').value.trim());
    formData.append('duracao', document.getElementById('c-duracao').value.trim());
    formData.append('descricao', document.getElementById('c-descricao').value.trim());

    fetch('/api/cursos/criar', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                fecharModalCurso();
                alerta('cursos-alert', 'success', data.message || 'Curso cadastrado com sucesso!');
                if (window.SuaFaculPainel) window.SuaFaculPainel.mostrar('cursos');
                carregarCursos();
                carregarStats();
            } else {
                alerta('curso-modal-alert', 'error', data.message || 'Não foi possível cadastrar o curso.');
            }
        })
        .catch(() => alerta('curso-modal-alert', 'error', 'Erro ao cadastrar curso.'));
}

// ── Vestibulares: cadastrados ──
function carregarVestibularesCadastrados() {
    const loading = document.getElementById('vestibulares-cadastro-loading');
    const table = document.getElementById('vestibulares-cadastro-table');
    loading.style.display = 'flex';
    table.style.display = 'none';

    const params = new URLSearchParams({ page: estadoVestibulares.pagina, limit: PAGINA_ADMIN, incluir_privados: 'true' });
    if (estadoVestibulares.busca) params.append('busca', estadoVestibulares.busca);

    fetch('/api/vestibulares/listar?' + params.toString())
        .then(r => r.json())
        .then(data => {
            loading.style.display = 'none';
            if (!data.success) {
                alerta('vestibulares-cadastro-alert', 'error', data.message || 'Erro ao carregar vestibulares.');
                return;
            }
            table.style.display = 'table';
            renderizarVestibularesCadastrados(data.vestibulares);
            document.getElementById('vestibulares-cadastro-total').textContent =
                `${data.total} vestibular${data.total === 1 ? '' : 'es'}${estadoVestibulares.busca ? ' encontrados' : ''}`;
            renderizarPaginacao('vestibulares-paginacao', estadoVestibulares.pagina, data.total_pages, (p) => {
                estadoVestibulares.pagina = p;
                carregarVestibularesCadastrados();
            });
        })
        .catch(() => {
            loading.style.display = 'none';
            alerta('vestibulares-cadastro-alert', 'error', 'Erro ao carregar vestibulares.');
        });
}

const ROTULO_STATUS = { ativo: 'Ativo', encerrado: 'Encerrado', data_invalida: 'Data inválida', nao_validado: 'Não validado' };

function renderizarVestibularesCadastrados(vestibulares) {
    const tbody = document.getElementById('vestibulares-cadastro-list');
    if (!vestibulares.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="admin-vazio">Nenhum vestibular encontrado.</td></tr>';
        return;
    }
    tbody.innerHTML = vestibulares.map(v => {
        const status = v.status_validacao || 'nao_validado';
        const edital = urlSegura(v.link_edital);
        return `
            <tr>
                <td><strong>${esc(v.nome)}</strong>${edital ? `<br><a href="${edital}" target="_blank" rel="noopener">Edital</a>` : ''}</td>
                <td>${esc(v.instituicao || '—')}<br><small class="admin-secundario">${esc(v.tipo_instituicao || '')}</small></td>
                <td>${esc([v.cidade, v.regiao].filter(Boolean).join(' · ') || '—')}</td>
                <td>${dataBR(v.data_prova)}</td>
                <td><span class="badge badge-${esc(status)}">${esc(ROTULO_STATUS[status] || status)}</span></td>
            </tr>`;
    }).join('');
}

function abrirModalVestibular() {
    document.getElementById('vestibular-form').reset();
    document.getElementById('vestibular-modal-alert').innerHTML = '';
    abrirModal('vestibular-modal');
}

function fecharModalVestibular() {
    document.getElementById('vestibular-modal').style.display = 'none';
}

function salvarVestibular() {
    const campos = {
        nome: 'v-nome', instituicao: 'v-instituicao', tipo_instituicao: 'v-tipo', cidade: 'v-cidade',
        regiao: 'v-regiao', periodo_inscricao: 'v-inscricao', data_prova: 'v-data',
        link_edital: 'v-edital', descricao: 'v-descricao'
    };
    const formData = new FormData();
    Object.entries(campos).forEach(([chave, id]) => formData.append(chave, document.getElementById(id).value.trim()));
    if (!formData.get('nome') || !formData.get('instituicao')) {
        alerta('vestibular-modal-alert', 'error', 'Nome e instituição são obrigatórios.');
        return;
    }
    fetch('/api/vestibulares/criar', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                fecharModalVestibular();
                alerta('vestibulares-cadastro-alert', 'success', data.message || 'Vestibular cadastrado com sucesso!');
                carregarVestibularesCadastrados();
                carregarStats();
            } else {
                alerta('vestibular-modal-alert', 'error', data.message || 'Não foi possível cadastrar o vestibular.');
            }
        })
        .catch(() => alerta('vestibular-modal-alert', 'error', 'Erro ao cadastrar vestibular.'));
}

// ── Vestibulares: validação/automação ──
function validarVestibulares(aplicar) {
    const resumoEl = document.getElementById('vestibulares-resumo');
    const table = document.getElementById('vestibulares-table');

    alerta('vestibulares-alert', '', 'Validando vestibulares...');

    const formData = new FormData();
    formData.append('aplicar', aplicar ? 'true' : 'false');

    fetch('/api/vestibulares/validar', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                alerta('vestibulares-alert', 'error', data.message || 'Erro ao validar.');
                return;
            }
            const r = data.resumo;
            alerta('vestibulares-alert', 'success', aplicar ? 'Validação aplicada e salva.' : 'Pré-visualização gerada (nada foi salvo ainda).');
            resumoEl.innerHTML = `
                <div class="painel-stats admin-resumo">
                    <div class="painel-stat"><span class="painel-stat-icone"><i class="fas fa-list"></i></span><span><span class="painel-stat-numero">${esc(r.total)}</span><span class="painel-stat-rotulo">Total</span></span></div>
                    <div class="painel-stat"><span class="painel-stat-icone painel-stat-icone--verde"><i class="fas fa-circle-check"></i></span><span><span class="painel-stat-numero">${esc(r.ativos)}</span><span class="painel-stat-rotulo">Ativos</span></span></div>
                    <div class="painel-stat"><span class="painel-stat-icone painel-stat-icone--rosa"><i class="fas fa-flag-checkered"></i></span><span><span class="painel-stat-numero">${esc(r.encerrados)}</span><span class="painel-stat-rotulo">Encerrados</span></span></div>
                    <div class="painel-stat"><span class="painel-stat-icone painel-stat-icone--laranja"><i class="fas fa-link-slash"></i></span><span><span class="painel-stat-numero">${esc(r.sem_faculdade_cadastrada)}</span><span class="painel-stat-rotulo">Sem faculdade vinculada</span></span></div>
                </div>
            `;
            renderizarVestibulares(data.itens);
            table.style.display = 'table';
            if (aplicar) {
                carregarStats();
                if (secoesCarregadas.vestibulares) carregarVestibularesCadastrados();
            }
        })
        .catch(() => {
            alerta('vestibulares-alert', 'error', 'Erro ao validar vestibulares.');
        });
}

function renderizarVestibulares(itens) {
    const tbody = document.getElementById('vestibulares-list');
    tbody.innerHTML = '';
    itens.forEach(item => {
        const row = document.createElement('tr');
        const statusLabel = ROTULO_STATUS[item.status_validacao] || item.status_validacao;
        row.innerHTML = `
            <td>${esc(item.nome)}</td>
            <td>${esc(item.instituicao || '-')}</td>
            <td><span class="badge badge-${esc(item.status_validacao)}">${esc(statusLabel)}</span></td>
            <td>${item.cadastrado_ok
                ? `<span class="badge badge-ok">Sim (${esc(item.faculdade_nome)})</span>`
                : '<span class="badge badge-pendente">Não cadastrada</span>'}</td>
        `;
        tbody.appendChild(row);
    });
}
