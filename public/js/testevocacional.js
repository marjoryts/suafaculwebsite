// Teste Vocacional - lógica de pontuação no frontend

const API_BASE_URL = '/api';

const profilesInfo = {
  tecnico: {
    nome: 'Perfil Técnico / Exato',
    descricao:
      'Você gosta de lógica, tecnologia e resolução de problemas. Prefere atividades estruturadas e analíticas.',
    areas: [
      'Engenharia',
      'TI / Desenvolvimento de Software',
      'Análise de Dados',
      'Sistemas de Informação',
      'Arquitetura'
    ]
  },
  criativo: {
    nome: 'Perfil Criativo / Comunicativo',
    descricao:
      'Você se destaca pela criatividade, comunicação e expressão. Gosta de ambientes dinâmicos e flexíveis.',
    areas: [
      'Design',
      'Publicidade e Propaganda',
      'Marketing',
      'Arquitetura',
      'Moda',
      'Produção Audiovisual'
    ]
  },
  humano: {
    nome: 'Perfil Humano / Social',
    descricao:
      'Você tem empatia, gosta de ajudar pessoas e trabalhar em grupo. Valoriza impacto social.',
    areas: [
      'Psicologia',
      'Pedagogia',
      'Recursos Humanos',
      'Serviço Social',
      'Enfermagem',
      'Fisioterapia'
    ]
  },
  gestao: {
    nome: 'Perfil Gestão / Negócios',
    descricao:
      'Você gosta de organizar, planejar, liderar e entender como as coisas funcionam em empresas.',
    areas: [
      'Administração',
      'Gestão Comercial',
      'Economia',
      'Logística',
      'Finanças',
      'Empreendedorismo'
    ]
  },
  cientifico: {
    nome: 'Perfil Científico / Investigativo',
    descricao:
      'Você é curioso(a), gosta de pesquisa, experimentos e se aprofunda em temas complexos.',
    areas: [
      'Medicina',
      'Biomedicina',
      'Biologia',
      'Química',
      'Física',
      'Pesquisa Acadêmica'
    ]
  },
  pratico: {
    nome: 'Perfil Prático / Operacional',
    descricao:
      'Você aprende fazendo, gosta de atividades manuais ou aplicadas e prefere menos teoria.',
    areas: [
      'Técnico em TI',
      'Mecatrônica',
      'Segurança do Trabalho',
      'Produção Industrial',
      'Manutenção e Mecânica'
    ]
  }
};

// Áreas reais do banco para buscar cursos por perfil
const profileAreasMap = {
  tecnico: ['Tecnologia', 'Engenharias'],
  criativo: ['Artes e Design', 'Comunicação'],
  humano: ['Saúde'],
  gestao: ['Negócios'],
  cientifico: ['Saúde'],
  pratico: ['Tecnologia', 'Engenharias']
};

// ──────────────────────────────────────────────
// Navegação do teste: uma pergunta por vez
// ──────────────────────────────────────────────

