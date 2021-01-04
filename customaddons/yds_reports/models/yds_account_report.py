# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class YDSAccountMoveLine(models.Model):
    _inherit = "account.move.line"
    yds_analytic_group_id = fields.Many2one('account.analytic.group',string='Analytic Group', readonly=True, store=True,related='analytic_account_id.group_id')
    
    #Add yds_analytic_group_id to Filters and Group By  (For reporting purposes)
    @api.model
    def fields_get(self, fields=None):
        #Fields to be added in Filters/Group By
        show = ['yds_analytic_group_id']
        res = super(YDSAccountMoveLine, self).fields_get()
        #True = add fields, False = Remove fields
        for field in show:
            res[field]['selectable'] = True
            res[field]['sortable'] = True
        return res
