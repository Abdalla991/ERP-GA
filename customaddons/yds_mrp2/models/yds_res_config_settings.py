from odoo import models, fields, api, exceptions, _


class Company(models.Model):
    _inherit = "res.company"
    mo_mark_done_restriction = fields.Boolean(
        string="Mark Done Restriction", default=True)

    qty_in_store_relation = fields.Many2one(
        'stock.location', string='Store Location')


class YDSMrpSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mo_mark_done_restriction = fields.Boolean(
        string="Activate Mark Done Restriction", related='company_id.mo_mark_done_restriction', readonly=False)

    qty_in_store_relation = fields.Many2one(
        'stock.location', string='Store Location')

    qty_in_store_id = fields.Integer(related='qty_in_store_relation.id')

    @api.model
    def get_values(self):
        res = super(YDSMrpSettings, self).get_values()
        res.update(
            qty_in_store_relation=int(self.env['ir.config_parameter'].sudo().get_param(
                'yds_mrp2.qty_in_store_id', default=False))
        )
        return res

    def set_values(self):
        super(YDSMrpSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()

        field1 = self.qty_in_store_id
        param.set_param(
            'yds_mrp2.qty_in_store_id', field1)
