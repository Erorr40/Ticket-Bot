import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, Select
from discord import ButtonStyle, Interaction, app_commands, CategoryChannel, SelectOption, PermissionOverwrite, File
import json
import os
import asyncio
import io

CONFIG_FILE = "config.json"
TICKET_FILE = "tickets.json"

def load_json(filename, default_data=None):
    """Loads data from a JSON file."""
    if default_data is None:
        default_data = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding='utf-8') as f:
                content = f.read()
                if not content:
                    return default_data
                f.seek(0)
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Warning: {filename} contains invalid JSON or is empty.")
            return default_data
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
            return default_data
    return default_data

def save_json(filename, data):
    """Saves data to a JSON file."""
    try:
        if isinstance(data, dict):
            data_to_save = {str(k): v for k, v in data.items()}
        else:
            data_to_save = data
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving {filename}: {e}")
        return False

config = load_json(CONFIG_FILE, {
    "bot_token": None, "guild_id": None, "moderator_role_id": None,
    "ticket_prefix": "ticket-", "active_categories": {}
})

if not config.get("bot_token") or not config.get("guild_id"):
    print("❌ Error: bot_token or guild_id is missing in config.json!")
    if not os.path.exists(CONFIG_FILE):
        print("🔧 Creating default config.json. Please fill in bot_token and guild_id.")
        save_json(CONFIG_FILE, {
            "bot_token": "التوكن_الحقيقي_بتاعك_هنا",
            "guild_id": 0,
            "moderator_role_id": None,
            "ticket_prefix": "ticket-",
            "active_categories": {}
        })
    exit()

BOT_TOKEN = config["bot_token"]
try:
    GUILD_ID = int(config["guild_id"])
except (ValueError, TypeError):
    print(f"❌ Error: guild_id '{config.get('guild_id')}' in config.json is not a valid integer!")
    exit()

MOD_ROLE_ID = None
mod_role_id_raw = config.get("moderator_role_id")
if mod_role_id_raw:
    try:
        MOD_ROLE_ID = int(mod_role_id_raw)
    except (ValueError, TypeError):
        print(f"⚠️ Warning: moderator_role_id '{mod_role_id_raw}' in config.json is not a valid integer. Ignoring.")

TICKET_PREFIX = config.get("ticket_prefix", "ticket-")

ticket_data = load_json(TICKET_FILE, {})

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

class TicketOpenView(View):
    def __init__(self):
        super().__init__(timeout=None)

