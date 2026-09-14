// Configuração da API
const API_BASE_URL = '/api';

// Variáveis globais
const itemsPerPage = 9;
let currentPage = 1;
let currentFilters = {
    curso: '',
    faculdade: '',
    cidade: '',
    modalidade: [],
    tipo_instituicao: null
};

// Evita race condition: se duas buscas saírem quase juntas (ex.: usuário
// muda dois filtros rápido), só a resposta da requisição mais recente é
// renderizada — uma resposta antiga que chegue depois é descartada.
let requestSequence = 0;

// Debounce genérico — atrasa a chamada de `fn` até `delay`ms sem novas
// chamadas, pra não disparar uma busca a cada tecla digitada. Expõe
// `.cancel()` pra descartar uma chamada pendente (usado quando o Enter
// já disparou a busca na hora, pra não duplicar).
function debounce(fn, delay) {
    let timeoutId;
    const debounced = (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn(...args), delay);
    };
    debounced.cancel = () => clearTimeout(timeoutId);
    return debounced;
}

// Referências aos elementos HTML
const searchButton = document.querySelector('.btn-buscar');
const cursoInput = document.querySelector('input[placeholder*="curso"]');
const faculdadeInput = document.querySelector('input[placeholder*="faculdade"]');
const cidadeInput = document.querySelector('input[placeholder*="cidade"]');
const modalidadeCheckboxes = document.querySelectorAll('.filtros1 input[type="checkbox"]');
const tipoInstituicaoRadios = document.querySelectorAll('.filtros input[type="radio"]');

// Busca faculdades da API
async function fetchFaculdades(filters = {}, page = 1) {
    try {
        const params = new URLSearchParams();

        if (filters.faculdade && filters.faculdade.trim()) {
            params.append('busca', filters.faculdade.trim());
        }
        if (filters.curso && filters.curso.trim()) {
            params.append('curso', filters.curso.trim());
        }
        if (filters.cidade && filters.cidade.trim()) {
            params.append('cidade', filters.cidade.trim());
        }

        if (filters.modalidade && filters.modalidade.length > 0) {
            filters.modalidade.forEach(m => {
                let modalidade = m.toLowerCase().trim();
                if (modalidade === 'híbrido' || modalidade === 'hibrido') {
                    modalidade = 'semipresencial';
                }
                params.append('modalidade', modalidade);
            });
        }

        if (filters.tipo_instituicao) {
            let tipo = filters.tipo_instituicao;
            if (tipo === 'Particular') tipo = 'Privada';
            params.append('tipo_instituicao', tipo);
        }

        params.append('page', page);
        params.append('limit', itemsPerPage);

        const url = `${API_BASE_URL}/faculdades/listar?${params.toString()}`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            return data;
        } else {
            console.error('Erro ao buscar faculdades:', data.message);
            return { faculdades: [], total: 0, page: 1, limit: itemsPerPage, total_pages: 0 };
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        return { faculdades: [], total: 0, page: 1, limit: itemsPerPage, total_pages: 0 };
    }
}

