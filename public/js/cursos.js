// Configuração da API
const API_BASE_URL = '/api';

// Variáveis globais
const coursesPerPage = 10;
let currentPage = 1;
let allCourses = [];
let filteredCourses = [];
let currentFilters = {
    area: null,
    modalidade: [],
    tipo_instituicao: [],
    busca: ''
};

const coursesGrid = document.querySelector('.courses-grid');
const paginationContainer = document.querySelector('.pagination');
const coursesCountElement = document.querySelector('.courses-count');
// Grupos identificados por data-filtro (antes era por posição com
// :nth-child, que pegava o grupo errado: "Modalidade" ia como tipo de
// instituição e "Pública/Privada" não filtrava nada).
const areaButtons = document.querySelectorAll('[data-filtro="area"] .filter-options button');
const modalityCheckboxes = document.querySelectorAll('[data-filtro="modalidade"] input[type="checkbox"]');
const institutionCheckboxes = document.querySelectorAll('[data-filtro="tipo-instituicao"] input[type="checkbox"]');
const applyFiltersButton = document.querySelector('.btn-apply');
const searchInput = document.querySelector('.search-box input[type="text"]');
const searchButton = document.querySelector('.btn-search');

async function fetchCourses(filters = {}, page = 1) {
    try {
        const params = new URLSearchParams();
        
        if (filters.area && filters.area !== 'Todas as áreas') {
            params.append('area', filters.area);
        }
        
        if (filters.modalidade && filters.modalidade.length > 0) {
            filters.modalidade.forEach(m => params.append('modalidade', m));
        }
        
        if (filters.tipo_instituicao && filters.tipo_instituicao.length > 0) {
            filters.tipo_instituicao.forEach(t => params.append('tipo_instituicao', t));
        }
        
        if (filters.busca) {
            params.append('busca', filters.busca);
        }
        
        params.append('page', page);
        params.append('limit', coursesPerPage);

        const response = await fetch(`${API_BASE_URL}/cursos/listar?${params.toString()}`);
        const data = await response.json();

        if (data.success) {
            return data;
        } else {
            console.error('Erro ao buscar cursos:', data.message);
            return { cursos: [], total: 0, page: 1, limit: coursesPerPage, total_pages: 0 };
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        return { cursos: [], total: 0, page: 1, limit: coursesPerPage, total_pages: 0 };
    }
}

function mapCourseData(apiCourse) {
    return {
        id: apiCourse.id,
        name: apiCourse.nome,
        institution: apiCourse.instituicao || 'Instituição não informada',
        modality: apiCourse.modalidade,
        description: apiCourse.descricao || '',
        duration: apiCourse.duracao || '',
        degree: apiCourse.grau || '',
        area: apiCourse.area || '',
        type: apiCourse.tipo_instituicao || ''
    };
}

function renderCourses(courses) {
    coursesGrid.innerHTML = '';

    if (courses.length === 0) {
        coursesGrid.innerHTML = '<p class="no-results">Nenhum curso encontrado com os filtros aplicados.</p>';
        coursesCountElement.textContent = `0-0 de 0 cursos`;
        return;
    }

    courses.forEach(course => {
        const courseCard = document.createElement('div');
        courseCard.classList.add('course-card');

        let tagClass = '';
        if (course.modality === 'presencial') {
            tagClass = 'presencial';
        } else if (course.modality === 'ead') {
            tagClass = 'ead';
        } else if (course.modality === 'semipresencial') {
            tagClass = 'semipresencial';
        }

        courseCard.innerHTML = `
            <div class="course-header">
                <h3>${escaparHtml(course.name)}</h3>
                <div class="course-header-actions">
                    <span class="tag ${tagClass}">${escaparHtml(course.modality.charAt(0).toUpperCase() + course.modality.slice(1))}</span>
                    <button class="btn-favorito" data-tipo="curso" data-item-id="${escaparHtml(course.id)}" data-nome-item="${escaparHtml(course.name)}" title="Adicionar aos favoritos">
                        <i class="far fa-heart"></i>
                    </button>
                </div>
            </div>
            <p class="institution">
                <i class="fas fa-university"></i> ${escaparHtml(course.institution)}
            </p>
            <p class="description">
                ${course.description ? escaparHtml(course.description.length > 150 ? course.description.substring(0, 150) + '...' : course.description) : 'Sem descrição disponível.'}
            </p>
            <div class="course-footer">
                <div class="course-info">
                    <span><i class="fas fa-clock"></i> ${escaparHtml(course.duration)}</span>
                    <span><i class="fas fa-graduation-cap"></i> ${escaparHtml(course.degree)}</span>
                </div>
                <a href="#" class="course-link" data-course-id="${escaparHtml(course.id)}">
                    Ver detalhes <i class="fas fa-chevron-right"></i>
                </a>
            </div>
        `;
        
        // Adicionar event listener para abrir modal ao clicar no card ou no link
        const courseLink = courseCard.querySelector('.course-link');
        courseLink.addEventListener('click', (e) => {
            e.preventDefault();
            openCourseModal(course);
        });
        
        // Também permite clicar no card inteiro para abrir o modal
        courseCard.style.cursor = 'pointer';
        courseCard.addEventListener('click', (e) => {
            // Não abrir se clicar no link (evitar duplo clique)
            if (!e.target.closest('.course-link')) {
                openCourseModal(course);
            }
        });
        
        coursesGrid.appendChild(courseCard);
    });
}

// Função para atualizar o contador de cursos
function updateCoursesCount(start, end, total) {
    coursesCountElement.textContent = `${start}-${end} de ${total} cursos`;
}

// Função para renderizar os botões de paginação
function renderPagination(totalPages) {
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
            await loadCourses();
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
            await loadCourses();
        });
        paginationContainer.appendChild(pageLink);
    }


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
            await loadCourses();
        }
    });
    paginationContainer.appendChild(nextButton);
}