class CategorySelect(Select):
    def __init__(self, user_id):
        self.user_id = user_id
        options = []
        current_config = load_json(CONFIG_FILE)
        active_categories = current_config.get("active_categories", {})
        if not active_categories:
             options.append(SelectOption(label="لا توجد أقسام متاحة حالياً", value="no_category", emoji="⚠️"))
        else:
            for key, cat_info in active_categories.items():
                category_emoji = cat_info.get("emoji")
                options.append(SelectOption(
                    label=cat_info.get("name", key),
                    value=key,
                    emoji=category_emoji
                ))
        super().__init__(placeholder="اختر قسم التذكرة...", min_values=1, max_values=1, options=options, custom_id="category_select")

    async def callback(self, interaction: Interaction):
        if not interaction.guild or interaction.guild.id != GUILD_ID: return
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("لا يمكنك اختيار قسم لتذكرة مستخدم آخر.", ephemeral=True)
            return

        selected_category_key = self.values[0]
        if selected_category_key == "no_category":
             await interaction.response.edit_message(content="لا توجد أقسام تذاكر معرفة حالياً. يرجى التواصل مع الإدارة.", view=None)
             return

        await interaction.response.defer(ephemeral=True, thinking=True)
        user = interaction.user
        guild = interaction.guild

        current_tickets = load_json(TICKET_FILE)
        current_config_check = load_json(CONFIG_FILE)

        all_archive_category_ids = set()
        for cat_data in current_config_check.get("active_categories", {}).values():
            if cat_data.get("archive_category_id"):
                try:
                    all_archive_category_ids.add(int(cat_data["archive_category_id"]))
                except (ValueError, TypeError):
                    pass

        existing_ticket_channel_id = None
        for chan_id_str, ticket_info in list(current_tickets.items()):
            if ticket_info.get("user_id") == user.id:
                try:
                    chan_id = int(chan_id_str)
                    existing_channel = guild.get_channel(chan_id)
                    if existing_channel:
                        if existing_channel.category_id not in all_archive_category_ids:
                            existing_ticket_channel_id = chan_id
                            break
                        else:
                            print(f"Ticket channel {chan_id} for user {user.id} found but is archived. Cleaning data.")
                            if chan_id_str in current_tickets:
                                del current_tickets[chan_id_str]
                                save_json(TICKET_FILE, current_tickets)
                    else:
                        print(f"Orphaned ticket data found for user {user.id}, channel {chan_id} not found. Cleaning.")
                        if chan_id_str in current_tickets:
                            del current_tickets[chan_id_str]
                            save_json(TICKET_FILE, current_tickets)
                except (ValueError, TypeError):
                    print(f"Invalid channel ID key '{chan_id_str}' found during check. Cleaning.")
                    if chan_id_str in current_tickets:
                        del current_tickets[chan_id_str]
                        save_json(TICKET_FILE, current_tickets)

        if existing_ticket_channel_id:
            await interaction.followup.send(f"❌ لديك تذكرة مفتوحة بالفعل: <#{existing_ticket_channel_id}>", ephemeral=True)
            try: await interaction.message.edit(content="لديك تذكرة مفتوحة بالفعل.", view=None)
            except discord.NotFound: pass
            except Exception as e_edit: print(f"Error editing interaction message on existing ticket: {e_edit}")
            return

        current_config = load_json(CONFIG_FILE)
        category_config = current_config.get("active_categories", {}).get(selected_category_key)
        if not category_config or not category_config.get("category_id"):
            await interaction.followup.send(f"❌ خطأ: القسم المختار '{selected_category_key}' غير معرف بشكل صحيح.", ephemeral=True)
            try: await interaction.message.edit(content="حدث خطأ في اختيار القسم.", view=None)
            except: pass
            return

        target_category_id = category_config["category_id"]
        target_category = guild.get_channel(target_category_id)
        if not target_category or not isinstance(target_category, CategoryChannel):
            print(f"⚠️ Warning: Active Category ID {target_category_id} for key '{selected_category_key}' not found or not a category.")
            await interaction.followup.send(f"❌ خطأ: لم يتم العثور على الـ Category النشطة لقسم '{category_config.get('name', selected_category_key)}'.", ephemeral=True)
            try: await interaction.message.edit(content="حدث خطأ في العثور على فئة القسم.", view=None)
            except: pass
            return

        mod_role = guild.get_role(MOD_ROLE_ID) if MOD_ROLE_ID else None
        if not mod_role: print(f"⚠️ Warning: Moderator role {MOD_ROLE_ID} not found or not set.")

        overwrites = {
            guild.default_role: PermissionOverwrite(read_messages=False, view_channel=False),
            user: PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, view_channel=True),
            bot.user: PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True, embed_links=True, attach_files=True, view_channel=True)
        }
        if mod_role:
            overwrites[mod_role] = PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True, embed_links=True, attach_files=True, view_channel=True, manage_channels=False)

        try:
            clean_user_name = "".join(c for c in user.name if c.isalnum() or c in ('-', '_')).lower()
            if not clean_user_name: clean_user_name = str(user.id)
            channel_name = f"{TICKET_PREFIX}{clean_user_name}-{selected_category_key}"[:100]
            channel = await guild.create_text_channel(
                channel_name,
                overwrites=overwrites,
                category=target_category,
                topic=f"Ticket for {user.name} ({user.id}) | Section: {category_config.get('name', selected_category_key)}",
                reason=f"Ticket opened by {user.name} ({user.id}) for section {selected_category_key}"
            )
        except discord.errors.Forbidden:
            print(f"❌ Bot lacks permission to create channels in category {target_category_id}.")
            await interaction.followup.send("❌ ليس لدى البوت صلاحية إنشاء قنوات في الفئة المحددة!", ephemeral=True)
            try: await interaction.message.edit(content="حدث خطأ في صلاحيات البوت.", view=None)
            except: pass
            return
        except Exception as e:
            print(f"❌ Error creating channel for {user.name}: {e}")
            await interaction.followup.send("❌ حدث خطأ أثناء محاولة إنشاء القناة.", ephemeral=True)
            try: await interaction.message.edit(content="حدث خطأ غير متوقع.", view=None)
            except: pass
            return

        current_tickets = load_json(TICKET_FILE)
        current_tickets[str(channel.id)] = {
            "user_id": user.id,
            "category_key": selected_category_key
        }
        save_json(TICKET_FILE, current_tickets)

        category_display_name = category_config.get('name', selected_category_key)
        category_emoji = category_config.get('emoji')
        title_prefix = f"{category_emoji} " if category_emoji else "🎟️ "
        welcome_embed = discord.Embed(
            title=f"{title_prefix}تذكرة {category_display_name} جديدة!",
            description=f"مرحباً {user.mention}!\n\nالرجاء شرح مشكلتك.\nسيقوم أحد أعضاء فريق الدعم ({mod_role.mention if mod_role else 'المشرفين'}) بالرد عليك.\n\nيمكنك الرد على رسالة البوت في الخاص للتواصل.",
            color=discord.Color.green()
        )
        welcome_embed.set_footer(text="لإغلاق التذكرة، استخدم أمر /close")
        mention_message = f"{user.mention}" + (f" {mod_role.mention}" if mod_role else "")
        await channel.send(mention_message, embed=welcome_embed)

        try:
            dm_embed = discord.Embed(title="📨 تم فتح التذكرة!", description=f"تم فتح تذكرة لك في **{guild.name}** قسم **{category_display_name}**.\nالقناة: <#{channel.id}>\nيمكنك الرد على هذه الرسالة مباشرة.", color=discord.Color.green())
            await user.send(embed=dm_embed)
        except discord.errors.Forbidden:
            print(f"Could not send DM to {user.name}.")
            await channel.send(f"⚠️ {user.mention} لم أتمكن من إرسال رسالة لك في الخاص.", delete_after=60)

        await interaction.followup.send(f"✅ تم فتح التذكرة بنجاح! <#{channel.id}>", ephemeral=True)
        try:
            await interaction.message.edit(content=f"تم فتح تذكرتك في قسم **{category_display_name}**: <#{channel.id}>", view=None)
        except discord.NotFound:
            print("Original interaction message not found for editing.")
        except Exception as e:
            print(f"Error editing original interaction message: {e}")

