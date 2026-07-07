/* gallery.js — Lightbox pour la galerie masonry */

document.addEventListener('DOMContentLoaded', () => {
  const gallery   = document.getElementById('gallery-grid');
  const lightbox  = document.getElementById('lightbox');
  const lbImg     = document.getElementById('lightbox-img');
  const lbClose   = document.getElementById('lightbox-close');
  const lbPrev    = document.getElementById('lightbox-prev');
  const lbNext    = document.getElementById('lightbox-next');

  if (!gallery || !lightbox) return;

  const thumbs = Array.from(gallery.querySelectorAll('.gallery-thumb-btn'));
  let current  = 0;

  function getSrc(btn) {
    return btn.querySelector('img').src;
  }

  function getAlt(btn) {
    return btn.querySelector('img').alt;
  }

  function open(index) {
    current = ((index % thumbs.length) + thumbs.length) % thumbs.length;
    lbImg.src = getSrc(thumbs[current]);
    lbImg.alt = getAlt(thumbs[current]);
    lightbox.removeAttribute('hidden');
    document.body.style.overflow = 'hidden';
    lbClose.focus();
  }

  function close() {
    lightbox.setAttribute('hidden', '');
    lbImg.src = '';
    document.body.style.overflow = '';
    // Retourner le focus au bouton qui a ouvert la lightbox
    if (thumbs[current]) thumbs[current].focus();
  }

  function navigate(delta) {
    open(current + delta);
  }

  thumbs.forEach((btn, i) => {
    btn.addEventListener('click', () => open(i));
  });

  lbClose.addEventListener('click', close);
  lbPrev.addEventListener('click',  () => navigate(-1));
  lbNext.addEventListener('click',  () => navigate(+1));

  // Clic en dehors de l'image
  lightbox.addEventListener('click', (e) => {
    if (e.target === lightbox) close();
  });

  // Clavier
  document.addEventListener('keydown', (e) => {
    if (lightbox.hasAttribute('hidden')) return;
    if (e.key === 'Escape')      close();
    if (e.key === 'ArrowLeft')   navigate(-1);
    if (e.key === 'ArrowRight')  navigate(+1);
  });
});
