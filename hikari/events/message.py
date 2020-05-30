#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © Nekoka.tt 2019-2020
#
# This file is part of Hikari.
#
# Hikari is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hikari is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Hikari. If not, see <https://www.gnu.org/licenses/>.
"""Application and entities that are used to describe Discord gateway message events."""

from __future__ import annotations

__all__ = [
    "MessageCreateEvent",
    "MessageUpdateEvent",
    "MessageDeleteEvent",
    "MessageDeleteBulkEvent",
    "MessageReactionAddEvent",
    "MessageReactionRemoveEvent",
    "MessageReactionRemoveAllEvent",
    "MessageReactionRemoveEmojiEvent",
]

import typing

import attr

from hikari.events import base as base_events
from hikari.models import applications
from hikari.models import bases as base_models
from hikari.models import embeds as embed_models
from hikari.models import emojis
from hikari.models import guilds
from hikari.models import intents
from hikari.models import messages
from hikari.models import users
from hikari.utilities import undefined
from hikari.utilities import snowflake

if typing.TYPE_CHECKING:
    import datetime


@base_events.requires_intents(intents.Intent.GUILD_MESSAGES, intents.Intent.DIRECT_MESSAGES)
@attr.s(eq=False, hash=False, kw_only=True, slots=True)
class MessageCreateEvent(base_events.HikariEvent, messages.Message):
    """Used to represent Message Create gateway events."""


# This is an arbitrarily partial version of `messages.Message`
@base_events.requires_intents(intents.Intent.GUILD_MESSAGES, intents.Intent.DIRECT_MESSAGES)
@attr.s(eq=False, hash=False, kw_only=True, slots=True)
class MessageUpdateEvent(base_events.HikariEvent, base_models.Unique):
    """Represents Message Update gateway events.

    !!! note
        All fields on this model except `MessageUpdateEvent.channel` and
        `MessageUpdateEvent.id` may be set to `hikari.models.undefined.Undefined` (a singleton)
        we have not received information about their state from Discord
        alongside field nullability.
    """

    channel_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the channel that the message was sent in."""

    guild_id: typing.Union[snowflake.Snowflake, undefined.Undefined] = attr.ib(repr=True)
    """The ID of the guild that the message was sent in."""

    author: typing.Union[users.User, undefined.Undefined] = attr.ib(repr=True)
    """The author of this message."""

    # TODO: can we merge member and author together?
    # We could override deserialize to to this and then reorganise the payload, perhaps?
    member: typing.Union[guilds.Member, undefined.Undefined] = attr.ib()
    """The member properties for the message's author."""

    content: typing.Union[str, undefined.Undefined] = attr.ib()
    """The content of the message."""

    timestamp: typing.Union[datetime.datetime, undefined.Undefined] = attr.ib()
    """The timestamp that the message was sent at."""

    edited_timestamp: typing.Union[datetime.datetime, undefined.Undefined, None] = attr.ib()
    """The timestamp that the message was last edited at.

    Will be `None` if the message wasn't ever edited.
    """

    is_tts: typing.Union[bool, undefined.Undefined] = attr.ib()
    """Whether the message is a TTS message."""

    is_mentioning_everyone: typing.Union[bool, undefined.Undefined] = attr.ib()
    """Whether the message mentions `@everyone` or `@here`."""

    user_mentions: typing.Union[typing.Set[snowflake.Snowflake], undefined.Undefined] = attr.ib()
    """The users the message mentions."""

    role_mentions: typing.Union[typing.Set[snowflake.Snowflake], undefined.Undefined] = attr.ib()
    """The roles the message mentions."""

    channel_mentions: typing.Union[typing.Set[snowflake.Snowflake], undefined.Undefined] = attr.ib()
    """The channels the message mentions."""

    attachments: typing.Union[typing.Sequence[messages.Attachment], undefined.Undefined] = attr.ib()
    """The message attachments."""

    embeds: typing.Union[typing.Sequence[embed_models.Embed], undefined.Undefined] = attr.ib()
    """The message's embeds."""

    reactions: typing.Union[typing.Sequence[messages.Reaction], undefined.Undefined] = attr.ib()
    """The message's reactions."""

    is_pinned: typing.Union[bool, undefined.Undefined] = attr.ib()
    """Whether the message is pinned."""

    webhook_id: typing.Union[snowflake.Snowflake, undefined.Undefined] = attr.ib()
    """If the message was generated by a webhook, the webhook's ID."""

    type: typing.Union[messages.MessageType, undefined.Undefined] = attr.ib()
    """The message's type."""

    activity: typing.Union[messages.MessageActivity, undefined.Undefined] = attr.ib()
    """The message's activity."""

    application: typing.Optional[applications.Application] = attr.ib()
    """The message's application."""

    message_reference: typing.Union[messages.MessageCrosspost, undefined.Undefined] = attr.ib()
    """The message's cross-posted reference data."""

    flags: typing.Union[messages.MessageFlag, undefined.Undefined] = attr.ib()
    """The message's flags."""

    nonce: typing.Union[str, undefined.Undefined] = attr.ib()
    """The message nonce.

    This is a string used for validating a message was sent.
    """


