# -*- coding: utf-8 -*-

from odoo import _, _lt, models, fields, api
from odoo.tools.misc import format_date
from datetime import timedelta

from collections import defaultdict


class YDSReportPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger"

    def _get_report_line_move_line(self, options, partner, aml, cumulated_init_balance, cumulated_balance):
        # OVERRIDE to change the format of Account column for vendor payments fields(CSH1)
        # old format line_name, move_ref, move_name
        # new format move_ref
        res = super(YDSReportPartnerLedger, self)._get_report_line_move_line(
            options, partner, aml, cumulated_init_balance, cumulated_balance)
        if res['columns'][0]['name'] != "NINV" and res['columns'][0]['name'] != "BILL":
            res['columns'][2]['name'] = self._format_aml_name(
                '/', aml['ref'], '/')
        return res

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
            'colspan': 6,
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
        if self.user_has_groups('base.group_multi_currency'):
            if aml['currency_id']:
                currency = self.env['res.currency'].browse(aml['currency_id'])
                formatted_amount = self.format_value(
                    aml['amount_currency'], currency=currency, blank_if_zero=True)
                columns.append({'name': formatted_amount, 'class': 'number'})
            else:
                columns.append({'name': ''})
        columns.append({'name': self.format_value(
            cumulated_balance), 'class': 'number'})
        return {
            'id': aml['id'],
            'parent_id': 'partner_%s' % (partner.id if partner else 0),
            'name': format_date(self.env, aml['date']),
            # do not format as date to prevent text centering
            'class': 'text' + aml.get('class', ''),
            'columns': columns,
            'caret_options': caret_type,
            'level': 2,
        }

    @api.model
    def _get_report_line_total(self, options, initial_balance, debit, credit, balance):
        columns = [
            # {'name': self.format_value(initial_balance), 'class': 'number'},
            {'name': self.format_value(debit), 'class': 'number'},
            {'name': self.format_value(credit), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': ''})
        columns.append({'name': self.format_value(balance), 'class': 'number'})
        return {
            'id': 'partner_ledger_total_%s' % self.env.company.id,
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': columns,
            'colspan': 6,
        }

    @api.model
    def _get_partner_ledger_lines(self, options, line_id=None):
        ''' Get lines for the whole report or for a specific line.
        :param options: The report options.
        :return:        A list of lines, each one represented by a dictionary.
        '''
        lines = []
        unfold_all = options.get('unfold_all') or (
            self._context.get('print_mode') and not options['unfolded_lines'])

        expanded_partner = line_id and self.env['res.partner'].browse(
            int(line_id[8:]))
        partners_results = self._do_query(
            options, expanded_partner=expanded_partner)

        total_initial_balance = total_debit = total_credit = total_balance = 0.0
        i = 0
        for partner, results in partners_results:
            is_unfolded = 'partner_%s' % (
                partner.id if partner else 0) in options['unfolded_lines']

            # res.partner record line.
            partner_sum = results.get('sum', {})
            partner_init_bal = results.get('initial_balance', {})

            initial_balance = partner_init_bal.get('balance', 0.0)
            debit = partner_sum.get('debit', 0.0)
            credit = partner_sum.get('credit', 0.0)
            balance = initial_balance + partner_sum.get('balance', 0.0)

            lines.append(self._get_report_line_partner(
                options, partner, initial_balance, debit, credit, balance))
            total_initial_balance += initial_balance
            total_debit += debit
            total_credit += credit
            total_balance += balance

            if unfold_all or is_unfolded:
                cumulated_balance = initial_balance

                # account.move.line record lines.
                amls = results.get('lines', [])

                load_more_remaining = len(amls)
                load_more_counter = self._context.get(
                    'print_mode') and load_more_remaining or self.MAX_LINES

                for aml in amls:
                    # Don't show more line than load_more_counter.
                    if load_more_counter == 0:
                        break

                    cumulated_init_balance = cumulated_balance
                    cumulated_balance += aml['balance']
                    lines.append(self._get_report_line_move_line(
                        options, partner, aml, cumulated_init_balance, cumulated_balance))
                    load_more_remaining -= 1
                    load_more_counter -= 1

                if load_more_remaining > 0:
                    # Load more line.
                    lines.append(self._get_report_line_load_more(
                        options,
                        partner,
                        self.MAX_LINES,
                        load_more_remaining,
                        cumulated_balance,
                    ))

        if not line_id:
            # Report total line.
            lines.append(self._get_report_line_total(
                options,
                total_initial_balance,
                total_debit,
                total_credit,
                total_balance
            ))
        return lines

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
            'colspan': 9 if self.user_has_groups('base.group_multi_currency') else 8,
            'columns': [{}],
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

        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': _('Amount Currency'), 'class': 'number'})

        columns.append({'name': _('Balance'), 'class': 'number'})
        return columns
