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
                ${course.description ? escaparHtml(course.description.length > 120 ? course.description.substring(0, 120) + '...' : course.description) : 'Sem descrição disponível.'}
            </p>
            <div class="course-footer">
                <div class="course-info">
                    ${course.duration ? `<span><i class="fas fa-clock"></i> ${escaparHtml(course.duration)}</span>` : ''}
                    ${course.degree ? `<span><i class="fas fa-graduation-cap"></i> ${escaparHtml(course.degree)}</span>` : ''}
                </div>
                <a href="#" class="course-link" data-course-id="${escaparHtml(course.id)}">
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

// Inicialização da seção "Cursos" da home
document.addEventListener('DOMContentLoaded', () => {
    carregarCatalogoDeCursosDaHome();
    ativarBuscaDeCursosDaHome();

    // Corações dos carrosséis "Faculdades em destaque" e "Próximos vestibulares"
    if (typeof inicializarFavoritos === 'function') {
        inicializarFavoritos('faculdade');
        inicializarFavoritos('vestibular');
    }
});

// ── Grade de cursos com imagens ────────────────────────────────────────
// Os cursos vêm do banco (/api/cursos/catalogo): nome, área, imagem e
// quantas instituições oferecem cada um. Cada card leva à listagem de
// faculdades filtrada por aquele curso (/faculdades?curso=<nome>&exato=1).

const CURSOS_VISIVEIS_INICIALMENTE = 12; // 3 linhas de 4 no desktop

const estadoCatalogo = {
    cursos: [],
    area: '',
    termo: '',
    expandido: false
};

// Ícone exibido quando a foto do curso não carrega (sem conexão com a CDN)
const ICONE_POR_AREA = {
    'Tecnologia': 'fa-laptop-code',
    'Saúde': 'fa-heart-pulse',
    'Engenharias': 'fa-gears',
    'Negócios': 'fa-briefcase',
    'Direito': 'fa-scale-balanced',
    'Humanas': 'fa-landmark',
    'Educação': 'fa-chalkboard-user',
    'Ciências Exatas': 'fa-square-root-variable',
    'Ciências Biológicas': 'fa-dna',
    'Ciências Agrárias': 'fa-seedling',
    'Comunicação': 'fa-bullhorn',
    'Artes e Design': 'fa-palette'
};