class SetupModal(Modal, title="إعداد رسالة التيكت"):
    def __init__(self):
        super().__init__(timeout=None)
        self.main_message = TextInput(label="📌 الرسالة الأساسية", placeholder="اكتب هنا الرسالة التي ستظهر فوق الزر...", style=discord.TextStyle.paragraph, required=True, max_length=1000)
        self.embed_description = TextInput(label="📄 وصف Embed (اختياري)", placeholder="اكتب هنا الوصف الذي سيظهر داخل الـ Embed...", style=discord.TextStyle.paragraph, required=False, max_length=2000)
        self.embed_title = TextInput(label="👑 عنوان Embed (اختياري)", placeholder="اكتب هنا عنوان الـ Embed...", required=False, max_length=256)
        self.button_text = TextInput(label="🔤 نص الزر", placeholder="مثال: افتح تذكرة", required=True, max_length=80)
        self.button_color = TextInput(label="🎨 لون الزر (green, red, blue, grey)", placeholder="green", required=False, max_length=5)
        self.add_item(self.main_message); self.add_item(self.embed_title); self.add_item(self.embed_description); self.add_item(self.button_text); self.add_item(self.button_color)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        color_map = {"red": ButtonStyle.red, "blue": ButtonStyle.blurple, "grey": ButtonStyle.grey, "green": ButtonStyle.green}
        button_style = color_map.get(self.button_color.value.lower().strip(), ButtonStyle.green)
        view = TicketOpenView()
        button = Button(label=self.button_text.value, style=button_style, custom_id="persistent_open_ticket_button")
        view.add_item(button)
        content_to_send = self.main_message.value if self.main_message.value else None
        embed_to_send = None
        if self.embed_description.value or self.embed_title.value:
            embed_to_send = discord.Embed(title=self.embed_title.value, description=self.embed_description.value, color=discord.Color.blue())
        try:
            if embed_to_send: await interaction.channel.send(content=content_to_send, embed=embed_to_send, view=view)
            elif content_to_send: await interaction.channel.send(content=content_to_send, view=view)
            else: await interaction.channel.send(view=view)
            await interaction.followup.send("✅ تم إعداد رسالة فتح التيكت بنجاح!", ephemeral=True)
        except discord.errors.Forbidden:
            await interaction.followup.send("❌ ليس لدى البوت صلاحية الإرسال في هذه القناة!", ephemeral=True)
        except Exception as e_send:
            print(f"Error sending setup message: {e_send}")
            await interaction.followup.send("❌ حدث خطأ أثناء إرسال الرسالة.", ephemeral=True)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        print(f"Error in SetupModal: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ حدث خطأ أثناء معالجة الإعداد.", ephemeral=True)
        else:
            await interaction.followup.send("❌ حدث خطأ أثناء معالجة الإعداد.", ephemeral=True)

@bot.tree.command(name="setup", description="إرسال رسالة فتح تيكت مخصصة مع زر")
@app_commands.checks.has_permissions(manage_guild=True)
async def setup_command(interaction: discord.Interaction):
    await interaction.response.send_modal(SetupModal())

@setup_command.error
async def setup_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        if not interaction.response.is_done(): await interaction.response.send_message("❌ ليس لديك صلاحية `Manage Server`.", ephemeral=True)
        else: await interaction.followup.send("❌ ليس لديك صلاحية `Manage Server`.", ephemeral=True)
    else:
        print(f"Error in setup command: {error}")
        if not interaction.response.is_done(): await interaction.response.send_message("❌ خطأ غير متوقع.", ephemeral=True)
        else: await interaction.followup.send("❌ خطأ غير متوقع.", ephemeral=True)

