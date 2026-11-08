Runtime = {
  handlerUrl: (element, endpoint_name) => {
    logResult('handlerUrl-call', {endpoint_name, element: element.outerHTML});
    return `/api/${endpoint_name}/`
  },
}

function logResult (testId, value) {
  // Result must be JSON serializable or this will fail.
  const result = JSON.stringify(value)
  const output = document.createElement('div')
  output.setAttribute('data-testid', testId)
  output.setAttribute('class', 'log-entry')
  output.innerText = result
  document.body.appendChild(output)
}

$.ajax({
  beforeSend(jqXHR, settings) {
    const result = [...arguments]
    logResult('post-call', result)
  }
})
