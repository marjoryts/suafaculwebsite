// Configuração da API
const API_BASE_URL = '/api';

// Variáveis globais
const vestibularesPerPage = 10;
let currentPage = 1;
let currentFilters = {
    tipo_instituicao: null,
    regiao: [],
    meses: [],
    busca: '',
    curso: ''
};

// Referências aos elementos HTML
const vestibularesGrid = document.querySelector('.vestibulares-grid');
const paginationContainer = document.querySelector('.pagination');
const vestibularesCountElement = document.querySelector('.vestibulares-count');
const institutionButtons = document.querySelectorAll('.filter-group:first-child .filter-options button');
const regionCheckboxes = document.querySelectorAll('.filter-group:nth-child(2) input[type="checkbox"]');
const monthCheckboxes = document.querySelectorAll('.filter-group:nth-child(3) input[type="checkbox"]');
const cursoSelect = document.querySelector('#filtro-curso');
const applyFiltersButton = document.querySelector('.btn-apply');
const searchInput = document.querySelector('.search-box input[type="text"]');
const searchButton = document.querySelector('.btn-search');

// Função para buscar vestibulares da API
async function fetchVestibulares(filters = {}, page = 1) {
    try {
        const params = new URLSearchParams();
        
        // Por padrão, mostrar apenas vestibulares públicos
        if (!filters.tipo_instituicao || filters.tipo_instituicao === 'Pública') {
            // Não precisa adicionar parâmetro, a API já filtra por padrão
        } else if (filters.tipo_instituicao === 'Todas') {
            params.append('incluir_privados', 'true');
        }
        
        if (filters.regiao && filters.regiao.length > 0) {
            filters.regiao.forEach(r => params.append('regiao', r));
        }
        
        if (filters.meses && filters.meses.length > 0) {
            filters.meses.forEach(m => params.append('mes', m));
        }
        
        if (filters.busca) {
            params.append('busca', filters.busca);
        }

        if (filters.curso) {
            params.append('curso', filters.curso);
        }
        
        params.append('page', page);
        params.append('limit', vestibularesPerPage);

        const response = await fetch(`${API_BASE_URL}/vestibulares/listar?${params.toString()}`);
        const data = await response.json();

        if (data.success) {
            return data;
        } else {
            console.error('Erro ao buscar vestibulares:', data.message);
            return { vestibulares: [], total: 0, page: 1, limit: vestibularesPerPage, total_pages: 0 };
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        return { vestibulares: [], total: 0, page: 1, limit: vestibularesPerPage, total_pages: 0 };
    }
}

// Função para formatar data
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

// Função para renderizar os vestibulares na grade
// Extrai a sigla da instituição a partir do padrão "SIGLA - Nome completo"
// usado em todos os registros (ex: "USP - Universidade de São Paulo" -> "USP").
// Se não houver esse padrão (ex: "INEP"), mantém o texto original.
function extrairSiglaInstituicao(instituicao) {
    if (!instituicao) return 'Instituição não informada';
    const partes = instituicao.split(' - ');
    return partes[0].trim();
}

function renderVestibulares(vestibulares) {
    if (!vestibularesGrid) return;
    
    vestibularesGrid.innerHTML = '';

    if (vestibulares.length === 0) {
        vestibularesGrid.innerHTML = '<p class="no-results">Nenhum vestibular encontrado com os filtros aplicados.</p>';
        if (vestibularesCountElement) {
            vestibularesCountElement.textContent = `0-0 de 0 vestibulares`;
        }
        return;
    }

    vestibulares.forEach(vestibular => {
        const vestibularCard = document.createElement('div');
        vestibularCard.classList.add('vestibular-card');

        const dataProva = formatDate(vestibular.data_prova);
        const cidadeRegiao = vestibular.cidade && vestibular.regiao 
            ? `${vestibular.cidade} - ${vestibular.regiao}`
            : vestibular.cidade || vestibular.regiao || 'Nacional';

        vestibularCard.innerHTML = `
            <div class="vestibular-header">
                <h3>${vestibular.nome}</h3>
                <div class="vestibular-header-actions">
                    <span class="tag instituicao" title="${vestibular.instituicao || 'Instituição não informada'}">${extrairSiglaInstituicao(vestibular.instituicao)}</span>
                    <button class="btn-favorito" data-tipo="vestibular" data-item-id="${vestibular.id}" data-nome-item="${vestibular.nome}" title="Adicionar aos favoritos">
                        <i class="far fa-heart"></i>
                    </button>
                </div>
            </div>
            <p class="periodo">
                <i class="fas fa-calendar-alt"></i> Inscrições: ${vestibular.periodo_inscricao || 'A definir'}
            </p>
            <p class="data">
                <i class="fas fa-calendar-check"></i> Prova: ${dataProva || 'A definir'}
            </p>
            <p class="description">
                ${vestibular.descricao || ''}
            </p>
            <div class="vestibular-footer">
                <div class="vestibular-info">
                    <span><i class="fas fa-map-marker-alt"></i> ${cidadeRegiao}</span>
                </div>
                <a href="${vestibular.link_edital || '#'}" class="vestibular-link" ${vestibular.link_edital ? 'target="_blank"' : ''}>
                    Ver edital <i class="fas fa-chevron-right"></i>
                </a>
            </div>
        `;
        vestibularesGrid.appendChild(vestibularCard);
    });
}

// Função para atualizar o contador de vestibulares
function updateVestibularesCount(start, end, total) {
    if (vestibularesCountElement) {
        vestibularesCountElement.textContent = `${start}-${end} de ${total} vestibulares`;
    }
}

// Função para renderizar os botões de paginação
function renderPagination(totalPages) {
    if (!paginationContainer) return;
    
    paginationContainer.innerHTML = '';

    // Botão "Anterior"
    const prevButton = document.createElement('a');
    prevButton.href = "#";
    prevButton.innerHTML = '<i class="fas fa-chevron-left"></i>';
    if (currentPage === 1) {
        prevButton.classList.add('disabled');
    }
    prevButton.addEventListener('click', async (e) => {
        e.preventDefault();
        if (currentPage > 1) {
            currentPage--;
            await loadVestibulares();
        }
    });
    paginationContainer.appendChild(prevButton);

    // Limita o número de botões de página visíveis
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
        if (i === currentPage) {
            pageLink.classList.add('active');
        }
        pageLink.addEventListener('click', async (e) => {
            e.preventDefault();
            currentPage = i;
            await loadVestibulares();
        });
        paginationContainer.appendChild(pageLink);
    }

    // Botão "Próximo"
    const nextButton = document.createElement('a');
    nextButton.href = "#";
    nextButton.innerHTML = '<i class="fas fa-chevron-right"></i>';
    if (currentPage === totalPages || totalPages === 0) {
        nextButton.classList.add('disabled');
    }
    nextButton.addEventListener('click', async (e) => {
        e.preventDefault();
        if (currentPage < totalPages) {
            currentPage++;
            await loadVestibulares();
        }
    });
    paginationContainer.appendChild(nextButton);
}

