// Admin JavaScript
let deleteUserId = null;
let deleteFaculdadeId = null;

document.addEventListener('DOMContentLoaded', function() {
    carregarStats();
    carregarUsuarios();
});

function openTab(tabName) {
    const tabContents = document.getElementsByClassName('tab-content');
    for (let content of tabContents) {
        content.classList.remove('active');
    }

    const tabButtons = document.getElementsByClassName('tab-button');
    for (let button of tabButtons) {
        button.classList.remove('active');
    }
    document.getElementById(tabName).classList.add('active');
    event.target.closest('.tab-button').classList.add('active');

    if (tabName === 'faculdades') carregarFaculdades();
}

// ── Stats do dashboard ──
function carregarStats() {
    fetch('/api/admin/stats')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            const s = data.stats;
            document.getElementById('total-users').textContent = s.total_usuarios;
            document.getElementById('total-cursos').textContent = s.total_cursos;
            document.getElementById('total-faculdades').textContent = s.total_faculdades;
            document.getElementById('total-vestibulares').textContent = s.total_vestibulares;
            document.getElementById('vestibulares-ativos').textContent = s.vestibulares_ativos;
            document.getElementById('vestibulares-sem-faculdade').textContent = s.vestibulares_sem_faculdade;
        })
        .catch(() => {});
}

// ── Usuários ──
function carregarUsuarios() {
    const loading = document.getElementById('users-loading');
    const table = document.getElementById('users-table');
    const alert = document.getElementById('users-alert');

    loading.style.display = 'block';
    table.style.display = 'none';
    alert.textContent = '';

    fetch('/api/usuario/listar')
        .then(response => response.json())
        .then(data => {
            loading.style.display = 'none';
            if (data.success) {
                table.style.display = 'table';
                renderizarUsuarios(data.usuarios);
            } else {
                alert.innerHTML = `<div class="alert error">${data.message}</div>`;
            }
        })
        .catch(() => {
            loading.style.display = 'none';
            alert.innerHTML = '<div class="alert error">Erro ao carregar usuários.</div>';
        });
}

