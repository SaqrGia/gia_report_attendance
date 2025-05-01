# -*- coding: utf-8 -*-
# wizard/attendance_absence_report_wizard.py

from odoo import api, fields, models
from datetime import time


class AttendanceAbsenceReportWizard(models.TransientModel):
    _name = 'attendance.absence.report.wizard'
    _description = 'معالج تقرير غياب الموظفين'

    date_from = fields.Date(string='من تاريخ', required=True)
    date_to = fields.Date(string='إلى تاريخ', required=True)
    work_hour_from = fields.Float(string='وقت بدء الدوام', required=True, default=8.0)
    work_hour_to = fields.Float(string='وقت نهاية الدوام', required=True, default=17.0)
    closing_hour = fields.Float(string='وقت إغلاق البصمة', required=True, default=18.0)

    def action_print_report(self):
        """إنشاء وعرض التقرير"""
        # الحصول على معرفات الموظفين المختارين من السياق
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model')

        # تحديد معرفات الموظفين المختارين
        employee_ids = []
        if active_model == 'hr.employee' and active_ids:
            # إذا كان المستخدم يختار من قائمة الموظفين مباشرة
            employee_ids = active_ids
        elif active_model == 'gia.biometric.attendance' and active_ids:
            # إذا كان المستخدم يختار من قائمة البصمات
            attendance_records = self.env['gia.biometric.attendance'].browse(active_ids)
            employee_ids = list(set(attendance_records.mapped('employee_id.id')))

        # حذف النتائج السابقة إن وجدت
        self.env['attendance.absence.report'].search([]).unlink()

        # حساب الغيابات
        absence_report = self.env['attendance.absence.report']
        results = absence_report.calculate_absences(
            self.date_from, self.date_to,
            self.work_hour_from, self.work_hour_to, self.closing_hour,
            employee_ids if employee_ids else None
        )

        # إعداد البيانات للتقرير
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'work_hour_from': self.work_hour_from,
            'work_hour_to': self.work_hour_to,
            'closing_hour': self.closing_hour,
            'results': results,
            'ids': self.ids,
            'model': self._name,
        }

        # عرض التقرير
        return self.env.ref('gia_report_attendance.action_attendance_absence_report').report_action(self, data=data)