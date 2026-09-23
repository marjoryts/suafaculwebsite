// Dashboard do usuário — perfil e configurações.
// A navegação entre seções fica em painel.js e os favoritos em
// dashboard-favoritos.js.
document.addEventListener('DOMContentLoaded', function () {
    // ── Perfil: salva os PRÓPRIOS dados via /api/usuario/perfil ──
    const form = document.getElementById('perfil-form');
    const alerta = document.getElementById('perfil-alert');

    function mostrarAlerta(tipo, mensagem) {
        alerta.innerHTML = '';
        const div = document.createElement('div');
        div.className = `alert ${tipo}`;
        div.textContent = mensagem;
        alerta.appendChild(div);
    }

    if (form) {
        const botaoSalvar = form.querySelector('button[type="submit"]');

        form.addEventListener('reset', () => {
            // O reset nativo volta aos valores renderizados pelo servidor.
            alerta.innerHTML = '';
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = form.username.value.trim();
            const email = form.email.value.trim();
            const senha = form.password.value;
            const confirmacao = form.password_confirm.value;

            if (!username || !email) {
                mostrarAlerta('error', 'Preencha o nome de usuário e o e-mail.');
                return;
            }
            if (senha && senha.length < 6) {
                mostrarAlerta('error', 'A nova senha deve ter pelo menos 6 caracteres.');
                return;
            }
            if (senha !== confirmacao) {
                mostrarAlerta('error', 'A confirmação não confere com a nova senha.');
                return;
            }

            const dados = new FormData();
            dados.append('username', username);
            dados.append('email', email);
            if (senha) {
                dados.append('password', senha);
                dados.append('password_confirm', confirmacao);
            }

            botaoSalvar.disabled = true;
            try {
                const resp = await fetch('/api/usuario/perfil', { method: 'POST', body: dados, credentials: 'same-origin' });
                const data = await resp.json();
                if (data.success) {
                    mostrarAlerta('success', data.message || 'Perfil atualizado com sucesso!');
                    // Recarrega para atualizar nome/e-mail no header e na barra lateral.
                    setTimeout(() => { window.location.reload(); }, 900);
                } else {
                    mostrarAlerta('error', data.message || 'Não foi possível atualizar o perfil.');
                    botaoSalvar.disabled = false;
                }
            } catch (err) {
                mostrarAlerta('error', 'Erro de conexão ao atualizar o perfil. Tente novamente.');
                botaoSalvar.disabled = false;
            }
        });
    }

    // ── Aparência: Claro / Escuro / Automático (theme.js) ──
    const opcoesTema = document.querySelectorAll('input[name="tema"]');
    function marcarTemaAtual() {
        if (!window.SuaFaculTema) return;
        const atual = window.SuaFaculTema.preferencia();
        opcoesTema.forEach((op) => { op.checked = op.value === atual; });
    }
    opcoesTema.forEach((op) => {
        op.addEventListener('change', () => {
            if (op.checked && window.SuaFaculTema) window.SuaFaculTema.definir(op.value);
        });
    });
    // O botão sol/lua do header também muda o tema: mantém as opções em sincronia.
    document.addEventListener('tema:alterado', marcarTemaAtual);
    marcarTemaAtual();

    // Mantido por compatibilidade com chamadas antigas.
    window.handleLogout = function () {
        window.location.href = '/logout';
    };
});
