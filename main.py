import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import datetime
import asyncio
from typing import Optional, Dict

import config
from database import Database, Application
from rcon_client import RconClient
from utils import validate_minecraft_nickname, validate_age, validate_text_length, create_application_embed

# Initialize database and RCON client
db = Database(config.DB_PATH)
rcon = RconClient(config.RCON_HOST, config.RCON_PORT, config.RCON_PASSWORD)

# Хранилище временных данных заявок
application_temp_data = {}

# Initialize Discord bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


class RulesConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 минут таймаут

    @discord.ui.button(label="Я согласен с правилами", style=discord.ButtonStyle.primary)
    async def confirm_rules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Открываем первую часть формы заявки
        application_modal_part1 = ApplicationModalPart1()
        await interaction.response.send_modal(application_modal_part1)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Операция отменена.", ephemeral=True)


# Первая часть формы заявки
class ApplicationModalPart1(Modal, title="Заявка на сервер Minecraft (1/2)"):
    minecraft_nickname = TextInput(
        label="Ник в Minecraft",
        placeholder="Введите ник (3-16 символов, латиница)",
        min_length=3,
        max_length=16,
        required=True
    )

    age = TextInput(
        label="Возраст",
        placeholder="Укажите возраст (минимум 14 лет)",
        min_length=1,
        max_length=3,
        required=True
    )

    experience = TextInput(
        label="Опыт игры",
        placeholder="Сколько играете в Minecraft и на каких серверах играли?",
        min_length=200,
        style=discord.TextStyle.paragraph,
        required=True
    )

    has_microphone = TextInput(
        label="Наличие микрофона",
        placeholder="Да / Нет / Планирую приобрести",
        min_length=2,
        max_length=20,
        required=True
    )

    motivation = TextInput(
        label="Почему хотите играть на сервере",
        placeholder="Минимум 300 символов",
        min_length=300,
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction: discord.Interaction):
        # Validate inputs
        if not validate_minecraft_nickname(self.minecraft_nickname.value):
            await interaction.response.send_message(
                "Ник должен содержать только латинские буквы, цифры и символ подчеркивания, длиной от 3 до 16 символов.",
                ephemeral=True
            )
            return

        if not validate_age(self.age.value):
            await interaction.response.send_message(
                "Минимальный возраст для игры на сервере - 14 лет.",
                ephemeral=True
            )
            return

        # Check if user can submit a new application
        can_submit, error_message = db.can_submit_new_application(interaction.user.id)
        if not can_submit:
            await interaction.response.send_message(error_message, ephemeral=True)
            return

        # Сохраняем данные первой части формы во временное хранилище
        application_temp_data[interaction.user.id] = {
            "minecraft_nickname": self.minecraft_nickname.value,
            "age": int(self.age.value),
            "experience": self.experience.value,
            "has_microphone": self.has_microphone.value,
            "motivation": self.motivation.value,
        }

        # Открываем вторую часть формы
        application_modal_part2 = ApplicationModalPart2()
        await interaction.response.send_message(
            "Продолжите заполнение заявки. Нажмите на кнопку ниже:",
            view=ApplicationPart2Button(),
            ephemeral=True
        )


