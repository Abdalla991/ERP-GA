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
        if res['columns'][0]['name'] == "CSH1":
            res['columns'][2]['name'] = self._format_aml_name(
                False, aml['ref'], False)
        return res
