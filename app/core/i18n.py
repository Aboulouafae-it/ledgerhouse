from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QTableWidget,
    QWidget,
)

from app.core.database import session_scope
from app.services.settings_service import SettingsService


LANGUAGE_ENGLISH = "English"
LANGUAGE_ITALIAN = "Italian"
LANGUAGE_ARABIC = "Arabic"
SUPPORTED_LANGUAGES = [LANGUAGE_ENGLISH, LANGUAGE_ITALIAN, LANGUAGE_ARABIC]


TRANSLATIONS: dict[str, dict[str, str]] = {
    LANGUAGE_ITALIAN: {
        "Personal Ledger Pro - Login": "Personal Ledger Pro - Accesso",
        "Secure personal finance management": "Gestione sicura delle finanze personali",
        "Username": "Nome utente",
        "Password": "Password",
        "Show": "Mostra",
        "Hide": "Nascondi",
        "Remember me": "Ricordami",
        "Login": "Accedi",
        "Your data stays local on this device.": "I tuoi dati restano locali su questo dispositivo.",
        "Local-first finance manager for Debian": "Gestore finanziario locale per Debian",
        "Local finance suite": "Suite finanziaria locale",
        "SQLite local storage": "Archivio locale SQLite",
        "Dashboard": "Pannello",
        "Transactions": "Movimenti",
        "Debts": "Debiti",
        "Shared Living": "Spese condivise",
        "People": "Persone",
        "Reports": "Report",
        "Settings": "Impostazioni",
        "Your month at a glance: cash flow, obligations, and shared living balances.": "Il mese in sintesi: flusso di cassa, obblighi e saldi condivisi.",
        "Capture income, expenses, savings, debt activity, and shared costs.": "Registra entrate, uscite, risparmi, debiti e costi condivisi.",
        "Track debts, partial payments, remaining balances, and status changes.": "Monitora debiti, pagamenti parziali, saldi residui e stati.",
        "Split household expenses and generate settlement suggestions.": "Dividi le spese domestiche e genera suggerimenti di saldo.",
        "Manage contacts, house members, and financial relationships.": "Gestisci contatti, coinquilini e relazioni finanziarie.",
        "Generate administrative PDF reports and CSV exports.": "Genera report PDF amministrativi ed esportazioni CSV.",
        "Central control panel for security, people, reports, backup, and appearance.": "Pannello centrale per sicurezza, persone, report, backup e aspetto.",
        "Generate PDF report": "Genera report PDF",
        "Export transactions CSV": "Esporta movimenti CSV",
        "Add transaction": "Aggiungi movimento",
        "Refresh": "Aggiorna",
        "Add debt": "Aggiungi debito",
        "Register partial payment": "Registra pagamento parziale",
        "Quick add person": "Aggiungi persona veloce",
        "Add equal split expense": "Aggiungi spesa divisa in parti uguali",
        "Add person": "Aggiungi persona",
        "House member": "Membro casa",
        "General Settings": "Impostazioni generali",
        "Default workspace behavior": "Comportamento predefinito dell'area di lavoro",
        "Security & Login": "Sicurezza e accesso",
        "Local password protection": "Protezione con password locale",
        "People Management": "Gestione persone",
        "Creditors & Debtors": "Creditori e debitori",
        "Shared Living Members": "Membri casa",
        "Categories": "Categorie",
        "Payment Methods": "Metodi di pagamento",
        "Reports & PDF Identity": "Identita report e PDF",
        "Backup & Restore": "Backup e ripristino",
        "Appearance": "Aspetto",
        "Owner name": "Nome proprietario",
        "Default currency": "Valuta predefinita",
        "Language": "Lingua",
        "Choose the application language": "Scegli la lingua dell'applicazione",
        "Save language": "Salva lingua",
        "Save and restart the app to apply the language across all screens.": "Salva e riavvia l'app per applicare la lingua a tutte le schermate.",
        "Language saved. Restart the app to apply it everywhere.": "Lingua salvata. Riavvia l'app per applicarla ovunque.",
        "Language not saved": "Lingua non salvata",
        "Save general settings": "Salva impostazioni generali",
        "Require login when the app starts": "Richiedi accesso all'avvio",
        "Remember username on login screen": "Ricorda nome utente nella schermata di accesso",
        "Current password": "Password attuale",
        "New password": "Nuova password",
        "Confirm password": "Conferma password",
        "Save security settings": "Salva impostazioni di sicurezza",
        "Search people": "Cerca persone",
        "Deactivate selected": "Disattiva selezionato",
        "Add creditor/debtor": "Aggiungi creditore/debitore",
        "Add shared living member": "Aggiungi membro casa",
        "Category name": "Nome categoria",
        "Add category": "Aggiungi categoria",
        "Payment method": "Metodo di pagamento",
        "Add method": "Aggiungi metodo",
        "Title prefix": "Prefisso titolo",
        "Footer text": "Testo pie pagina",
        "Logo path": "Percorso logo",
        "Include charts in PDF reports": "Includi grafici nei report PDF",
        "Include signature area": "Includi area firma",
        "Save report identity": "Salva identita report",
        "Backup folder": "Cartella backup",
        "Create backup": "Crea backup",
        "Restore from backup": "Ripristina da backup",
        "Backup encryption placeholder": "Segnaposto cifratura backup",
        "Theme": "Tema",
        "Accent color": "Colore accento",
        "Compact mode": "Modalita compatta",
        "Table density": "Densita tabella",
        "Save appearance": "Salva aspetto",
        "ID": "ID",
        "Date": "Data",
        "Type": "Tipo",
        "Amount": "Importo",
        "Category": "Categoria",
        "Person": "Persona",
        "Note": "Nota",
        "Name": "Nome",
        "Phone": "Telefono",
        "Email": "Email",
        "Status": "Stato",
        "Roles": "Ruoli",
        "Creditor": "Creditore",
        "Debtor": "Debitore",
        "Color": "Colore",
        "Active": "Attivo",
        "Direction": "Direzione",
        "Original": "Originale",
        "Remaining": "Residuo",
        "Due": "Scadenza",
        "Created": "Creato",
        "Title": "Titolo",
        "Paid By": "Pagato da",
        "Participants": "Partecipanti",
        "From": "Da",
        "To": "A",
        "Income": "Entrate",
        "Expenses": "Uscite",
        "Net Balance": "Saldo netto",
        "Savings": "Risparmi",
        "Owed To Me": "Mi devono",
        "I Owe": "Devo",
        "Shared To Collect": "Condiviso da incassare",
        "Shared To Pay": "Condiviso da pagare",
        "Recent Transactions": "Movimenti recenti",
        "Income vs Expenses": "Entrate vs uscite",
        "Last six months": "Ultimi sei mesi",
        "Security reminder": "Promemoria sicurezza",
        "You are using the default password. Please change it in Settings.": "Stai usando la password predefinita. Cambiala nelle Impostazioni.",
    },
    LANGUAGE_ARABIC: {
        "Personal Ledger Pro - Login": "Personal Ledger Pro - تسجيل الدخول",
        "Secure personal finance management": "إدارة آمنة للمال الشخصي",
        "Username": "اسم المستخدم",
        "Password": "كلمة المرور",
        "Show": "إظهار",
        "Hide": "إخفاء",
        "Remember me": "تذكرني",
        "Login": "دخول",
        "Your data stays local on this device.": "تبقى بياناتك محلية على هذا الجهاز.",
        "Local-first finance manager for Debian": "مدير مالي محلي لنظام Debian",
        "Local finance suite": "حزمة مالية محلية",
        "SQLite local storage": "تخزين SQLite محلي",
        "Dashboard": "لوحة التحكم",
        "Transactions": "المعاملات",
        "Debts": "الديون",
        "Shared Living": "السكن المشترك",
        "People": "الأشخاص",
        "Reports": "التقارير",
        "Settings": "الإعدادات",
        "Your month at a glance: cash flow, obligations, and shared living balances.": "نظرة شهرية على التدفق النقدي والالتزامات وأرصدة السكن المشترك.",
        "Capture income, expenses, savings, debt activity, and shared costs.": "سجل الدخل والمصاريف والادخار والديون والتكاليف المشتركة.",
        "Track debts, partial payments, remaining balances, and status changes.": "تتبع الديون والمدفوعات الجزئية والأرصدة المتبقية والحالة.",
        "Split household expenses and generate settlement suggestions.": "قسم مصاريف المنزل وأنشئ اقتراحات التسوية.",
        "Manage contacts, house members, and financial relationships.": "إدارة جهات الاتصال وأعضاء المنزل والعلاقات المالية.",
        "Generate administrative PDF reports and CSV exports.": "إنشاء تقارير PDF إدارية وتصدير CSV.",
        "Central control panel for security, people, reports, backup, and appearance.": "لوحة مركزية للأمان والأشخاص والتقارير والنسخ الاحتياطي والمظهر.",
        "Generate PDF report": "إنشاء تقرير PDF",
        "Export transactions CSV": "تصدير المعاملات CSV",
        "Add transaction": "إضافة معاملة",
        "Refresh": "تحديث",
        "Add debt": "إضافة دين",
        "Register partial payment": "تسجيل دفعة جزئية",
        "Quick add person": "إضافة شخص سريعاً",
        "Add equal split expense": "إضافة مصروف بتقسيم متساو",
        "Add person": "إضافة شخص",
        "House member": "عضو منزل",
        "General Settings": "الإعدادات العامة",
        "Default workspace behavior": "سلوك مساحة العمل الافتراضي",
        "Security & Login": "الأمان وتسجيل الدخول",
        "Local password protection": "حماية بكلمة مرور محلية",
        "People Management": "إدارة الأشخاص",
        "Creditors & Debtors": "الدائنون والمدينون",
        "Shared Living Members": "أعضاء السكن المشترك",
        "Categories": "الفئات",
        "Payment Methods": "طرق الدفع",
        "Reports & PDF Identity": "هوية التقارير و PDF",
        "Backup & Restore": "النسخ الاحتياطي والاستعادة",
        "Appearance": "المظهر",
        "Owner name": "اسم المالك",
        "Default currency": "العملة الافتراضية",
        "Language": "اللغة",
        "Choose the application language": "اختر لغة التطبيق",
        "Save language": "حفظ اللغة",
        "Save and restart the app to apply the language across all screens.": "احفظ وأعد تشغيل التطبيق لتطبيق اللغة على كل الشاشات.",
        "Language saved. Restart the app to apply it everywhere.": "تم حفظ اللغة. أعد تشغيل التطبيق لتطبيقها في كل مكان.",
        "Language not saved": "لم يتم حفظ اللغة",
        "Save general settings": "حفظ الإعدادات العامة",
        "Require login when the app starts": "طلب تسجيل الدخول عند بدء التطبيق",
        "Remember username on login screen": "تذكر اسم المستخدم في شاشة الدخول",
        "Current password": "كلمة المرور الحالية",
        "New password": "كلمة مرور جديدة",
        "Confirm password": "تأكيد كلمة المرور",
        "Save security settings": "حفظ إعدادات الأمان",
        "Search people": "بحث عن أشخاص",
        "Deactivate selected": "تعطيل المحدد",
        "Add creditor/debtor": "إضافة دائن/مدين",
        "Add shared living member": "إضافة عضو سكن مشترك",
        "Category name": "اسم الفئة",
        "Add category": "إضافة فئة",
        "Payment method": "طريقة الدفع",
        "Add method": "إضافة طريقة",
        "Title prefix": "بادئة العنوان",
        "Footer text": "نص التذييل",
        "Logo path": "مسار الشعار",
        "Include charts in PDF reports": "تضمين الرسوم في تقارير PDF",
        "Include signature area": "تضمين مساحة توقيع",
        "Save report identity": "حفظ هوية التقرير",
        "Backup folder": "مجلد النسخ الاحتياطي",
        "Create backup": "إنشاء نسخة احتياطية",
        "Restore from backup": "استعادة من نسخة احتياطية",
        "Backup encryption placeholder": "خيار تشفير النسخ الاحتياطي",
        "Theme": "السمة",
        "Accent color": "لون التمييز",
        "Compact mode": "الوضع المضغوط",
        "Table density": "كثافة الجدول",
        "Save appearance": "حفظ المظهر",
        "ID": "المعرف",
        "Date": "التاريخ",
        "Type": "النوع",
        "Amount": "المبلغ",
        "Category": "الفئة",
        "Person": "الشخص",
        "Note": "ملاحظة",
        "Name": "الاسم",
        "Phone": "الهاتف",
        "Email": "البريد",
        "Status": "الحالة",
        "Roles": "الأدوار",
        "Creditor": "دائن",
        "Debtor": "مدين",
        "Color": "اللون",
        "Active": "نشط",
        "Direction": "الاتجاه",
        "Original": "الأصلي",
        "Remaining": "المتبقي",
        "Due": "الاستحقاق",
        "Created": "أُنشئ",
        "Title": "العنوان",
        "Paid By": "دفع بواسطة",
        "Participants": "المشاركون",
        "From": "من",
        "To": "إلى",
        "Income": "الدخل",
        "Expenses": "المصاريف",
        "Net Balance": "الرصيد الصافي",
        "Savings": "الادخار",
        "Owed To Me": "مستحق لي",
        "I Owe": "مستحق علي",
        "Shared To Collect": "مشترك للتحصيل",
        "Shared To Pay": "مشترك للدفع",
        "Recent Transactions": "المعاملات الأخيرة",
        "Income vs Expenses": "الدخل مقابل المصاريف",
        "Last six months": "آخر ستة أشهر",
        "Security reminder": "تذكير أمان",
        "You are using the default password. Please change it in Settings.": "أنت تستخدم كلمة المرور الافتراضية. يرجى تغييرها من الإعدادات.",
    },
}