@bot.tree.command(name="ctc", description="إنشاء قسم تيكت جديد مع فئة أرشيف خاصة به")
@app_commands.describe(
    internal_key="المعرف الداخلي (انجليزي بدون مسافات)",
    display_name="اسم القسم الظاهر للمستخدم",
    emoji="الأيقونة (Emoji) التي ستظهر بجانب اسم القسم (اختياري)"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def create_ticket_category(interaction: discord.Interaction, internal_key: str, display_name: str, emoji: str = None):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    current_config = load_json(CONFIG_FILE)
    active_categories = current_config.get("active_categories", {})

    internal_key = internal_key.lower().strip().replace(" ", "_")
    if not internal_key:
        await interaction.followup.send("❌ المعرف الداخلي لا يمكن أن يكون فارغًا.", ephemeral=True); return
    if internal_key in active_categories:
        await interaction.followup.send(f"❌ المعرف الداخلي '{internal_key}' مستخدم بالفعل.", ephemeral=True); return

    mod_role = guild.get_role(MOD_ROLE_ID) if MOD_ROLE_ID else None

    active_overwrites = {
        guild.default_role: PermissionOverwrite(read_messages=False, view_channel=False),
        bot.user: PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, view_channel=True)
    }
    if mod_role:
        active_overwrites[mod_role] = PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, view_channel=True)

    new_active_category = None
    new_archive_category = None
    try:
        active_category_name = f"{emoji} {display_name}" if emoji else display_name
        new_active_category = await guild.create_category(
            name=active_category_name[:100],
            overwrites=active_overwrites,
            reason=f"Active ticket category created by {interaction.user.name}"
        )
        print(f"✅ Created active category: {new_active_category.name} ({new_active_category.id})")
    except discord.errors.Forbidden:
        await interaction.followup.send("❌ ليس لدى البوت صلاحية إنشاء Categories!", ephemeral=True); return
    except Exception as e:
        print(f"❌ Error creating active Discord category: {e}")
        await interaction.followup.send("❌ حدث خطأ أثناء إنشاء الـ Category النشطة.", ephemeral=True); return

    archive_overwrites = {
        guild.default_role: PermissionOverwrite(read_messages=False, view_channel=False),
        bot.user: PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, view_channel=True)
    }
    if mod_role:
        archive_overwrites[mod_role] = PermissionOverwrite(read_messages=True, send_messages=False, manage_channels=True, view_channel=True)

    try:
        archive_category_name = f"📦 Archived - {display_name}"[:100]
        new_archive_category = await guild.create_category(
            name=archive_category_name,
            overwrites=archive_overwrites,
            reason=f"Archive category for '{display_name}' created by {interaction.user.name}"
        )
        print(f"✅ Created archive category: {new_archive_category.name} ({new_archive_category.id})")
    except discord.errors.Forbidden:
        await interaction.followup.send("❌ تم إنشاء الفئة النشطة، لكن ليس لدى البوت صلاحية إنشاء فئة الأرشيف!", ephemeral=True)
        if new_active_category:
            try: await new_active_category.delete(reason="Failed to create corresponding archive category")
            except: print(f"⚠️ Failed to rollback active category {new_active_category.id}")
        return
    except Exception as e:
        print(f"❌ Error creating archive Discord category: {e}")
        await interaction.followup.send("❌ تم إنشاء الفئة النشطة، لكن حدث خطأ أثناء إنشاء فئة الأرشيف.", ephemeral=True)
        if new_active_category:
            try: await new_active_category.delete(reason="Failed to create corresponding archive category")
            except: print(f"⚠️ Failed to rollback active category {new_active_category.id}")
        return

    active_categories[internal_key] = {
        "name": display_name,
        "category_id": new_active_category.id,
        "emoji": emoji,
        "archive_category_id": new_archive_category.id
    }
    current_config["active_categories"] = active_categories
    if save_json(CONFIG_FILE, current_config):
        global config
        config = current_config
        emoji_text = f" بالأيقونة {emoji}" if emoji else ""
        await interaction.followup.send(
            f"✅ تم إنشاء قسم التذاكر '{display_name}'{emoji_text} بنجاح.\n"
            f"   - الفئة النشطة: {new_active_category.mention} (`{new_active_category.id}`)\n"
            f"   - فئة الأرشيف: {new_archive_category.mention} (`{new_archive_category.id}`)",
            ephemeral=True
        )
    else:
        try: await new_active_category.delete(reason="Failed to save config")
        except: pass
        try: await new_archive_category.delete(reason="Failed to save config")
        except: pass
        await interaction.followup.send("❌ حدث خطأ أثناء حفظ الإعدادات. لم يتم حفظ القسم الجديد وتمت محاولة حذف الفئات.", ephemeral=True)

@create_ticket_category.error
async def create_ticket_category_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
     if isinstance(error, app_commands.MissingPermissions):
         if not interaction.response.is_done(): await interaction.response.send_message("❌ ليس لديك صلاحية `Manage Server`.", ephemeral=True)
         else: await interaction.followup.send("❌ ليس لديك صلاحية `Manage Server`.", ephemeral=True)
     else:
         print(f"Error in create_ticket_category: {error}")
         if not interaction.response.is_done(): await interaction.response.send_message("❌ خطأ غير متوقع.", ephemeral=True)
         else: await interaction.followup.send("❌ خطأ غير متوقع.", ephemeral=True)