function normalizarTexto(texto) {
    return (texto || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
}

async function carregarCatalogoDeCursosDaHome() {
    const grade = document.getElementById('cursos-lista-home');
    if (!grade) return;

    try {
        const response = await fetch(`${API_BASE_URL}/cursos/catalogo`);
        const data = await response.json();
        if (!data.success || !Array.isArray(data.cursos) || data.cursos.length === 0) {
            grade.innerHTML = '<p class="no-results">Nenhum curso disponível no momento.</p>';
            grade.setAttribute('aria-busy', 'false');
            return;
        }
        estadoCatalogo.cursos = data.cursos;
        renderizarAreasDoCatalogo(data.areas || []);
        renderizarGradeDeCursos();
    } catch (error) {
        console.error('Erro ao carregar o catálogo de cursos:', error);
        grade.innerHTML = '<p class="error">Não foi possível carregar os cursos.</p>';
        grade.setAttribute('aria-busy', 'false');
    }

    const botaoMais = document.getElementById('home-cursos-mais');
    if (botaoMais) {
        botaoMais.addEventListener('click', () => {
            estadoCatalogo.expandido = true;
            renderizarGradeDeCursos();
        });
    }
}

function renderizarAreasDoCatalogo(areas) {
    const container = document.getElementById('home-cursos-areas');
    if (!container) return;

    const opcoes = [{ valor: '', rotulo: 'Todas as áreas' }]
        .concat(areas.map(area => ({ valor: area, rotulo: area })));

    container.innerHTML = opcoes.map(opcao => `
        <button type="button" class="cursos-area-chip${opcao.valor === estadoCatalogo.area ? ' active' : ''}"
                data-area="${escaparHtml(opcao.valor)}" aria-pressed="${opcao.valor === estadoCatalogo.area}">
            ${escaparHtml(opcao.rotulo)}
        </button>
    `).join('');

    container.querySelectorAll('.cursos-area-chip').forEach(botao => {
        botao.addEventListener('click', () => {
            estadoCatalogo.area = botao.getAttribute('data-area');
            container.querySelectorAll('.cursos-area-chip').forEach(b => {
                const ativo = b === botao;
                b.classList.toggle('active', ativo);
                b.setAttribute('aria-pressed', String(ativo));
            });
            renderizarGradeDeCursos();
        });
    });
}

function cursosFiltradosDoCatalogo() {
    const termo = normalizarTexto(estadoCatalogo.termo);
    return estadoCatalogo.cursos.filter(curso => {
        if (estadoCatalogo.area && curso.area !== estadoCatalogo.area) return false;
        if (termo && !normalizarTexto(curso.nome).includes(termo)) return false;
        return true;
    });
}

function textoInstituicoes(total) {
    if (!total) return 'Em breve';
    return total === 1 ? '1 instituição' : `${total} instituições`;
}

function criarCardDeCurso(curso) {
    const link = document.createElement('a');
    link.className = 'curso-card';
    link.href = `/faculdades?curso=${encodeURIComponent(curso.nome)}&exato=1`;
    link.setAttribute('aria-label', `${curso.nome}: ver faculdades que oferecem o curso`);

    const icone = ICONE_POR_AREA[curso.area] || 'fa-graduation-cap';
    link.innerHTML = `
        <div class="curso-card-media">
            <i class="fas ${icone} curso-card-icone" aria-hidden="true"></i>
            ${curso.imagem_url ? `<img src="${escaparHtml(curso.imagem_url)}" alt="" loading="lazy" decoding="async" width="640" height="320">` : ''}
        </div>
        <div class="curso-card-body">
            <h3>${escaparHtml(curso.nome)}</h3>
            <span class="curso-card-meta">${escaparHtml(textoInstituicoes(curso.total_instituicoes))}</span>
        </div>
    `;

    const media = link.querySelector('.curso-card-media');
    const img = link.querySelector('img');
    if (!img) {
        media.classList.add('sem-imagem');
    } else {
        // Sem a foto (CDN fora do ar, rede bloqueada), mostra o ícone da área
        img.addEventListener('error', () => {
            img.remove();
            media.classList.add('sem-imagem');
        });
    }
    return link;
}

function renderizarGradeDeCursos() {
    const grade = document.getElementById('cursos-lista-home');
    const botaoMais = document.getElementById('home-cursos-mais');
    if (!grade) return;

    const filtrados = cursosFiltradosDoCatalogo();
    const filtrando = Boolean(estadoCatalogo.termo.trim()) || Boolean(estadoCatalogo.area);
    const mostrarTodos = estadoCatalogo.expandido || filtrando;
    const visiveis = mostrarTodos ? filtrados : filtrados.slice(0, CURSOS_VISIVEIS_INICIALMENTE);

    grade.innerHTML = '';
    grade.setAttribute('aria-busy', 'false');

    if (visiveis.length === 0) {
        const termo = estadoCatalogo.termo.trim();
        const vazio = document.createElement('div');
        vazio.className = 'cursos-grade-vazio';
        vazio.innerHTML = termo
            ? `<p>Nenhum curso do catálogo corresponde a "${escaparHtml(termo)}".</p>
               <button type="button" class="section-link">Buscar "${escaparHtml(termo)}" em todos os cursos <i class="fas fa-arrow-right" aria-hidden="true"></i></button>`
            : '<p>Nenhum curso nesta área por enquanto.</p>';
        const botao = vazio.querySelector('button');
        if (botao) botao.addEventListener('click', () => openCourseSearchModal(termo));
        grade.appendChild(vazio);
    } else {
        const fragmento = document.createDocumentFragment();
        visiveis.forEach(curso => fragmento.appendChild(criarCardDeCurso(curso)));
        grade.appendChild(fragmento);
    }

    if (botaoMais) {
        const restantes = filtrados.length - visiveis.length;
        botaoMais.hidden = mostrarTodos || restantes <= 0;
    }
}

// Campo "Pesquisar curso" da seção Cursos: filtra os cards enquanto o
// usuário digita e, ao enviar, abre o modal com todos os cursos cadastrados
// que têm esse nome (inclusive os que não estão no catálogo da home).
function ativarBuscaDeCursosDaHome() {
    const form = document.getElementById('home-curso-busca');
    const input = document.getElementById('home-curso-input');
    if (!form || !input) return;

    let timer;
    input.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => {
            estadoCatalogo.termo = input.value;
            renderizarGradeDeCursos();
        }, 150);
    });

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const termo = input.value.trim();
        if (!termo) {
            input.focus();
            return;
        }
        openCourseSearchModal(termo);
    });
}
