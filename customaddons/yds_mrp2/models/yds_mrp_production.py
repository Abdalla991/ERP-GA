from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError
from collections import defaultdict
import ipdb
from datetime import datetime


class YdsMrpProduction(models.Model):
    _inherit = "mrp.production"
    yds_bom_expired = fields.Boolean(
        string="Selected Bill of Material has expired !", readonly=True, Default="False")

    mark_done_restriction = fields.Boolean(
        related="company_id.mo_mark_done_restriction")

    @api.depends('product_id', 'bom_id', 'company_id')
    def _compute_allowed_product_ids(self):

        for production in self:
            if production.bom_id:
                if production.bom_id.yds_start_date and production.bom_id.yds_end_date:
                    start = datetime.strptime(
                        str(production.bom_id.yds_start_date), '%Y-%m-%d')
                    end = datetime.strptime(
                        str(production.bom_id.yds_end_date), '%Y-%m-%d')
                    current = datetime.strptime(
                        str(datetime.now().date()), '%Y-%m-%d')
                    if start <= current and end > current:
                        production.yds_bom_expired = False
                        print(str(production.yds_bom_expired))
                    else:
                        production.yds_bom_expired = True
                        print(str(production.yds_bom_expired))

        return super(YdsMrpProduction, self)._compute_allowed_product_ids()

    # def button_mark_done(self):
    #     for move in self.move_raw_ids:
    #         if move.forecast_availability < move.quantity_done:
    #             raise ValidationError(_('Please check the availability for all components.'))
    #             return
    #     res = super(YdsMrpProduction, self).button_mark_done()
    #     return res

    def button_mark_done(self):
        if self.mark_done_restriction:
            unavailable_components = []
            for move in self.move_raw_ids:
                if move.state not in ['assigned', 'done', 'partially_available']:
                    unavailable_components.append(move.product_id.name)
            if len(unavailable_components) > 0:
                unavail_str = ', '.join(unavailable_components)
                raise ValidationError(
                    _(f'Please check the availability of the following components: {unavail_str}.'))
                return
            res = super(YdsMrpProduction, self).button_mark_done()
            return res
        else:
            res = super(YdsMrpProduction, self).button_mark_done()
            return res
