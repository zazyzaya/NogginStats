function openTab(evt, tabName) {
  var i;
  var x = document.getElementsByClassName("tab");
  for (i = 0; i < x.length; i++) {
    x[i].style.display = "none";
  }
  document.getElementById(tabName).style.display = "block";

  tablinks = document.getElementsByClassName("tablink");
  for (i = 0; i < x.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" w3-green", "");
  }
  evt.currentTarget.className += " w3-green";
  setChildWidths();

  setTimeout(() => {
        const plots = document.querySelectorAll(".js-plotly-plot");
        plots.forEach(p => {
            Plotly.Plots.resize(p);
        });
    }, 50); // delay allows browser to paint the new layout

  sessionStorage.setItem('last_tab', tabName)
}

function revertToTab() {
  var i;
  var x = document.getElementsByClassName("tab");
  for (i = 0; i < x.length; i++) {
    x[i].style.display = "none";
  }
  
  let last_tab = sessionStorage.getItem('last_tab'); 
  if (last_tab == null) {
    last_tab = 'Submit'; 
    sessionStorage.setItem('last_tab', 'Submit'); 
  }

  document.getElementById(last_tab).style.display = "block";

  tablinks = document.getElementsByClassName("tablink");
  for (i = 0; i < x.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" w3-green", "");
  }

  let target = document.getElementById(sessionStorage.getItem('last_tab') +'-tab')
  target.className += " w3-green";
  setChildWidths();

  setTimeout(() => {
        const plots = document.querySelectorAll(".js-plotly-plot");
        plots.forEach(p => {
            Plotly.Plots.resize(p);
        });
    }, 50); // delay allows browser to paint the new layout
}

function toggleSpinner() {
    let elm = document.getElementById('spinner'); 
    if (elm.style.display == 'none') {
        elm.style.display = 'flex'; 
    } else {
        elm.style.display = 'none';
    }
}

function spin() {
  let elm = document.getElementById('spinner'); 
  elm.style.display = 'flex'; 
}

function stopSpin() {
  let elm = document.getElementById('spinner'); 
  elm.style.display = 'none'; 
}

function submit() {
    spin(); 

    let elms = Array.from(document.getElementsByClassName('stat-input'))
    let ret = {}; 

    elms.forEach(element => {
        let id = element.id;
        let val = element.value; 

        if (id.includes("range")) {
            ret[id] = Number(val); 
        }
        else if (id.includes("checked")) {
            ret[id] = element.checked; 
        }
        else {
            ret[id] = val; 
        }
    });
  
    let cur_date = document.getElementById('stat-date').value; 
    sessionStorage.setItem('cached_journal', cur_date); 

    fetch('/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(ret)
    })
    .then( () => { stopSpin(); location.reload() }); 
}

function register() {
    spin(); 

    let elms = Array.from(document.getElementsByClassName('create-input'));
    let ret = {}; 

    elms.forEach(element => {
        let id = element.id; 
        let value = element.value; 
        ret[id] = value; 
    });

    fetch('/register', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify(ret)
    }).then(response => {
        if (response.redirected) {
            // On success, follow the redirect
            stopSpin(); 
            window.location.href = response.url;
        } else {
            response.text().then(text => {
                document.getElementById('register-failed').innerHTML = text;
            });
        }
    }).finally(
      () => { stopSpin(); }
    );
}

function login() {
    spin(); 

    let elms = Array.from(document.getElementsByClassName('login-input'));
    let ret = {}; 

    elms.forEach(element => {
        let id = element.id; 
        let value = element.value; 
        ret[id] = value; 
    });

    fetch('/authorize', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify(ret)
    }).then(response => {
        if (response.redirected) {
            // On success, follow the redirect
            stopSpin(); 
            window.location.href = response.url;
        } else {
            response.text().then(text => {
                document.getElementById('login-failed').innerHTML = text;
            });
        }
    }).finally(
      () => { stopSpin(); }
    )
}

function pwd_reset() {
  spin(); 
  let elms = Array.from(document.getElementsByClassName('pwd_reset_input'));
  let ret = {}; 

  elms.forEach(element => {
      let id = element.id;
      let val = element.value; 
      ret[id] = val 
  });

  fetch('/reset_pwd_submit', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify(ret)
  }).then(response => {
    if (response.redirected) {
        // On success, follow the redirect
        stopSpin();
        window.location.href = response.url;
    } else {
      response.text().then(text => {
        document.getElementById('reset-failed').innerHTML = text;
      });
    }
  }).finally(
    () => { stopSpin(); }
  )
}

function reveal(elm_id) {
    let el = document.getElementById(elm_id)
    
    // TODO animate this 
    if (el.style.display == '') {
        el.style.display = 'table-row';
    }
    else {
        el.style.display = ''
    }
}

function request_repop(val) {
  spin(); 
  if (!val) {
    val = document.getElementById('stat-date').value; 
  }
  
  fetch('/repop', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({'stat-date': val})
  }).then( resp => resp.json() )
    .then( result => {
      for (const key in result) {
        el = document.getElementById(key); 
        
        if (key.includes('checked')) {
          el.checked = result[key];
        } else {
          el.value = result[key]; 
          if (key.includes('range')) {
            document.getElementById(key.replace('-range','-label')).innerHTML = result[key]
          }
        }
      }
    })
    .finally(() => { toggleSpinner(); });
}

// Freeze width 
function setChildWidths() {
    document.querySelectorAll('.journal-entry').forEach(entry => {
        const width = entry.offsetWidth;
        entry.querySelectorAll('.journal-content').forEach(child => {
            child.style.width = width + "px";
        });
    });
}
document.addEventListener("DOMContentLoaded", setChildWidths);

// Make enter submit
function loginListeners() {
    let elms = Array.from(document.getElementsByClassName('login-input'));
    elms.forEach(elm => {
        elm.addEventListener('keydown', function (e) {
            if (e.code == 'Enter') {
                login(); 
            }
        });
    });
}
function createAcctListeners() {
    let elms = Array.from(document.getElementsByClassName('create-input'));
    elms.forEach(elm => {
        elm.addEventListener('keydown', function (e) {
            if (e.code == 'Enter') {
                register(); 
            }
        });
    });
}
function pwdResetListeners() {
    let elms = Array.from(document.getElementsByClassName('pwd_reset_input'));
    elms.forEach(elm => {
        elm.addEventListener('keydown', function (e) {
            if (e.code == 'Enter') {
                pwd_reset(); 
            }
        });
    });
}
document.addEventListener("DOMContentLoaded", loginListeners);
document.addEventListener("DOMContentLoaded", pwdResetListeners);
document.addEventListener("DOMContentLoaded", createAcctListeners);

// After page reloads on submit, dont reset the date 
document.addEventListener('DOMContentLoaded', () => {
  let date = sessionStorage.getItem('cached_journal')
  if (date != 'null') {
    sessionStorage.setItem('cached_journal', null)
    request_repop(date); 
  }
});