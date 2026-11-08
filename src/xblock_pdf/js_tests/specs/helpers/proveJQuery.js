(function () {
  const id = setInterval(() => {
    try {
      // Invocation should throw if jQuery is not yet loaded.
      $('body');
      const tag = document.createElement('div')
      tag.setAttribute('data-testid', 'jquery-loaded')
      document.body.appendChild(tag)
      clearInterval(id)
    } catch {}
  }, 50)
})()