// Função para carregar vestibulares da API
async function loadVestibulares() {
    try {
        // Mostrar loading
        if (vestibularesGrid) {
            vestibularesGrid.innerHTML = '<p class="loading">Carregando vestibulares...</p>';
        }

        const filters = {
            tipo_instituicao: currentFilters.tipo_instituicao,
            regiao: currentFilters.regiao.length > 0 ? currentFilters.regiao[0] : null,
            meses: currentFilters.meses,
            busca: currentFilters.busca,
            curso: currentFilters.curso
        };

        const data = await fetchVestibulares(filters, currentPage);
        
        renderVestibulares(data.vestibulares);
        
        const startDisplay = ((currentPage - 1) * vestibularesPerPage) + 1;
        const endDisplay = Math.min(currentPage * vestibularesPerPage, data.total);
        updateVestibularesCount(startDisplay, endDisplay, data.total);
        
        renderPagination(data.total_pages);
    } catch (error) {
        console.error('Erro ao carregar vestibulares:', error);
        if (vestibularesGrid) {
            vestibularesGrid.innerHTML = '<p class="error">Erro ao carregar vestibulares. Tente novamente mais tarde.</p>';
        }
    }
}

// Função para aplicar os filtros
function applyFilters() {
    const selectedInstitution = document.querySelector('.filter-group:first-child .filter-options button.active')?.textContent.trim() || 'Todas as Instituições';
    const selectedRegions = Array.from(regionCheckboxes)
        .filter(checkbox => checkbox.checked)
        .map(checkbox => checkbox.nextSibling.textContent.trim());
    
    // Capturar meses selecionados e converter para números
    const selectedMonths = Array.from(monthCheckboxes)
        .filter(checkbox => checkbox.checked)
        .map(checkbox => {
            const monthName = checkbox.nextSibling.textContent.trim();
            // Mapear nome do mês para número
            const monthMap = {
                'Janeiro': 1,
                'Junho': 6,
                'Novembro': 11
            };
            return monthMap[monthName] || null;
        })
        .filter(m => m !== null);
    
    const searchTerm = searchInput ? searchInput.value.trim() : '';
    const selectedCurso = cursoSelect ? cursoSelect.value : '';

    // Determinar tipo de instituição
    let tipoInstituicao = null;
    if (selectedInstitution.includes('Públicas')) {
        tipoInstituicao = 'Pública';
    } else if (selectedInstitution.includes('Privadas')) {
        tipoInstituicao = 'Privada';
    } else {
        tipoInstituicao = 'Todas';
    }

    currentFilters = {
        tipo_instituicao: tipoInstituicao,
        regiao: selectedRegions,
        meses: selectedMonths,
        busca: searchTerm,
        curso: selectedCurso
    };

    currentPage = 1;
    loadVestibulares();
}