def current_language() -> str:
    try:
        with session_scope() as session:
            language = SettingsService(session).get_str("default_language", LANGUAGE_ENGLISH)
    except Exception:
        return LANGUAGE_ENGLISH
    return language if language in SUPPORTED_LANGUAGES else LANGUAGE_ENGLISH


def tr(text: str, language: str | None = None) -> str:
    if not text:
        return text
    language = language or current_language()
    return TRANSLATIONS.get(language, {}).get(text, text)


def apply_translations(root: QWidget, language: str | None = None) -> None:
    language = language or current_language()
    root.setLayoutDirection(Qt.RightToLeft if language == LANGUAGE_ARABIC else Qt.LeftToRight)
    if root.windowTitle():
        root.setWindowTitle(tr(root.windowTitle(), language))
    for widget in root.findChildren(QWidget):
        widget.setLayoutDirection(Qt.RightToLeft if language == LANGUAGE_ARABIC else Qt.LeftToRight)
        if isinstance(widget, QLabel) and widget.text():
            widget.setText(tr(widget.text(), language))
        elif isinstance(widget, QAbstractButton) and widget.text():
            widget.setText(tr(widget.text(), language))
        elif isinstance(widget, QLineEdit) and widget.placeholderText():
            widget.setPlaceholderText(tr(widget.placeholderText(), language))
        elif isinstance(widget, QTableWidget):
            for col in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(col)
                if item and item.text():
                    item.setText(tr(item.text(), language))
        elif isinstance(widget, QComboBox):
            if widget.property("translateItems"):
                current = widget.currentText()
                for index in range(widget.count()):
                    widget.setItemText(index, tr(widget.itemText(index), language))
                if current:
                    widget.setCurrentText(tr(current, language))
        elif isinstance(widget, QListWidget):
            for index in range(widget.count()):
                item = widget.item(index)
                item.setText(tr(item.text(), language))
