/*
 * Busca dinâmica do card de pesquisa (home e /faculdades).
 *
 * Enquanto o usuário digita em qualquer um dos três campos (curso,
 * faculdade, cidade), consulta /api/busca/sugestoes e mostra, logo abaixo
 * do campo, os resultados reais do banco agrupados em Localizações,
 * Faculdades e Cursos — o grupo do próprio campo aparece primeiro.
 *
 * Ao escolher um resultado, o valor vai para o campo certo daquele tipo
 * (ex.: escolher a cidade "São Paulo" digitando no campo de curso preenche
 * o campo de cidade e limpa o texto parcial do campo de curso) e dispara
 * os eventos 'input' e 'busca:selecionada', que home-search.js /
 * faculdades.js já tratam para aplicar o filtro.
 *
 * Substitui o antigo curso-autocomplete.js (que só sugeria cursos).
 */
(function () {
    const DEBOUNCE_MS = 200;
    const TAMANHO_MINIMO = 2;
    const LIMITE_POR_TIPO = 5;

    // Campo do formulário ↔ tipo de sugestão, identificados pelo mesmo
    // placeholder que home-search.js e faculdades.js já usam.
    const CAMPOS = {
        curso: { seletor: '.text-input[placeholder*="curso" i]', tipo: 'curso' },
        faculdade: { seletor: '.text-input[placeholder*="faculdade" i]', tipo: 'faculdade' },
        cidade: { seletor: '.text-input[placeholder*="cidade" i]', tipo: 'local' },
    };

    const GRUPOS = {
        local: { titulo: 'Localizações', icone: 'fa-location-dot' },
        faculdade: { titulo: 'Faculdades', icone: 'fa-building-columns' },
        curso: { titulo: 'Cursos', icone: 'fa-book' },
    };

    const ICONE_LOCAL = { cidade: 'fa-location-dot', estado: 'fa-map', regiao: 'fa-earth-americas' };

    let contadorIds = 0;

    function debounce(fn, delay) {
        let timeoutId;
        const debounced = (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn(...args), delay);
        };
        debounced.cancel = () => clearTimeout(timeoutId);
        return debounced;
    }

    // Mesma normalização do backend (config/database.py): sem acentos e
    // em minúsculas — usada só para destacar o trecho digitado.
    function normalizarCaractere(ch) {
        return ch.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
    }

    function escaparHtml(texto) {
        const div = document.createElement('div');
        div.textContent = texto == null ? '' : String(texto);
        return div.innerHTML;
    }

    // Envolve em <mark> o trecho do texto que casa com o termo, ignorando
    // acentos ("sao" destaca "São"). Mapeia cada caractere original para
    // sua forma normalizada para achar a posição certa no texto original.
    function destacarTermo(texto, termo) {
        const alvo = Array.from(termo).map(normalizarCaractere).join('');
        if (!alvo) return escaparHtml(texto);
        const chars = Array.from(texto);
        const normalizados = chars.map(normalizarCaractere);
        const inicioPorIndice = [];
        let acumulado = '';
        normalizados.forEach((n) => { inicioPorIndice.push(acumulado.length); acumulado += n; });
        const pos = acumulado.indexOf(alvo);
        if (pos === -1) return escaparHtml(texto);
        const fim = pos + alvo.length;
        let html = '';
        let aberto = false;
        chars.forEach((ch, i) => {
            const ini = inicioPorIndice[i];
            const dentro = ini >= pos && ini < fim;
            if (dentro && !aberto) { html += '<mark>'; aberto = true; }
            if (!dentro && aberto) { html += '</mark>'; aberto = false; }
            html += escaparHtml(ch);
        });
        if (aberto) html += '</mark>';
        return html;
    }

    function encontrarCampo(escopo, nome) {
        return escopo.querySelector(CAMPOS[nome].seletor) || document.querySelector(CAMPOS[nome].seletor);
    }

    function inicializar(input, nomeCampo) {
        const escopo = input.closest('.container-input') || document;
        const tipoDoCampo = CAMPOS[nomeCampo].tipo;
        const idLista = `busca-sugestoes-${++contadorIds}`;

        // A lista fica no <body> (e não dentro do card) para não ser
        // cortada pelo overflow:hidden do hero; é posicionada sob o campo.
        const painel = document.createElement('div');
        painel.className = 'busca-sugestoes';
        painel.id = idLista;
        painel.setAttribute('role', 'listbox');
        painel.setAttribute('aria-label', 'Sugestões de busca');
        painel.hidden = true;
        document.body.appendChild(painel);

        input.setAttribute('role', 'combobox');
        input.setAttribute('aria-autocomplete', 'list');
        input.setAttribute('aria-expanded', 'false');
        input.setAttribute('aria-controls', idLista);
        input.setAttribute('autocomplete', 'off');

        let itensAtuais = [];
        let indiceAtivo = -1;
        let requisicaoAtual = 0;
        let controlador = null;
        let ignorarProximoInput = false;
        let selecionadoEm = 0;

        function posicionar() {
            if (painel.hidden) return;
            const r = input.getBoundingClientRect();
            const margem = 12;
            const largura = Math.min(Math.max(r.width, 340), window.innerWidth - margem * 2);
            let esquerda = r.left;
            if (esquerda + largura > window.innerWidth - margem) {
                esquerda = Math.max(margem, r.right - largura);
            }
            painel.style.width = `${largura}px`;
            painel.style.left = `${esquerda + window.scrollX}px`;
            painel.style.top = `${r.bottom + window.scrollY + 6}px`;
        }

        function abrir() {
            painel.hidden = false;
            input.setAttribute('aria-expanded', 'true');
            posicionar();
        }

        function fechar() {
            if (controlador) controlador.abort();
            requisicaoAtual++;
            painel.hidden = true;
            painel.innerHTML = '';
            itensAtuais = [];
            indiceAtivo = -1;
            input.setAttribute('aria-expanded', 'false');
            input.removeAttribute('aria-activedescendant');
        }

        function mostrarEstado(classe, icone, texto) {
            itensAtuais = [];
            indiceAtivo = -1;
            painel.innerHTML = `
                <div class="busca-sugestoes-estado ${classe}" role="status">
                    ${icone}<span>${texto}</span>
                </div>`;
            abrir();
        }

        function mostrarCarregando() {
            mostrarEstado('is-loading', '<span class="busca-sugestoes-spinner" aria-hidden="true"></span>', 'Buscando…');
        }

        function atualizarAtivo() {
            const opcoes = painel.querySelectorAll('.busca-sugestoes-item');
            opcoes.forEach((el, i) => {
                const ativo = i === indiceAtivo;
                el.classList.toggle('is-active', ativo);
                el.setAttribute('aria-selected', ativo ? 'true' : 'false');
                if (ativo) {
                    input.setAttribute('aria-activedescendant', el.id);
                    el.scrollIntoView({ block: 'nearest' });
                }
            });
            if (indiceAtivo < 0) input.removeAttribute('aria-activedescendant');
        }

        function renderizar(resultados, termo) {
            const ordem = [tipoDoCampo, ...Object.keys(GRUPOS).filter((t) => t !== tipoDoCampo)];
            itensAtuais = [];
            indiceAtivo = -1;
            let html = '';
            ordem.forEach((tipo) => {
                const itens = (resultados && resultados[tipo]) || [];
                if (!itens.length) return;
                const grupo = GRUPOS[tipo];
                html += `<div class="busca-sugestoes-grupo" role="group" aria-label="${grupo.titulo}">
                    <div class="busca-sugestoes-titulo" aria-hidden="true">
                        <i class="fas ${grupo.icone}"></i>${grupo.titulo}
                    </div>`;
                itens.forEach((item) => {
                    const indice = itensAtuais.push(item) - 1;
                    const icone = tipo === 'local' ? (ICONE_LOCAL[item.subtipo] || grupo.icone) : grupo.icone;
                    html += `<div class="busca-sugestoes-item" id="${idLista}-op-${indice}" role="option"
                                  aria-selected="false" data-indice="${indice}">
                        <span class="busca-sugestoes-icone busca-sugestoes-icone--${tipo}" aria-hidden="true">
                            <i class="fas ${icone}"></i>
                        </span>
                        <span class="busca-sugestoes-texto">
                            <span class="busca-sugestoes-rotulo">${destacarTermo(item.rotulo, termo)}</span>
                            ${item.detalhe ? `<span class="busca-sugestoes-detalhe">${escaparHtml(item.detalhe)}</span>` : ''}
                        </span>
                    </div>`;
                });
                html += '</div>';
            });

            if (!itensAtuais.length) {
                mostrarEstado('is-empty', '<i class="fas fa-magnifying-glass" aria-hidden="true"></i>',
                    `Nenhum resultado encontrado para “${escaparHtml(termo)}”`);
                return;
            }
            painel.innerHTML = html;
            abrir();
        }

        async function buscar(termo) {
            const id = ++requisicaoAtual;
            if (controlador) controlador.abort();
            controlador = new AbortController();
            try {
                const params = new URLSearchParams({ q: termo, limite: LIMITE_POR_TIPO });
                const resp = await fetch(`/api/busca/sugestoes?${params}`, { signal: controlador.signal });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                if (id !== requisicaoAtual) return; // resposta de uma digitação antiga
                renderizar(data.resultados, termo);
            } catch (e) {
                if (e.name === 'AbortError' || id !== requisicaoAtual) return;
                mostrarEstado('is-error', '<i class="fas fa-circle-exclamation" aria-hidden="true"></i>',
                    'Não foi possível carregar as sugestões.');
            }
        }

        const buscarComAtraso = debounce(buscar, DEBOUNCE_MS);

        function selecionar(item) {
            if (!item) return;
            const destino = encontrarCampo(escopo, item.campo) || input;
            buscarComAtraso.cancel();
            fechar();

            // O texto parcial digitado em outro campo não é um filtro
            // válido (ex.: "São" no campo de curso) — limpa-o.
            if (destino !== input) {
                input.value = '';
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
            destino.value = item.valor;
            // O evento abaixo passa pelo nosso próprio listener do campo de
            // destino — a flag evita reabrir a lista para o valor escolhido.
            destino.dispatchEvent(new CustomEvent('busca:ignorar-sugestoes'));
            destino.dispatchEvent(new Event('input', { bubbles: true }));
            destino.dispatchEvent(new CustomEvent('busca:selecionada', { bubbles: true, detail: item }));
            destino.focus();
        }

        input.addEventListener('busca:ignorar-sugestoes', () => {
            ignorarProximoInput = true;
            selecionadoEm = Date.now();
        });

        input.addEventListener('input', () => {
            if (ignorarProximoInput) {
                ignorarProximoInput = false;
                return;
            }
            const termo = input.value.trim();
            if (termo.length < TAMANHO_MINIMO) {
                buscarComAtraso.cancel();
                fechar();
                return;
            }
            mostrarCarregando();
            buscarComAtraso(termo);
        });

        input.addEventListener('keydown', (e) => {
            if (painel.hidden) return;
            if (e.key === 'Escape') {
                e.preventDefault();
                fechar();
                return;
            }
            if (!itensAtuais.length) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                indiceAtivo = (indiceAtivo + 1) % itensAtuais.length;
                atualizarAtivo();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                indiceAtivo = indiceAtivo <= 0 ? itensAtuais.length - 1 : indiceAtivo - 1;
                atualizarAtivo();
            } else if (e.key === 'Enter' && indiceAtivo >= 0) {
                // Só intercepta o Enter com um item destacado pelo teclado;
                // sem isso o Enter continua disparando a busca normal
                // (preventDefault no keydown também cancela o keypress).
                e.preventDefault();
                selecionar(itensAtuais[indiceAtivo]);
            } else if (e.key === 'Tab') {
                fechar();
            }
        });

        // mousedown (e não click) para agir antes do blur do campo.
        painel.addEventListener('mousedown', (e) => {
            e.preventDefault();
            const el = e.target.closest('.busca-sugestoes-item');
            if (el) selecionar(itensAtuais[Number(el.dataset.indice)]);
        });

        painel.addEventListener('mousemove', (e) => {
            const el = e.target.closest('.busca-sugestoes-item');
            if (!el) return;
            const indice = Number(el.dataset.indice);
            if (indice !== indiceAtivo) {
                indiceAtivo = indice;
                atualizarAtivo();
            }
        });

        input.addEventListener('blur', () => {
            // pequeno atraso: permite que o mousedown na lista aconteça antes
            setTimeout(() => {
                if (document.activeElement !== input) fechar();
            }, 120);
        });

        input.addEventListener('focus', () => {
            // Não reabre logo após uma seleção (o próprio selecionar() foca o campo).
            if (Date.now() - selecionadoEm < 500) return;
            if (input.value.trim().length >= TAMANHO_MINIMO && painel.hidden) {
                mostrarCarregando();
                buscar(input.value.trim());
            }
        });

        window.addEventListener('resize', posicionar);
        window.addEventListener('scroll', posicionar, { passive: true });
    }

    document.addEventListener('DOMContentLoaded', () => {
        Object.keys(CAMPOS).forEach((nome) => {
            document.querySelectorAll(CAMPOS[nome].seletor).forEach((input) => inicializar(input, nome));
        });
    });
})();
