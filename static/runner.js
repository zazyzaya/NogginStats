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
    })
    .then(response => response.json())
    .then(result => {
        console.log('Success:', result);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}