@bot.tree.command(name="close", description="إغلاق وأرشفة التيكت الحالي إلى فئته المخصصة")
@app_commands.checks.has_permissions(manage_messages=True)
async def close_ticket(interaction: discord.Interaction):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel) or channel.guild.id != GUILD_ID:
        await interaction.response.send_message("❌ هذا الأمر يعمل فقط في قنوات التيكت النصية داخل السيرفر.", ephemeral=True); return

    channel_id_str = str(channel.id)
    current_tickets = load_json(TICKET_FILE)
    ticket_info = current_tickets.get(channel_id_str)

    if not ticket_info and not channel.name.startswith(TICKET_PREFIX):
         await interaction.response.send_message("❌ هذه القناة لا تبدو كقناة تيكت نشطة.", ephemeral=True); return

    category_key = None
    if ticket_info:
        category_key = ticket_info.get("category_key")
    else:
        parts = channel.name.split('-')
        if len(parts) > 1 and channel.name.startswith(TICKET_PREFIX):
            potential_key = parts[-1]
            temp_config = load_json(CONFIG_FILE)
            if potential_key in temp_config.get("active_categories", {}):
                category_key = potential_key
                print(f"ℹ️ Inferred category key '{category_key}' from channel name for closing.")
            else:
                 await interaction.response.send_message(f"❌ لم أتمكن من تحديد القسم الأصلي للتذكرة من اسمها ('{potential_key}' غير موجود).", ephemeral=True); return
        else:
            await interaction.response.send_message("❌ لم أتمكن من تحديد القسم الأصلي للتذكرة.", ephemeral=True); return

    if not category_key:
        await interaction.response.send_message("❌ لم يتم العثور على مفتاح القسم المرتبط بهذه التذكرة في البيانات.", ephemeral=True); return

    current_config = load_json(CONFIG_FILE)
    category_settings = current_config.get("active_categories", {}).get(category_key)

    if not category_settings:
        await interaction.response.send_message(f"❌ خطأ: إعدادات القسم '{category_key}' غير موجودة في `config.json`.", ephemeral=True); return

    archive_category_id = category_settings.get("archive_category_id")
    if not archive_category_id:
        await interaction.response.send_message(f"❌ خطأ: لم يتم تحديد فئة أرشيف مخصصة للقسم '{category_settings.get('name', category_key)}' في الإعدادات!", ephemeral=True); return

    try:
        archive_category = interaction.guild.get_channel(int(archive_category_id))
        if not archive_category or not isinstance(archive_category, CategoryChannel):
            await interaction.response.send_message(f"❌ خطأ: فئة الأرشيف المخصصة (ID: {archive_category_id}) للقسم '{category_settings.get('name', category_key)}' غير موجودة أو ليست Category صالحة!", ephemeral=True); return
    except (ValueError, TypeError):
         await interaction.response.send_message(f"❌ خطأ: ID فئة الأرشيف المخصصة ('{archive_category_id}') غير صالح في الإعدادات.", ephemeral=True); return
    except discord.NotFound:
         await interaction.response.send_message(f"❌ خطأ: فئة الأرشيف المخصصة (ID: {archive_category_id}) غير موجودة في Discord.", ephemeral=True); return

    if channel.category_id == archive_category.id:
        await interaction.response.send_message("❌ هذه القناة موجودة بالفعل في فئة الأرشيف الخاصة بها.", ephemeral=True); return

    confirm_view = View(timeout=30)
    async def confirm_callback(confirm_interaction: Interaction):
        if confirm_interaction.user.id != interaction.user.id:
            await confirm_interaction.response.send_message("فقط المستخدم الذي بدأ الأمر يمكنه التأكيد.", ephemeral=True); return

        await confirm_interaction.response.edit_message(content=f"⏳ جارٍ أرشفة التيكت {channel.mention} إلى {archive_category.mention}...", view=None)

        user_id = ticket_info.get("user_id") if ticket_info else None
        original_user = interaction.guild.get_member(user_id) if user_id else None

        new_overwrites = channel.overwrites.copy()
        if original_user:
             new_overwrites[original_user] = PermissionOverwrite(read_messages=True, send_messages=False, view_channel=True)
        new_overwrites[interaction.guild.default_role] = PermissionOverwrite(send_messages=False, view_channel=False)
        mod_role = interaction.guild.get_role(MOD_ROLE_ID) if MOD_ROLE_ID else None
        if mod_role:
             new_overwrites[mod_role] = PermissionOverwrite(read_messages=True, send_messages=False, manage_channels=True, view_channel=True)
        new_overwrites[bot.user] = PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, view_channel=True)

        try:
            base_name = channel.name.replace(TICKET_PREFIX, "", 1)
            new_name = f"archived-{base_name}"[:100]
            await channel.edit(
                name=new_name,
                category=archive_category,
                overwrites=new_overwrites,
                sync_permissions=False,
                reason=f"Ticket archived by {interaction.user.name} to category {category_key}"
            )
        except discord.errors.Forbidden:
            await confirm_interaction.followup.send("❌ ليس لدى البوت صلاحية نقل القناة أو تعديل صلاحياتها!", ephemeral=True); return
        except Exception as e:
            print(f"Error archiving channel {channel.id} to category {archive_category.id}: {e}")
            await confirm_interaction.followup.send("❌ حدث خطأ أثناء أرشفة القناة.", ephemeral=True); return

        current_tickets_on_confirm = load_json(TICKET_FILE)
        if channel_id_str in current_tickets_on_confirm:
            del current_tickets_on_confirm[channel_id_str]
            save_json(TICKET_FILE, current_tickets_on_confirm)

        if original_user:
            try:
                await original_user.send(f"✅ تم إغلاق وأرشفة التيكت الخاص بك (قسم {category_settings.get('name', category_key)}) في سيرفر **{interaction.guild.name}** بواسطة {interaction.user.mention}.")
            except discord.errors.Forbidden: print(f"Could not notify user {user_id} about ticket archival (DM closed).")
            except Exception as e_dm: print(f"Error notifying user {user_id} about ticket archival: {e_dm}")

        await confirm_interaction.followup.send(f"✅ تم أرشفة التيكت {channel.mention} إلى {archive_category.mention} بنجاح.", ephemeral=True)

    async def cancel_callback(cancel_interaction: Interaction):
         if cancel_interaction.user.id != interaction.user.id:
             await cancel_interaction.response.send_message("فقط المستخدم الذي بدأ الأمر يمكنه الإلغاء.", ephemeral=True); return
         await cancel_interaction.response.edit_message(content="👍 تم إلغاء عملية أرشفة التيكت.", view=None)

    confirm_button = Button(label="✅ تأكيد الأرشفة", style=ButtonStyle.red, custom_id="confirm_archive_action")
    cancel_button = Button(label="❌ إلغاء", style=ButtonStyle.grey, custom_id="cancel_archive_action")
    confirm_button.callback = confirm_callback
    cancel_button.callback = cancel_callback
    confirm_view.add_item(confirm_button)
    confirm_view.add_item(cancel_button)
    await interaction.response.send_message(f"❓ هل أنت متأكد من إغلاق وأرشفة التيكت {channel.mention}؟ سيتم نقله إلى {archive_category.mention}.", view=confirm_view, ephemeral=True)

