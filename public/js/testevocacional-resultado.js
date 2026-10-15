// Tela de resultados do Teste Vocacional.
// - Prévia (perfil + quantidade de cursos compatíveis): GET /api/teste_vocacional/resultado
// - Lista completa: GET /api/teste_vocacional/recomendacoes — protegida no
//   servidor (401 sem login). O front-end nunca recebe a lista antes disso.

(function () {
  const API = '/api/teste_vocacional';
  const POR_PAGINA = 12;
  const el = (id) => document.getElementById(id);

  const ui = {
    secao: el('resultado-vocacional'),
    carregando: el('resultado-carregando'),
    erro: el('resultado-erro'),
    erroTexto: el('resultado-erro-texto'),
    tentarNovamente: el('resultado-tentar-novamente'),
    fazerTeste: el('resultado-fazer-teste'),
    conteudo: el('resultado-conteudo'),
    perfilNome: el('perfil-nome'),
    perfilDescricao: el('perfil-descricao'),
    pontuacoes: el('perfil-pontuacoes'),
    bloqueio: el('resultado-bloqueio'),
    bloqueioTexto: el('bloqueio-texto'),
    bloqueioTotal: el('bloqueio-total'),
    recomendacoes: el('resultado-recomendacoes'),
    resumo: el('recomendacoes-resumo'),
    cursos: el('resultado-cursos'),
    verMais: el('btn-ver-mais')
  };

  let cursos = [];
  let exibidos = 0;

  function escaparHtml(texto) {
    return String(texto ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function mostrar(estado) {
    ui.carregando.hidden = estado !== 'carregando';
    ui.erro.hidden = estado !== 'erro' && estado !== 'sem_resultado';
    ui.conteudo.hidden = estado !== 'conteudo';
  }

  function mostrarErro(texto, { semResultado = false } = {}) {
    ui.erroTexto.textContent = texto;
    ui.tentarNovamente.hidden = semResultado;
    ui.fazerTeste.hidden = !semResultado;
    mostrar(semResultado ? 'sem_resultado' : 'erro');
  }

  async function getJson(url) {
    const response = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
    let data = {};
    try { data = await response.json(); } catch (e) { /* sem corpo JSON */ }
    return { status: response.status, ok: response.ok, data };
  }

  function nivelCompatibilidade(pct) {
    if (pct >= 75) return 'alta';
    if (pct >= 45) return 'media';
    return 'baixa';
  }

  function renderPerfil(resultado) {
    ui.perfilNome.textContent = resultado.perfil_nome || 'Perfil não identificado';
    ui.perfilDescricao.textContent = resultado.perfil_descricao || '';
    ui.perfilDescricao.hidden = !resultado.perfil_descricao;
    ui.pontuacoes.innerHTML = (resultado.pontuacoes || []).map((p) => `
      <li>
        <div class="resultado-barra-info"><span>${escaparHtml(p.nome)}</span><strong>${escaparHtml(p.percentual)}%</strong></div>
        <div class="quiz-progress-track"><div class="quiz-progress-fill" style="width:${Number(p.percentual) || 0}%"></div></div>
      </li>`).join('');
  }

  function renderBloqueio(totalCompativeis, sessaoExpirada) {
    ui.recomendacoes.hidden = true;
    ui.bloqueio.hidden = false;
    if (sessaoExpirada) {
      ui.bloqueioTexto.textContent = 'Sua sessão expirou. Entre novamente para ver os cursos com maior compatibilidade com seu perfil.';
    }
    if (typeof totalCompativeis === 'number' && totalCompativeis > 0) {
      ui.bloqueioTotal.textContent = `Encontramos ${totalCompativeis} curso${totalCompativeis > 1 ? 's' : ''} compatíve${totalCompativeis > 1 ? 'is' : 'l'} com você.`;
      ui.bloqueioTotal.hidden = false;
    }
  }

  function cardCurso(curso) {
    const pct = Number(curso.compatibilidade) || 0;
    const nivel = nivelCompatibilidade(pct);
    const instituicoes = curso.total_instituicoes > 1
      ? `${curso.total_instituicoes} instituições`
      : '1 instituição';
    return `
      <article class="course-card resultado-curso">
        <div class="course-header">
          <h3>${escaparHtml(curso.nome)}</h3>
          <span class="resultado-pct resultado-pct--${nivel}">${pct}%</span>
        </div>
        <div class="resultado-compat" role="img" aria-label="Compatibilidade de ${pct}%">
          <div class="resultado-compat-info"><span>Compatibilidade</span><span class="resultado-compat-nivel">${nivel === 'alta' ? 'Alta' : nivel === 'media' ? 'Média' : 'Baixa'}</span></div>
          <div class="quiz-progress-track"><div class="quiz-progress-fill resultado-compat-fill--${nivel}" style="width:${pct}%"></div></div>
        </div>
        ${curso.area ? `<p class="institution"><i class="fas fa-tag" aria-hidden="true"></i> ${escaparHtml(curso.area)}</p>` : ''}
        ${curso.descricao ? `<p class="description">${escaparHtml(curso.descricao)}</p>` : ''}
        <div class="course-footer">
          <div class="course-info">
            ${curso.grau ? `<span><i class="fas fa-graduation-cap" aria-hidden="true"></i> ${escaparHtml(curso.grau)}</span>` : ''}
            <span><i class="fas fa-university" aria-hidden="true"></i> ${instituicoes}</span>
          </div>
        </div>
        <div class="resultado-curso-acoes">
          <a class="course-link" href="/cursos?curso=${encodeURIComponent(curso.id)}">Conhecer o curso <i class="fas fa-chevron-right" aria-hidden="true"></i></a>
          <a class="course-link resultado-link-secundario" href="/cursos?busca=${encodeURIComponent(curso.nome)}">Ver onde estudar</a>
        </div>
      </article>`;
  }

  function renderMais() {
    const proximos = cursos.slice(exibidos, exibidos + POR_PAGINA);
    ui.cursos.insertAdjacentHTML('beforeend', proximos.map(cardCurso).join(''));
    exibidos += proximos.length;
    ui.verMais.hidden = exibidos >= cursos.length;
  }

  function renderRecomendacoes(data) {
    ui.bloqueio.hidden = true;
    ui.recomendacoes.hidden = false;
    cursos = data.cursos || [];
    exibidos = 0;
    ui.cursos.innerHTML = '';

    if (cursos.length === 0) {
      ui.resumo.textContent = '';
      ui.cursos.innerHTML = `
        <p class="resultado-vazio">
          Ainda não há cursos cadastrados com dados suficientes para calcular a compatibilidade com o seu perfil.
          Explore a página de <a href="/cursos">Cursos</a> enquanto ampliamos a base.
        </p>`;
      ui.verMais.hidden = true;
      return;
    }

    const total = data.total_compativeis || cursos.length;
    ui.resumo.textContent = `${total} curso${total > 1 ? 's' : ''} compatíve${total > 1 ? 'is' : 'l'}, do maior para o menor percentual.`
      + (total > cursos.length ? ` Mostrando os ${cursos.length} primeiros.` : '');
    renderMais();
  }

  async function carregar() {
    mostrar('carregando');
    let previa;
    try {
      previa = await getJson(`${API}/resultado`);
    } catch (e) {
      mostrarErro('Sem conexão com o servidor. Verifique sua internet e tente novamente.');
      return;
    }

    if (previa.status === 404) {
      mostrarErro('Não encontramos um teste vocacional concluído. Faça o teste para descobrir seus cursos recomendados.', { semResultado: true });
      return;
    }
    if (!previa.ok || !previa.data.success) {
      mostrarErro(previa.data.message || 'Não foi possível carregar seus resultados agora.');
      return;
    }

    renderPerfil(previa.data.resultado);
    mostrar('conteudo');

    if (!previa.data.autenticado) {
      // A página foi aberta logada mas o servidor não reconhece mais a sessão
      const sessaoExpirada = ui.secao.dataset.autenticado === 'true';
      renderBloqueio(previa.data.total_compativeis, sessaoExpirada);
      return;
    }

    let rec;
    try {
      rec = await getJson(`${API}/recomendacoes?id=${encodeURIComponent(previa.data.resultado.id)}&limite=60`);
    } catch (e) {
      ui.recomendacoes.hidden = false;
      ui.cursos.innerHTML = '<p class="resultado-vazio">Sem conexão para carregar os cursos recomendados. <button type="button" class="resultado-link-botao" data-recarregar>Tentar novamente</button></p>';
      return;
    }

    if (rec.status === 401) {
      renderBloqueio(previa.data.total_compativeis, true);
      return;
    }
    if (!rec.ok || !rec.data.success) {
      ui.recomendacoes.hidden = false;
      ui.cursos.innerHTML = `<p class="resultado-vazio">${escaparHtml(rec.data.message || 'Não foi possível carregar os cursos recomendados agora.')} <button type="button" class="resultado-link-botao" data-recarregar>Tentar novamente</button></p>`;
      return;
    }
    renderRecomendacoes(rec.data);
  }

  ui.tentarNovamente.addEventListener('click', carregar);
  ui.verMais.addEventListener('click', renderMais);
  ui.cursos.addEventListener('click', (e) => {
    if (e.target.closest('[data-recarregar]')) carregar();
  });

  document.addEventListener('DOMContentLoaded', carregar);
})();
