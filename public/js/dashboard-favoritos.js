// Seções de favoritos do Dashboard do Usuário (cursos, faculdades e
// vestibulares). Cada seção carrega seus dados só quando é aberta pela
// primeira vez (evento 'painel:secao' de painel.js).
(function () {
    const FAVORITOS_API_BASE_URL = '/api/favoritos';
    const API_BASE_URL = '/api';

    const SECAO_POR_TIPO = {
        curso: 'cursos-favoritos',
        faculdade: 'faculdades-favoritas',
        vestibular: 'vestibulares-favoritos'
    };

    const VAZIO = {
        curso: { icone: 'fa-book', titulo: 'Nenhum curso favoritado', texto: 'Toque no coração de um curso para guardá-lo aqui.', url: '/cursos', acao: 'Explorar cursos' },
        faculdade: { icone: 'fa-building-columns', titulo: 'Nenhuma faculdade favoritada', texto: 'Salve as instituições que você está considerando.', url: '/faculdades', acao: 'Buscar faculdades' },
        vestibular: { icone: 'fa-clipboard-list', titulo: 'Nenhum vestibular salvo', texto: 'Salve vestibulares para acompanhar inscrições e provas.', url: '/vestibulares', acao: 'Ver vestibulares' }
    };

    const carregados = { curso: false, vestibular: false, faculdade: false };

    function esc(texto) {
        const div = document.createElement('div');
        div.textContent = texto == null ? '' : String(texto);
        return div.innerHTML;
    }

    function urlSegura(url) {
        return /^https?:\/\//i.test(url || '') ? esc(url) : '';
    }

    document.addEventListener('painel:secao', (e) => {
        const tipo = Object.keys(SECAO_POR_TIPO).find((t) => SECAO_POR_TIPO[t] === e.detail.id);
        if (tipo && !carregados[tipo]) {
            carregados[tipo] = true;
            loadFavoritos(tipo);
        }
    });

    function atualizarContador(tipo, delta) {
        document.querySelectorAll(`[data-contador="${tipo}"]`).forEach((el) => {
            const atual = parseInt(el.textContent, 10) || 0;
            el.textContent = Math.max(0, atual + delta);
        });
    }

    function renderizarVazio(tipo, grid) {
        const v = VAZIO[tipo];
        grid.innerHTML = `
            <div class="painel-vazio">
                <i class="fas ${v.icone}"></i>
                <strong>${v.titulo}</strong>
                <p>${v.texto}</p>
                <a href="${v.url}" class="btn btn-outline">${v.acao}</a>
            </div>`;
    }

    async function loadFavoritos(tipo) {
        const grid = document.getElementById(`dash-${tipo}-grid`);
        if (!grid) return;

        try {
            const response = await fetch(`${FAVORITOS_API_BASE_URL}/listar?tipo=${tipo}`, { credentials: 'same-origin' });
            const data = await response.json();
            if (!data.success) throw new Error(data.message);

            if (data.favoritos.length === 0) {
                renderizarVazio(tipo, grid);
                return;
            }
            await renderFavoritos(tipo, data.favoritos, grid);
        } catch (error) {
            console.error('Erro ao carregar favoritos:', error);
            grid.innerHTML = `
                <div class="painel-vazio">
                    <i class="fas fa-triangle-exclamation"></i>
                    <strong>Não foi possível carregar seus favoritos</strong>
                    <p>Verifique sua conexão e tente novamente.</p>
                </div>`;
            carregados[tipo] = false;
        }
    }

    async function buscarItem(tipo, id) {
        const rota = { curso: 'cursos', vestibular: 'vestibulares', faculdade: 'faculdades' }[tipo];
        const r = await fetch(`${API_BASE_URL}/${rota}/buscar?id=${encodeURIComponent(id)}`);
        const d = await r.json();
        return d.success ? d[tipo] : null;
    }

    async function renderFavoritos(tipo, favoritos, grid) {
        // Busca os detalhes de todos os itens em paralelo (antes era um por vez).
        const itens = await Promise.all(favoritos.map((f) => buscarItem(tipo, f.item_id).catch(() => null)));
        grid.innerHTML = '';
        itens.filter(Boolean).forEach((item) => grid.appendChild(criarCardFavorito(tipo, item)));
        if (!grid.children.length) renderizarVazio(tipo, grid);
    }

    function criarCardFavorito(tipo, item) {
        const card = document.createElement('div');
        card.classList.add('course-card');

        if (tipo === 'curso') {
            const modalidade = (item.modalidade || '').toLowerCase();
            const descricao = item.descricao || 'Sem descrição disponível.';
            card.innerHTML = `
                <div class="course-header">
                    <h3>${esc(item.nome)}</h3>
                    <div class="course-header-actions">
                        ${modalidade ? `<span class="tag ${esc(modalidade)}">${esc(modalidade.charAt(0).toUpperCase() + modalidade.slice(1))}</span>` : ''}
                        <button class="btn-favorito favoritado" data-item-id="${esc(item.id)}" title="Remover dos favoritos" aria-label="Remover ${esc(item.nome)} dos favoritos">
                            <i class="fas fa-heart"></i>
                        </button>
                    </div>
                </div>
                <p class="institution"><i class="fas fa-building-columns"></i> ${esc(item.instituicao || 'Instituição não informada')}</p>
                <p class="description">${esc(descricao)}</p>
                <div class="course-footer">
                    <div class="course-info">
                        ${item.duracao ? `<span><i class="fas fa-clock"></i> ${esc(item.duracao)}</span>` : ''}
                        ${item.grau ? `<span><i class="fas fa-graduation-cap"></i> ${esc(item.grau)}</span>` : ''}
                    </div>
                    <a href="/cursos" class="course-link">Ver cursos <i class="fas fa-chevron-right"></i></a>
                </div>
            `;
        } else if (tipo === 'vestibular') {
            const dataProva = item.data_prova ? new Date(`${item.data_prova.slice(0, 10)}T12:00:00`).toLocaleDateString('pt-BR') : 'A definir';
            const cidadeRegiao = item.cidade && item.regiao ? `${item.cidade} - ${item.regiao}` : (item.cidade || item.regiao || 'Nacional');
            const edital = urlSegura(item.link_edital);
            card.innerHTML = `
                <div class="course-header">
                    <h3>${esc(item.nome)}</h3>
                    <div class="course-header-actions">
                        <span class="tag instituicao" title="${esc(item.instituicao || 'Vestibular')}">${esc(item.instituicao || 'Vestibular')}</span>
                        <button class="btn-favorito favoritado" data-item-id="${esc(item.id)}" title="Remover dos favoritos" aria-label="Remover ${esc(item.nome)} dos favoritos">
                            <i class="fas fa-heart"></i>
                        </button>
                    </div>
                </div>
                <p class="institution"><i class="fas fa-calendar-days"></i> Inscrições: ${esc(item.periodo_inscricao || 'A definir')}</p>
                <p class="description"><i class="fas fa-calendar-check"></i> Prova: ${esc(dataProva)}</p>
                <div class="course-footer">
                    <div class="course-info"><span><i class="fas fa-location-dot"></i> ${esc(cidadeRegiao)}</span></div>
                    ${edital ? `<a href="${edital}" class="course-link" target="_blank" rel="noopener">Ver edital <i class="fas fa-chevron-right"></i></a>` : ''}
                </div>
            `;
        } else if (tipo === 'faculdade') {
            const tagClass = item.tipo_instituicao === 'Pública' ? 'publica' : 'privada';
            const localizacao = [item.cidade, item.uf].filter(Boolean).join('/') || 'Localização não informada';
            const totalCursos = (item.cursos && item.cursos.length) || item.total_cursos || 0;
            const site = urlSegura(item.url);
            card.innerHTML = `
                <div class="course-header">
                    <h3>${esc(item.nome)}${item.sigla ? ` (${esc(item.sigla)})` : ''}</h3>
                    <div class="course-header-actions">
                        ${item.tipo_instituicao ? `<span class="tag ${tagClass}">${esc(item.tipo_instituicao)}</span>` : ''}
                        <button class="btn-favorito favoritado" data-item-id="${esc(item.id)}" title="Remover dos favoritos" aria-label="Remover ${esc(item.nome)} dos favoritos">
                            <i class="fas fa-heart"></i>
                        </button>
                    </div>
                </div>
                <p class="institution"><i class="fas fa-location-dot"></i> ${esc(localizacao)}</p>
                <p class="description">${esc(item.endereco || 'Endereço não informado.')}</p>
                <div class="course-footer">
                    <div class="course-info">
                        <span><i class="fas fa-book"></i> ${totalCursos} curso${totalCursos === 1 ? '' : 's'}</span>
                        ${item.telefone ? `<span><i class="fas fa-phone"></i> ${esc(item.telefone)}</span>` : ''}
                    </div>
                    ${site
                        ? `<a href="${site}" target="_blank" rel="noopener" class="course-link">Ver site <i class="fas fa-chevron-right"></i></a>`
                        : `<a href="/cursos?busca=${encodeURIComponent(item.nome)}" class="course-link">Ver cursos <i class="fas fa-chevron-right"></i></a>`}
                </div>
            `;
        }

        const botaoRemover = card.querySelector('.btn-favorito');
        if (botaoRemover) {
            botaoRemover.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                botaoRemover.disabled = true;
                const ok = await removerFavorito(tipo, parseInt(botaoRemover.dataset.itemId, 10));
                if (!ok) {
                    botaoRemover.disabled = false;
                    return;
                }
                atualizarContador(tipo, -1);
                card.classList.add('is-removendo');
                setTimeout(() => {
                    const grid = card.parentElement;
                    card.remove();
                    if (grid && !grid.querySelector('.course-card')) renderizarVazio(tipo, grid);
                }, 200);
            });
        }

        return card;
    }

    async function removerFavorito(tipo, itemId) {
        const formData = new FormData();
        formData.append('tipo', tipo);
        formData.append('item_id', itemId);
        try {
            const r = await fetch(`${FAVORITOS_API_BASE_URL}/remover`, { method: 'POST', body: formData, credentials: 'same-origin' });
            const d = await r.json();
            return !!d.success;
        } catch (error) {
            console.error('Erro ao remover favorito:', error);
            return false;
        }
    }
})();
