# -*- coding: utf-8 -*-

from odoo import models, fields, api


# class MrpProductionSchedule(models.Model):
#     _inherit = 'mrp.production.schedule'

#     is_replenished = fields.Boolean(default=True)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _compute_state(self):
        super(MrpProduction, self)._compute_state()
        if self.origin == "MPS":
            self.state = "draft"
