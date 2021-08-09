from odoo import models, fields, api, exceptions, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    check_return_journal = fields.Many2one(
        'account.journal', string="Return Journal")
    check_return_journal_id = fields.Integer(related='check_return_journal.id')


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            check_return_journal=int(self.env['ir.config_parameter'].sudo().get_param(
                'kamah_tech_cheque_management.check_return_journal_id', default=False))
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()

        field1 = self.check_return_journal_id
        param.set_param(
            'kamah_tech_cheque_management.check_return_journal_id', field1)