@close_ticket.error
async def close_ticket_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
     if isinstance(error, app_commands.MissingPermissions):
         if not interaction.response.is_done(): await interaction.response.send_message("❌ ليس لديك صلاحية `Manage Messages`.", ephemeral=True)
         else: await interaction.followup.send("❌ ليس لديك صلاحية `Manage Messages`.", ephemeral=True)
     else:
         print(f"Error in close command: {error}")
         if not interaction.response.is_done(): await interaction.response.send_message("❌ خطأ غير متوقع.", ephemeral=True)
         else: await interaction.followup.send("❌ خطأ غير متوقع.", ephemeral=True)

@bot.tree.command(name="r", description="رد على المستخدم صاحب التيكت في رسائله الخاصة")
@app_commands.describe(message="الرسالة التي تريد إرسالها للمستخدم")
@app_commands.checks.has_permissions(manage_messages=True)
async def reply_to_user(interaction: discord.Interaction, message: str):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel) or not channel.guild or channel.guild.id != GUILD_ID:
        await interaction.response.send_message("❌ هذا الأمر يعمل فقط في قنوات التيكت النصية داخل السيرفر.", ephemeral=True); return

    channel_id_str = str(channel.id)
    current_tickets = load_json(TICKET_FILE)
    ticket_info = current_tickets.get(channel_id_str)

    if not ticket_info or not ticket_info.get("user_id"):
        await interaction.response.send_message("❌ هذه القناة لا تبدو كقناة تيكت نشطة أو أنها مؤرشفة.", ephemeral=True)
        return

    user_id = ticket_info["user_id"]
    target_user = None
    try:
        target_user = await bot.fetch_user(user_id)
    except discord.NotFound:
        await interaction.response.send_message(f"❌ لم يتم العثور على المستخدم (ID: {user_id}).", ephemeral=True); return
    except Exception as e_fetch:
        print(f"Error fetching user {user_id}: {e_fetch}")
        await interaction.response.send_message(f"❌ خطأ أثناء محاولة الوصول للمستخدم (ID: {user_id}).", ephemeral=True); return

    staff_member = interaction.user
    embed_to_user = discord.Embed(description=message, color=discord.Color.blue())
    embed_to_user.set_author(name=f"رد من فريق الدعم ({staff_member.display_name})", icon_url=staff_member.display_avatar.url if staff_member.display_avatar else None)
    embed_to_user.set_footer(text=f"من سيرفر: {interaction.guild.name} | قناة: #{channel.name}")
    embed_to_user.timestamp = discord.utils.utcnow()

    try:
        await target_user.send(embed=embed_to_user)
    except discord.errors.Forbidden:
        await interaction.response.send_message(f"❌ لا يمكن إرسال الرسالة إلى {target_user.mention} (الخاص مغلق أو قام بحظر البوت).", ephemeral=True)
        await channel.send(f"⚠️ لم يتمكن البوت من إرسال الرد للخاص للمستخدم {target_user.mention}. رسالة من {staff_member.mention}:\n>>> {message}")
        return
    except Exception as e:
        print(f"Error DM reply: {e}")
        await interaction.response.send_message("❌ خطأ أثناء إرسال الرسالة للخاص.", ephemeral=True)
        return

    embed_in_channel = discord.Embed(description=message, color=discord.Color.green())
    embed_in_channel.set_author(name=f"⬆️ رسالة أُرسلت إلى {target_user.name} بواسطة {staff_member.display_name}", icon_url=staff_member.display_avatar.url if staff_member.display_avatar else None)
    embed_in_channel.timestamp = discord.utils.utcnow()
    await channel.send(embed=embed_in_channel)
    await interaction.response.send_message("✅ تم إرسال الرد للمستخدم بنجاح.", ephemeral=True)

