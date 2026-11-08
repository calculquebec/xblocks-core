// Tests require that addAjaxPrefix is called
// before the tests are run.
import './ajax_prefix.js';

window.AjaxPrefix.addAjaxPrefix($, function() {
    return '';
});
