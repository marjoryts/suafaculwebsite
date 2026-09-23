// Tema claro/escuro do SuaFacul.
// Carregado no <head> de todas as páginas com header, SEM defer/async: assim a
// classe .dark-mode entra no <html> antes da página ser pintada e não há
// "flash" de tema claro ao navegar entre páginas.
(function () {
    const STORAGE_KEY = 'suafacul-theme';
    const root = document.documentElement;

    function lerPreferencia() {
        try {
            return localStorage.getItem(STORAGE_KEY);
        } catch (e) {
            return null; // navegação privada / storage bloqueado
        }
    }

    function salvarPreferencia(tema) {
        try {
            localStorage.setItem(STORAGE_KEY, tema);
        } catch (e) { /* sem persistência, mas o toggle ainda funciona */ }
    }

    function temaInicial() {
        const salvo = lerPreferencia();
        if (salvo === 'dark' || salvo === 'light') return salvo;
        // Sem escolha salva: segue a preferência do sistema operacional.
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light';
    }

    function atualizarBotao(tema) {
        const botao = document.getElementById('theme-toggle');
        if (!botao) return;
        const escuro = tema === 'dark';
        botao.setAttribute('aria-pressed', escuro ? 'true' : 'false');
        const rotulo = escuro ? 'Ativar modo claro' : 'Ativar modo noturno';
        botao.setAttribute('aria-label', rotulo);
        botao.setAttribute('title', rotulo);
    }

    function aplicarTema(tema) {
        root.classList.toggle('dark-mode', tema === 'dark');
        atualizarBotao(tema);
    }

    // 1) Aplica imediatamente (antes do <body> renderizar).
    aplicarTema(temaInicial());

    // 2) Liga o botão do header quando o DOM estiver pronto.
    document.addEventListener('DOMContentLoaded', function () {
        atualizarBotao(root.classList.contains('dark-mode') ? 'dark' : 'light');
        const botao = document.getElementById('theme-toggle');
        if (!botao) return;
        botao.addEventListener('click', function () {
            const novoTema = root.classList.contains('dark-mode') ? 'light' : 'dark';
            aplicarTema(novoTema);
            salvarPreferencia(novoTema);
        });
    });

    // 3) Mantém outras abas abertas do site sincronizadas.
    window.addEventListener('storage', function (e) {
        if (e.key === STORAGE_KEY && (e.newValue === 'dark' || e.newValue === 'light')) {
            aplicarTema(e.newValue);
        }
    });
})();