async function loadCourses() {
    try {
        coursesGrid.innerHTML = '<p class="loading">Carregando cursos...</p>';

        const filters = {
            area: currentFilters.area,
            // Listas: fetchCourses percorre com forEach e a API aceita vários
            // valores (antes ia só o primeiro, como texto, e o forEach falhava).
            modalidade: currentFilters.modalidade,
            tipo_instituicao: currentFilters.tipo_instituicao,
            busca: currentFilters.busca
        };

        const data = await fetchCourses(filters, currentPage);
        
        const mappedCourses = data.cursos.map(mapCourseData);
        renderCourses(mappedCourses);
        
        const startDisplay = data.total > 0 ? ((currentPage - 1) * coursesPerPage) + 1 : 0;
        const endDisplay = Math.min(currentPage * coursesPerPage, data.total);
        updateCoursesCount(startDisplay, endDisplay, data.total);
        
        renderPagination(data.total_pages);

        // Ativa os corações dos cards recém-desenhados (antes só acontecia no
        // carregamento inicial; após filtrar, buscar ou paginar, não funcionavam).
        if (typeof inicializarFavoritos === 'function') {
            await inicializarFavoritos('curso');
        }
    } catch (error) {
        console.error('Erro ao carregar cursos:', error);
        coursesGrid.innerHTML = '<p class="error">Erro ao carregar cursos. Tente novamente mais tarde.</p>';
    }
}

// Função para aplicar os filtros
function applyFilters() {
    const selectedArea = document.querySelector('[data-filtro="area"] .filter-options button.active')?.textContent.trim() || 'Todas as áreas';
    const selectedModalities = Array.from(modalityCheckboxes)
        .filter(checkbox => checkbox.checked)
        .map(checkbox => checkbox.nextSibling.textContent.trim().toLowerCase());
    const selectedInstitutions = Array.from(institutionCheckboxes)
        .filter(checkbox => checkbox.checked)
        .map(checkbox => checkbox.nextSibling.textContent.trim());
    const searchTerm = searchInput.value.trim();

    currentFilters = {
        area: selectedArea !== 'Todas as áreas' ? selectedArea : null,
        modalidade: selectedModalities,
        tipo_instituicao: selectedInstitutions,
        busca: searchTerm
    };

    currentPage = 1;
    loadCourses();
}


// --- Menu mobile: lógica centralizada em /static/js/header.js ---

if (areaButtons.length > 0) {
    areaButtons.forEach(button => {
        button.addEventListener('click', () => {
            areaButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        });
    });
}

if (applyFiltersButton) {
    applyFiltersButton.addEventListener('click', (e) => {
        e.preventDefault();
        applyFilters();
    });
}

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

