// Script da aba "Meus Favoritos" dentro do Dashboard do Usuário
(function () {
    const FAVORITOS_API_BASE_URL = '/api/favoritos';
    const API_BASE_URL = '/api';

    const NOMES_TIPO = {
        curso: { singular: 'curso', plural: 'cursos' },
        vestibular: { singular: 'vestibular', plural: 'vestibulares' },
        faculdade: { singular: 'faculdade', plural: 'faculdades' }
    };

    let favoritosCarregados = { curso: false, vestibular: false, faculdade: false };

    // ── Abas principais do dashboard (Visão Geral / Meus Favoritos) ──
    const dashTabButtons = document.querySelectorAll('.dashboard-tab-button');
    dashTabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tab = button.getAttribute('data-dash-tab');

            dashTabButtons.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.dashboard-tab-content').forEach(c => c.classList.remove('active'));

            button.classList.add('active');
            document.getElementById(`${tab}-tab`).classList.add('active');

            if (tab === 'favoritos' && !favoritosCarregados.curso) {
                loadFavoritos('curso');
                favoritosCarregados.curso = true;
            }
        });
    });

    // ── Sub-abas (Cursos / Vestibulares / Faculdades) ──
    const subTabButtons = document.querySelectorAll('.subtab-button');
    subTabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tipo = button.getAttribute('data-favtipo');

            subTabButtons.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.favorites-subcontent').forEach(c => c.classList.remove('active'));

            button.classList.add('active');
            document.getElementById(`dash-${tipo}-content`).classList.add('active');

            if (!favoritosCarregados[tipo]) {
                loadFavoritos(tipo);
                favoritosCarregados[tipo] = true;
            }
        });
    });

    async function loadFavoritos(tipo) {
        const grid = document.getElementById(`dash-${tipo}-grid`);
        if (!grid) return;

        try {
            const response = await fetch(`${FAVORITOS_API_BASE_URL}/listar?tipo=${tipo}`, {
                method: 'GET',
                credentials: 'same-origin'
            });
            const data = await response.json();

            if (!data.success) {
                console.error('Erro ao carregar favoritos:', data.message);
                return;
            }

            if (data.favoritos.length === 0) {
                const nomes = NOMES_TIPO[tipo];
                grid.innerHTML = `
                    <div class="empty-state">
                        <i class="far fa-heart"></i>
                        <h3>Nenhum ${nomes.singular} favoritado</h3>
                        <p>Comece a favoritar ${nomes.plural} para vê-los aqui!</p>
                    </div>
                `;
                return;
            }

            await renderFavoritos(tipo, data.favoritos, grid);
        } catch (error) {
            console.error('Erro ao carregar favoritos:', error);
        }
    }

    async function renderFavoritos(tipo, favoritos, grid) {
        grid.innerHTML = '';

        for (const favorito of favoritos) {
            try {
                let itemData = null;

                if (tipo === 'curso') {
                    const r = await fetch(`${API_BASE_URL}/cursos/buscar?id=${favorito.item_id}`);
                    const d = await r.json();
                    if (d.success) itemData = d.curso;
                } else if (tipo === 'vestibular') {
                    const r = await fetch(`${API_BASE_URL}/vestibulares/buscar?id=${favorito.item_id}`);
                    const d = await r.json();
                    if (d.success) itemData = d.vestibular;
                } else if (tipo === 'faculdade') {
                    const r = await fetch(`${API_BASE_URL}/faculdades/buscar?id=${favorito.item_id}`);
                    const d = await r.json();
                    if (d.success) itemData = d.faculdade;
                }

                if (itemData) {
                    grid.appendChild(criarCardFavorito(tipo, itemData));
                }
            } catch (error) {
                console.error(`Erro ao carregar ${tipo} ${favorito.item_id}:`, error);
            }
        }
    }

    function criarCardFavorito(tipo, item) {
        const card = document.createElement('div');
        card.classList.add('course-card');

        if (tipo === 'curso') {
            const modalidade = item.modalidade || '';
            card.innerHTML = `
                <div class="course-header">
                    <h3>${item.nome}</h3>
                    <div class="course-header-actions">
                        ${modalidade ? `<span class="tag ${modalidade}">${modalidade.charAt(0).toUpperCase() + modalidade.slice(1)}</span>` : ''}
                        <button class="btn-favorito favoritado" data-tipo="curso" data-item-id="${item.id}" title="Remover dos favoritos">
                            <i class="fas fa-heart"></i>
                        </button>
                    </div>
                </div>
                <p class="institution"><i class="fas fa-university"></i> ${item.instituicao || 'Instituição não informada'}</p>
                <p class="description">${item.descricao ? (item.descricao.length > 150 ? item.descricao.substring(0, 150) + '...' : item.descricao) : 'Sem descrição disponível.'}</p>
                <div class="course-footer">
                    <div class="course-info">
                        ${item.duracao ? `<span><i class="fas fa-clock"></i> ${item.duracao}</span>` : ''}
                        ${item.grau ? `<span><i class="fas fa-graduation-cap"></i> ${item.grau}</span>` : ''}
                    </div>
                    <a href="/cursos" class="course-link">Ver detalhes <i class="fas fa-chevron-right"></i></a>
                </div>
            `;
        } else if (tipo === 'vestibular') {
            const dataProva = item.data_prova ? new Date(item.data_prova).toLocaleDateString('pt-BR') : 'A definir';
            const cidadeRegiao = item.cidade && item.regiao ? `${item.cidade} - ${item.regiao}` : (item.cidade || item.regiao || 'Nacional');
            card.innerHTML = `
                <div class="course-header">
                    <h3>${item.nome}</h3>
                    <div class="course-header-actions">
                        <span class="tag instituicao">${item.instituicao || 'Vestibular'}</span>
                        <button class="btn-favorito favoritado" data-tipo="vestibular" data-item-id="${item.id}" title="Remover dos favoritos">
                            <i class="fas fa-heart"></i>
                        </button>
                    </div>
                </div>
                <p class="institution"><i class="fas fa-calendar-alt"></i> Inscrições: ${item.periodo_inscricao || 'A definir'}</p>
                <p class="description"><i class="fas fa-calendar-check"></i> Prova: ${dataProva}</p>
                <div class="course-footer">
                    <div class="course-info"><span><i class="fas fa-map-marker-alt"></i> ${cidadeRegiao}</span></div>
                    <a href="${item.link_edital || '#'}" class="course-link" ${item.link_edital ? 'target="_blank"' : ''}>Ver edital <i class="fas fa-chevron-right"></i></a>
                </div>
            `;
        } else if (tipo === 'faculdade') {
            const tagClass = item.tipo_instituicao === 'Pública' ? 'publica' : 'privada';
            const localizacao = [item.cidade, item.uf].filter(Boolean).join('/') || 'Localização não informada';
            const totalCursos = item.total_cursos || 0;
            card.innerHTML = `
                <div class="course-header">
                    <h3>${item.nome}${item.sigla ? ` (${item.sigla})` : ''}</h3>
                    <div class="course-header-actions">
                        ${item.tipo_instituicao ? `<span class="tag ${tagClass}">${item.tipo_instituicao}</span>` : ''}
                        <button class="btn-favorito favoritado" data-tipo="faculdade" data-item-id="${item.id}" title="Remover dos favoritos">
                            <i class="fas fa-heart"></i>
                        </button>
                    </div>
                </div>
                <p class="institution"><i class="fas fa-map-marker-alt"></i> ${localizacao}</p>
                <p class="description">${item.endereco || 'Endereço não informado.'}</p>
                <div class="course-footer">
                    <div class="course-info">
                        <span><i class="fas fa-book"></i> ${totalCursos} curso${totalCursos === 1 ? '' : 's'}</span>
                        ${item.telefone ? `<span><i class="fas fa-phone"></i> ${item.telefone}</span>` : ''}
                    </div>
                    ${item.url ? `<a href="${item.url}" target="_blank" rel="noopener" class="course-link">Ver site <i class="fas fa-chevron-right"></i></a>` : ''}
                </div>
            `;
        }

        const botaoRemover = card.querySelector('.btn-favorito');
        if (botaoRemover) {
            botaoRemover.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                const itemId = parseInt(botaoRemover.getAttribute('data-item-id'));
                await removerFavorito(tipo, itemId);
                await loadFavoritos(tipo);
            });
        }

        return card;
    }

    async function removerFavorito(tipo, itemId) {
        const formData = new FormData();
        formData.append('tipo', tipo);
        formData.append('item_id', itemId);
        try {
            await fetch(`${FAVORITOS_API_BASE_URL}/remover`, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });
        } catch (error) {
            console.error('Erro ao remover favorito:', error);
        }
    }
})();
