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

window.addEventListener('message', async (event) => {
  if (typeof event.data === "string" && event.data.startsWith("Clipboard: ")) {
    try {
      const text = event.data.slice("Clipboard: ".length);
      await navigator.clipboard.writeText(text);
      console.log('Text copied to clipboard');
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  }
});
