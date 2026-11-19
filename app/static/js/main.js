(function () {
  var csrf = document.querySelector('meta[name="csrf-token"]').content;
  var isAuth = document.body.dataset.auth === '1';

  // Mobile menu
  var toggle = document.getElementById('navToggle');
  if (toggle) toggle.addEventListener('click', function () {
    document.getElementById('menu').classList.toggle('open');
  });

  // Favorite (heart) buttons
  document.querySelectorAll('.fav-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!isAuth) { window.location = document.body.dataset.loginUrl; return; }
      fetch('/ad/' + btn.dataset.id + '/favorite', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf }
      }).then(function (r) { return r.json(); })
        .then(function (d) { btn.classList.toggle('active', d.saved); })
        .catch(function () { alert('Could not save. Please try again.'); });
    });
  });

  // Gallery thumbnails
  var main = document.getElementById('mainImg');
  document.querySelectorAll('.thumb').forEach(function (t, i) {
    if (i === 0) t.classList.add('on');
    t.addEventListener('click', function () {
      main.src = t.src;
      document.querySelectorAll('.thumb').forEach(function (x) { x.classList.remove('on'); });
      t.classList.add('on');
    });
  });

  // Photo preview + limit on the ad form
  var input = document.getElementById('images');
  var preview = document.getElementById('preview');
  if (input && preview) {
    input.addEventListener('change', function () {
      preview.innerHTML = '';
      if (input.files.length > 5) {
        alert('You can upload at most 5 photos.');
        input.value = '';
        return;
      }
      Array.prototype.forEach.call(input.files, function (file) {
        var img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        preview.appendChild(img);
      });
    });
  }
})();