// Função para abrir o modal com detalhes do curso
function openCourseModal(course) {
    const modal = document.getElementById('courseModal');
    const modalContent = modal.querySelector('.modal-content');
    
    let tagClass = '';
    if (course.modality === 'presencial') {
        tagClass = 'presencial';
    } else if (course.modality === 'ead') {
        tagClass = 'ead';
    } else if (course.modality === 'semipresencial') {
        tagClass = 'semipresencial';
    }
    
    modalContent.innerHTML = `
        <span class="modal-close">&times;</span>
        <div class="modal-header">
            <h2>${escaparHtml(course.name)}</h2>
            <span class="tag ${tagClass}">${escaparHtml(course.modality.charAt(0).toUpperCase() + course.modality.slice(1))}</span>
        </div>
        <div class="modal-body">
            <div class="modal-info-item">
                <i class="fas fa-university"></i>
                <div>
                    <strong>Instituição:</strong>
                    <p>${escaparHtml(course.institution)}</p>
                </div>
            </div>
            ${course.area ? `
            <div class="modal-info-item">
                <i class="fas fa-tag"></i>
                <div>
                    <strong>Área:</strong>
                    <p>${escaparHtml(course.area)}</p>
                </div>
            </div>
            ` : ''}
            ${course.duration ? `
            <div class="modal-info-item">
                <i class="fas fa-clock"></i>
                <div>
                    <strong>Duração:</strong>
                    <p>${escaparHtml(course.duration)}</p>
                </div>
            </div>
            ` : ''}
            ${course.degree ? `
            <div class="modal-info-item">
                <i class="fas fa-graduation-cap"></i>
                <div>
                    <strong>Grau:</strong>
                    <p>${escaparHtml(course.degree)}</p>
                </div>
            </div>
            ` : ''}
            ${course.type ? `
            <div class="modal-info-item">
                <i class="fas fa-building"></i>
                <div>
                    <strong>Tipo de Instituição:</strong>
                    <p>${escaparHtml(course.type)}</p>
                </div>
            </div>
            ` : ''}
            <div class="modal-description">
                <h3>Sobre o Curso</h3>
                <p>${course.description ? escaparHtml(course.description) : 'Descrição não disponível no momento.'}</p>
            </div>
        </div>
    `;
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Previne scroll do body
    
    // Event listeners para fechar o modal
    const closeBtn = modalContent.querySelector('.modal-close');
    closeBtn.addEventListener('click', closeCourseModal);
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeCourseModal();
        }
    });
    
    // Fechar com ESC
    document.addEventListener('keydown', function escHandler(e) {
        if (e.key === 'Escape') {
            closeCourseModal();
            document.removeEventListener('keydown', escHandler);
        }
    });
}

// Função para fechar o modal
function closeCourseModal() {
    const modal = document.getElementById('courseModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto'; // Restaura scroll do body
}

document.addEventListener('DOMContentLoaded', async () => {
    const todasAreasButton = document.querySelector('[data-filtro="area"] .filter-options button.active');
    if (todasAreasButton) {
        todasAreasButton.classList.add('active');
    }
    
    // Termo vindo de outra página (ex.: "Ver cursos" em Faculdades usa
    // /cursos?busca=<nome da faculdade>).
    const buscaDaURL = new URLSearchParams(window.location.search).get('busca');
    if (buscaDaURL && searchInput) {
        searchInput.value = buscaDaURL;
        currentFilters.busca = buscaDaURL.trim();
    }

    // loadCourses() já ativa os botões de favorito de cada carga
    await loadCourses();

    // Link direto para um curso (ex.: "Conhecer o curso" nos resultados do
    // Teste Vocacional usa /cursos?curso=<id>) abre o modal de detalhes.
    const cursoDaURL = new URLSearchParams(window.location.search).get('curso');
    if (cursoDaURL) {
        try {
            const response = await fetch(`${API_BASE_URL}/cursos/buscar?id=${encodeURIComponent(cursoDaURL)}`);
            const data = await response.json();
            if (data.success && data.curso) {
                openCourseModal(mapCourseData(data.curso));
            }
        } catch (error) {
            console.error('Erro ao abrir curso da URL:', error);
        }
    }
});
