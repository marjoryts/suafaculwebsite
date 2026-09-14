// Configuração da API de Favoritos
const FAVORITOS_API_BASE_URL = '/api/favoritos';

// Função para verificar se o usuário está logado
function isUserLoggedIn() {
    // Verifica se há uma sessão ativa fazendo uma requisição simples
    return fetch('/api/favoritos/listar-ids?tipo=curso', {
        method: 'GET',
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => data.success !== false)
    .catch(() => false);
}

// Função para adicionar favorito
async function adicionarFavorito(tipo, itemId, nomeItem) {
    try {
        const formData = new FormData();
        formData.append('tipo', tipo);
        formData.append('item_id', itemId);
        formData.append('nome_item', nomeItem);

        const response = await fetch(`${FAVORITOS_API_BASE_URL}/adicionar`, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Erro ao adicionar favorito:', error);
        return { success: false, message: 'Erro de conexão.' };
    }
}

// Função para remover favorito
async function removerFavorito(tipo, itemId) {
    try {
        const formData = new FormData();
        formData.append('tipo', tipo);
        formData.append('item_id', itemId);

        const response = await fetch(`${FAVORITOS_API_BASE_URL}/remover`, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Erro ao remover favorito:', error);
        return { success: false, message: 'Erro de conexão.' };
    }
}

// Função para verificar se um item é favorito
async function verificarFavorito(tipo, itemId) {
    try {
        const response = await fetch(`${FAVORITOS_API_BASE_URL}/verificar?tipo=${tipo}&item_id=${itemId}`, {
            method: 'GET',
            credentials: 'same-origin'
        });

        const data = await response.json();
        return data.success ? data.is_favorito : false;
    } catch (error) {
        console.error('Erro ao verificar favorito:', error);
        return false;
    }
}

// Função para obter lista de IDs de favoritos por tipo
async function obterIdsFavoritos(tipo) {
    try {
        const response = await fetch(`${FAVORITOS_API_BASE_URL}/listar-ids?tipo=${tipo}`, {
            method: 'GET',
            credentials: 'same-origin'
        });

        const data = await response.json();
        return data.success ? data.ids : [];
    } catch (error) {
        console.error('Erro ao obter favoritos:', error);
        return [];
    }
}

// Função para alternar favorito (adiciona se não existe, remove se existe)
async function toggleFavorito(tipo, itemId, nomeItem, buttonElement) {
    const isFavorito = buttonElement.classList.contains('favoritado');
    
    if (isFavorito) {
        // Remover favorito
        const result = await removerFavorito(tipo, itemId);
        if (result.success) {
            buttonElement.classList.remove('favoritado');
            buttonElement.querySelector('i').classList.remove('fas');
            buttonElement.querySelector('i').classList.add('far');
            buttonElement.title = 'Adicionar aos favoritos';
        } else {
            if (result.message.includes('não autenticado')) {
                alert('Você precisa estar logado para favoritar itens. Redirecionando para login...');
                window.location.href = '/login';
            } else {
                alert(result.message || 'Erro ao remover favorito.');
            }
        }
    } else {
        // Adicionar favorito
        const result = await adicionarFavorito(tipo, itemId, nomeItem);
        if (result.success) {
            buttonElement.classList.add('favoritado');
            buttonElement.querySelector('i').classList.remove('far');
            buttonElement.querySelector('i').classList.add('fas');
            buttonElement.title = 'Remover dos favoritos';
        } else {
            if (result.message.includes('não autenticado')) {
                alert('Você precisa estar logado para favoritar itens. Redirecionando para login...');
                window.location.href = '/login';
            } else {
                alert(result.message || 'Erro ao adicionar favorito.');
            }
        }
    }
}

// Função para criar botão de favorito
function criarBotaoFavorito(tipo, itemId, nomeItem, isFavorito = false) {
    const button = document.createElement('button');
    button.className = `btn-favorito ${isFavorito ? 'favoritado' : ''}`;
    button.setAttribute('data-tipo', tipo);
    button.setAttribute('data-item-id', itemId);
    button.setAttribute('data-nome-item', nomeItem);
    button.title = isFavorito ? 'Remover dos favoritos' : 'Adicionar aos favoritos';
    
    const icon = document.createElement('i');
    icon.className = isFavorito ? 'fas fa-heart' : 'far fa-heart';
    button.appendChild(icon);
    
    button.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        await toggleFavorito(tipo, itemId, nomeItem, button);
    });
    
    return button;
}

// Função para inicializar botões de favorito em uma página
async function inicializarFavoritos(tipo) {
    const buttons = document.querySelectorAll(`.btn-favorito[data-tipo="${tipo}"]`);
    
    if (buttons.length === 0) return;
    
    // Obter lista de IDs favoritos
    const idsFavoritos = await obterIdsFavoritos(tipo);
    
    buttons.forEach(button => {
        const itemId = parseInt(button.getAttribute('data-item-id'));
        const isFavorito = idsFavoritos.includes(itemId);
        
        if (isFavorito) {
            button.classList.add('favoritado');
            const icon = button.querySelector('i');
            if (icon) {
                icon.classList.remove('far');
                icon.classList.add('fas');
            }
            button.title = 'Remover dos favoritos';
        }
        
        // Adicionar event listener se ainda não tiver
        if (!button.hasAttribute('data-listener-added')) {
            button.setAttribute('data-listener-added', 'true');
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                const nomeItem = button.getAttribute('data-nome-item') || '';
                await toggleFavorito(tipo, itemId, nomeItem, button);
            });
        }
    });
}

