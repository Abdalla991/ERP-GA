# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models



class YDSSaleReport(models.Model):
    _inherit = 'sale.report'

    margin = fields.Float('Margin')

    #Fix margin value in reports
    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['margin'] = ", SUM(l.yds_margin / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS margin"
        return super(YDSSaleReport, self)._query(with_clause, fields, groupby, from_clause)