odoo.define('yds_trial_balance.custom_fix', function (require) {
    "use strict";
    var core = require('web.core');
    var accountReportsWidget = require('account_reports.account_report')

    var QWeb = core.qweb;
    var _t = core._t;

    var accountReportsWidget = accountReportsWidget.include({
        filter_accounts: function(e) {
            var self = this;
            var query = e.target.value.trim().toLowerCase();
            this.filterOn = false;
            this.$('.o_account_searchable_line').each(function(index, el) {
                var $accountReportLineFoldable = $(el);
                var line_id = $accountReportLineFoldable.find('.o_account_report_line').data('id');
                var $childs = self.$('tr[data-parent-id="'+line_id+'"]');
                if ($accountReportLineFoldable.find('.account_report_line_name').contents().get(0) == undefined) {
                    console.log('here');
                    return;
                }
                var lineText = $accountReportLineFoldable.find('.account_report_line_name')
                    // Only the direct text node, not text situated in other child nodes
                    .contents().get(0).nodeValue
                    .trim();
    
                // The python does this too
                var queryFound = lineText.split(' ').some(function (str) {
                    return str.toLowerCase().startsWith(query);
                });
    
                $accountReportLineFoldable.toggleClass('o_account_reports_filtered_lines', !queryFound);
                $childs.toggleClass('o_account_reports_filtered_lines', !queryFound);
    
                if (!queryFound) {
                    self.filterOn = true;
                }
            });
            if (this.filterOn) {
                this.$('.o_account_reports_level1.total').hide();
            }
            else {
                this.$('.o_account_reports_level1.total').show();
            }
            this.report_options['filter_accounts'] = query;
            this.render_footnotes();
        },
    });

    return accountReportsWidget;

});