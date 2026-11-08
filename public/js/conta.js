// Páginas de conta do site (verificar e-mail, recuperar senha). Usam a API /api/v1
// — as mesmas regras do app: códigos de 5 dígitos, limites e mensagens do servidor.
(function () {
    'use strict';

    const API = '/api/v1';

    async function postar(caminho, corpo) {
        let resposta;
        try {
            resposta = await fetch(API + caminho, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(corpo),
            });
        } catch (e) {
            return { ok: false, status: 0, erro: { message: 'Sem conexão. Verifique sua internet e tente de novo.' } };
        }
        const dados = await resposta.json().catch(() => ({}));
        return {
            ok: resposta.ok,
            status: resposta.status,
            dados: dados.data,
            erro: dados.error,
            retryAfter: Number(resposta.headers.get('Retry-After')) || 0,
        };
    }

    function alerta(el, tipo, texto) {
        el.className = 'conta-alerta conta-alerta--' + tipo;
        el.textContent = texto || '';
    }

    function mensagemDeErro(r) {
        const e = r.erro || {};
        if (e.code === 'INVALID_CODE' && e.details && e.details.tentativas_restantes !== undefined) {
            return `${e.message} Restam ${e.details.tentativas_restantes} tentativa(s).`;
        }
        return e.message || 'Não foi possível concluir. Tente novamente.';
    }

    // Cinco caixas de dígito: avança sozinho, volta no Backspace e aceita colar o código.
    function caixasDeCodigo(container) {
        const caixas = Array.from(container.querySelectorAll('input'));
        // Vários dígitos de uma vez (autopreenchimento do código, digitação rápida):
        // espalha a partir da caixa atual.
        function distribuir(inicio, digitos) {
            let j = inicio;
            for (const d of digitos) {
                if (j >= caixas.length) break;
                caixas[j].value = d;
                j += 1;
            }
            (caixas[j] || caixas[caixas.length - 1]).focus();
        }
        caixas.forEach((caixa, i) => {
            caixa.removeAttribute('maxlength'); // permite receber o código inteiro na 1ª caixa
            caixa.addEventListener('input', () => {
                const digitos = caixa.value.replace(/\D/g, '');
                if (digitos.length > 1) { distribuir(i, digitos); return; }
                caixa.value = digitos;
                if (digitos && caixas[i + 1]) caixas[i + 1].focus();
            });
            caixa.addEventListener('keydown', (ev) => {
                if (ev.key === 'Backspace' && !caixa.value && caixas[i - 1]) caixas[i - 1].focus();
            });
            caixa.addEventListener('paste', (ev) => {
                const digitos = (ev.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, caixas.length);
                if (!digitos) return;
                ev.preventDefault();
                caixas.forEach((c, j) => { c.value = digitos[j] || ''; });
                (caixas[digitos.length] || caixas[caixas.length - 1]).focus();
            });
        });
        return {
            valor: () => caixas.map((c) => c.value).join(''),
            limpar: () => { caixas.forEach((c) => { c.value = ''; }); caixas[0].focus(); },
            focar: () => caixas[0].focus(),
        };
    }

    // Botão "reenviar" com contagem regressiva (o servidor exige intervalo entre envios).
    function esperar(botao, segundos, rotulo) {
        let restante = Math.max(1, Math.ceil(segundos));
        botao.disabled = true;
        botao.textContent = `${rotulo} (${restante}s)`;
        const timer = setInterval(() => {
            restante -= 1;
            if (restante <= 0) {
                clearInterval(timer);
                botao.disabled = false;
                botao.textContent = rotulo;
            } else {
                botao.textContent = `${rotulo} (${restante}s)`;
            }
        }, 1000);
    }

    // Só caminhos internos (evita redirecionamento aberto).
    function destinoSeguro(valor) {
        return valor && valor.startsWith('/') && !valor.startsWith('//') && !valor.includes('\\') ? valor : null;
    }

    window.SuaFaculConta = { postar, alerta, mensagemDeErro, caixasDeCodigo, esperar, destinoSeguro };
})();
