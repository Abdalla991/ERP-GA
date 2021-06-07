from odoo import models, fields, api, exceptions, _


class Company(models.Model):
    _inherit = "res.company"
    mo_mark_done_restriction = fields.Boolean(
        string="Mark Done Restriction", default=True)


class YDSMrpSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mo_mark_done_restriction = fields.Boolean(
        string="Activate Mark Done Restriction", related='company_id.mo_mark_done_restriction', readonly=False)
