# -*- coding: utf-8 -*-
import json
import lxml.html
from odoo import _, _lt, models, fields, api
from odoo.tools.misc import format_date
from odoo.tools import config

from collections import defaultdict


class YDSReportPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger"

    @api.model
    def _get_report_line_partner(self, options, partner, initial_balance, debit, credit, balance):
        company_currency = self.env.company.currency_id
        unfold_all = self._context.get(
            'print_mode') and not options.get('unfolded_lines')

        columns = [
            # {'name': self.format_value(initial_balance), 'class': 'number'},
            {'name': self.format_value(debit), 'class': 'number'},
            {'name': self.format_value(credit), 'class': 'number'},
        ]
        if not options.get("print", False):
            if self.user_has_groups('base.group_multi_currency'):
                columns.append({'name': ''})
        columns.append({'name': self.format_value(balance), 'class': 'number'})

        return {
            'id': 'partner_%s' % (partner.id if partner else 0),
            'partner_id': partner.id if partner else None,
            'name': partner is not None and (partner.name or '')[:128] or _('Unknown Partner'),
            'columns': columns,
            'level': 2,
            'trust': partner.trust if partner else None,
            'unfoldable': not company_currency.is_zero(debit) or not company_currency.is_zero(credit),
            'unfolded': 'partner_%s' % (partner.id if partner else 0) in options['unfolded_lines'] or unfold_all,
            'colspan': 2 if options.get("print", False) else 6,
        }

    @api.model
    def _get_report_line_move_line(self, options, partner, aml, cumulated_init_balance, cumulated_balance):
        if aml['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move'

        date_maturity = aml['date_maturity'] and format_date(
            self.env, fields.Date.from_string(aml['date_maturity']))
        columns = [
            {'name': aml['journal_code']},
            {'name': aml['account_code']},
            {'name': self._format_aml_name(
                aml['name'], aml['ref'], aml['move_name'])},
            {'name': date_maturity or '', 'class': 'date'},
            {'name': aml['matching_number'] or ''},
            # {'name': self.format_value(
            #     cumulated_init_balance), 'class': 'number'},
            {'name': self.format_value(
                aml['debit'], blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(
                aml['credit'], blank_if_zero=True), 'class': 'number'},
        ]

        if options.get("print", False):
            columns = [
                # {'name': aml['journal_code']},
                # {'name': aml['account_code']},
                {'name': self._format_aml_name(
                    aml['name'], aml['ref'], aml['move_name'])},
                # {'name': date_maturity or '', 'class': 'date'},
                # {'name': aml['matching_number'] or ''},
                # {'name': self.format_value(
                #     cumulated_init_balance), 'class': 'number'},
                {'name': self.format_value(
                    aml['debit'], blank_if_zero=True), 'class': 'number'},
                {'name': self.format_value(
                    aml['credit'], blank_if_zero=True), 'class': 'number'},
            ]

        if not options.get("print", False):
            if self.user_has_groups('base.group_multi_currency'):
                if aml['currency_id']:
                    currency = self.env['res.currency'].browse(
                        aml['currency_id'])
                    formatted_amount = self.format_value(
                        aml['amount_currency'], currency=currency, blank_if_zero=True)
                    columns.append(
                        {'name': formatted_amount, 'class': 'number'})
                else:
                    columns.append({'name': ''})
        columns.append({'name': self.format_value(
            cumulated_balance), 'class': 'number'})

        res = {
            'id': aml['id'],
            'parent_id': 'partner_%s' % (partner.id if partner else 0),
            'name': format_date(self.env, aml['date']),
            # do not format as date to prevent text centering
            'class': 'text' + aml.get('class', ''),
            'columns': columns,
            'caret_options': caret_type,
            'level': 2,
        }
        # change the format of Account column for vendor payments fields(CSH1)
        # old format line_name, move_ref, move_name
        # new format move_ref
        # if res['columns'][0]['name'] != "NINV" and res['columns'][0]['name'] != "BILL":
        #     res['columns'][2]['name'] = self._format_aml_name(
        #         '/', aml['ref'], '/')
        return res

    @api.model
    def _get_report_line_load_more(self, options, partner, offset, remaining, progress):
        return {
            'id': 'loadmore_%s' % (partner.id if partner else 0),
            'offset': offset,
            'progress': progress,
            'remaining': remaining,
            'class': 'o_account_reports_load_more text-center',
            'parent_id': 'partner_%s' % (partner.id if partner else 0),
            'name': _('Load more... (%s remaining)', remaining),
            # YDS: decrease colspan by 1
            'colspan': 1 if options.get("print", False) else (9 if self.user_has_groups('base.group_multi_currency') else 8),
            'columns': [{}],
        }

    @api.model
    def _get_report_line_total(self, options, initial_balance, debit, credit, balance):
        columns = [
            # {'name': self.format_value(initial_balance), 'class': 'number'},
            {'name': self.format_value(debit), 'class': 'number'},
            {'name': self.format_value(credit), 'class': 'number'},
        ]
        if not options.get("print", False):
            if self.user_has_groups('base.group_multi_currency'):
                columns.append({'name': ''})
        columns.append({'name': self.format_value(balance), 'class': 'number'})
        return {
            'id': 'partner_ledger_total_%s' % self.env.company.id,
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': columns,
            'colspan': 2 if options.get("print", False) else 6,
        }

    def _get_columns_name(self, options):
        columns = [
            {},
            {'name': _('JRNL')},
            {'name': _('Account')},
            {'name': _('Ref')},
            {'name': _('Due Date'), 'class': 'date'},
            {'name': _('Matching Number')},
            # {'name': _('Initial Balance'), 'class': 'number'},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
        ]
        if options.get("print", False):
            columns = [
                {},
                # {'name': _('JRNL')},
                # {'name': _('Account')},
                {'name': _('Ref')},
                # {'name': _('Due Date'), 'class': 'date'},
                # {'name': _('Matching Number')},
                # {'name': _('Initial Balance'), 'class': 'number'},
                {'name': _('Debit'), 'class': 'number'},
                {'name': _('Credit'), 'class': 'number'},
            ]
        if not options.get("print", False):
            if self.user_has_groups('base.group_multi_currency'):
                columns.append(
                    {'name': _('Amount Currency'), 'class': 'number'})

        columns.append({'name': _('Balance'), 'class': 'number'})
        return columns

    def print_pdf(self, options):
        options["print"] = True
        return {
            'type': 'ir_actions_account_report_download',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options),
                     'output_format': 'pdf',
                     'financial_id': self.env.context.get('id'),
                     }
        }

    def get_pdf(self, options, minimal_layout=True):
        # Overwrite to make landscape always true when printing
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        body = self.env['ir.ui.view']._render_template(
            "account_reports.print_template",
            values=dict(rcontext),
        )
        body_html = self.with_context(print_mode=True).get_html(options)

        body = body.replace(b'<body class="o_account_reports_body_print">',
                            b'<body class="o_account_reports_body_print">' + body_html)
        if minimal_layout:
            header = ''
            footer = self.env['ir.actions.report']._render_template(
                "web.internal_layout", values=rcontext)
            spec_paperformat_args = {
                'data-report-margin-top': 10, 'data-report-header-spacing': 10}
            footer = self.env['ir.actions.report']._render_template(
                "web.minimal_layout", values=dict(rcontext, subst=True, body=footer))
        else:
            rcontext.update({
                'css': '',
                'o': self.env.user,
                'res_company': self.env.company,
            })
            header = self.env['ir.actions.report']._render_template(
                "web.external_layout", values=rcontext)
            # Ensure that headers and footer are correctly encoded
            header = header.decode('utf-8')
            spec_paperformat_args = {}
            # Default header and footer in case the user customized web.external_layout and removed the header/footer
            headers = header.encode()
            footer = b''
            # parse header as new header contains header, body and footer
            try:
                root = lxml.html.fromstring(header)
                match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

                for node in root.xpath(match_klass.format('header')):
                    headers = lxml.html.tostring(node)
                    headers = self.env['ir.actions.report']._render_template(
                        "web.minimal_layout", values=dict(rcontext, subst=True, body=headers))

                for node in root.xpath(match_klass.format('footer')):
                    footer = lxml.html.tostring(node)
                    footer = self.env['ir.actions.report']._render_template(
                        "web.minimal_layout", values=dict(rcontext, subst=True, body=footer))

            except lxml.etree.XMLSyntaxError:
                headers = header.encode()
                footer = b''
            header = headers

        landscape = False
        if len(self.with_context(print_mode=True).get_header(options)[-1]) > 5:
            landscape = True

        # Make landscape true when printing
        if options.get("print", False):
            landscape = True

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header, footer=footer,
            landscape=landscape,
            specific_paperformat_args=spec_paperformat_args
        )