function showResultsSection() {
    const resultsSection = document.querySelector('.results-section');
    if (resultsSection) {
        const jaEstavaVisivel = resultsSection.style.display === 'block';
        resultsSection.style.display = 'block';
        // Só rola a página na primeira vez que os resultados aparecem —
        // com a busca dinâmica (digitar/marcar filtro), repetir o scroll
        // a cada busca ficaria incômodo enquanto o usuário ainda ajusta
        // os filtros.
        if (!jaEstavaVisivel) {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

// Renderiza os cartões de faculdade
function renderFaculdades(faculdades) {
    const grid = document.querySelector('.courses-grid');
    if (!grid) return;

    grid.innerHTML = '';

    if (faculdades.length === 0) {
        grid.innerHTML = '<p class="no-results">Nenhuma faculdade encontrada com os filtros aplicados.</p>';
        const countElement = document.querySelector('.results-count');
        if (countElement) countElement.textContent = `0-0 de 0 faculdades encontradas`;
        return;
    }

    faculdades.forEach(f => {
        const card = document.createElement('div');
        card.classList.add('course-card');

        const tagClass = f.tipo_instituicao === 'Pública' ? 'publica' : 'privada';
        const localizacao = [f.cidade, f.uf].filter(Boolean).join('/') || 'Localização não informada';
        const totalCursos = f.total_cursos || 0;

        card.innerHTML = `
            <div class="course-header">
                <h3>${f.nome}${f.sigla ? ` (${f.sigla})` : ''}</h3>
                <div class="course-header-actions">
                    <span class="tag ${tagClass}">${f.tipo_instituicao}</span>
                    <button class="btn-favorito" data-tipo="faculdade" data-item-id="${f.id}" data-nome-item="${f.nome}" title="Adicionar aos favoritos">
                        <i class="far fa-heart"></i>
                    </button>
                </div>
            </div>
            <p class="institution">
                <i class="fas fa-map-marker-alt"></i> ${localizacao}
            </p>
            <p class="description">
                ${f.endereco || 'Endereço não informado.'}
            </p>
            <div class="course-footer">
                <div class="course-info">
                    <span><i class="fas fa-book"></i> ${totalCursos} curso${totalCursos === 1 ? '' : 's'}</span>
                    ${f.telefone ? `<span><i class="fas fa-phone"></i> ${f.telefone}</span>` : ''}
                </div>
                ${f.url
                    ? `<a href="${f.url}" target="_blank" rel="noopener" class="course-link">Ver site <i class="fas fa-chevron-right"></i></a>`
                    : `<a href="/cursos?busca=${encodeURIComponent(f.nome)}" class="course-link">Ver cursos <i class="fas fa-chevron-right"></i></a>`}
            </div>
        `;
        grid.appendChild(card);
    });
}

function updateResultsCount(start, end, total) {
    const countElement = document.querySelector('.results-count');
    if (countElement) {
        countElement.textContent = `${start}-${end} de ${total} faculdades encontradas`;
    }
}

function renderPagination(totalPages) {
    const paginationContainer = document.querySelector('.pagination');
    if (!paginationContainer) return;

    paginationContainer.innerHTML = '';

    const prevButton = document.createElement('a');
    prevButton.href = "#";
    prevButton.innerHTML = '<i class="fas fa-chevron-left"></i>';
    if (currentPage === 1) prevButton.classList.add('disabled');
    prevButton.addEventListener('click', async (e) => {
        e.preventDefault();
        if (currentPage > 1) {
            currentPage--;
            await loadFaculdades();
        }
    });
    paginationContainer.appendChild(prevButton);

    const maxPageButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxPageButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxPageButtons - 1);
    if (endPage - startPage + 1 < maxPageButtons) {
        startPage = Math.max(1, endPage - maxPageButtons + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageLink = document.createElement('a');
        pageLink.href = "#";
        pageLink.textContent = i;
        if (i === currentPage) pageLink.classList.add('active');
        pageLink.addEventListener('click', async (e) => {
            e.preventDefault();
            currentPage = i;
            await loadFaculdades();
        });
        paginationContainer.appendChild(pageLink);
    }

    const nextButton = document.createElement('a');
    nextButton.href = "#";
    nextButton.innerHTML = '<i class="fas fa-chevron-right"></i>';
    if (currentPage === totalPages || totalPages === 0) nextButton.classList.add('disabled');
    nextButton.addEventListener('click', async (e) => {
        e.preventDefault();
        if (currentPage < totalPages) {
            currentPage++;
            await loadFaculdades();
        }
    });
    paginationContainer.appendChild(nextButton);
}

async function loadFaculdades() {
    const requestId = ++requestSequence;
    try {
        showResultsSection();

        const grid = document.querySelector('.courses-grid');
        if (grid) grid.innerHTML = '<p class="loading">Carregando faculdades...</p>';

        const data = await fetchFaculdades(currentFilters, currentPage);

        // Uma busca mais nova já foi disparada enquanto esta esperava a
        // resposta — descarta esta (evita sobrescrever resultado atual
        // com um desatualizado).
        if (requestId !== requestSequence) return;

        renderFaculdades(data.faculdades);

        const startDisplay = data.total > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0;
        const endDisplay = Math.min(currentPage * itemsPerPage, data.total);
        updateResultsCount(startDisplay, endDisplay, data.total);

        renderPagination(data.total_pages);

        if (typeof inicializarFavoritos === 'function') {
            await inicializarFavoritos('faculdade');
        }
    } catch (error) {
        if (requestId !== requestSequence) return;
        console.error('Erro ao carregar faculdades:', error);
        const grid = document.querySelector('.courses-grid');
        if (grid) grid.innerHTML = '<p class="error">Erro ao carregar faculdades. Tente novamente mais tarde.</p>';
    }
}

function applyFilters() {
    const cursoValue = cursoInput ? cursoInput.value.trim() : '';
    const faculdadeValue = faculdadeInput ? faculdadeInput.value.trim() : '';
    const cidadeValue = cidadeInput ? cidadeInput.value.trim() : '';

    const selectedModalities = Array.from(modalidadeCheckboxes)
        .filter(checkbox => checkbox.checked)
        .map(checkbox => checkbox.parentElement.textContent.trim());

    const selectedTipoInstituicao = Array.from(tipoInstituicaoRadios).find(radio => radio.checked);

    let tipoInstituicao = null;
    if (selectedTipoInstituicao) {
        const label = selectedTipoInstituicao.parentElement.textContent.trim();
        if (label.includes('Pública')) tipoInstituicao = 'Pública';
        else if (label.includes('Particular')) tipoInstituicao = 'Privada';
    }

    currentFilters = {
        curso: cursoValue,
        faculdade: faculdadeValue,
        cidade: cidadeValue,
        modalidade: selectedModalities,
        tipo_instituicao: tipoInstituicao
    };

    currentPage = 1;
    loadFaculdades();
}

// --- Event Listeners ---
// Pesquisa dinâmica: digitar nos campos de texto dispara a busca sozinho
// depois de uma pausa (debounce), sem precisar de Enter/clique.
const applyFiltersDebounced = debounce(applyFilters, 450);
[cursoInput, faculdadeInput, cidadeInput].forEach(input => {
    if (input) {
        input.addEventListener('input', applyFiltersDebounced);
    }
});

// Clique no botão e Enter disparam na hora (comportamento original
// preservado) — cancelam qualquer chamada debounced pendente pra não
// rodar a busca duas vezes (uma na hora + uma pelo debounce atrasado).
if (searchButton) {
    searchButton.addEventListener('click', (e) => {
        e.preventDefault();
        applyFiltersDebounced.cancel();
        applyFilters();
    });
}

[cursoInput, faculdadeInput, cidadeInput].forEach(input => {
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                applyFiltersDebounced.cancel();
                applyFilters();
            }
        });
    }
});

