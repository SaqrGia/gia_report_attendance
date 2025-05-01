# report/attendance_absence_report.py
from odoo import api, models
from datetime import time


class AttendanceAbsenceReportPDF(models.AbstractModel):
    _name = 'report.gia_report_attendance.absence_report_tpl'
    _description = 'نموذج تقرير غياب الموظفين'

    @api.model
    def _get_report_values(self, docids, data=None):
        """إعداد القيم التي سيتم عرضها في التقرير"""
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        work_hour_from = data.get('work_hour_from')
        work_hour_to = data.get('work_hour_to')
        closing_hour = data.get('closing_hour')

        # تحويل ساعات العمل لعرضها بتنسيق مناسب
        work_hour_from_fmt = "{:02d}:{:02d}".format(
            int(work_hour_from),
            int((work_hour_from % 1) * 60)
        )
        work_hour_to_fmt = "{:02d}:{:02d}".format(
            int(work_hour_to),
            int((work_hour_to % 1) * 60)
        )
        closing_hour_fmt = "{:02d}:{:02d}".format(
            int(closing_hour),
            int((closing_hour % 1) * 60)
        )

        # الحصول على نتائج التقرير
        absence_records = self.env['attendance.absence.report'].search([])
        results = []

        for record in absence_records:
            absent_dates = record.absent_dates.split(', ') if record.absent_dates else []
            absence_reasons = record.absence_reason.split('\n') if record.absence_reason else []

            results.append({
                'employee_id': record.employee_id.id,
                'employee_name': record.employee_id.name,
                'absent_days': record.absent_days,
                'absent_dates': absent_dates,
                'absence_reasons': absence_reasons
            })

        return {
            'doc_ids': docids,
            'doc_model': 'attendance.absence.report.wizard',
            'docs': self.env['attendance.absence.report.wizard'].browse(docids),
            'data': data,
            'results': results,
            'date_from': date_from,
            'date_to': date_to,
            'work_hour_from': work_hour_from_fmt,
            'work_hour_to': work_hour_to_fmt,
            'closing_hour': closing_hour_fmt,
        }