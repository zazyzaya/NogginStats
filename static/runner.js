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
  document.getElementById(sessionStorage.getItem('last_tab')).style.display = "block";

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

function submit() {
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
  
    fetch('/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(ret)
    }).then( () => { location.reload(); });
}

function pwd_reset() {
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
        window.location.href = response.url;
    } else {
        response.text().then(text => {
              document.getElementById('reset-failed').innerHTML = text;
          });
    }
  })
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