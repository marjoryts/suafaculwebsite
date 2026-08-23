// Header compartilhado — menu mobile + destaque do link ativo.
// Carregado em todas as páginas que usam o header padrão do SuaFacul.
document.addEventListener('DOMContentLoaded', function () {
    const mobileMenuButton = document.getElementById('mobile-menu-btn') || document.querySelector('.mobile-menu');
    const navbar = document.getElementById('main-nav') || document.querySelector('.navbar');

    if (mobileMenuButton && navbar) {
        mobileMenuButton.addEventListener('click', () => {
            const isOpen = navbar.classList.toggle('active');
            mobileMenuButton.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });

        navbar.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                if (navbar.classList.contains('active')) {
                    navbar.classList.remove('active');
                    mobileMenuButton.setAttribute('aria-expanded', 'false');
                }
            });
        });
    }

    // Marca automaticamente o link correspondente à página atual,
    // caso o template não já tenha marcado manualmente com class="active".
    if (navbar && !navbar.querySelector('a.active')) {
        const currentPath = window.location.pathname.replace(/\/$/, '') || '/';
        navbar.querySelectorAll('a').forEach(link => {
            const linkPath = link.getAttribute('href');
            if (!linkPath || linkPath.startsWith('#')) return;
            const normalized = linkPath.replace(/\/$/, '') || '/';
            if (normalized === currentPath && !link.classList.contains('btn-nav')) {
                link.classList.add('active');
            }
        });
    }
});
