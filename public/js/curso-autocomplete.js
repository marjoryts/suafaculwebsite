/*
 * Autocomplete do campo "curso" nas buscas — reutilizável, injetado em
 * qualquer input que bata com o seletor abaixo (usado tanto na home
 * quanto em /faculdades, que compartilham a mesma estrutura de card de
 * busca). Não duplica a lógica de busca em si: só preenche o valor do
 * campo e dispara um evento 'input' real, que os scripts de cada página
 * (faculdades.js, home-search.js) já escutam do jeito deles.
 */
(function () {
    const SELETOR_INPUT_CURSO = '.text-input[placeholder*="curso" i]';
    const DEBOUNCE_MS = 200;
    const TAMANHO_MINIMO = 2;

    function debounce(fn, delay) {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn(...args), delay);
        };
    }

    function destacarTermo(nome, termo) {
        const idx = nome.toLowerCase().indexOf(termo.toLowerCase());
        if (idx === -1) return nome;
        const antes = nome.slice(0, idx);
        const meio = nome.slice(idx, idx + termo.length);
        const depois = nome.slice(idx + termo.length);
        return `${antes}<strong>${meio}</strong>${depois}`;
    }

    function inicializarAutocomplete(input) {
        // Envolve SÓ o input num wrapper próprio (não o .card inteiro,
        // que também contém os checkboxes/radios abaixo) — assim
        // "top: 100%" no dropdown fica relativo à altura do input, e não
        // à altura do card inteiro (era a causa do espaço grande entre
        // o campo e as sugestões).
        const wrapper = document.createElement('div');
        wrapper.className = 'curso-autocomplete-wrapper';
        input.parentElement.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const dropdown = document.createElement('ul');
        dropdown.className = 'curso-autocomplete-dropdown';
        dropdown.style.display = 'none';
        wrapper.appendChild(dropdown);

        let sugestoesAtuais = [];
        let indiceDestacado = -1;
        let requestId = 0;
        let ignorarProximoEventoInput = false;

        function fecharDropdown() {
            dropdown.style.display = 'none';
            dropdown.innerHTML = '';
            sugestoesAtuais = [];
            indiceDestacado = -1;
        }

        function selecionarSugestao(nome) {
            input.value = nome;
            fecharDropdown();
            // O evento sintético abaixo também passa pelo NOSSO listener
            // de 'input' (é o mesmo elemento) — sem essa flag, o dropdown
            // reabriria mostrando sugestões pro nome que acabou de ser
            // selecionado.
            ignorarProximoEventoInput = true;
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }

        function renderizarDropdown(termo) {
            dropdown.innerHTML = '';
            if (sugestoesAtuais.length === 0) {
                fecharDropdown();
                return;
            }
            sugestoesAtuais.forEach((nome, i) => {
                const item = document.createElement('li');
                item.className = 'curso-autocomplete-item';
                item.innerHTML = destacarTermo(nome, termo);
                item.addEventListener('mousedown', (e) => {
                    // mousedown (não click) pra disparar antes do input
                    // perder o foco (blur), que fecharia o dropdown antes.
                    e.preventDefault();
                    selecionarSugestao(nome);
                });
                dropdown.appendChild(item);
            });
            dropdown.style.display = 'block';
        }

        async function buscarSugestoes(termo) {
            const idAtual = ++requestId;
            try {
                const resp = await fetch(`/api/cursos/sugestoes?q=${encodeURIComponent(termo)}`);
                const data = await resp.json();
                if (idAtual !== requestId) return; // resposta desatualizada — descarta
                sugestoesAtuais = data.sugestoes || [];
                indiceDestacado = -1;
                renderizarDropdown(termo);
            } catch (e) {
                if (idAtual !== requestId) return;
                fecharDropdown();
            }
        }

        const buscarSugestoesDebounced = debounce(buscarSugestoes, DEBOUNCE_MS);

        input.addEventListener('input', () => {
            if (ignorarProximoEventoInput) {
                ignorarProximoEventoInput = false;
                return;
            }
            const termo = input.value.trim();
            if (termo.length < TAMANHO_MINIMO) {
                fecharDropdown();
                return;
            }
            buscarSugestoesDebounced(termo);
        });

        input.addEventListener('keydown', (e) => {
            if (dropdown.style.display === 'none' || sugestoesAtuais.length === 0) return;

            const itens = dropdown.querySelectorAll('.curso-autocomplete-item');
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                indiceDestacado = Math.min(indiceDestacado + 1, itens.length - 1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                indiceDestacado = Math.max(indiceDestacado - 1, 0);
            } else if (e.key === 'Enter' && indiceDestacado >= 0) {
                // Só intercepta o Enter quando há uma sugestão destacada
                // via teclado — sem isso, o Enter continua funcionando
                // como já funcionava (dispara a busca com o texto digitado).
                e.preventDefault();
                selecionarSugestao(sugestoesAtuais[indiceDestacado]);
                return;
            } else if (e.key === 'Escape') {
                fecharDropdown();
                return;
            } else {
                return;
            }

            itens.forEach((item, i) => item.classList.toggle('is-highlighted', i === indiceDestacado));
        });

        // Clicar fora fecha o dropdown.
        document.addEventListener('click', (e) => {
            if (e.target !== input && !dropdown.contains(e.target)) {
                fecharDropdown();
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll(SELETOR_INPUT_CURSO).forEach(inicializarAutocomplete);
    });
})();
