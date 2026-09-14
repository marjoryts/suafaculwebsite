// Controla as setas dos carrosséis de "Faculdades em destaque" e
// "Próximos vestibulares" na home. Rolagem horizontal suave, sem
// depender de nenhuma biblioteca externa.
(function () {
    function scrollAmount(track) {
        const firstCard = track.firstElementChild;
        if (!firstCard) return track.clientWidth;
        const style = window.getComputedStyle(track);
        const gap = parseFloat(style.columnGap || style.gap || '0') || 0;
        return firstCard.getBoundingClientRect().width + gap;
    }

    function atStart(track) {
        return track.scrollLeft <= 1;
    }

    function atEnd(track) {
        return track.scrollLeft + track.clientWidth >= track.scrollWidth - 1;
    }

    function updateButtons(track, prevBtn, nextBtn) {
        if (prevBtn) prevBtn.disabled = atStart(track);
        if (nextBtn) nextBtn.disabled = atEnd(track);
    }

    document.querySelectorAll('.carousel-wrapper').forEach(wrapper => {
        const prevBtn = wrapper.querySelector('.carousel-prev');
        const nextBtn = wrapper.querySelector('.carousel-next');
        const targetId = (prevBtn || nextBtn)?.getAttribute('data-target');
        const track = targetId ? document.getElementById(targetId) : wrapper.querySelector('[class$="-lista"]');

        if (!track) return;

        updateButtons(track, prevBtn, nextBtn);

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                track.scrollBy({ left: -scrollAmount(track), behavior: 'smooth' });
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                track.scrollBy({ left: scrollAmount(track), behavior: 'smooth' });
            });
        }

        track.addEventListener('scroll', () => updateButtons(track, prevBtn, nextBtn));
        window.addEventListener('resize', () => updateButtons(track, prevBtn, nextBtn));
    });
})();
