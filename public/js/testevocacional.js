// Teste Vocacional - lógica de pontuação no frontend

const API_BASE_URL = '/api';

// Respostas em andamento ficam no sessionStorage (só as alternativas
// marcadas — nada sensível) para não se perderem ao atualizar a página.
// A pontuação e a compatibilidade com cursos são calculadas no servidor
// (app/services/vocacional_service.py).
const STORAGE_RESPOSTAS = 'suafacul:teste-vocacional:respostas';

function lerRespostasSalvas() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_RESPOSTAS) || '{}') || {};
  } catch (e) {
    return {};
  }
}

function salvarRespostas(answers) {
  try {
    sessionStorage.setItem(STORAGE_RESPOSTAS, JSON.stringify(answers));
  } catch (e) { /* armazenamento indisponível: segue sem persistir */ }
}

function limparRespostasSalvas() {
  try {
    sessionStorage.removeItem(STORAGE_RESPOSTAS);
  } catch (e) { /* ignore */ }
}

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
    firstPending,
    // Leva o usuário até a primeira pergunta sem resposta
    goToFirstPending() {
      const pending = firstPending();
      if (pending === -1) return false;
      goTo(pending);
      showFeedback(`Faltam ${total - answeredCount()} pergunta(s). Responda todas para ver seu resultado.`);
      shake(steps[pending].querySelector('.quiz-options'));
      return true;
    }
  };
}

function coletarRespostas(form) {
  const answers = {};
  new FormData(form).forEach((value, key) => {
    answers[key] = value;
  });
  return answers;
}

function restaurarRespostas(form) {
  const salvas = lerRespostasSalvas();
  let restauradas = 0;
  Object.entries(salvas).forEach(([name, value]) => {
    const input = Array.from(form.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`))
      .find((i) => i.value === value);
    if (input) {
      input.checked = true;
      restauradas += 1;
    }
  });
  return restauradas;
}

function initVocationalTest() {
  const form = document.getElementById('vocational-form');
  const scrollButton = document.getElementById('scroll-to-test');
  const scrollButtonTop = document.getElementById('scroll-to-test-top');

  function scrollToTest(e) {
    if (e) e.preventDefault();
    const target = document.getElementById('vocational-test');
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  if (scrollButton) scrollButton.addEventListener('click', scrollToTest);
  if (scrollButtonTop) scrollButtonTop.addEventListener('click', scrollToTest);

  if (!form) return;

  const restauradas = restaurarRespostas(form);
  const wizard = createQuizWizard(form);
  const finishButton = document.getElementById('quiz-finish');
  let submitting = false;

  // Continua de onde parou depois de atualizar a página
  if (restauradas > 0) {
    const pendente = wizard.firstPending();
    wizard.goTo(pendente === -1 ? wizard.total - 1 : pendente, { focus: false });
  }

  form.addEventListener('change', (e) => {
    if (e.target.matches('input[type="radio"]')) salvarRespostas(coletarRespostas(form));
  });

  function setLoading(loading) {
    submitting = loading;
    finishButton.disabled = loading;
    finishButton.classList.toggle('is-loading', loading);
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (submitting) return;

    const answers = coletarRespostas(form);
    const missing = wizard.names.filter((q) => !answers[q]);
    if (missing.length > 0) {
      wizard.goToFirstPending();
      return;
    }

    setLoading(true);
    try {
      const payload = new URLSearchParams();
      payload.append('respostas_json', JSON.stringify(answers));
      const response = await fetch(`${API_BASE_URL}/teste_vocacional/salvar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: payload.toString(),
        credentials: 'same-origin'
      });
      let data = {};
      try { data = await response.json(); } catch (err) { /* resposta sem JSON */ }

      if (!response.ok || !data.success) {
        wizard.showFeedback(data.message || 'Não foi possível processar seu teste agora. Suas respostas foram mantidas — tente novamente.');
        setLoading(false);
        return;
      }

      // Resultado salvo no servidor: as respostas locais já não são necessárias
      limparRespostasSalvas();
      window.location.href = data.redirect || '/testevocacional/resultado';
    } catch (err) {
      console.error('Erro ao enviar o teste vocacional:', err);
      wizard.showFeedback('Sem conexão com o servidor. Suas respostas foram mantidas — tente novamente em instantes.');
      setLoading(false);
    }
  });
}

document.addEventListener('DOMContentLoaded', initVocationalTest);