@base_events.requires_intents(intents.Intent.GUILD_MESSAGES, intents.Intent.DIRECT_MESSAGES)
@attr.s(eq=False, hash=False, kw_only=True, slots=True)
class MessageDeleteEvent(base_events.HikariEvent):
    """Used to represent Message Delete gateway events.

    Sent when a message is deleted in a channel we have access to.
    """

    # TODO: common base class for Message events.

    channel_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the channel where this message was deleted."""

    guild_id: typing.Optional[snowflake.Snowflake] = attr.ib(repr=True)
    """The ID of the guild where this message was deleted.

    This will be `None` if this message was deleted in a DM channel.
    """

    message_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the message that was deleted."""


@base_events.requires_intents(intents.Intent.GUILD_MESSAGES)
@attr.s(eq=False, hash=False, kw_only=True, slots=True)
class MessageDeleteBulkEvent(base_events.HikariEvent):
    """Used to represent Message Bulk Delete gateway events.

    Sent when multiple messages are deleted in a channel at once.
    """

    channel_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the channel these messages have been deleted in."""

    guild_id: typing.Optional[snowflake.Snowflake] = attr.ib(repr=True)
    """The ID of the channel these messages have been deleted in.

    This will be `None` if these messages were bulk deleted in a DM channel.
    """

    message_ids: typing.Set[snowflake.Snowflake] = attr.ib()
    """A collection of the IDs of the messages that were deleted."""


@base_events.requires_intents(intents.Intent.GUILD_MESSAGE_REACTIONS, intents.Intent.DIRECT_MESSAGE_REACTIONS)
@attr.s(eq=False, hash=False, kw_only=True, slots=True)
class MessageReactionAddEvent(base_events.HikariEvent):
    """Used to represent Message Reaction Add gateway events."""

    # TODO: common base classes!

    user_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the user adding the reaction."""

    channel_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the channel where this reaction is being added."""

    message_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the message this reaction is being added to."""

    guild_id: typing.Optional[snowflake.Snowflake] = attr.ib(repr=True)
    """The ID of the guild where this reaction is being added.

    This will be `None` if this is happening in a DM channel.
    """

    # TODO: does this contain a user? If not, should it be a PartialGuildMember?
    member: typing.Optional[guilds.Member] = attr.ib()
    """The member object of the user who's adding this reaction.

    This will be `None` if this is happening in a DM channel.
    """

    emoji: typing.Union[emojis.CustomEmoji, emojis.UnicodeEmoji] = attr.ib(repr=True)
    """The object of the emoji being added."""


@base_events.requires_intents(intents.Intent.GUILD_MESSAGE_REACTIONS, intents.Intent.DIRECT_MESSAGE_REACTIONS)
@attr.s(eq=False, hash=False, kw_only=True, slots=True)
class MessageReactionRemoveEvent(base_events.HikariEvent):
    """Used to represent Message Reaction Remove gateway events."""

    user_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the user who is removing their reaction."""

    channel_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the channel where this reaction is being removed."""

    message_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the message this reaction is being removed from."""

    guild_id: typing.Optional[snowflake.Snowflake] = attr.ib(repr=True)
    """The ID of the guild where this reaction is being removed

    This will be `None` if this event is happening in a DM channel.
    """

    emoji: typing.Union[emojis.UnicodeEmoji, emojis.CustomEmoji] = attr.ib(repr=True)
    """The object of the emoji being removed."""


@base_events.requires_intents(intents.Intent.GUILD_MESSAGE_REACTIONS, intents.Intent.DIRECT_MESSAGE_REACTIONS)
@attr.s(eq=False, hash=False, kw_only=True, slots=True)
class MessageReactionRemoveAllEvent(base_events.HikariEvent):
    """Used to represent Message Reaction Remove All gateway events.

    Sent when all the reactions are removed from a message, regardless of emoji.
    """

    channel_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the channel where the targeted message is."""

    message_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the message all reactions are being removed from."""

    guild_id: typing.Optional[snowflake.Snowflake] = attr.ib(repr=True,)
    """The ID of the guild where the targeted message is, if applicable."""


@base_events.requires_intents(intents.Intent.GUILD_MESSAGE_REACTIONS, intents.Intent.DIRECT_MESSAGE_REACTIONS)
@attr.s(eq=False, hash=False, kw_only=True, slots=True)
class MessageReactionRemoveEmojiEvent(base_events.HikariEvent):
    """Represents Message Reaction Remove Emoji events.

    Sent when all the reactions for a single emoji are removed from a message.
    """

    channel_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the channel where the targeted message is."""

    guild_id: typing.Optional[snowflake.Snowflake] = attr.ib(repr=True)
    """The ID of the guild where the targeted message is, if applicable."""

    message_id: snowflake.Snowflake = attr.ib(repr=True)
    """The ID of the message the reactions are being removed from."""

    emoji: typing.Union[emojis.UnicodeEmoji, emojis.CustomEmoji] = attr.ib(repr=True)
    """The object of the emoji that's being removed."""
