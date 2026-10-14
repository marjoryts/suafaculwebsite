// Script para a página de favoritos
const API_BASE_URL = '/api';
// FAVORITOS_API_BASE_URL já é declarada em favoritos.js (carregado antes
// nesta página); declarar de novo dava erro e impedia este script de rodar.

// Tabs
const tabButtons = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.favorites-content');

tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tabName = button.getAttribute('data-tab');
        
        // Remove active de todos
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        // Adiciona active no selecionado
        button.classList.add('active');
        document.getElementById(`${tabName}-content`).classList.add('active');
        
        // Carrega o conteúdo da aba
        loadFavorites(tabName);
    });
});

// Função para carregar favoritos
// As abas usam o plural (cursos, vestibulares, faculdades) e a API e os
// cards usam o singular (curso, vestibular, faculdade). Antes a página
// pedia ?tipo=cursos e a lista sempre vinha vazia.
const TIPO_SINGULAR = { cursos: 'curso', vestibulares: 'vestibular', faculdades: 'faculdade' };
const TIPO_PLURAL = { curso: 'cursos', vestibular: 'vestibulares', faculdade: 'faculdades' };

async function loadFavorites(tipoAba) {
    const tipo = TIPO_PLURAL[tipoAba] || tipoAba;          // plural: ids das abas
    const tipoApi = TIPO_SINGULAR[tipo] || tipoAba;        // singular: API e cards
    try {
        const response = await fetch(`${FAVORITOS_API_BASE_URL}/listar?tipo=${tipoApi}`, {
            method: 'GET',
            credentials: 'same-origin'
        });

        const data = await response.json();
        
        if (!data.success) {
            console.error('Erro ao carregar favoritos:', data.message);
            return;
        }

        const grid = document.getElementById(`${tipo}-grid`);
        if (!grid) return;

        if (data.favoritos.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1;">
                    <i class="far fa-heart"></i>
                    <h3>Nenhum ${tipo === 'cursos' ? 'curso' : tipo === 'vestibulares' ? 'vestibular' : 'faculdade'} favoritado</h3>
                    <p>Comece a favoritar ${tipo === 'cursos' ? 'cursos' : tipo === 'vestibulares' ? 'vestibulares' : 'faculdades'} para vê-los aqui!</p>
                </div>
            `;
            return;
        }

        // Buscar detalhes dos itens favoritados
        await renderFavorites(tipoApi, data.favoritos, grid);
    } catch (error) {
        console.error('Erro ao carregar favoritos:', error);
    }
}

// Função para renderizar favoritos
async function renderFavorites(tipo, favoritos, grid) {
    grid.innerHTML = '';

    for (const favorito of favoritos) {
        try {
            let itemData = null;

            if (tipo === 'curso') {
                const response = await fetch(`${API_BASE_URL}/cursos/buscar?id=${favorito.item_id}`);
                const data = await response.json();
                if (data.success) {
                    itemData = data.curso;
                }
            } else if (tipo === 'vestibular') {
                const response = await fetch(`${API_BASE_URL}/vestibulares/buscar?id=${favorito.item_id}`);
                const data = await response.json();
                if (data.success) {
                    itemData = data.vestibular;
                }
            } else if (tipo === 'faculdade') {
                // Antes não havia este ramo: a aba Faculdades ficava sempre vazia.
                const response = await fetch(`${API_BASE_URL}/faculdades/buscar?id=${favorito.item_id}`);
                const data = await response.json();
                if (data.success) {
                    itemData = data.faculdade;
                }
            }

            if (itemData) {
                const card = createFavoriteCard(tipo, itemData, favorito);
                grid.appendChild(card);
            }
        } catch (error) {
            console.error(`Erro ao carregar ${tipo} ${favorito.item_id}:`, error);
        }
    }
}

// Função para criar card de favorito
function createFavoriteCard(tipo, itemData, favorito) {
    const card = document.createElement('div');
    card.classList.add('course-card');

    if (tipo === 'curso') {
        let tagClass = '';
        if (itemData.modalidade === 'presencial') {
            tagClass = 'presencial';
        } else if (itemData.modalidade === 'ead') {
            tagClass = 'ead';
        } else if (itemData.modalidade === 'semipresencial') {
            tagClass = 'semipresencial';
        }

        card.innerHTML = `
            <div class="course-header">
                <h3>${escaparHtml(itemData.nome)}</h3>
                <div class="course-header-actions">
                    <span class="tag ${tagClass}">${escaparHtml(itemData.modalidade.charAt(0).toUpperCase() + itemData.modalidade.slice(1))}</span>
                    <button class="btn-favorito favoritado" data-tipo="curso" data-item-id="${escaparHtml(itemData.id)}" data-nome-item="${escaparHtml(itemData.nome)}" title="Remover dos favoritos">
                        <i class="fas fa-heart"></i>
                    </button>
                </div>
            </div>
            <p class="institution">
                <i class="fas fa-university"></i> ${escaparHtml(itemData.instituicao || 'Instituição não informada')}
            </p>
            <p class="description">
                ${itemData.descricao ? escaparHtml(itemData.descricao.length > 150 ? itemData.descricao.substring(0, 150) + '...' : itemData.descricao) : 'Sem descrição disponível.'}
            </p>
            <div class="course-footer">
                <div class="course-info">
                    ${itemData.duracao ? `<span><i class="fas fa-clock"></i> ${escaparHtml(itemData.duracao)}</span>` : ''}
                    ${itemData.grau ? `<span><i class="fas fa-graduation-cap"></i> ${escaparHtml(itemData.grau)}</span>` : ''}
                </div>
                <a href="/cursos" class="course-link">
                    Ver detalhes <i class="fas fa-chevron-right"></i>
                </a>
            </div>
        `;
    } else if (tipo === 'vestibular') {
        const dataProva = itemData.data_prova ? new Date(itemData.data_prova).toLocaleDateString('pt-BR') : 'A definir';
        const cidadeRegiao = itemData.cidade && itemData.regiao 
            ? [itemData.cidade, itemData.regiao].join(' - ')
            : itemData.cidade || itemData.regiao || 'Nacional';

        card.innerHTML = `
            <div class="course-header">
                <h3>${escaparHtml(itemData.nome)}</h3>
                <div class="course-header-actions">
                    <span class="tag instituicao">${escaparHtml(itemData.instituicao || 'Vestibular')}</span>
                    <button class="btn-favorito favoritado" data-tipo="vestibular" data-item-id="${escaparHtml(itemData.id)}" data-nome-item="${escaparHtml(itemData.nome)}" title="Remover dos favoritos">
                        <i class="fas fa-heart"></i>
                    </button>
                </div>
            </div>
            <p class="institution">
                <i class="fas fa-calendar-alt"></i> Inscrições: ${escaparHtml(itemData.periodo_inscricao || 'A definir')}
            </p>
            <p class="description">
                <i class="fas fa-calendar-check"></i> Prova: ${escaparHtml(dataProva)}
            </p>
            <p class="description">
                ${escaparHtml(itemData.descricao || '')}
            </p>
            <div class="course-footer">
                <div class="course-info">
                    <span><i class="fas fa-map-marker-alt"></i> ${escaparHtml(cidadeRegiao)}</span>
                </div>
                <a href="${urlSegura(itemData.link_edital) || '#'}" class="course-link" ${urlSegura(itemData.link_edital) ? 'target="_blank" rel="noopener"' : ''}>
                    Ver edital <i class="fas fa-chevron-right"></i>
                </a>
            </div>
        `;
    }

    if (tipo === 'faculdade') {
        const tagClass = itemData.tipo_instituicao === 'Pública' ? 'publica' : 'privada';
        const localizacao = [itemData.cidade, itemData.uf].filter(Boolean).join('/') || 'Localização não informada';
        const site = urlSegura(itemData.url);
        card.innerHTML = `
            <div class="course-header">
                <h3>${escaparHtml(itemData.nome)}${itemData.sigla ? ` (${escaparHtml(itemData.sigla)})` : ''}</h3>
                <div class="course-header-actions">
                    ${itemData.tipo_instituicao ? `<span class="tag ${tagClass}">${escaparHtml(itemData.tipo_instituicao)}</span>` : ''}
                    <button class="btn-favorito favoritado" data-tipo="faculdade" data-item-id="${escaparHtml(itemData.id)}" data-nome-item="${escaparHtml(itemData.nome)}" title="Remover dos favoritos">
                        <i class="fas fa-heart"></i>
                    </button>
                </div>
            </div>
            <p class="institution">
                <i class="fas fa-map-marker-alt"></i> ${escaparHtml(localizacao)}
            </p>
            <p class="description">
                ${itemData.endereco ? escaparHtml(itemData.endereco) : 'Endereço não informado.'}
            </p>
            <div class="course-footer">
                <div class="course-info"></div>
                ${site
                    ? `<a href="${site}" target="_blank" rel="noopener" class="course-link">Ver site <i class="fas fa-chevron-right"></i></a>`
                    : `<a href="/cursos?busca=${encodeURIComponent(itemData.nome || '')}" class="course-link">Ver cursos <i class="fas fa-chevron-right"></i></a>`}
            </div>
        `;
    }

    // Adicionar event listener para remover favorito
    const favoritoButton = card.querySelector('.btn-favorito');
    if (favoritoButton) {
        favoritoButton.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const itemId = parseInt(favoritoButton.getAttribute('data-item-id'));
            const nomeItem = favoritoButton.getAttribute('data-nome-item');
            await toggleFavorito(tipo, itemId, nomeItem, favoritoButton);
            
            // Recarregar a lista após remover
            await loadFavorites(tipo);
        });
    }

    return card;
}

// Carregar favoritos da aba ativa ao carregar a página
document.addEventListener('DOMContentLoaded', async () => {
    await loadFavorites('cursos');
});

