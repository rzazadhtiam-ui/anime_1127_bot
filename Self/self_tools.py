# ============================================================
# self_tools.py — نسخه نهایی و کاملاً اصلاح‌شده
# ============================================================

import datetime
import jdatetime
import asyncio

from telethon import events
from telethon.tl.functions.messages import DeleteMessagesRequest
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.errors import MessageDeleteForbiddenError
from multi_lang import multi_lang, reply_auto, edit_auto
import re
import asyncio
from telethon.tl.functions.messages import DeleteMessagesRequest
from telethon.errors import MessageDeleteForbiddenError
from collections import defaultdict, deque
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
# ===================== فونت‌ها =====================

fonts_list = [
    # فونت 1: ساده (مثال)
    {c:c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"},

# 1 Bold
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳")),

# 2 Italic
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧")),

# 3 Bold Italic
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛")),

# 4 Script
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝒜𝐵𝒞𝒟𝐸𝐹𝒢𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒬𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵𝒶𝒷𝒸𝒹𝒺𝒻𝒼𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝓄𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏")),

# 5 Fraktur
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷")),

# 6 Double Struck
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫")),

# 7 Sans Bold
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇")),

# 8 Sans Italic
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻")),

# 9 Sans Bold Italic
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯")),

# 10 Monospace
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣")),

# 11 Circled
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ")),

# 12 Fullwidth
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ")),

# 13 Small Caps Style
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"ABCDEFGHIJKLMNOPQRSTUVWXYZᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ")),

# 14 Square
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙")),

# 15 Bubble
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"ABCDEFGHIJKLMNOPQRSTUVWXYZⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ")),

# 16
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"卂乃匚刀乇千厶卄丨ﾌҜㄥ爪几ㄖ卩Ɋ尺丂ㄒㄩᐯ山乂ㄚ乙卂乃匚刀乇千厶卄丨ﾌҜㄥ爪几ㄖ卩Ɋ尺丂ㄒㄩᐯ山乂ㄚ乙")),

#17
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁")),


#18
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"₳฿₵ĐɆ₣₲ⱧłJ₭Ⱡ₥₦Ø₱QⱤ₴₮ɄV₩ӾɎⱫ₳฿₵đɇ₣₲ⱨłJ₭Ⱡ₥₦ø₱qⱤ₴₮Ʉv₩ӾɏⱫ")),

#19
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"ȺɃƇƊɆƑƓǶƗɈƘȽṀƝØƤɊƦƧƬƲƲƜҲƳƵȺɃƈƌɇƒɠɦɨɉƙƚɱɲøƥɋɾʂƭʋʋɯҳƴƶ")),

#20
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍")),

#21
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃")),

#22
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟")),

#23
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭")),

#24
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ")),

#25
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉")),

#26
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩")),

#27
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"𝒜ℬ𝒞𝒟ℰℱ𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵𝒜ℬ𝒞𝒟ℰℱ𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵")),

#28
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"ﾑ乃ζÐ乇ｷǤんﾉﾌズﾚᄊ刀Ծｱq尺ㄎｲЦЏЩﾒﾘ乙ﾑ乃ζÐ乇ｷǤんﾉﾌズﾚᄊ刀Ծｱq尺ㄎｲЦЏЩﾒﾘ乙")),

#29
dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
"ᗩᗷᑕᗪᕮᖴᘜᕼᖗᒍᖉᒐᗰᘉᗝᑭᘯᖇᔕᙢᑌᕓᗯ᙭ᖻᘔᗩᗷᑕᗪᕮᖴᘜᕼᖗᒍᖉᒐᗰᘉᗝᑭᘯᖇᔕᙢᑌᕓᗯ᙭ᖻᘔ"))


]

# ===================== توابع کمکی =====================
async def owner_only(event):
    me = await event.client.get_me()
    return event.sender_id == me.id

def today_text():
    now = datetime.datetime.now()
    j_now = jdatetime.datetime.fromgregorian(datetime=now)
    return f"📅 {j_now.strftime('%Y/%m/%d')}\n⏰ {j_now.strftime('%H:%M:%S')}"

def fancy_sentence(text):
    out = []
    for i, font in enumerate(fonts_list, 1):
        out.append(f"{i}_ {''.join(font.get(c, c) for c in text)}")
    return "\n".join(out)

async def is_admin(client, chat):
    try:
        async for u in client.iter_participants(chat, filter=ChannelParticipantsAdmins):
            if u.is_self:
                return True
    except:
        pass
    return False

async def delete_fast(client, ids):
    deleted = 0
    for i in range(0, len(ids), 100):
        try:
            await client(DeleteMessagesRequest(
                id=ids[i:i + 100],
                revoke=True
            ))
            deleted += len(ids[i:i + 100])
        except MessageDeleteForbiddenError:
            pass
        except:
            pass
        await asyncio.sleep(0.05)
    return deleted


