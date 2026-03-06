import re


def validate_minecraft_nickname(nickname: str) -> bool:
    """
    Validates a Minecraft nickname.
    - Only latin characters, numbers and underscores
    - Length between 3 and 16 characters
    """
    pattern = re.compile(r'^[a-zA-Z0-9_]{3,16}$')
    return bool(pattern.match(nickname))


def validate_age(age: str) -> bool:
    """Validates that age is a number and at least 14."""
    try:
        age_int = int(age)
        return age_int >= 14
    except ValueError:
        return False


def validate_text_length(text: str, min_length: int) -> bool:
    """Validates that text has at least min_length characters."""
    return len(text) >= min_length


def create_application_embed(application, user):
    from discord import Embed, Colour
    import datetime

    embed = Embed(
        title=f"Заявка от {user.display_name}",
        description=f"Discord ID: {user.id}",
        color=Colour.blue(),
        timestamp=datetime.datetime.now()
    )

    embed.add_field(name="Ник в Minecraft", value=application.minecraft_nickname, inline=True)
    embed.add_field(name="Возраст", value=application.age, inline=True)
    embed.add_field(name="Микрофон", value=application.has_microphone, inline=True)

    embed.add_field(name="Опыт игры", value=application.experience, inline=False)
    embed.add_field(name="Почему хотите играть на сервере", value=application.motivation, inline=False)
    embed.add_field(name="Планы на сервере", value=application.plans, inline=False)

    embed.add_field(name="Согласие с правилами", value="Подтверждено", inline=True)
    embed.add_field(name="Заполнено самостоятельно", value="Подтверждено", inline=True)
    embed.add_field(name="Дата подачи", value=application.created_at, inline=True)

    embed.set_footer(text=f"Заявка #{application.application_id}")

    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)

    return embed