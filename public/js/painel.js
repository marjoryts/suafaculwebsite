/*
 * Navegação por seções do layout de painel (dashboard do usuário e painel
 * administrativo) — ver /static/css/components/painel.css.
 *
 * - Links com data-painel-link e href="#id" (na barra lateral) e botões com
 *   data-painel-ir="id" (dentro do conteúdo) mostram a <section
 *   class="painel-secao" id="id"> correspondente e escondem as outras.
 * - A seção atual fica no hash da URL (/dashboard#perfil), então dá para
 *   linkar direto uma seção e o voltar/avançar do navegador funciona.
 * - Dispara o evento 'painel:secao' (detail.id) no document sempre que uma
 *   seção é exibida — os scripts de cada página usam isso para carregar os
 *   dados daquela seção só quando ela é aberta.
 */
(function () {
    function secoes() {
        return Array.from(document.querySelectorAll('.painel-secao'));
    }

    // No mobile a navegação vira uma faixa horizontal rolável: mantém o item
    // ativo visível rolando só a faixa (scrollIntoView rolaria a página).
    function manterVisivelNaFaixa(link) {
        const nav = link.closest('.painel-nav');
        if (!nav || nav.scrollWidth <= nav.clientWidth) return;
        const esquerda = link.offsetLeft - nav.offsetLeft;
        if (esquerda < nav.scrollLeft || esquerda + link.offsetWidth > nav.scrollLeft + nav.clientWidth) {
            nav.scrollLeft = Math.max(0, esquerda - 16);
        }
    }

    function mostrar(id, opcoes = {}) {
        const lista = secoes();
        if (!lista.length) return;
        const alvo = lista.find((s) => s.id === id) || lista[0];

        lista.forEach((s) => { s.hidden = s !== alvo; });

        document.querySelectorAll('.painel-nav [data-painel-link]').forEach((link) => {
            const ativo = link.getAttribute('href') === `#${alvo.id}`;
            link.classList.toggle('is-active', ativo);
            if (ativo) {
                link.setAttribute('aria-current', 'page');
                manterVisivelNaFaixa(link);
            } else {
                link.removeAttribute('aria-current');
            }
        });

        if (opcoes.atualizarHash !== false && location.hash !== `#${alvo.id}`) {
            history.pushState(null, '', `#${alvo.id}`);
        }
        if (opcoes.rolar) {
            const topo = document.querySelector('.painel');
            if (topo && topo.getBoundingClientRect().top < 0) {
                topo.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
        document.dispatchEvent(new CustomEvent('painel:secao', { detail: { id: alvo.id } }));
    }

    function secaoDoHash() {
        return decodeURIComponent(location.hash.replace(/^#/, ''));
    }

    document.addEventListener('click', (e) => {
        const link = e.target.closest('[data-painel-link], [data-painel-ir]');
        if (!link) return;
        const id = link.dataset.painelIr || (link.getAttribute('href') || '').replace(/^#/, '');
        if (!id || !document.getElementById(id)) return;
        e.preventDefault();
        mostrar(id, { rolar: true });
    });

    window.addEventListener('popstate', () => mostrar(secaoDoHash(), { atualizarHash: false }));

    document.addEventListener('DOMContentLoaded', () => {
        mostrar(secaoDoHash(), { atualizarHash: false });
    });

    // Ao abrir /pagina#secao (ou trocar o hash na barra de endereço) o
    // navegador rola até o elemento com esse id, escondendo o topo do painel
    // sob o header fixo — volta para o topo.
    function desfazerRolagemDaAncora() {
        if (secaoDoHash() && document.getElementById(secaoDoHash())) {
            window.scrollTo({ top: 0, behavior: 'instant' });
        }
    }
    window.addEventListener('load', desfazerRolagemDaAncora);
    window.addEventListener('hashchange', desfazerRolagemDaAncora);

    window.SuaFaculPainel = { mostrar };
})();
