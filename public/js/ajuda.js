// Ajuda — busca nas perguntas frequentes.
// Filtra as perguntas pelo texto digitado (pergunta e resposta, sem
// diferenciar acentos e maiúsculas), abre as que combinam e esconde os
// grupos que ficaram vazios.
(function () {
    const form = document.getElementById('faq-busca');
    const input = document.getElementById('faq-busca-input');
    const faq = document.getElementById('faq');
    const vazio = document.getElementById('faq-vazio');
    const status = document.getElementById('faq-status');
    if (!form || !input || !faq) return;

    const itens = Array.from(faq.querySelectorAll('.faq-item'));
    const grupos = Array.from(faq.querySelectorAll('.faq-group'));

    const normalizar = (texto) => texto
        .normalize('NFD')
        .replace(/[̀-ͯ]/g, '')
        .toLowerCase();

    const indice = itens.map((item) => normalizar(item.textContent));

    function filtrar() {
        const termos = normalizar(input.value).split(/\s+/).filter(Boolean);
        let visiveis = 0;

        itens.forEach((item, i) => {
            const combina = termos.every((t) => indice[i].includes(t));
            item.hidden = !combina;
            if (combina) visiveis += 1;
            // Com busca ativa, abre as respostas encontradas
            item.open = termos.length > 0 && combina;
        });

        grupos.forEach((grupo) => {
            grupo.hidden = !grupo.querySelector('.faq-item:not([hidden])');
        });

        if (vazio) vazio.hidden = visiveis > 0;
        if (status) {
            status.textContent = termos.length
                ? `${visiveis} de ${itens.length} perguntas`
                : '';
        }
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        filtrar();
        faq.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    input.addEventListener('input', filtrar);
})();
