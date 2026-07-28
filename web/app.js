var vocab = {};
var vocabSet = null;

(function init() {
  loadVocab().then(function() {
    console.log('[init] vocab', Object.keys(vocab).length);
    render().then(function() {
      setupUI();
    });
  }).catch(function(e) {
    console.error('[init]', e);
    var m = document.getElementById('main');
    if (m) m.innerHTML = '<div class="empty"><h3>加载失败</h3><p>刷新重试</p></div>';
  });
})();

function loadVocab() {
  return fetch('/api/vocab').then(function(r) { return r.json(); }).then(function(data) {
    vocab = data || {};
    vocabSet = new Set(Object.keys(vocab).map(function(k) { return k.toLowerCase(); }));
  }).catch(function(e) {
    console.error('vocab', e);
    vocab = {};
    vocabSet = new Set();
  });
}

function countVocab(text) {
  if (!vocabSet || vocabSet.size === 0) return 0;
  var ws = (text || '').match(/[a-zA-Z]+/g) || [];
  var seen = {};
  var n = 0;
  for (var i = 0; i < ws.length; i++) {
    var lo = ws[i].toLowerCase();
    if (vocabSet.has(lo) && !seen[lo]) {
      seen[lo] = true;
      n++;
    }
  }
  return n;
}

function esc(s) {
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function highlight(html) {
  if (!vocabSet || vocabSet.size === 0) return html;
  return html.replace(/[a-zA-Z]+/g, function(m) {
    var lo = m.toLowerCase();
    if (vocabSet.has(lo)) {
      return '<span class="vocab" data-word="' + lo + '">' + m + '</span>';
    }
    return m;
  });
}

function buildBilingual(paragraphs) {
  if (!paragraphs || !paragraphs.length) return '';
  var rows = '';
  for (var p = 0; p < paragraphs.length; p++) {
    var para = paragraphs[p];
    rows += '<div class="para-block">';
    for (var i = 0; i < para.length; i++) {
      var e = para[i].en ? highlight(esc(para[i].en)) : '';
      var z = para[i].zh ? esc(para[i].zh) : '';
      rows += '<div class="sentence-row"><div class="sentence-en">' + e + '</div><div class="sentence-zh">' + z + '</div></div>';
    }
    rows += '</div>';
  }
  return rows;
}

function buildArticle(a, i) {
  var paragraphs = a.paragraphs || [];
  var vc = 0;
  var allEn = '';
  for (var p = 0; p < paragraphs.length; p++) {
    for (var s = 0; s < paragraphs[p].length; s++) {
      allEn += ' ' + (paragraphs[p][s].en || '');
    }
  }
  vc = countVocab(allEn);
  var zhTitle = a.title_zh || '';
  return (
    '<section class="art" id="art' + i + '">' +
    '<div class="art-head">' +
    '<h2>' + (zhTitle ? esc(zhTitle) : esc(a.title)) + '</h2>' +
    (zhTitle ? '<h3>' + esc(a.title) + '</h3>' : '') +
    '<div class="art-meta">' +
    '<a class="tag-src" href="' + (a.url || '#') + '" target="_blank" rel="noopener">' + esc(a.source_name) + '</a>' +
'<span>' + (a.word_count || 0) + ' 词</span>' +
'<span class="tag-voc">' + vc + ' 考研词</span>' +
    '</div></div>' +
    '<div class="art-body">' +
    '<div class="art-col-label"><span>English</span><span>中文译文</span></div>' +
    buildBilingual(paragraphs) +
    '</div></section>'
  );
}

function buildSide(a, i) {
  var title = a.title_zh || a.title;
  return (
    '<button class="side-item' + (i === 0 ? ' on' : '') + '" data-idx="' + i + '">' +
    '<span class="side-item-num">' + (i + 1) + '</span>' +
    esc(title) +
    '</button>'
  );
}

function safeGet(id) {
  return document.getElementById(id);
}

function showArticles(arts) {
  console.log('[show]', arts.length);
  var el;
  el = safeGet('loading'); if (el) el.hidden = true;
  el = safeGet('empty'); if (el) el.hidden = true;
  safeGet('main').innerHTML = '';

  var mainHTML = '';
  var sideHTML = '';
  var totalVocab = 0;
  var totalWords = 0;

  for (var i = 0; i < arts.length; i++) {
    mainHTML += buildArticle(arts[i], i);
    sideHTML += buildSide(arts[i], i);
    totalWords += (arts[i].word_count || 0);
  }
  // sum vocab from all EN text in bilingual paragraphs
  for (var i = 0; i < arts.length; i++) {
    var paras = arts[i].paragraphs || [];
    var enText = '';
    for (var p = 0; p < paras.length; p++) {
      for (var s = 0; s < paras[p].length; s++) {
        enText += ' ' + (paras[p][s].en || '');
      }
    }
    totalVocab += countVocab(enText);
  }

  var m = safeGet('main'); if (m) m.innerHTML = mainHTML;
  var sn = safeGet('sideNav'); if (sn) sn.innerHTML = sideHTML;
  var sc = safeGet('sideCount'); if (sc) sc.textContent = arts.length;
  var dh = safeGet('headerDate'); if (dh) dh.textContent = (arts[0] && arts[0]._date) || '';

  var sv = safeGet('stVocab'); if (sv) sv.textContent = totalVocab;
  var sw = safeGet('stWords'); if (sw) sw.textContent = totalWords.toLocaleString();
  var sa = safeGet('stArts'); if (sa) sa.textContent = arts.length;
  var sb = safeGet('statbar'); if (sb) sb.hidden = false;

  bindSide();
  bindVocab();
}

function bindSide() {
  var items = document.querySelectorAll('.side-item');
  for (var i = 0; i < items.length; i++) {
    (function(item) {
      item.addEventListener('click', function() {
        var art = document.getElementById('art' + item.dataset.idx);
        if (art) {
          var h2 = art.querySelector('h2');
          if (h2) h2.scrollIntoView({ behavior: 'smooth', block: 'start' });
          else art.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    })(items[i]);
  }
}

function bindVocab() {
  var pop = safeGet('vocabPop');
  if (!pop) return;
  var vocabs = document.querySelectorAll('.vocab');
  for (var i = 0; i < vocabs.length; i++) {
    (function(v) {
      v.addEventListener('mouseenter', function() {
        var w = v.dataset.word;
        var defs = (w && vocab[w]) || [];
        if (!Array.isArray(defs) || defs.length === 0) {
          pop.innerHTML = '';
          pop.hidden = false;
          return;
        }
        var text = defs.join('; ');
        text = text.replace(/(\S)\s+(?=(vt\.|vi\.|adj\.|adv\.|n\.|prep\.|conj\.|pron\.|int\.|art\.|num\.|aux\.|v\.)\s)/g, '$1<br>');
        pop.innerHTML = '<span>' + text + '</span>';
        pop.hidden = false;
      });
      v.addEventListener('mousemove', function(e) {
        var x = Math.min(e.clientX + 12, window.innerWidth - pop.offsetWidth - 10);
        var y = e.clientY - pop.offsetHeight - 10;
        pop.style.left = x + 'px';
        pop.style.top = y + 'px';
      });
      v.addEventListener('mouseleave', function() { pop.hidden = true; });
    })(vocabs[i]);
  }
}

function onScroll() {
  var arts = document.querySelectorAll('.art');
  var cur = '0';
  for (var i = 0; i < arts.length; i++) {
    if (arts[i].getBoundingClientRect().top < 120) cur = arts[i].id.replace('art', '');
  }
  var items = document.querySelectorAll('.side-item');
  for (var i = 0; i < items.length; i++) {
    items[i].classList.toggle('on', items[i].dataset.idx === cur);
  }
  var docH = document.documentElement.scrollHeight - window.innerHeight;
  var pct = docH > 0 ? Math.min(100, (window.scrollY / docH) * 100) : 0;
  var p = safeGet('progress');
  if (p) p.style.width = pct + '%';
}

function setupUI() {
  var sel = safeGet('dateSelect');
  if (sel) sel.addEventListener('change', render);

  var btns = document.querySelectorAll('.size-ctl button');
  for (var i = 0; i < btns.length; i++) {
    btns[i].addEventListener('click', function() {
      var siblings = this.parentNode.querySelectorAll('button');
      for (var j = 0; j < siblings.length; j++) siblings[j].classList.remove('on');
      this.classList.add('on');
      document.documentElement.style.setProperty('--fs', this.dataset.s + 'px');
    });
  }
  window.addEventListener('scroll', onScroll);
}

function render() {
  console.log('[render] start');
  var dateInput = safeGet('dateSelect');
  var date = (dateInput && dateInput.value) || new Date().toISOString().slice(0, 10);

  var ld = safeGet('loading');
  if (ld) ld.hidden = false;
  var emp = safeGet('empty');
  if (emp) emp.hidden = true;
  var main = safeGet('main');
  if (main) main.innerHTML = '';
  var sb = safeGet('statbar');
  if (sb) sb.hidden = true;

  return fetch('/api/dates').then(function(r) { return r.json(); }).then(function(dd) {
    var availableDates = dd.dates || [];
    console.log('[render] dates:', availableDates);

    if (availableDates.length > 0 && availableDates.indexOf(date) === -1) {
      date = availableDates[0];
      if (dateInput) dateInput.value = date;
    }
    console.log('[render] using date:', date);

    return fetch('/api/articles?date=' + date).then(function(r) { return r.json(); }).then(function(ad) {
      console.log('[render] response:', ad.total);
      if (ad.error || !ad.articles || ad.articles.length === 0) {
        if (ld) ld.hidden = true;
        if (emp) emp.hidden = false;
        return;
      }
      for (var i = 0; i < ad.articles.length; i++) {
        ad.articles[i]._date = date;
      }
      showArticles(ad.articles);

      // populate date select (只显示有文章的日期)
      if (dateInput) {
        dateInput.innerHTML = '';
        for (var j = 0; j < availableDates.length; j++) {
          var opt = document.createElement('option');
          opt.value = availableDates[j];
          opt.textContent = availableDates[j];
          dateInput.appendChild(opt);
        }
        dateInput.value = date;
      }
      console.log('[render] done');
    });
  }).catch(function(e) {
    console.error('[render]', e);
    if (ld) ld.hidden = true;
    if (emp) emp.hidden = false;
  });
}
