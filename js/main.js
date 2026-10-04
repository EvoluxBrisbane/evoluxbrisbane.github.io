/* EVOLUX — progressive enhancement only. Site is fully usable with JS disabled. */
(function () {
  'use strict';

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- sticky header ---- */
  var hdr = document.querySelector('.hdr');
  if (hdr) {
    var onScroll = function () {
      hdr.classList.toggle('is-stuck', window.scrollY > 24);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---- mobile drawer ---- */
  var burger = document.querySelector('.burger');
  var mobnav = document.querySelector('.mobnav');
  if (burger && mobnav) {
    var setOpen = function (open) {
      burger.setAttribute('aria-expanded', String(open));
      burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      mobnav.classList.toggle('is-open', open);
      mobnav.setAttribute('aria-hidden', String(!open));
      document.body.classList.toggle('is-locked', open);
    };
    burger.addEventListener('click', function () {
      setOpen(burger.getAttribute('aria-expanded') !== 'true');
    });
    mobnav.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && burger.getAttribute('aria-expanded') === 'true') {
        setOpen(false);
        burger.focus();
      }
    });
    window.addEventListener('resize', function () {
      if (window.innerWidth > 980) setOpen(false);
    });
    /* keep the drawer out of the tab order while closed */
    mobnav.setAttribute('aria-hidden', 'true');
    var sync = function () {
      var open = mobnav.classList.contains('is-open');
      Array.prototype.forEach.call(mobnav.querySelectorAll('a'), function (a) {
        if (open) a.removeAttribute('tabindex');
        else a.setAttribute('tabindex', '-1');
      });
    };
    new MutationObserver(sync).observe(mobnav, { attributes: true, attributeFilter: ['class'] });
    sync();
  }

  /* ---- scroll reveal ---- */
  var items = document.querySelectorAll('[data-reveal]');
  if (items.length) {
    if (reduce || !('IntersectionObserver' in window)) {
      Array.prototype.forEach.call(items, function (el) { el.classList.add('is-in'); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          en.target.classList.add('is-in');
          io.unobserve(en.target);
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
      Array.prototype.forEach.call(items, function (el) { io.observe(el); });
      /* safety: never leave content hidden */
      window.setTimeout(function () {
        Array.prototype.forEach.call(items, function (el) { el.classList.add('is-in'); });
      }, 2600);
    }
  }

  /* ---- mark current page in nav ---- */
  var here = location.pathname.split('/').pop() || 'index.html';
  Array.prototype.forEach.call(document.querySelectorAll('.nav__list a, .mobnav__list a'), function (a) {
    var href = a.getAttribute('href');
    if (!href) return;
    var target = href.split('#')[0];
    if (target === here || (here === '' && target === 'index.html')) {
      a.setAttribute('aria-current', 'page');
    }
  });

  /* ---- footer year ---- */
  Array.prototype.forEach.call(document.querySelectorAll('[data-year]'), function (el) {
    el.textContent = String(new Date().getFullYear());
  });
})();