# Кнопка для открытия второй части формы
class ApplicationPart2Button(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 минут таймаут

    @discord.ui.button(label="Продолжить заполнение заявки", style=discord.ButtonStyle.primary)
    async def continue_application_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверяем, есть ли данные первой части
        if interaction.user.id not in application_temp_data:
            await interaction.response.send_message(
                "Сессия заполнения заявки истекла. Начните снова.",
                ephemeral=True
            )
            return

        # Открываем вторую часть формы
        application_modal_part2 = ApplicationModalPart2()
        await interaction.response.send_modal(application_modal_part2)


# Вторая часть формы заявки
class ApplicationModalPart2(Modal, title="Заявка на сервер Minecraft (2/2)"):
    plans = TextInput(
        label="Планы на сервере",
        placeholder="Минимум 300 символов",
        min_length=300,
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction: discord.Interaction):
        # Проверяем, есть ли данные первой части
        if interaction.user.id not in application_temp_data:
            await interaction.response.send_message(
                "Сессия заполнения заявки истекла. Начните снова.",
                ephemeral=True
            )
            return

        # Получаем данные из первой части
        temp_data = application_temp_data[interaction.user.id]

        # Создаем заявку со всеми данными
        application = Application(
            user_id=interaction.user.id,
            username=interaction.user.name,
            minecraft_nickname=temp_data["minecraft_nickname"],
            age=temp_data["age"],
            experience=temp_data["experience"],
            has_microphone=temp_data["has_microphone"],
            motivation=temp_data["motivation"],
            plans=self.plans.value,
            agreed_rules=True,
            filled_manually=True,
            status="pending",
            created_at=datetime.datetime.now().isoformat()
        )

        # Очищаем временные данные
        del application_temp_data[interaction.user.id]

        # Сохраняем заявку в базу данных
        application_id = db.create_application(application)
        application.application_id = application_id

        # Отправляем заявку на рассмотрение
        review_channel = client.get_channel(config.REVIEW_CHANNEL_ID)
        if not review_channel:
            await interaction.response.send_message(
                "Ошибка при отправке заявки. Обратитесь к администрации.",
                ephemeral=True
            )
            return

        embed = create_application_embed(application, interaction.user)

        # Create approval buttons
        approve_button = Button(
            style=discord.ButtonStyle.success,
            label="Одобрить",
            custom_id=f"approve_{application_id}"
        )

        reject_button = Button(
            style=discord.ButtonStyle.danger,
            label="Отклонить",
            custom_id=f"reject_{application_id}"
        )

        view = View(timeout=None)
        view.add_item(approve_button)
        view.add_item(reject_button)

        await review_channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            "Ваша заявка успешно отправлена и будет рассмотрена администрацией. "
            "Вы получите уведомление о результате в личные сообщения.",
            ephemeral=True
        )


class ApplicationButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Подать заявку", style=discord.ButtonStyle.primary, custom_id="application_button")
    async def application_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user can submit a new application
        can_submit, error_message = db.can_submit_new_application(interaction.user.id)
        if not can_submit:
            await interaction.response.send_message(error_message, ephemeral=True)
            return

        # Отправляем сообщение с информацией о правилах и подтверждением
        embed = discord.Embed(
            title="Подтверждение правил",
            description=(
                "Перед подачей заявки, пожалуйста, ознакомьтесь со следующими пунктами:\n\n"
                "1. Я прочитал(а) и полностью согласен(на) с правилами сервера.\n"
                "2. Я обязуюсь заполнить заявку самостоятельно без использования ИИ.\n"
                "3. Мне известно, что заявки, написанные с помощью ИИ, будут отклонены.\n\n"
                "Если вы согласны с указанными пунктами, нажмите кнопку 'Я согласен с правилами'."
            ),
            color=discord.Color.blue()
        )

        view = RulesConfirmationView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    # Sync commands with Discord
    await tree.sync(guild=discord.Object(id=config.GUILD_ID))

    # Set up application button in the application channel
    channel = client.get_channel(config.APPLICATION_CHANNEL_ID)
    if channel:
        # Check if the button message already exists
        async for message in channel.history(limit=50):
            if message.author == client.user and any(
                    hasattr(component, 'type') and component.type == discord.ComponentType.button and
                    hasattr(component, 'custom_id') and component.custom_id == "application_button"
                    for row in message.components for component in row.children
            ):
                print("Application button already exists")
                return

        # Create the button message
        embed = discord.Embed(
            title="Подать заявку на сервер Minecraft",
            description=(
                "Нажмите кнопку ниже, чтобы подать заявку на вступление на сервер. "
                "Перед подачей заявки, пожалуйста, ознакомьтесь с правилами сервера."
            ),
            color=discord.Color.blue()
        )

        view = ApplicationButton()
        await channel.send(embed=embed, view=view)
        print("Created application button")


