from telegram import ReplyKeyboardMarkup


def build_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Return the main menu keyboard.

    Parameters
    ----------
    is_admin:
        Whether to include admin-specific options.
    """
    keyboard = [
        ["📚 المستويات", "🗂 الخطة الدراسية"],
        ["🔧 البرامج الهندسية", " بحث"],
        ["📡 القنوات والمجموعات", "🆘 مساعدة"],
        ["📨 تواصل معنا"],
    ]
    if is_admin:
        keyboard.append(["👤 إدارة المشرفين"])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="اختر خيارًا من القائمة  ⬇️",
    )
