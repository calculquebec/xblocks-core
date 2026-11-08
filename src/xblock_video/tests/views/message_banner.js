import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';
import HtmlUtils from 'edx-ui-toolkit/js/utils/html-utils';

// Mock message banner template for testing
const messageBannerTemplate = `
    <div class="message-banner">
        <div class="message-content">
            <%- message %>
        </div>
        <% if (!hideCloseBtn) { %>
            <button class="close-btn">×</button>
        <% } %>
    </div>
`;

const MessageBannerView = Backbone.View.extend({

    events: {
        'click .close-btn': 'closeBanner'
    },

    closeBanner: function(event) {
        sessionStorage.setItem('isBannerClosed', true);
        this.hideMessage();
    },

    initialize: function(options) {
        if (_.isUndefined(options)) {
            options = {};
        }
        this.options = _.defaults(options, {
            urgency: 'high',
            type: '',
            hideCloseBtn: true,
            isRecoveryEmailMsg: false,
            isLearnerPortalEnabled: false
        });
    },

    render: function() {
        if (_.isUndefined(this.message) || _.isNull(this.message)) {
            this.$el.html('');
        } else {
            this.$el.html(_.template(messageBannerTemplate)(_.extend(this.options, { // xss-lint: disable=javascript-jquery-html
                message: this.message,
                HtmlUtils: HtmlUtils
            })));
        }
        return this;
    },

    showMessage: function(message) {
        this.message = message;
        if (sessionStorage.getItem('isBannerClosed') == null) {
            this.render();
        }
    },

    hideMessage: function() {
        this.message = null;
        this.render();
    }
});

export default MessageBannerView;