@client.event
async def on_interaction(interaction: discord.Interaction):
    # Проверяем, что это интеракция с компонентом (кнопкой)
    if not interaction.type == discord.InteractionType.component:
        return

    # Получаем custom_id кнопки
    custom_id = interaction.data.get('custom_id', '')

    # Обрабатываем кнопки одобрения/отклонения заявки
    if custom_id.startswith('approve_') or custom_id.startswith('reject_'):
        # Проверяем права пользователя
        has_permission = False
        if interaction.user.guild_permissions.administrator:
            has_permission = True
        else:
            for role in interaction.user.roles:
                if role.id in config.ADMIN_ROLES:
                    has_permission = True
                    break

        if not has_permission:
            await interaction.response.send_message(
                "У вас нет прав для выполнения этого действия.",
                ephemeral=True
            )
            return

        # Получаем ID заявки из custom_id
        application_id = int(custom_id.split('_')[1])
        application = db.get_application_by_id(application_id)

        if not application:
            await interaction.response.send_message(
                "Заявка не найдена.",
                ephemeral=True
            )
            return

        if application.status != 'pending':
            await interaction.response.send_message(
                "Эта заявка уже была обработана.",
                ephemeral=True
            )
            return

        # Обрабатываем заявку в зависимости от нажатой кнопки
        if custom_id.startswith('approve_'):
            # Добавляем в whitelist через RCON
            success = rcon.add_to_whitelist(application.minecraft_nickname)

            if not success:
                await interaction.response.send_message(
                    "Ошибка при добавлении в whitelist. Проверьте RCON соединение.",
                    ephemeral=True
                )
                return

            # Обновляем статус заявки в базе данных
            db.update_application_status(application_id, 'approved', interaction.user.id)

            # Выдаем роль игрока пользователю
            guild = interaction.guild
            if guild:
                member = guild.get_member(application.user_id)
                if member:
                    player_role = guild.get_role(config.PLAYER_ROLE_ID)
                    if player_role:
                        try:
                            await member.add_roles(player_role)
                        except discord.Forbidden:
                            await interaction.response.send_message(
                                "Не удалось выдать роль пользователю. Проверьте права бота.",
                                ephemeral=True
                            )
                            return

            # Отправляем личное сообщение пользователю
            try:
                user = await client.fetch_user(application.user_id)
                await user.send(
                    "Ваша заявка одобрена. Вы добавлены в whitelist сервера. "
                    "После входа на сервер используйте команду /discord link для привязки аккаунта."
                )
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                # Пользователь мог отключить личные сообщения
                pass

            # Логируем действие
            logs_channel = client.get_channel(config.LOGS_CHANNEL_ID)
            if logs_channel:
                embed = discord.Embed(
                    title="Заявка одобрена",
                    description=f"Заявка #{application_id} от <@{application.user_id}> одобрена.",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name="Minecraft ник", value=application.minecraft_nickname)
                embed.add_field(name="Одобрил", value=f"<@{interaction.user.id}>")
                await logs_channel.send(embed=embed)

            # Обновляем сообщение с заявкой
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.title = f"{embed.title} (ОДОБРЕНА)"

            await interaction.message.edit(embed=embed, view=None)
            await interaction.response.send_message(
                f"Заявка от {application.username} (Minecraft: {application.minecraft_nickname}) одобрена.",
                ephemeral=True
            )

        elif custom_id.startswith('reject_'):
            # Обновляем статус заявки в базе данных
            db.update_application_status(application_id, 'rejected', interaction.user.id)

            # Отправляем личное сообщение пользователю
            try:
                user = await client.fetch_user(application.user_id)
                await user.send(
                    "Ваша заявка на сервер отклонена. Повторная подача заявки возможна через 14 дней."
                )
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                # Пользователь мог отключить личные сообщения
                pass

            # Логируем действие
            logs_channel = client.get_channel(config.LOGS_CHANNEL_ID)
            if logs_channel:
                embed = discord.Embed(
                    title="Заявка отклонена",
                    description=f"Заявка #{application_id} от <@{application.user_id}> отклонена.",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name="Minecraft ник", value=application.minecraft_nickname)
                embed.add_field(name="Отклонил", value=f"<@{interaction.user.id}>")
                await logs_channel.send(embed=embed)

            # Обновляем сообщение с заявкой
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()
            embed.title = f"{embed.title} (ОТКЛОНЕНА)"

            await interaction.message.edit(embed=embed, view=None)
            await interaction.response.send_message(
                f"Заявка от {application.username} (Minecraft: {application.minecraft_nickname}) отклонена.",
                ephemeral=True
            )


# Добавляем команду для форсированного создания кнопки
@tree.command(
    name="create_application_button",
    description="Создать кнопку подачи заявки",
    guild=discord.Object(id=config.GUILD_ID)
)
@app_commands.checks.has_permissions(administrator=True)
async def create_application_button(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel

    embed = discord.Embed(
        title="Подать заявку на сервер Minecraft",
        description=(
            "Нажмите кнопку ниже, чтобы подать заявку на вступление на сервер. "
            "Перед подачей заявки, пожалуйста, ознакомьтесь с правилами сервера."
        ),
        color=discord.Color.blue()
    )

    view = ApplicationButton()
    await target_channel.send(embed=embed, view=view)

    await interaction.response.send_message(
        f"Кнопка подачи заявки создана в канале {target_channel.mention}",
        ephemeral=True
    )


# Run the bot
client.run(config.BOT_TOKEN)