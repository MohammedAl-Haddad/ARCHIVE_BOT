from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

import logging

from ..config import OWNER_TG_ID
from ..db import (
    UPLOAD_CONTENT,
    get_admin_with_permissions,
    insert_ingestion,
    attach_material,
    get_group_id_by_chat,
    get_binding,
    get_or_create_year,
    get_or_create_lecturer,
    insert_term_resource,
)
from ..db.materials import insert_material, find_exact
from bot.db.admins import is_owner
from ..parser.hashtags import parse_hashtags
from ..utils.telegram import send_ephemeral, get_file_unique_id_from_message


logger = logging.getLogger(__name__)


async def ingestion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    file_unique_id = get_file_unique_id_from_message(message)
    text = message.caption or message.text or ""
    info, error = parse_hashtags(text)
    if error:
        await send_ephemeral(
            context,
            message.chat_id,
            error,
            reply_to_message_id=message.message_id,
            message_thread_id=message.message_thread_id,
        )
        return

    year = info.year
    category = info.content_type
    title = info.title or ""
    lecturer_name = info.lecturer

    lecture_attachment_categories = [
        "board_images",
        "slides",
        "audio",
        "video",
        "mind_map",
        "transcript",
        "related",
    ]

    if category == "lecture" or category in lecture_attachment_categories:
        lecture_title = f"محاضرة {info.lecture_no}: {info.title}"
    else:
        lecture_title = title

    user = update.effective_user
    if not user:
        logger.warning("No effective user on update")
        if message:
            await send_ephemeral(
                context,
                message.chat_id,
                "لا يمكن تحديد المستخدم.",
                reply_to_message_id=message.message_id,
                message_thread_id=message.message_thread_id,
            )
        return

    admin_info = await get_admin_with_permissions(user.id)
    if admin_info is None:
        logger.warning("User %s is not an admin", user.id)
        await send_ephemeral(
            context,
            message.chat_id,
            "المستخدم ليس مشرفًا.",
            reply_to_message_id=message.message_id,
            message_thread_id=message.message_thread_id,
        )
        return
    admin_id, permissions = admin_info
    if not (permissions & UPLOAD_CONTENT):
        logger.warning("User %s lacks upload permission", user.id)
        await send_ephemeral(
            context,
            message.chat_id,
            "لا تملك صلاحية رفع المحتوى.",
            reply_to_message_id=message.message_id,
            message_thread_id=message.message_thread_id,
        )
        return

    chat = update.effective_chat
    thread_id = message.message_thread_id if message else None
    if chat is None:
        logger.warning("Missing chat %s", chat)
        if message:
            await send_ephemeral(
                context,
                message.chat_id,
                "لا يمكن تحديد المحادثة.",
                reply_to_message_id=message.message_id,
                message_thread_id=message.message_thread_id,
            )
        return

    group_info = await get_group_id_by_chat(chat.id)
    logger.debug("group_info=%s", group_info)
    if group_info is None:
        logger.warning("Group info not found for chat %s", chat.id)
        await send_ephemeral(
            context,
            message.chat_id,
            "المجموعة غير معروفة.",
            reply_to_message_id=message.message_id,
            message_thread_id=message.message_thread_id,
        )
        return
    binding = None
    if category != "attendance":
        if thread_id is None:
            await send_ephemeral(
                context,
                message.chat_id,
                "هذا النوع يتطلب ربط الـTopic بمادة/قسم عبر /insert_sub.",
                reply_to_message_id=message.message_id,
                message_thread_id=message.message_thread_id,
            )
            return
        binding = await get_binding(chat.id, thread_id)
        logger.debug("binding=%s", binding)
        if binding is None:
            await send_ephemeral(
                context,
                message.chat_id,
                "هذا النوع يتطلب ربط الـTopic بمادة/قسم عبر /insert_sub.",
                reply_to_message_id=message.message_id,
                message_thread_id=message.message_thread_id,
            )
            return
        subject_id = binding["subject_id"]
        section = binding["section"]
        subject_name = binding["subject_name"]
    else:
        subject_id = section = subject_name = None

    if category is None:
        await send_ephemeral(
            context,
            message.chat_id,
            "لم يتم التعرف على نوع المحتوى.",
            reply_to_message_id=message.message_id,
            message_thread_id=message.message_thread_id,
        )
        return

    if category == "attendance":
        term_id = group_info[2]
        await insert_term_resource(term_id, "attendance", chat.id, message.message_id)
        await send_ephemeral(
            context,
            chat.id,
            "✅ تم الاستلام.",
            reply_to_message_id=message.message_id,
            message_thread_id=thread_id,
        )
        return

    year_id = await get_or_create_year(str(year)) if year else None
    lecturer_id = (
        await get_or_create_lecturer(lecturer_name) if lecturer_name else None
    )

    lookup_title = lecture_title
    alt_title = title if lecture_title != title else None
    existing = await find_exact(
        subject_id,
        section,
        category,
        lookup_title,
        year_id=year_id,
        lecturer_id=lecturer_id,
        alt_title=alt_title,
    )
    if existing:
        ctx = context.user_data.setdefault("replace_ctx", {})
        ctx[message.message_id] = {
            "old_material_id": existing[0],
            "chat_id": chat.id,
            "thread_id": thread_id,
            "admin_id": admin_id,
            "tg_user_id": user.id,
            "subject_name": subject_name,
            "section": section,
            "category": category,
            "title": title,
            "year": year,
            "year_id": year_id,
            "lecturer_id": lecturer_id,
            "lecturer_name": lecturer_name,
            "file_unique_id": file_unique_id,
        }
        buttons = [
            [
                InlineKeyboardButton(
                    "استبدال",
                    callback_data=f"dup:rep:{message.message_id}:{existing[0]}",
                ),
                InlineKeyboardButton(
                    "إلغاء", callback_data=f"dup:cancel:{message.message_id}"
                ),
            ]
        ]
        await message.reply_text(
            "هذا الملف مرفوع من قبل لنفس المحاضرة/السنة/المحاضر.",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    material_title = lecture_title if lecture_title != title else title
    material_id = await insert_material(
        subject_id,
        section,
        category,
        material_title,
        year_id=year_id,
        lecturer_id=lecturer_id,
        file_unique_id=file_unique_id,
        source_chat_id=chat.id,
        source_topic_id=thread_id,
        source_message_id=message.message_id,
        created_by_admin_id=admin_id,
    )

    if category in lecture_attachment_categories:
        lecture = await find_exact(
            subject_id,
            section,
            "lecture",
            lecture_title,
            year_id=year_id,
            lecturer_id=lecturer_id,
            alt_title=title if lecture_title != title else None,
        )
        if not lecture:
            await insert_material(
                subject_id,
                section,
                "lecture",
                lecture_title,
                year_id=year_id,
                lecturer_id=lecturer_id,
                created_by_admin_id=admin_id,
            )

    ingestion_id = await insert_ingestion(
        message.message_id, admin_id, file_unique_id=file_unique_id
    )
    await attach_material(ingestion_id, material_id, "pending")
    await send_ephemeral(
        context,
        chat.id,
        f"✅ تم الاستلام. رقم العملية: #{ingestion_id}\nسيتم إشعارك بعد المراجعة.",
        reply_to_message_id=message.message_id,
        message_thread_id=thread_id,
    )
    logger.info(
        "pending #%s subject=%s section=%s year=%s type=%s title=%s",
        ingestion_id,
        subject_name,
        section,
        year,
        category,
        title,
    )

    summary = (
        f"المادة: {subject_name}\nالقسم: {section}\nالسنة: {year or '---'}\nالنوع: {category}\nالعنوان: {title}"
    )
    buttons = [
        [
            InlineKeyboardButton("Approve", callback_data=f"appr:{ingestion_id}"),
            InlineKeyboardButton("Reject", callback_data=f"rej:{ingestion_id}"),
        ]
    ]
    try:
        await context.bot.copy_message(
            chat_id=OWNER_TG_ID,
            from_chat_id=chat.id,
            message_id=message.message_id,
            caption=summary,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as e:
        logger.error("Failed to notify approver: %s", e)


async def handle_duplicate_decision(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    _, action, msg_id, *rest = query.data.split(":")
    msg_id = int(msg_id)
    ctx = context.user_data.get("replace_ctx", {})
    data = ctx.get(msg_id)
    if data is None:
        await query.edit_message_text("انتهت صلاحية الطلب.")
        return
    if query.from_user.id != data["tg_user_id"] and not is_owner(query.from_user.id):
        await send_ephemeral(
            context,
            query.message.chat_id,
            "العملية مخصّصة لمرسل الملف",
            message_thread_id=query.message.message_thread_id,
        )
        return
    try:
        await query.message.delete()
    except Exception:
        await query.edit_message_reply_markup(None)
    if action == "cancel":
        ctx.pop(msg_id, None)
        await send_ephemeral(
            context,
            query.message.chat_id,
            "تم الإلغاء.",
            message_thread_id=query.message.message_thread_id,
        )
        user_id = query.from_user.id
        buttons = [
            [
                InlineKeyboardButton(
                    "إبقاء الرسالة", callback_data=f"dup:keep:{msg_id}:{user_id}"
                ),
                InlineKeyboardButton(
                    "حذف الرسالة", callback_data=f"dup:del:{msg_id}:{user_id}"
                ),
            ]
        ]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="ماذا تريد أن تفعل بالرسالة الأصلية؟",
            reply_markup=InlineKeyboardMarkup(buttons),
            message_thread_id=query.message.message_thread_id,
        )
        return
    old_material_id = data["old_material_id"]
    admin_id = data["admin_id"]
    ingestion_id = await insert_ingestion(
        msg_id, admin_id, action="replace", file_unique_id=data.get("file_unique_id")
    )
    await attach_material(ingestion_id, old_material_id, "pending")
    await send_ephemeral(
        context,
        data["chat_id"],
        f"✅ تم الاستلام. رقم العملية: #{ingestion_id}\nسيتم إشعارك بعد المراجعة.",
        reply_to_message_id=msg_id,
        message_thread_id=data.get("thread_id"),
    )
    summary = (
        "طلب استبدال ملف مرفوع سابقًا\n"
        f"المادة: {data['subject_name']}\nالقسم: {data['section']}\n"
        f"السنة: {data['year'] or '---'}\nالنوع: {data['category']}\nالعنوان: {data['title']}"
    )
    buttons = [
        [
            InlineKeyboardButton(
                "Approve استبدال", callback_data=f"appr:{ingestion_id}"
            ),
            InlineKeyboardButton("Reject", callback_data=f"rej:{ingestion_id}"),
        ]
    ]
    try:
        await context.bot.copy_message(
            chat_id=OWNER_TG_ID,
            from_chat_id=data["chat_id"],
            message_id=msg_id,
            caption=summary,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as e:
        logger.error("Failed to notify approver: %s", e)
    ctx.pop(msg_id, None)


async def handle_duplicate_cancel_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    _, action, msg_id, user_id = query.data.split(":")
    msg_id = int(msg_id)
    user_id = int(user_id)
    if query.from_user.id != user_id and not is_owner(query.from_user.id):
        await send_ephemeral(
            context,
            query.message.chat_id,
            "العملية مخصّصة لمرسل الملف",
            message_thread_id=query.message.message_thread_id,
        )
        return
    if action == "del":
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id, message_id=msg_id
            )
        except Exception:
            pass
    try:
        await query.message.delete()
    except Exception:
        pass


duplicate_callback = CallbackQueryHandler(
    handle_duplicate_decision, pattern=r"^dup:(rep|cancel):"
)

duplicate_cancel_callback = CallbackQueryHandler(
    handle_duplicate_cancel_choice, pattern=r"^dup:(keep|del):"
)


__all__ = ["ingestion_handler", "duplicate_callback", "duplicate_cancel_callback"]