function renderizarUsuarios(usuarios) {
    const tbody = document.getElementById('users-list');
    tbody.innerHTML = '';

    usuarios.forEach(user => {
        const row = document.createElement('tr');
        const tipoLabel = user.tipo === 'admin' ? 'Admin' : 'Aluno';
        row.innerHTML = `
            <td>${user.id}</td>
            <td>${user.nome_usuario}</td>
            <td>${user.email}</td>
            <td>
                <span class="badge badge-${user.tipo === 'admin' ? 'ok' : 'pendente'}">${tipoLabel}</span>
            </td>
            <td class="user-actions">
                <button class="btn-admin btn-warning" onclick='editarUsuario(${user.id}, ${JSON.stringify(user.nome_usuario)}, ${JSON.stringify(user.email)}, ${JSON.stringify(user.tipo)})'>
                    <i class="fas fa-edit"></i> Editar
                </button>
                <button class="btn-admin btn-danger" onclick="excluirUsuario(${user.id})">
                    <i class="fas fa-trash"></i> Excluir
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function buscarUsuarios() {
    carregarUsuarios();
}

function abrirModalAdicionar() {
    document.getElementById('modal-title').textContent = 'Adicionar Usuário';
    document.getElementById('user-form').reset();
    document.getElementById('user-id').value = '';
    document.getElementById('tipo-group').style.display = 'none';
    document.getElementById('user-modal').style.display = 'block';
}

function editarUsuario(id, username, email, tipo) {
    document.getElementById('modal-title').textContent = 'Editar Usuário';
    document.getElementById('user-id').value = id;
    document.getElementById('username').value = username;
    document.getElementById('email').value = email;
    document.getElementById('password').value = '';
    document.getElementById('tipo-group').style.display = 'block';
    document.getElementById('user-tipo').value = tipo || 'aluno';
    document.getElementById('user-modal').style.display = 'block';
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
                const alertEl = document.getElementById('faculdades-alert');
                alertEl.innerHTML = `<div class="alert ${data.success ? 'success' : 'error'}">${data.message}</div>`;
                if (data.success) { carregarFaculdades(); carregarStats(); }
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
            document.getElementById('users-alert').innerHTML = `<div class="alert ${data.success ? 'success' : 'error'}">${data.message}</div>`;
            if (data.success) { carregarUsuarios(); carregarStats(); }
        })
        .catch(() => {
            fecharConfirmModal();
            document.getElementById('users-alert').innerHTML = '<div class="alert error">Erro ao excluir usuário.</div>';
        });
}

function excluirUsuario(id) {
    deleteUserId = id;
    document.getElementById('confirm-message').textContent = 'Tem certeza que deseja excluir este usuário?';
    document.getElementById('confirm-modal').style.display = 'block';
}

function handleLogout() {
    window.location.href = '/logout';
}

function irParaDashboard() {
    window.location.href = '/dashboard';
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('user-form').addEventListener('submit', function(e) {
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
                        await fetch('/api/usuario/definir-tipo', { method: 'POST', body: tipoForm });
                    }
                    document.getElementById('modal-alert').innerHTML = `<div class="alert success">${data.message}</div>`;
                    fecharModal();
                    carregarUsuarios();
                    carregarStats();
                } else {
                    document.getElementById('modal-alert').innerHTML = `<div class="alert error">${data.message}</div>`;
                }
            })
            .catch(() => {
                document.getElementById('modal-alert').innerHTML = '<div class="alert error">Erro ao salvar usuário.</div>';
            });
    });

    document.getElementById('faculdade-form').addEventListener('submit', function(e) {
        e.preventDefault();
        salvarFaculdade();
    });

    window.onclick = function(event) {
        const userModal = document.getElementById('user-modal');
        const confirmModal = document.getElementById('confirm-modal');
        const faculdadeModal = document.getElementById('faculdade-modal');
        if (event.target === userModal) fecharModal();
        if (event.target === confirmModal) fecharConfirmModal();
        if (event.target === faculdadeModal) fecharModalFaculdade();
    };
});

// ── Faculdades ──
function carregarFaculdades(busca) {
    const loading = document.getElementById('faculdades-loading');
    const table = document.getElementById('faculdades-table');
    const alertEl = document.getElementById('faculdades-alert');

    loading.style.display = 'block';
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
            } else {
                alertEl.innerHTML = `<div class="alert error">${data.message}</div>`;
            }
        })
        .catch(() => {
            loading.style.display = 'none';
            alertEl.innerHTML = '<div class="alert error">Erro ao carregar faculdades.</div>';
        });
}

function renderizarFaculdades(faculdades) {
    const tbody = document.getElementById('faculdades-list');
    tbody.innerHTML = '';

    faculdades.forEach(f => {
        const row = document.createElement('tr');
        const contato = [f.telefone, f.email].filter(Boolean).join(' / ') || '<em>a completar</em>';
        row.innerHTML = `
            <td><strong>${f.nome}</strong>${f.sigla ? ' (' + f.sigla + ')' : ''}${f.url ? `<br><a href="${f.url}" target="_blank" rel="noopener">${f.url}</a>` : ''}</td>
            <td>${[f.cidade, f.uf].filter(Boolean).join('/') || '-'}</td>
            <td>${f.tipo_instituicao}</td>
            <td>${f.fonte === 'emec' ? '<span class="badge badge-ok">e-MEC</span>' : '<span class="badge badge-pendente">Manual</span>'}</td>
            <td>${contato}</td>
            <td class="user-actions">
                <button class="btn-admin btn-warning" onclick='editarFaculdade(${JSON.stringify(f)})'>
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-admin btn-danger" onclick="excluirFaculdade(${f.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function buscarFaculdades() {
    carregarFaculdades(document.getElementById('faculdade-search-input').value);
}

function abrirModalFaculdade() {
    document.getElementById('faculdade-modal-title').textContent = 'Cadastrar Faculdade';
    document.getElementById('faculdade-form').reset();
    document.getElementById('faculdade-id').value = '';
    document.getElementById('faculdade-modal').style.display = 'block';
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
    document.getElementById('faculdade-modal').style.display = 'block';
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
                document.getElementById('faculdade-modal-alert').innerHTML = `<div class="alert success">${data.message}</div>`;
                fecharModalFaculdade();
                carregarFaculdades();
                carregarStats();
            } else {
                document.getElementById('faculdade-modal-alert').innerHTML = `<div class="alert error">${data.message}</div>`;
            }
        })
        .catch(() => {
            document.getElementById('faculdade-modal-alert').innerHTML = '<div class="alert error">Erro ao salvar faculdade.</div>';
        });
}

function excluirFaculdade(id) {
    deleteFaculdadeId = id;
    document.getElementById('confirm-message').textContent = 'Tem certeza que deseja excluir esta faculdade?';
    document.getElementById('confirm-modal').style.display = 'block';
}

function importarEmec() {
    const codigo = document.getElementById('emec-codigo').value.trim();
    const alertEl = document.getElementById('faculdades-alert');
    if (!codigo) {
        alertEl.innerHTML = '<div class="alert error">Informe o código e-MEC da instituição.</div>';
        return;
    }
    alertEl.innerHTML = '<div class="alert">Importando do e-MEC, aguarde...</div>';
    const formData = new FormData();
    formData.append('codigo', codigo);
    fetch('/api/faculdades/emec/importar', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            alertEl.innerHTML = `<div class="alert ${data.success ? 'success' : 'error'}">${data.message || (data.success ? 'Importado com sucesso.' : 'Falha na importação.')}</div>`;
            if (data.success) {
                document.getElementById('emec-codigo').value = '';
                carregarFaculdades();
                carregarStats();
            }
        })
        .catch(() => {
            alertEl.innerHTML = '<div class="alert error">Erro ao importar do e-MEC.</div>';
        });
}

function importarEmecPorUF() {
    const uf = document.getElementById('emec-uf').value;
    const alertEl = document.getElementById('faculdades-alert');
    if (!uf) {
        alertEl.innerHTML = '<div class="alert error">Selecione uma UF.</div>';
        return;
    }
    alertEl.innerHTML = `<div class="alert">Importando todas as instituições de ${uf} do e-MEC, isso pode levar um tempo...</div>`;
    const formData = new FormData();
    formData.append('uf', uf);
    fetch('/api/faculdades/emec/importar-uf', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alertEl.innerHTML = `<div class="alert success">UF ${data.uf}: ${data.total_encontradas} instituições encontradas — ${data.criadas} criadas, ${data.atualizadas} atualizadas${data.falhas ? `, ${data.falhas} falharam` : ''}.</div>`;
                carregarFaculdades();
                carregarStats();
            } else {
                alertEl.innerHTML = `<div class="alert error">${data.message || 'Falha na importação.'}</div>`;
            }
        })
        .catch(() => {
            alertEl.innerHTML = '<div class="alert error">Erro ao importar instituições da UF.</div>';
        });
}

