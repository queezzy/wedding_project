/* main.js — nav sticky, countdown, AOS, hamburger, FAQ */

document.addEventListener('DOMContentLoaded', () => {

  // --------------------------------------------------------
  // AOS init
  // --------------------------------------------------------
  if (typeof AOS !== 'undefined') {
    AOS.init({ duration: 700, once: true, offset: 60 });
  }

  // --------------------------------------------------------
  // Nav : scroll shadow + hamburger
  // --------------------------------------------------------
  const navbar    = document.getElementById('navbar');
  const hamburger = document.getElementById('hamburger');
  const navLinks  = document.getElementById('nav-links');

  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
  }

  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      const isOpen = navLinks.classList.toggle('open');
      hamburger.classList.toggle('open', isOpen);
      hamburger.setAttribute('aria-expanded', String(isOpen));
    });

    // Fermer le menu en cliquant sur un lien
    navLinks.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        hamburger.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      });
    });

    // Fermer en cliquant en dehors
    document.addEventListener('click', (e) => {
      if (navbar && !navbar.contains(e.target)) {
        navLinks.classList.remove('open');
        hamburger.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // --------------------------------------------------------
  // Nav : section active via IntersectionObserver
  // --------------------------------------------------------
  const sections = document.querySelectorAll('section[id]');
  const allNavLinks = document.querySelectorAll('.nav-link');

  if (sections.length && allNavLinks.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            allNavLinks.forEach(link => {
              link.classList.toggle(
                'active',
                link.getAttribute('href') === '#' + entry.target.id
              );
            });
          }
        });
      },
      { rootMargin: '-40% 0px -55% 0px' }
    );
    sections.forEach(s => observer.observe(s));
  }

  // --------------------------------------------------------
  // Countdown jusqu'au 19 septembre 2026 13h30 (Meaux, Europe/Paris)
  // --------------------------------------------------------
  const cdDays    = document.getElementById('cd-days');
  const cdHours   = document.getElementById('cd-hours');
  const cdMinutes = document.getElementById('cd-minutes');
  const cdSeconds = document.getElementById('cd-seconds');

  if (cdDays) {
    // 19 sep 2026 13:30:00 heure locale Paris (UTC+2 en été)
    const TARGET = new Date('2026-09-19T11:30:00Z'); // 13h30 CEST = 11h30 UTC

    function pad(n) { return String(n).padStart(2, '0'); }

    function tick() {
      const now  = new Date();
      const diff = TARGET - now;

      if (diff <= 0) {
        cdDays.textContent    = '0';
        cdHours.textContent   = '00';
        cdMinutes.textContent = '00';
        cdSeconds.textContent = '00';
        return;
      }

      const days    = Math.floor(diff / 86400000);
      const hours   = Math.floor((diff % 86400000) / 3600000);
      const minutes = Math.floor((diff % 3600000)  / 60000);
      const seconds = Math.floor((diff % 60000)    / 1000);

      cdDays.textContent    = days;
      cdHours.textContent   = pad(hours);
      cdMinutes.textContent = pad(minutes);
      cdSeconds.textContent = pad(seconds);
    }

    tick();
    setInterval(tick, 1000);
  }

  // --------------------------------------------------------
  // FAQ accordion
  // --------------------------------------------------------
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const answer   = btn.nextElementSibling;
      const isOpen   = btn.getAttribute('aria-expanded') === 'true';
      const allBtns  = document.querySelectorAll('.faq-question');

      // Fermer tous les autres
      allBtns.forEach(b => {
        if (b !== btn) {
          b.setAttribute('aria-expanded', 'false');
          b.nextElementSibling.classList.remove('open');
        }
      });

      btn.setAttribute('aria-expanded', String(!isOpen));
      answer.classList.toggle('open', !isOpen);
    });
  });

  // --------------------------------------------------------
  // Smooth scroll pour les ancres internes
  // --------------------------------------------------------
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        const navH = parseInt(getComputedStyle(document.documentElement)
          .getPropertyValue('--nav-height')) || 68;
        const top = target.getBoundingClientRect().top + window.scrollY - navH;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });

});