@reply_to_user.error
async def reply_to_user_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
     if isinstance(error, app_commands.MissingPermissions):
         if not interaction.response.is_done(): await interaction.response.send_message("❌ ليس لديك صلاحية `Manage Messages`.", ephemeral=True)
         else: await interaction.followup.send("❌ ليس لديك صلاحية `Manage Messages`.", ephemeral=True)
     else:
         print(f"Error in reply command: {error}")
         if not interaction.response.is_done(): await interaction.response.send_message("❌ خطأ غير متوقع.", ephemeral=True)
         else: await interaction.followup.send("❌ خطأ غير متوقع.", ephemeral=True)

@bot.tree.command(name="ping", description="عرض سرعة استجابة البوت (البنج)")
async def ping(interaction: discord.Interaction):
    """Calculates and displays the bot's latency."""
    latency_ms = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"سرعة استجابة البوت: **{latency_ms}ms**",
        color=discord.Color.green() if latency_ms < 150 else (discord.Color.orange() if latency_ms < 300 else discord.Color.red())
    )
    try:
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Error sending ping response: {e}")
        try:
            await interaction.response.send_message(f"Pong! {latency_ms}ms", ephemeral=True)
        except Exception as e_fallback:
             print(f"Failed to send fallback ping response: {e_fallback}")