function importarEmecBrasil() {
    const alertEl = document.getElementById('faculdades-alert');
    if (!confirm('Isso vai importar as instituições de TODAS as 27 UFs do Brasil e pode levar vários minutos. Deseja continuar?')) {
        return;
    }
    alertEl.innerHTML = '<div class="alert">Importando instituições de todo o Brasil, isso pode levar vários minutos — não feche esta página...</div>';
    fetch('/api/faculdades/emec/importar-brasil', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alertEl.innerHTML = `<div class="alert success">${data.ufs_processadas} UFs processadas: ${data.total_criadas} faculdades criadas, ${data.total_atualizadas} atualizadas.</div>`;
                carregarFaculdades();
                carregarStats();
            } else {
                alertEl.innerHTML = `<div class="alert error">${data.message || 'Falha na importação.'}</div>`;
            }
        })
        .catch(() => {
            alertEl.innerHTML = '<div class="alert error">Erro ao importar instituições do Brasil.</div>';
        });
}

// ── Vestibulares: validação/automação ──
function validarVestibulares(aplicar) {
    const alertEl = document.getElementById('vestibulares-alert');
    const resumoEl = document.getElementById('vestibulares-resumo');
    const table = document.getElementById('vestibulares-table');

    alertEl.innerHTML = '<div class="alert">Validando vestibulares...</div>';

    const formData = new FormData();
    formData.append('aplicar', aplicar ? 'true' : 'false');

    fetch('/api/vestibulares/validar', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                alertEl.innerHTML = `<div class="alert error">${data.message || 'Erro ao validar.'}</div>`;
                return;
            }
            const r = data.resumo;
            alertEl.innerHTML = `<div class="alert success">${aplicar ? 'Validação aplicada e salva.' : 'Pré-visualização gerada (nada foi salvo ainda).'}</div>`;
            resumoEl.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-number">${r.total}</div><div class="stat-label">Total</div></div>
                    <div class="stat-card"><div class="stat-number">${r.ativos}</div><div class="stat-label">Ativos</div></div>
                    <div class="stat-card"><div class="stat-number">${r.encerrados}</div><div class="stat-label">Encerrados</div></div>
                    <div class="stat-card"><div class="stat-number">${r.sem_faculdade_cadastrada}</div><div class="stat-label">Sem faculdade vinculada</div></div>
                </div>
            `;
            renderizarVestibulares(data.itens);
            table.style.display = 'table';
            if (aplicar) carregarStats();
        })
        .catch(() => {
            alertEl.innerHTML = '<div class="alert error">Erro ao validar vestibulares.</div>';
        });
}

function renderizarVestibulares(itens) {
    const tbody = document.getElementById('vestibulares-list');
    tbody.innerHTML = '';
    itens.forEach(item => {
        const row = document.createElement('tr');
        const statusLabel = { ativo: 'Ativo', encerrado: 'Encerrado', data_invalida: 'Data inválida' }[item.status_validacao] || item.status_validacao;
        row.innerHTML = `
            <td>${item.nome}</td>
            <td>${item.instituicao || '-'}</td>
            <td><span class="badge badge-${item.status_validacao}">${statusLabel}</span></td>
            <td>${item.cadastrado_ok
                ? `<span class="badge badge-ok">Sim (${item.faculdade_nome})</span>`
                : '<span class="badge badge-pendente">Não cadastrada</span>'}</td>
        `;
        tbody.appendChild(row);
    });
}