// --- Menu mobile: lógica centralizada em /static/js/header.js ---

// --- Event Listeners para os filtros ---

// Tipo de Instituição
if (institutionButtons.length > 0) {
    institutionButtons.forEach(button => {
        button.addEventListener('click', () => {
            institutionButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        });
    });
}

// Botão "Aplicar Filtros"
if (applyFiltersButton) {
    applyFiltersButton.addEventListener('click', (e) => {
        e.preventDefault();
        applyFilters();
    });
}

// Busca por texto
if (searchButton) {
    searchButton.addEventListener('click', (e) => {
        e.preventDefault();
        applyFilters();
    });
}

if (searchInput) {
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyFilters();
        }
    });
}

// Busca os cursos reais cadastrados para popular o filtro "Curso" do
// painel lateral (mesma abordagem usada na home: nomes distintos vindos
// da API, nunca uma lista fixa).
async function popularFiltroDeCursos() {
    if (!cursoSelect) return;
    try {
        const response = await fetch(`${API_BASE_URL}/cursos/listar?limit=50`);
        const data = await response.json();
        if (!data.success || !data.cursos) return;

        const nomesUnicos = [...new Set(data.cursos.map(c => c.nome))]
            .sort((a, b) => a.localeCompare(b, 'pt-BR'));

        nomesUnicos.forEach(nome => {
            const option = document.createElement('option');
            option.value = nome;
            option.textContent = nome;
            cursoSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Erro ao carregar cursos para o filtro:', error);
    }
}

// --- Inicialização ---
document.addEventListener('DOMContentLoaded', async () => {
    // Carrega os vestibulares ao inicializar
    await loadVestibulares();
    await popularFiltroDeCursos();
    
    // Inicializar favoritos após carregar os vestibulares
    if (typeof inicializarFavoritos === 'function') {
        await inicializarFavoritos('vestibular');
    }
});

