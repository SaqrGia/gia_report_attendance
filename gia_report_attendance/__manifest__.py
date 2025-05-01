{
    'name': 'GIA report',
    'version': '1.0',
    'summary': 'تقرير غياب الموظفين بناءً على بيانات البصمة',
    'description': """
        تقرير لعرض أيام غياب الموظفين استنادًا إلى بيانات البصمة
        - يستبعد أيام الإجازات المعتمدة
        - يستبعد أيام العطل الأسبوعية (الخميس والجمعة)
    """,
    'category': 'Human Resources/Attendance',
    'author': 'Your Company',
    'depends': ['hr_attendance', 'hr_holidays', 'hr','gia_biometric_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/attendance_absence_report_wizard_view.xml',
        'report/attendance_absence_reports.xml',
        'report/attendance_absence_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}