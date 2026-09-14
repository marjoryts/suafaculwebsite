// Redireciona a busca da home para a página de Faculdades, preservando os
// filtros preenchidos (Problema: home deve redirecionar para /faculdades
// com os filtros aplicados, em vez de não fazer nada ao clicar em "Buscar").
//
// Usa os MESMOS seletores/convenções de public/js/faculdades.js (mesmos
// placeholders, mesmos textos de label nos checkboxes/radio) para que os
// nomes de parâmetro na URL sejam diretamente compatíveis com a lógica de
// pré-preenchimento implementada em faculdades.js.
document.addEventListener('DOMContentLoaded', () => {
    const cursoInput = document.querySelector('input[placeholder*="curso"]');
    const faculdadeInput = document.querySelector('input[placeholder*="faculdade"]');
    const cidadeInput = document.querySelector('input[placeholder*="cidade"]');
    const modalidadeCheckboxes = document.querySelectorAll('.filtros1 input[type="checkbox"]');
    const tipoInstituicaoRadios = document.querySelectorAll('.filtros input[type="radio"]');
    const buscarButton = document.querySelector('.btn-buscar');

    if (!buscarButton) return;

    function irParaFaculdades() {
        const params = new URLSearchParams();

        const cursoValue = cursoInput ? cursoInput.value.trim() : '';
        if (cursoValue) params.append('curso', cursoValue);

        const faculdadeValue = faculdadeInput ? faculdadeInput.value.trim() : '';
        if (faculdadeValue) params.append('faculdade', faculdadeValue);

        const cidadeValue = cidadeInput ? cidadeInput.value.trim() : '';
        if (cidadeValue) params.append('cidade', cidadeValue);

        Array.from(modalidadeCheckboxes)
            .filter(checkbox => checkbox.checked)
            .forEach(checkbox => {
                const label = checkbox.parentElement.textContent.trim();
                if (label) params.append('modalidade', label);
            });

        const selectedTipo = Array.from(tipoInstituicaoRadios).find(radio => radio.checked);
        if (selectedTipo) {
            const label = selectedTipo.parentElement.textContent.trim();
            if (label) params.append('tipo', label);
        }

        const queryString = params.toString();
        window.location.href = queryString ? `/faculdades?${queryString}` : '/faculdades';
    }

    buscarButton.addEventListener('click', (e) => {
        e.preventDefault();
        irParaFaculdades();
    });

    // Permite pesquisar com Enter em qualquer um dos três campos, mesmo
    // comportamento já usado na própria página de Faculdades.
    [cursoInput, faculdadeInput, cidadeInput].forEach(input => {
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    irParaFaculdades();
                }
            });
        }
    });
});
