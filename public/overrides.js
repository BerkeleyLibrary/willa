function changeLoginButtonText(buttons) {
  for (var i = 0; i < buttons.length; i++) {
    if (buttons[i].innerText === 'Continue with Cas') {
      buttons[i].innerHTML = 'Login with CalNet SSO';
      }
  }
}

function mutationObserverCallback(mutationsList, observer) {
  var buttons = document.querySelectorAll('button');
  if (buttons.length === 1) {
    changeLoginButtonText(buttons);
    observer.disconnect();
  }
}

if (window.location.href.includes('login')) {
  const observer = new MutationObserver(mutationObserverCallback);
  const config = { childList: true, subtree: true };
  observer.observe(document.body, config);
}
