
document.addEventListener('DOMContentLoaded', function() {
    window.toggleForm = function() {
        const container = document.getElementById('container');
        if (container) {
            container.classList.toggle('active');
        }
    };
    window.handleLogout = async function() {
        try {
            const response = await fetch('/logout', {
                method: 'GET'
            });
            
            if (response.ok) {
                window.location.href = '/login';
            } else {
                alert('Erro ao fazer logout. Tente novamente.');
            }
        } catch (error) {
            console.error('Erro ao fazer logout:', error);
            alert('Erro ao fazer logout. Tente novamente.');
        }
    };

    window.carregarEstatisticas = function() {
        console.log('Carregando estatísticas...');
    };

    window.navegarParaSecao = function(secao) {
        window.location.href = `/${secao}`;
    };
    console.log('Dashboard carregado com sucesso!');
}); 