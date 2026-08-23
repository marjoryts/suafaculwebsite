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

function initVocationalTest() {
  const form = document.getElementById('vocational-form');
  const resultSection = document.getElementById('vocational-result');
  const resultProfilesContainer = document.getElementById('result-profiles');
  const scrollButton = document.getElementById('scroll-to-test');
  const scrollButtonTop = document.getElementById('scroll-to-test-top');

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

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(form);
    const answers = {};
    formData.forEach((value, key) => {
      answers[key] = value;
    });

    // Verificar se todas as perguntas foram respondidas
    const requiredQuestions = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10'];
    const missing = requiredQuestions.filter((q) => !answers[q]);
    if (missing.length > 0) {
      alert('Responda todas as perguntas para ver seu resultado 😊');
      return;
    }

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

    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
        return;
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