// Pesquisa dinâmica: marcar/desmarcar modalidade ou tipo de instituição
// dispara a busca na hora (ação discreta, sem precisar de debounce).
modalidadeCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', applyFilters);
});
tipoInstituicaoRadios.forEach(radio => {
    radio.addEventListener('change', applyFilters);
});

// --- Inicialização ---
// Se a página foi acessada a partir da busca da home (via home-search.js),
// os filtros vêm como query params na URL — pré-preenche os campos com
// esses valores e aplica a busca automaticamente. Sem query params,
// mantém o comportamento original: mostra todas as faculdades de cara.
function preencherFiltrosDaURL() {
    const params = new URLSearchParams(window.location.search);
    let temFiltroNaURL = false;

    const curso = params.get('curso');
    if (curso && cursoInput) {
        cursoInput.value = curso;
        temFiltroNaURL = true;
    }

    const faculdade = params.get('faculdade');
    if (faculdade && faculdadeInput) {
        faculdadeInput.value = faculdade;
        temFiltroNaURL = true;
    }

    const cidade = params.get('cidade');
    if (cidade && cidadeInput) {
        cidadeInput.value = cidade;
        temFiltroNaURL = true;
    }

    const modalidadesSelecionadas = params.getAll('modalidade').map(m => m.toLowerCase());
    if (modalidadesSelecionadas.length > 0) {
        modalidadeCheckboxes.forEach(checkbox => {
            const label = checkbox.parentElement.textContent.trim().toLowerCase();
            if (modalidadesSelecionadas.includes(label)) {
                checkbox.checked = true;
                temFiltroNaURL = true;
            }
        });
    }

    const tipo = params.get('tipo');
    if (tipo) {
        tipoInstituicaoRadios.forEach(radio => {
            const label = radio.parentElement.textContent.trim().toLowerCase();
            if (label === tipo.toLowerCase()) {
                radio.checked = true;
                temFiltroNaURL = true;
            }
        });
    }

    return temFiltroNaURL;
}

document.addEventListener('DOMContentLoaded', async () => {
    currentPage = 1;
    if (preencherFiltrosDaURL()) {
        applyFilters();
    } else {
        await loadFaculdades();
    }
});
