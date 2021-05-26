from odoo import models, fields, api, _

class account_journal(models.Model):

    _inherit = 'account.journal'

    payment_subtype = fields.Selection([('issue_check',_('Issued Checks')),('rece_check',_('Received Checks'))],string="Payment Subtype")
    inter_journal_type = fields.Selection([('receive',_('Receive')),('pay',_('Pay'))],string="Intermediate Journal Type")