function createQuizWizard(form) {
  const steps = Array.from(form.querySelectorAll('.quiz-step'));
  const total = steps.length;
  const el = (id) => document.getElementById(id);
  const ui = {
    category: el('quiz-category'),
    current: el('quiz-current'),
    total: el('quiz-total'),
    progressLabel: el('quiz-progress-label'),
    progressPercent: el('quiz-progress-percent'),
    progressFill: el('quiz-progress-fill'),
    progressBar: el('quiz-progressbar'),
    stepsNav: el('quiz-steps-nav'),
    feedback: el('quiz-feedback'),
    prev: el('quiz-prev'),
    next: el('quiz-next'),
    finish: el('quiz-finish')
  };
  let index = 0;

  const questionName = (step) => step.querySelector('input[type="radio"]').name;
  const isAnswered = (step) => !!step.querySelector('input[type="radio"]:checked');
  const answeredCount = () => steps.filter(isAnswered).length;
  const firstPending = () => steps.findIndex((s) => !isAnswered(s));

  // Navegador numerado (1…N) para pular entre perguntas
  const dots = steps.map((step, i) => {
    const dot = document.createElement('button');
    dot.type = 'button';
    dot.className = 'quiz-step-dot';
    dot.textContent = String(i + 1);
    dot.addEventListener('click', () => {
      // Só permite pular para perguntas já respondidas ou para a próxima pendente
      const pending = firstPending();
      if (isAnswered(step) || i === pending || pending === -1) {
        goTo(i);
      } else {
        showFeedback('Responda as perguntas anteriores antes de avançar para esta.');
      }
    });
    ui.stepsNav.appendChild(dot);
    return dot;
  });

  function showFeedback(message) {
    ui.feedback.textContent = message;
    ui.feedback.hidden = false;
  }

  function hideFeedback() {
    ui.feedback.hidden = true;
    ui.feedback.textContent = '';
  }

  function shake(node) {
    node.classList.remove('is-shaking');
    void node.offsetWidth; // reinicia a animação
    node.classList.add('is-shaking');
  }

  function render() {
    steps.forEach((step, i) => {
      step.hidden = i !== index;
    });
    const step = steps[index];
    const answered = answeredCount();
    const percent = Math.round((answered / total) * 100);

    ui.category.textContent = step.dataset.category || '';
    ui.current.textContent = String(index + 1);
    ui.total.textContent = String(total);
    ui.progressLabel.textContent = `${answered} de ${total} respondidas`;
    ui.progressPercent.textContent = `${percent}%`;
    ui.progressFill.style.width = `${percent}%`;
    ui.progressBar.setAttribute('aria-valuenow', String(percent));

    ui.prev.disabled = index === 0;
    ui.next.hidden = index === total - 1;
    ui.next.disabled = !isAnswered(step);
    ui.finish.classList.toggle('is-ready', answered === total);

    dots.forEach((dot, i) => {
      dot.classList.toggle('is-current', i === index);
      dot.classList.toggle('is-answered', isAnswered(steps[i]));
      dot.setAttribute('aria-label', `Pergunta ${i + 1}${isAnswered(steps[i]) ? ' (respondida)' : ''}`);
      if (i === index) dot.setAttribute('aria-current', 'step');
      else dot.removeAttribute('aria-current');
    });
  }

  function focusCurrent() {
    const step = steps[index];
    const target = step.querySelector('input:checked') || step.querySelector('input');
    if (target) target.focus({ preventScroll: true });
  }

  function goTo(i, { focus = true } = {}) {
    index = Math.max(0, Math.min(total - 1, i));
    hideFeedback();
    render();
    if (focus) focusCurrent();
  }

  function next() {
    if (!isAnswered(steps[index])) {
      showFeedback('Escolha uma alternativa para continuar.');
      shake(steps[index].querySelector('.quiz-options'));
      return;
    }
    goTo(index + 1);
  }

  ui.prev.addEventListener('click', () => goTo(index - 1));
  ui.next.addEventListener('click', next);

  form.addEventListener('change', (e) => {
    if (e.target.matches('input[type="radio"]')) {
      hideFeedback();
      render();
    }
  });

  // Enter avança (ou finaliza na última pergunta) sem enviar o formulário antes da hora
  form.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || e.target.tagName === 'BUTTON') return;
    e.preventDefault();
    if (index < total - 1) next();
    else form.requestSubmit ? form.requestSubmit(ui.finish) : ui.finish.click();
  });

  render();

  return {
    total,
    names: steps.map(questionName),
    goTo,
    render,
    showFeedback,
    // Leva o usuário até a primeira pergunta sem resposta
    goToFirstPending() {
      const pending = firstPending();
      if (pending === -1) return false;
      goTo(pending);
      showFeedback(`Faltam ${total - answeredCount()} pergunta(s). Responda todas para ver seu resultado 😊`);
      shake(steps[pending].querySelector('.quiz-options'));
      return true;
    }
  };
}

