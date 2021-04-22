# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


# class MrpProductionSchedule(models.Model):
#     _inherit = 'mrp.production.schedule'

#     is_replenished = fields.Boolean(default=True)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.depends(
        'move_raw_ids.state', 'move_raw_ids.quantity_done', 'move_finished_ids.state',
        'workorder_ids', 'workorder_ids.state', 'product_qty', 'qty_producing')
    def _compute_state(self):
        super(MrpProduction, self)._compute_state()
        for production in self:
            if production.origin == "MPS" and (timedelta(seconds=1) > datetime.now() - production.create_date):
                production.state = "draft"
                production.mps_on_create = False

