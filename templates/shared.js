// Shared JS for all Travel Planner pages
// Lightbox, broken image handler

// Hide broken images globally
document.addEventListener('error', function(e){
  if(e.target.tagName === 'IMG'){
    e.target.classList.add('broken');
  }
}, true);

// ═══ LIGHTBOX ═══
(function(){
  var images = [];
  var currentIdx = 0;
  var lb = null;
  var lbImg = null;
  var lbCounter = null;

  function buildLightbox() {
    lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.innerHTML =
      '<button class="close-btn">&times;</button>' +
      '<div class="lbox-img-wrap">' +
        '<div class="lbox-left"><span class="lbox-arrow">&#8249;</span></div>' +
        '<img src="" alt="">' +
        '<div class="lbox-right"><span class="lbox-arrow">&#8250;</span></div>' +
      '</div>' +
      '<div class="counter"></div>';
    document.body.appendChild(lb);
    lbImg = lb.querySelector('img');
    lbCounter = lb.querySelector('.counter');

    lb.querySelector('.close-btn').addEventListener('click', close);
    lb.querySelector('.lbox-left').addEventListener('click', function(e){ e.stopPropagation(); prev(); });
    lb.querySelector('.lbox-right').addEventListener('click', function(e){ e.stopPropagation(); next(); });
    lb.addEventListener('click', function(e){ if(e.target === lb) close(); });
    document.addEventListener('keydown', function(e){
      if(!lb.classList.contains('open')) return;
      if(e.key === 'Escape') close();
      if(e.key === 'ArrowLeft') prev();
      if(e.key === 'ArrowRight') next();
    });
  }

  function collectImages() {
    images = [];
    var all = document.querySelectorAll('.slider-track img, .food-img, .food-thumbs img, .hero-placeholder, .dining-card img, .lightbox-clickable');
    all.forEach(function(img, i){
      if(img.naturalWidth > 0 || img.complete) {
        images.push(img);
        img.style.cursor = 'pointer';
        img.setAttribute('data-lb-idx', images.length - 1);
        if(!img.hasLbListener) {
          img.addEventListener('click', function(e){
            e.stopPropagation();
            open(img.getAttribute('data-lb-idx'));
          });
          img.hasLbListener = true;
        }
      }
    });
  }

  function open(idx) {
    if(!lb) buildLightbox();
    collectImages();
    idx = parseInt(idx);
    if(idx < 0) idx = images.length - 1;
    if(idx >= images.length) idx = 0;
    currentIdx = idx;
    var src = images[currentIdx].src || images[currentIdx].getAttribute('src');
    // strip Unsplash size params for full resolution
    src = src.replace(/[?&]w=\d+/g, '').replace(/[?&]h=\d+/g, '').replace(/[?&]fit=crop/g, '');
    if(src.indexOf('?') === -1) src += '?w=1400'; else src += '&w=1400';
    lbImg.src = src;
    lbCounter.textContent = (currentIdx + 1) + ' / ' + images.length;
    lb.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    lb.classList.remove('open');
    document.body.style.overflow = '';
  }

  function next() { open(currentIdx + 1); }
  function prev() { open(currentIdx - 1); }

  window.addEventListener('load', function(){ collectImages(); });
})();