@ping.error
async def ping_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handles errors for the ping command."""
    print(f"Error in ping command: {error}")
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ حدث خطأ أثناء حساب البنج.", ephemeral=True)
        else:
            await interaction.followup.send("❌ حدث خطأ أثناء حساب البنج.", ephemeral=True)
    except Exception as e_handler:
        print(f"Error within ping error handler: {e_handler}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name} ({bot.user.id})")
    print(f"🔗 Invite Link: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands")
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print(f"❌ Error: Bot not in specified guild {GUILD_ID}.")
        await bot.close(); return
    else:
        print(f"🌍 Operating in guild: {guild.name} ({guild.id})")

        current_config = load_json(CONFIG_FILE)
        current_ticket_data = load_json(TICKET_FILE)

        all_archive_category_ids = set()
        for cat_data in current_config.get("active_categories", {}).values():
            if cat_data.get("archive_category_id"):
                try:
                    all_archive_category_ids.add(int(cat_data["archive_category_id"]))
                except (ValueError, TypeError):
                    print(f"⚠️ Invalid archive category ID '{cat_data['archive_category_id']}' found in config during startup cleanup.")

        print(f"🔍 Found {len(all_archive_category_ids)} potential archive category IDs for cleanup: {all_archive_category_ids}")

        tickets_to_remove = []
        for channel_id_str, ticket_info in list(current_ticket_data.items()):
             try:
                 channel_id = int(channel_id_str)
                 channel = guild.get_channel(channel_id)
                 if not channel:
                     print(f"🧹 Ticket channel {channel_id} (from data) not found. Removing.")
                     tickets_to_remove.append(channel_id_str)
                 elif channel.category_id in all_archive_category_ids:
                     print(f"🧹 Ticket channel {channel_id} is in an archive category ({channel.category_id}). Removing from active data.")
                     tickets_to_remove.append(channel_id_str)
             except (ValueError, TypeError):
                  print(f"🧹 Invalid channel ID key '{channel_id_str}' in tickets.json. Removing.")
                  tickets_to_remove.append(channel_id_str)
             except discord.NotFound:
                  print(f"🧹 Ticket channel {channel_id_str} (from data) caused NotFound error. Removing.")
                  tickets_to_remove.append(channel_id_str)

        if tickets_to_remove:
            updated_data = current_ticket_data.copy()
            for channel_id_str_to_remove in tickets_to_remove:
                if channel_id_str_to_remove in updated_data:
                    del updated_data[channel_id_str_to_remove]
            if save_json(TICKET_FILE, updated_data):
                 print(f"✅ Removed {len(tickets_to_remove)} inactive/invalid ticket entries from {TICKET_FILE}.")
            else:
                 print(f"❌ Failed to save cleaned ticket data to {TICKET_FILE}.")

    try:
        guild_obj = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} commands to guild {GUILD_ID}.")
    except discord.errors.Forbidden as e_sync_forbidden:
        print(f"❌ Failed to sync commands: {e_sync_forbidden}")
    except Exception as e_sync:
        print(f"❌ Failed to sync commands: {e_sync}")

    view_to_register = TicketOpenView()
    view_to_register.add_item(Button(label="Open Ticket", style=ButtonStyle.secondary, custom_id="persistent_open_ticket_button"))
    bot.add_view(view_to_register, message_id=None)
    print("🔘 Persistent 'Open Ticket' button view registered.")

@bot.event
async def on_interaction(interaction: Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id") if interaction.data else None
        if custom_id == "persistent_open_ticket_button":
            view = View(timeout=180)
            view.add_item(CategorySelect(interaction.user.id))
            await interaction.response.send_message("يرجى اختيار القسم المطلوب لفتح التذكرة:", view=view, ephemeral=True)
            return

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.webhook_id: return
    guild = bot.get_guild(GUILD_ID)
    if not guild: return

    current_tickets = load_json(TICKET_FILE)
    current_config = load_json(CONFIG_FILE)

    if message.guild and message.guild.id == GUILD_ID and isinstance(message.channel, discord.TextChannel):
        channel_id_str = str(message.channel.id)
        ticket_info = current_tickets.get(channel_id_str)

        if ticket_info and ticket_info.get("user_id"):
            user_id = ticket_info["user_id"]
            try:
                if message.author.id != user_id:
                    target_user = await bot.fetch_user(user_id)
                    embed_to_user = discord.Embed(description=message.content if message.content else "[رسالة فارغة]", color=discord.Color.orange())
                    embed_to_user.set_author(name=f"رسالة من {message.author.display_name} في تذكرتك", icon_url=message.author.display_avatar.url if message.author.display_avatar else None)
                    embed_to_user.set_footer(text=f"من سيرفر: {guild.name} | قناة: #{message.channel.name}")
                    embed_to_user.timestamp = message.created_at

                    attachment_urls = [att.url for att in message.attachments]
                    if attachment_urls:
                         image_url = next((url for url in attachment_urls if url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))), None)
                         if image_url: embed_to_user.set_image(url=image_url)
                         attach_field_value = "\n".join(f"{att.filename}" for att in message.attachments)
                         embed_to_user.add_field(name="📎 مرفقات", value=attach_field_value if attach_field_value else "لا يوجد", inline=False)

                    try:
                        await target_user.send(embed=embed_to_user)
                    except discord.errors.Forbidden:
                        await message.channel.send(f"⚠️ لم أتمكن من إرسال إشعار لـ <@{user_id}> (الخاص مغلق).", delete_after=30, allowed_mentions=discord.AllowedMentions.none())
                    except Exception as e_dm:
                        print(f"Error sending channel msg to DM ({user_id}): {e_dm}")
            except discord.NotFound: print(f"User {user_id} (from ticket data) not found.")
            except Exception as e_proc_ch: print(f"Error processing channel message for ticket {channel_id_str}: {e_proc_ch}")
        return

    if isinstance(message.channel, discord.DMChannel):
        user = message.author
        user_id_to_find = user.id
        target_channel_id = None
        target_channel = None

        all_archive_category_ids_dm = set()
        for cat_data in current_config.get("active_categories", {}).values():
            if cat_data.get("archive_category_id"):
                try: all_archive_category_ids_dm.add(int(cat_data["archive_category_id"]))
                except (ValueError, TypeError): pass

        for chan_id_str, ticket_info in current_tickets.items():
            if ticket_info.get("user_id") == user_id_to_find:
                try:
                    chan_id = int(chan_id_str)
                    potential_channel = guild.get_channel(chan_id)
                    if potential_channel and potential_channel.category_id not in all_archive_category_ids_dm:
                         target_channel_id = chan_id
                         target_channel = potential_channel
                         break
                except (ValueError, TypeError, discord.NotFound): continue

        if target_channel:
            embed_to_channel = discord.Embed(description=message.content if message.content else "[رسالة فارغة]", color=discord.Color.purple())
            embed_to_channel.set_author(name=f"💬 رسالة من {user.display_name} ({user.name}) عبر الخاص", icon_url=user.display_avatar.url if user.display_avatar else None)
            embed_to_channel.timestamp = message.created_at

            files_to_send = []
            attachment_links_text = []
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.size < 8 * 1024 * 1024:
                        try:
                            file_bytes = await attachment.read()
                            files_to_send.append(File(io.BytesIO(file_bytes), filename=attachment.filename))
                        except Exception as e_attach:
                            print(f"Could not forward attachment {attachment.filename}: {e_attach}")
                            attachment_links_text.append(f"{attachment.filename} (خطأ في القراءة)")
                    else:
                        attachment_links_text.append(f"{attachment.filename} (حجم كبير)")

                if attachment_links_text:
                    embed_to_channel.add_field(name="📎 مرفقات (روابط/أخطاء)", value="\n".join(attachment_links_text), inline=False)

            try:
                await target_channel.send(embed=embed_to_channel, files=files_to_send if files_to_send else None)
                await message.add_reaction("✅")
            except discord.errors.Forbidden:
                await user.send(f"❌ عذراً، لم أتمكن من إرسال رسالتك إلى القناة {target_channel.mention}.")
            except Exception as e_send_ch:
                print(f"Error sending DM message to channel {target_channel_id}: {e_send_ch}")
                await message.add_reaction("❌")
        else:
            pass
        return

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "التوكن_الحقيقي_بتاعك_هنا":
        print("❌ Error: Bot token missing or placeholder in config.json!")
    else:
        try:
            bot.run(BOT_TOKEN)
        except discord.errors.LoginFailure: print("❌ Error: Failed to log in. Check bot_token.")
        except discord.errors.PrivilegedIntentsRequired: print("❌ Error: Privileged Gateway Intents not enabled!")
        except Exception as e: print(f"❌ An unexpected error occurred: {e}")
        