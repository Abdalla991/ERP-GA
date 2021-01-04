from odoo import api, models
from odoo.exceptions import ValidationError


class ReportMrp(models.AbstractModel):
    _name = 'report.yds_mrp2.mrp_report_view'

    @api.model
    def _get_report_values(self, docids, data=None):
        try:
            return {
                'doc_ids': data.get('ids'),
                'doc_model': data.get('model'),
                'data': data['form'],
            }
        except:
            ValidationError('there is no reports for that salesperson')
