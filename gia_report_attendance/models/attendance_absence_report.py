# -*- coding: utf-8 -*-
# models/attendance_absence_report.py

from odoo import api, fields, models
from datetime import datetime, timedelta, time
import logging
import pytz

_logger = logging.getLogger(__name__)


class AttendanceAbsenceReport(models.TransientModel):
    """
    نموذج تقرير غياب الموظفين
    يقوم بحساب أيام الغياب لكل موظف خلال فترة محددة
    مع مراعاة العطل الأسبوعية والإجازات المعتمدة
    """
    _name = 'attendance.absence.report'
    _description = 'تقرير غياب الموظفين'

    employee_id = fields.Many2one('hr.employee', string='الموظف')
    absent_days = fields.Integer(string='أيام الغياب')
    absent_dates = fields.Text(string='تواريخ الغياب')
    absence_reason = fields.Text(string='سبب الغياب')

    @api.model
    def calculate_absences(self, date_from, date_to, work_hour_from, work_hour_to, closing_hour, employee_ids=None):
        """
        حساب أيام الغياب للموظفين خلال الفترة المحددة

        المعلمات:
            date_from (date): تاريخ بداية الفترة
            date_to (date): تاريخ نهاية الفترة
            work_hour_from (float): وقت بدء الدوام
            work_hour_to (float): وقت نهاية الدوام
            closing_hour (float): وقت إغلاق البصمة
            employee_ids (list): قائمة بمعرفات الموظفين المختارين (اختياري)
        """
        # الحصول على الموظفين المحددين أو جميع الموظفين النشطين
        if employee_ids:
            employees = self.env['hr.employee'].browse(employee_ids)
            _logger.info(f"تقرير للموظفين المختارين فقط: {len(employees)} موظف")
        else:
            employees = self.env['hr.employee'].search([('active', '=', True)])
            _logger.info(f"تقرير لجميع الموظفين النشطين: {len(employees)} موظف")

        results = []

        # حذف السجلات السابقة من النموذج
        self.search([]).unlink()

        # تحويل التواريخ إلى كائنات date
        date_from_dt = fields.Date.from_string(date_from) if isinstance(date_from, str) else date_from
        date_to_dt = fields.Date.from_string(date_to) if isinstance(date_to, str) else date_to

        # الحصول على المنطقة الزمنية للمستخدم الحالي
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')

        # تنسيق أوقات الدوام للعرض
        work_from_str = self._format_time_value(work_hour_from)
        work_to_str = self._format_time_value(work_hour_to)
        closing_str = self._format_time_value(closing_hour)

        _logger.info(f"بداية حساب الغياب للفترة من {date_from_dt} إلى {date_to_dt}")
        _logger.info(f"ساعات العمل: من {work_from_str} إلى {work_to_str}")
        _logger.info(f"وقت إغلاق البصمة: {closing_str}")

        # حساب الغياب لكل موظف
        for employee in employees:
            _logger.info(f"حساب غياب الموظف: {employee.name} (ID: {employee.id})")

            absent_days, absent_dates, absence_reasons = self._calculate_employee_absences(
                employee, date_from_dt, date_to_dt, work_hour_from, work_hour_to, closing_hour, user_tz
            )

            if absent_days > 0:
                # إنشاء سجل جديد لهذا الموظف
                report_record = self.create({
                    'employee_id': employee.id,
                    'absent_days': absent_days,
                    'absent_dates': ', '.join(absent_dates),
                    'absence_reason': '\n'.join(absence_reasons),
                })

                _logger.info(f"تم تسجيل {absent_days} أيام غياب للموظف {employee.name}")

                # إضافة للنتائج لعرضها في التقرير
                results.append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'absent_days': absent_days,
                    'absent_dates': absent_dates,
                    'absence_reasons': absence_reasons
                })
            else:
                _logger.info(f"لا يوجد غياب للموظف {employee.name}")

        return results

    def _format_time_value(self, time_value):
        """تنسيق قيمة الوقت بغض النظر عن نوعها"""
        if isinstance(time_value, time):
            return f"{time_value.hour:02d}:{time_value.minute:02d}"
        else:
            hours = int(time_value)
            minutes = int((time_value % 1) * 60)
            return f"{hours:02d}:{minutes:02d}"

    def _float_to_time(self, float_time):
        """تحويل الوقت من تنسيق العدد العشري إلى كائن time"""
        if isinstance(float_time, time):
            return float_time

        hours = int(float_time)
        minutes = int((float_time % 1) * 60)
        return time(hours, minutes)

    def _format_datetime(self, dt):
        """تنسيق التاريخ والوقت بصيغة مناسبة للعرض"""
        if not dt:
            return ""
        return dt.strftime('%d/%m/%Y %H:%M:%S')

    def _calculate_employee_absences(self, employee, date_from, date_to, work_hour_from, work_hour_to, closing_hour,
                                     user_tz):
        """حساب أيام الغياب لموظف محدد"""
        absent_days = 0
        absent_dates = []
        absence_reasons = []
        current_date = date_from

        # تحويل أوقات العمل إلى كائنات time
        work_hour_from_time = self._float_to_time(work_hour_from)
        work_hour_to_time = self._float_to_time(work_hour_to)
        closing_hour_time = self._float_to_time(closing_hour)

        while current_date <= date_to:
            # تخطي أيام العطلة الأسبوعية (الخميس والجمعة)
            if current_date.weekday() in [3, 4]:  # 3=الخميس، 4=الجمعة
                current_date += timedelta(days=1)
                continue

            # التحقق من وجود إجازة معتمدة
            leave_domain = [
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', datetime.combine(current_date, datetime.max.time())),
                ('date_to', '>=', datetime.combine(current_date, datetime.min.time())),
            ]

            leave = self.env['hr.leave'].search(leave_domain, limit=1)

            if leave:
                current_date += timedelta(days=1)
                continue

            # تحديد بداية ونهاية يوم العمل ووقت إغلاق البصمة (بالتوقيت المحلي)
            day_start_local = datetime.combine(current_date, work_hour_from_time)
            day_end_local = datetime.combine(current_date, work_hour_to_time)
            day_closing_local = datetime.combine(current_date, closing_hour_time)

            # تحويل هذه الأوقات إلى UTC للمقارنة مع البصمات
            day_start = user_tz.localize(day_start_local).astimezone(pytz.UTC).replace(tzinfo=None)
            day_end = user_tz.localize(day_end_local).astimezone(pytz.UTC).replace(tzinfo=None)
            day_closing = user_tz.localize(day_closing_local).astimezone(pytz.UTC).replace(tzinfo=None)

            # البحث عن سجلات البصمة لهذا اليوم
            day_min = datetime.combine(current_date, datetime.min.time())
            day_max = datetime.combine(current_date + timedelta(days=1), datetime.min.time())

            # تحويل حدود اليوم إلى UTC
            day_min_utc = user_tz.localize(day_min).astimezone(pytz.UTC).replace(tzinfo=None)
            day_max_utc = user_tz.localize(day_max).astimezone(pytz.UTC).replace(tzinfo=None)

            attendance_domain = [
                ('employee_id', '=', employee.id),
                ('punching_time', '>=', day_min_utc),
                ('punching_time', '<', day_max_utc),
            ]

            attendances = self.env['gia.biometric.attendance'].search(attendance_domain)

            if not attendances:
                # حالة 1: لا يوجد سجل بصمة، اعتبار الموظف غائباً بالكامل
                absent_days += 1
                date_str = current_date.strftime('%d/%m/%Y')
                absent_dates.append(date_str)
                absence_reasons.append(f"{date_str}: غياب كامل")
            else:
                # تجميع جميع أوقات البصمة وترتيبها تصاعدياً
                punching_times = []
                for att in attendances:
                    if att.punching_time:
                        punching_times.append(att.punching_time)

                if punching_times:
                    punching_times.sort()
                    first_punch = punching_times[0]
                    last_punch = punching_times[-1]

                    # تحديد حالات الغياب
                    is_absent = False
                    reasons = []

                    # حالة 2: التأخر عن الدوام - بدون فترة سماح
                    if first_punch > day_start:
                        is_absent = True
                        delay_seconds = (first_punch - day_start).total_seconds()
                        delay_hours, remainder = divmod(delay_seconds, 3600)
                        delay_minutes = remainder // 60

                        if delay_hours > 0:
                            delay_text = f"تسجيل دخول متأخر بـ {int(delay_hours)} ساعة و {int(delay_minutes)} دقيقة"
                        else:
                            delay_text = f"تسجيل دخول متأخر بـ {int(delay_minutes)} دقيقة"

                        reasons.append(delay_text)

                    # حالة 3: الخروج المبكر
                    early_grace = timedelta(minutes=5)  # نبقي على فترة السماح للخروج

                    if last_punch < (day_end - early_grace):
                        is_absent = True
                        early_seconds = (day_end - last_punch).total_seconds()
                        early_hours, remainder = divmod(early_seconds, 3600)
                        early_minutes = remainder // 60

                        if early_hours > 0:
                            early_text = f"تسجيل خروج مبكر بـ {int(early_hours)} ساعة و {int(early_minutes)} دقيقة"
                        else:
                            early_text = f"تسجيل خروج مبكر بـ {int(early_minutes)} دقيقة"

                        reasons.append(early_text)

                    # حالة 4: الخروج بعد وقت إغلاق البصمة
                    if last_punch > day_closing:
                        is_absent = True
                        late_seconds = (last_punch - day_closing).total_seconds()
                        late_hours, remainder = divmod(late_seconds, 3600)
                        late_minutes = remainder // 60

                        if late_hours > 0:
                            late_text = f"تسجيل خروج بعد وقت الإغلاق بـ {int(late_hours)} ساعة و {int(late_minutes)} دقيقة"
                        else:
                            late_text = f"تسجيل خروج بعد وقت الإغلاق بـ {int(late_minutes)} دقيقة"

                        reasons.append(late_text)

                    # تسجيل الغياب إذا وجد أي سبب
                    if is_absent:
                        absent_days += 1
                        date_str = current_date.strftime('%d/%m/%Y')
                        absent_dates.append(date_str)

                        # إضافة معلومات البصمة للتوضيح
                        punch_info = f"الدخول: {first_punch.strftime('%H:%M:%S')}, الخروج: {last_punch.strftime('%H:%M:%S')}"
                        reason_text = f"{date_str}: {' - '.join(reasons)} ({punch_info})"

                        absence_reasons.append(reason_text)

            current_date += timedelta(days=1)

        return absent_days, absent_dates, absence_reasons