function initVocationalTest() {
  const form = document.getElementById('vocational-form');
  const quizCard = document.getElementById('quiz-card');
  const resultSection = document.getElementById('vocational-result');
  const resultProfilesContainer = document.getElementById('result-profiles');
  const scrollButton = document.getElementById('scroll-to-test');
  const scrollButtonTop = document.getElementById('scroll-to-test-top');
  const restartButton = document.getElementById('quiz-restart');
  const reviewButton = document.getElementById('quiz-review');

  function scrollToTest(e) {
    if (e) e.preventDefault();
    const target = document.getElementById('vocational-test');
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  if (scrollButton) {
    scrollButton.addEventListener('click', scrollToTest);
  }

  if (scrollButtonTop) {
    scrollButtonTop.addEventListener('click', scrollToTest);
  }

  if (!form || !resultSection || !resultProfilesContainer) {
    return;
  }

  const wizard = createQuizWizard(form);
  const finishButton = document.getElementById('quiz-finish');
  let submitting = false;

  function showQuiz(stepIndex) {
    resultSection.style.display = 'none';
    quizCard.hidden = false;
    wizard.goTo(stepIndex, { focus: false });
    scrollToTest();
  }

  if (restartButton) {
    restartButton.addEventListener('click', () => {
      form.reset();
      resultProfilesContainer.innerHTML = '';
      showQuiz(0);
    });
  }

  if (reviewButton) {
    reviewButton.addEventListener('click', () => showQuiz(0));
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (submitting) return;

    const formData = new FormData(form);
    const answers = {};
    formData.forEach((value, key) => {
      answers[key] = value;
    });

    // Verificar se todas as perguntas foram respondidas
    const requiredQuestions = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10'];
    const missing = requiredQuestions.filter((q) => !answers[q]);
    if (missing.length > 0) {
      wizard.goToFirstPending();
      return;
    }

    submitting = true;
    finishButton.disabled = true;
    finishButton.classList.add('is-loading');

    const scores = {
      tecnico: 0,
      criativo: 0,
      humano: 0,
      gestao: 0,
      cientifico: 0,
      pratico: 0
    };

    Object.values(answers).forEach((value) => {
      const tags = String(value).split(',');
      tags.forEach((tag) => {
        const key = tag.trim();
        if (key && scores[key] !== undefined) {
          scores[key] += 1;
        }
      });
    });

    const maxScore = Math.max(...Object.values(scores));
    const bestProfiles = Object.entries(scores)
      .filter(([, score]) => score === maxScore && score > 0)
      .map(([key]) => key);

    resultProfilesContainer.innerHTML = '';

    if (bestProfiles.length === 0) {
      resultProfilesContainer.innerHTML =
        '<p>Não foi possível identificar um perfil claro. Tente refazer o teste com mais calma.</p>';
    } else {
      bestProfiles.forEach((profileKey) => {
        const info = profilesInfo[profileKey];
        if (!info) return;

        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = `
          <h4>${info.nome}</h4>
          <p>${info.descricao}</p>
          <p><strong>Áreas possíveis:</strong> ${info.areas.join(', ')}</p>
          <div class="suggested-courses" data-profile="${profileKey}">
            <p class="loading">Carregando cursos sugeridos...</p>
          </div>
        `;
        resultProfilesContainer.appendChild(card);
      });
    }

    // Mostra o resultado já com os cards; os cursos sugeridos carregam em seguida
    quizCard.hidden = true;
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    resultSection.focus({ preventScroll: true });

    if (bestProfiles.length > 0) {
      // Buscar cursos sugeridos na API
      try {
        await loadSuggestedCourses(bestProfiles);
      } catch (err) {
        // Falha silenciosa, apenas loga no console
        console.error('Erro ao carregar cursos sugeridos:', err);
      }
    }

    // Salvar resultado no backend (se a API estiver disponível)
    try {
      await saveVocationalResult(bestProfiles, scores, answers);
    } catch (err) {
      console.warn('Não foi possível salvar o resultado do teste vocacional.', err);
    }

    submitting = false;
    finishButton.disabled = false;
    finishButton.classList.remove('is-loading');
  });
}

async function loadSuggestedCourses(profiles) {
  for (const profileKey of profiles) {
    const areas = profileAreasMap[profileKey];
    if (!areas || areas.length === 0) continue;

    const area = areas[0]; // pega a área principal para não fazer muitas requisições
    const container = document.querySelector(`.suggested-courses[data-profile="${profileKey}"]`);
    if (!container) continue;

    try {
      const params = new URLSearchParams();
      params.append('area', area);
      params.append('limit', '3');

      const response = await fetch(`${API_BASE_URL}/cursos/listar?${params.toString()}`);
      const data = await response.json();

      if (!data.success || !data.cursos || data.cursos.length === 0) {
        container.innerHTML = '<p>Nenhum curso sugerido encontrado para este perfil ainda.</p>';
        continue;
      }

      const list = document.createElement('ul');
      list.className = 'suggested-courses-list';

      data.cursos.forEach((curso) => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${curso.nome}</strong> <span>${curso.instituicao}</span>`;
        list.appendChild(li);
      });

      container.innerHTML = '<p><strong>Cursos sugeridos para você:</strong></p>';
      container.appendChild(list);
    } catch (error) {
      console.error('Erro ao buscar cursos sugeridos:', error);
      container.innerHTML = '<p>Não foi possível carregar cursos sugeridos agora.</p>';
    }
  }
}

async function saveVocationalResult(bestProfiles, scores, answers) {
  if (!bestProfiles || bestProfiles.length === 0) return;

  const perfilPrincipal = bestProfiles[0];

  const payload = new URLSearchParams();
  payload.append('perfil_principal', perfilPrincipal);
  payload.append('perfis_json', JSON.stringify({ scores, bestProfiles }));
  payload.append('respostas_json', JSON.stringify(answers));

  await fetch(`${API_BASE_URL}/teste_vocacional/salvar`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: payload.toString()
  });
}

document.addEventListener('DOMContentLoaded', initVocationalTest);