async def can_delete_all(client, chat_id):
    try:
        me = await client.get_me()
        p = await client(GetParticipantRequest(chat_id, me.id))

        return isinstance(
            p.participant,
            (
                ChannelParticipantAdmin,
                ChannelParticipantCreator,
                ChannelParticipantEditor
            )
        )
    except:
        return False

async def delete_fast(client, chat_id, msg_ids, revoke=False):
    deleted = 0

    for i in range(0, len(msg_ids), 100):
        batch = msg_ids[i:i + 100]

        try:
            await client(DeleteMessagesRequest(
                id=batch,
                revoke=revoke
            ))
            deleted += len(batch)

        except MessageDeleteForbiddenError:
            # دسترسی نداری
            break

        except Exception as e:
            # مهم: سکوت نکن
            print(f"Delete error: {e}")

    return deleted

# ===================== ماژول اصلی =====================
def self_tools(client):

    import time
    from collections import defaultdict, deque

    spam_db = defaultdict(lambda: deque())

    # ===================== امروز =====================
    @client.on(events.NewMessage)
    @multi_lang([".امروز", ".today"])
    async def today_handler(event):
        if not await owner_only(event):
            return
        await edit_auto(event, today_text())

    # ===================== فونت =====================
    @client.on(events.NewMessage)
    @multi_lang([".فونت", ".font"])
    async def font_handler(event):
        if not await owner_only(event):
            return

        text = event.ml_args
        if not text:
            await edit_auto(event, "❌ لطفاً متن وارد کنید")
            return

        fancy_lines = fancy_sentence(text).split("\n")
        unicode_result = "\n".join([f"`{line}`" for line in fancy_lines])

        mono_result = f"```\n{text}\n```"

        result = (
            f"📜 حالت Mono:\n{mono_result}\n\n"
            f"🎨 فونت‌ها:\n{unicode_result}"
        )

        await edit_auto(event, result)

    # ===================== Anti Spam =====================
    @client.on(events.NewMessage)
    async def anti_spam(event):

        if not event.text:
            return

        # ignore commands
        if event.text.startswith("."):
            return

        # ignore private chats
        if event.is_private:
            return

        uid = event.sender_id
        now = time.time()

        q = spam_db[uid]
        q.append(now)

        # remove old messages outside 3s window
        while q and now - q[0] > 3:
            q.popleft()

        # threshold check
        if len(q) >= 6:
            try:
                await event.delete()
            except:
                pass

            q.clear()

    # ===================== DELETE N =====================
    @client.on(events.NewMessage)
    @multi_lang([".حذف ", ".delete "])
    async def delete_number(event):

        if not await owner_only(event):
            return

        try:
            limit = int(re.findall(r"\d+", event.raw_text)[0])
        except:
            return await edit_auto(event, "❌ عدد معتبر نیست")

        msg = await edit_auto(event, "⏳ در حال پاکسازی پیام‌ها ...")

        revoke = event.is_private or await can_delete_all(client, event.chat_id)

        collected = []
        deleted_total = 0

        async for message in client.iter_messages(event.chat_id):

            if message.id == event.id:
                continue

        # اگر ادمین نیستی فقط پیام‌های خودت
            if not revoke and message.sender_id != (await client.get_me()).id:
                continue

            collected.append(message.id)
    
            if len(collected) >= 100:
                deleted_total += await delete_fast(client, event.chat_id, collected, revoke)
                collected.clear()

            if deleted_total >= limit:
                break

        if collected:
            deleted_total += await delete_fast(client, event.chat_id, collected, revoke)

        await edit_auto(event, f"✅ حذف شد: {deleted_total}")

    # ===================== DELETE ALL =====================
    @client.on(events.NewMessage)
    @multi_lang([".حذف همه", ".delete all"])
    async def delete_all(event):

        if not await owner_only(event):
            return

        await edit_auto(event, "⏳ در حال پاکسازی کامل پیام‌ها ...")

        revoke = event.is_private or await can_delete_all(client, event.chat_id)

        collected = []
        deleted_total = 0

        async for message in client.iter_messages(event.chat_id):

            if message.id == event.id:
                continue

            if not revoke and message.sender_id != (await client.get_me()).id:
                continue

            collected.append(message.id)

            if len(collected) >= 100:
                deleted_total += await delete_fast(client, event.chat_id, collected, revoke)
            collected.clear()
    
        if collected:
            deleted_total += await delete_fast(client, event.chat_id, collected, revoke)

        await edit_auto(event, f"✅ حذف کامل انجام شد: {deleted_total}")
