// Script para gerenciar cliques nos cursos da home
const API_BASE_URL = '/api';

// Função para buscar cursos por nome
async function buscarCursosPorNome(nomeCurso) {
    try {
        const params = new URLSearchParams();
        params.append('busca', nomeCurso);
        params.append('page', 1);
        params.append('limit', 12); // Limitar a 12 resultados no modal

        const response = await fetch(`${API_BASE_URL}/cursos/listar?${params.toString()}`);
        const data = await response.json();

        if (data.success) {
            return data.cursos;
        } else {
            console.error('Erro ao buscar cursos:', data.message);
            return [];
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        return [];
    }
}

// Função para mapear dados do curso
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

// Função para renderizar cursos no modal
function renderCoursesInModal(courses, gridElement) {
    gridElement.innerHTML = '';

    if (courses.length === 0) {
        document.getElementById('modal-no-results').style.display = 'block';
        return;
    }

    document.getElementById('modal-no-results').style.display = 'none';

    courses.forEach(course => {
        const courseCard = document.createElement('div');
        courseCard.classList.add('course-card');
        courseCard.style.cursor = 'pointer';

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
                <h3>${course.name}</h3>
                <div class="course-header-actions">
                    <span class="tag ${tagClass}">${course.modality.charAt(0).toUpperCase() + course.modality.slice(1)}</span>
                    <button class="btn-favorito" data-tipo="curso" data-item-id="${course.id}" data-nome-item="${course.name}" title="Adicionar aos favoritos">
                        <i class="far fa-heart"></i>
                    </button>
                </div>
            </div>
            <p class="institution">
                <i class="fas fa-university"></i> ${course.institution}
            </p>
            <p class="description">
                ${course.description ? (course.description.length > 120 ? course.description.substring(0, 120) + '...' : course.description) : 'Sem descrição disponível.'}
            </p>
            <div class="course-footer">
                <div class="course-info">
                    ${course.duration ? `<span><i class="fas fa-clock"></i> ${course.duration}</span>` : ''}
                    ${course.degree ? `<span><i class="fas fa-graduation-cap"></i> ${course.degree}</span>` : ''}
                </div>
                <a href="#" class="course-link" data-course-id="${course.id}">
                    Ver detalhes <i class="fas fa-chevron-right"></i>
                </a>
            </div>
        `;

        // Adicionar event listener para abrir modal de detalhes
        const courseLink = courseCard.querySelector('.course-link');
        courseLink.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (typeof openCourseModal === 'function') {
                openCourseModal(course);
            }
        });

        // Também permite clicar no card inteiro
        courseCard.addEventListener('click', (e) => {
            if (!e.target.closest('.course-link') && !e.target.closest('.btn-favorito')) {
                if (typeof openCourseModal === 'function') {
                    openCourseModal(course);
                }
            }
        });

        gridElement.appendChild(courseCard);
    });

    // Inicializar favoritos
    if (typeof inicializarFavoritos === 'function') {
        inicializarFavoritos('curso');
    }
}

// Função para abrir modal de busca de cursos
async function openCourseSearchModal(nomeCurso) {
    const modal = document.getElementById('courseSearchModal');
    const modalContent = modal.querySelector('.modal-content');
    const gridElement = document.getElementById('modal-courses-grid');
    const loadingElement = document.getElementById('modal-loading');
    const titleElement = document.getElementById('modal-course-title');

    // Atualizar título
    titleElement.textContent = `Cursos: ${nomeCurso}`;

    // Mostrar modal
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // Mostrar loading
    loadingElement.style.display = 'block';
    gridElement.style.display = 'none';
    document.getElementById('modal-no-results').style.display = 'none';

    // Buscar cursos
    const cursos = await buscarCursosPorNome(nomeCurso);
    const mappedCourses = cursos.map(mapCourseData);

    // Esconder loading
    loadingElement.style.display = 'none';
    gridElement.style.display = 'grid';

    // Renderizar cursos
    renderCoursesInModal(mappedCourses, gridElement);

    // Event listeners para fechar o modal
    const closeBtn = modalContent.querySelector('.modal-close');
    closeBtn.onclick = closeCourseSearchModal;

    modal.onclick = (e) => {
        if (e.target === modal) {
            closeCourseSearchModal();
        }
    };

    // Fechar com ESC
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            closeCourseSearchModal();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

// Função para fechar modal
function closeCourseSearchModal() {
    const modal = document.getElementById('courseSearchModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Função para abrir modal de detalhes (se não existir, redireciona)
function openCourseModal(course) {
    // Se a função já existe (da página de cursos), usar ela
    if (typeof window.openCourseModal === 'function') {
        window.openCourseModal(course);
        return;
    }

    // Caso contrário, criar um modal simples
    const modal = document.createElement('div');
    modal.className = 'course-modal';
    modal.style.display = 'flex';
    
    let tagClass = '';
    if (course.modality === 'presencial') {
        tagClass = 'presencial';
    } else if (course.modality === 'ead') {
        tagClass = 'ead';
    } else if (course.modality === 'semipresencial') {
        tagClass = 'semipresencial';
    }

    modal.innerHTML = `
        <div class="modal-content">
            <span class="modal-close">&times;</span>
            <div class="modal-header">
                <h2>${course.name}</h2>
                <span class="tag ${tagClass}">${course.modality.charAt(0).toUpperCase() + course.modality.slice(1)}</span>
            </div>
            <div class="modal-body">
                <div class="modal-info-item">
                    <i class="fas fa-university"></i>
                    <div>
                        <strong>Instituição:</strong>
                        <p>${course.institution}</p>
                    </div>
                </div>
                ${course.area ? `
                <div class="modal-info-item">
                    <i class="fas fa-tag"></i>
                    <div>
                        <strong>Área:</strong>
                        <p>${course.area}</p>
                    </div>
                </div>
                ` : ''}
                ${course.duration ? `
                <div class="modal-info-item">
                    <i class="fas fa-clock"></i>
                    <div>
                        <strong>Duração:</strong>
                        <p>${course.duration}</p>
                    </div>
                </div>
                ` : ''}
                ${course.degree ? `
                <div class="modal-info-item">
                    <i class="fas fa-graduation-cap"></i>
                    <div>
                        <strong>Grau:</strong>
                        <p>${course.degree}</p>
                    </div>
                </div>
                ` : ''}
                ${course.type ? `
                <div class="modal-info-item">
                    <i class="fas fa-building"></i>
                    <div>
                        <strong>Tipo de Instituição:</strong>
                        <p>${course.type}</p>
                    </div>
                </div>
                ` : ''}
                <div class="modal-description">
                    <h3>Sobre o Curso</h3>
                    <p>${course.description || 'Descrição não disponível no momento.'}</p>
                </div>
                <div style="margin-top: 2rem; text-align: center;">
                    <a href="/cursos" style="display: inline-block; padding: 0.8rem 2rem; background: var(--primary-color); color: var(--second-color); text-decoration: none; border-radius: 5px; font-weight: 600;">
                        Ver todos os cursos
                    </a>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';

    const closeBtn = modal.querySelector('.modal-close');
    closeBtn.onclick = () => {
        document.body.removeChild(modal);
        document.body.style.overflow = 'auto';
    };

    modal.onclick = (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
            document.body.style.overflow = 'auto';
        }
    };
}

// Adicionar event listeners aos itens de curso
document.addEventListener('DOMContentLoaded', () => {
    carregarListaDeCursosDaHome();
});

// Busca os cursos reais cadastrados e monta a lista de "cursos em destaque"
// dinamicamente — antes essa lista era um HTML fixo, dessincronizado da
// base de dados real (mostrava cursos inexistentes e escondia cursos que
// existiam de verdade). Busca um lote e mostra nomes distintos.
async function carregarListaDeCursosDaHome() {
    const container = document.getElementById('cursos-lista-home');
    if (!container) return;

    try {
        const params = new URLSearchParams();
        params.append('limit', 50);
        const response = await fetch(`${API_BASE_URL}/cursos/listar?${params.toString()}`);
        const data = await response.json();

        if (!data.success || !data.cursos || data.cursos.length === 0) {
            container.innerHTML = '<p class="no-results">Nenhum curso disponível no momento.</p>';
            return;
        }

        const nomesUnicos = [...new Set(data.cursos.map(c => c.nome))]
            .sort((a, b) => a.localeCompare(b, 'pt-BR'))
            .slice(0, 8);

        container.innerHTML = '';
        nomesUnicos.forEach(nome => {
            const item = document.createElement('div');
            item.className = 'curso-item';
            item.setAttribute('data-curso', nome);
            item.textContent = nome;
            container.appendChild(item);
        });

        ativarCliqueNosCursoItems(container);
    } catch (error) {
        console.error('Erro ao carregar lista de cursos da home:', error);
        container.innerHTML = '<p class="error">Não foi possível carregar os cursos.</p>';
    }
}

function ativarCliqueNosCursoItems(container) {
    const cursoItems = container.querySelectorAll('.curso-item[data-curso]');
    cursoItems.forEach(item => {
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => {
            const nomeCurso = item.getAttribute('data-curso');
            openCourseSearchModal(nomeCurso);
        });
    });
}

