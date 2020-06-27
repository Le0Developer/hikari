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
import datetime

import mock
import pytest


from hikari.api import rest
from hikari.impl import entity_factory
from hikari.events import channel as channel_events
from hikari.events import guild as guild_events
from hikari.events import message as message_events
from hikari.events import other as other_events
from hikari.events import voice as voice_events
from hikari.models import applications as application_models
from hikari.models import audit_logs as audit_log_models
from hikari.models import channels as channel_models
from hikari.models import colors as color_models
from hikari.models import embeds as embed_models
from hikari.models import emojis as emoji_models
from hikari.models import gateway as gateway_models
from hikari.models import guilds as guild_models
from hikari.models import invites as invite_models
from hikari.models import messages as message_models
from hikari.models import permissions as permission_models
from hikari.models import presences as presence_models
from hikari.models import users as user_models
from hikari.models import voices as voice_models
from hikari.models import webhooks as webhook_models
from hikari.utilities import files
from hikari.utilities import undefined


def test__deserialize_seconds_timedelta():
    assert entity_factory._deserialize_seconds_timedelta(30) == datetime.timedelta(seconds=30)


def test__deserialize_day_timedelta():
    assert entity_factory._deserialize_day_timedelta("4") == datetime.timedelta(days=4)


def test__deserialize_max_uses_returns_int():
    assert entity_factory._deserialize_max_uses(120) == 120


def test__deserialize_max_uses_returns_none_when_zero():
    # Yes, I changed this from float("inf") so that it returns None. I did this
    # to provide some level of consistency with `max_age`. We need to revisit
    # this if possible.
    assert entity_factory._deserialize_max_uses(0) is None


def test__deserialize_max_age_returns_timedelta():
    assert entity_factory._deserialize_max_age(120) == datetime.timedelta(seconds=120)


def test__deserialize_max_age_returns_null():
    assert entity_factory._deserialize_max_age(0) is None


class TestEntityFactoryImpl:
    @pytest.fixture()
    def mock_app(self) -> rest.IRESTClient:
        return mock.MagicMock(rest.IRESTClient)

    @pytest.fixture()
    def entity_factory_impl(self, mock_app) -> entity_factory.EntityFactoryComponentImpl:
        return entity_factory.EntityFactoryComponentImpl(app=mock_app)

    def test_app(self, entity_factory_impl, mock_app):
        assert entity_factory_impl.app is mock_app

    ######################
    # APPLICATION MODELS #
    ######################

    @pytest.fixture()
    def partial_integration(self):
        return {
            "id": "123123123123123",
            "name": "A Name",
            "type": "twitch",
            "account": {"name": "twitchUsername", "id": "123123"},
        }

    @pytest.fixture()
    def own_connection_payload(self, partial_integration):
        return {
            "friend_sync": False,
            "id": "2513849648abc",
            "integrations": [partial_integration],
            "name": "FS",
            "revoked": False,
            "show_activity": True,
            "type": "twitter",
            "verified": True,
            "visibility": 0,
        }

    def test_deserialize_own_connection(
        self, entity_factory_impl, mock_app, own_connection_payload, partial_integration
    ):
        own_connection = entity_factory_impl.deserialize_own_connection(own_connection_payload)
        assert own_connection.id == "2513849648abc"
        assert own_connection.name == "FS"
        assert own_connection.type == "twitter"
        assert own_connection.is_revoked is False
        assert own_connection.integrations == [entity_factory_impl.deserialize_partial_integration(partial_integration)]
        assert own_connection.is_verified is True
        assert own_connection.is_friend_sync_enabled is False
        assert own_connection.is_activity_visible is True
        assert own_connection.visibility == application_models.ConnectionVisibility.NONE
        assert isinstance(own_connection, application_models.OwnConnection)

    @pytest.fixture()
    def own_guild_payload(self):
        return {
            "id": "152559372126519269",
            "name": "Isopropyl",
            "icon": "d4a983885dsaa7691ce8bcaaf945a",
            "owner": False,
            "permissions": 2147483647,
            "features": ["DISCOVERABLE", "FORCE_RELAY"],
        }

    def test_deserialize_own_guild(self, entity_factory_impl, mock_app, own_guild_payload):
        own_guild = entity_factory_impl.deserialize_own_guild(own_guild_payload)
        assert own_guild.id == 152559372126519269
        assert own_guild.name == "Isopropyl"
        assert own_guild.icon_hash == "d4a983885dsaa7691ce8bcaaf945a"
        assert own_guild.features == {guild_models.GuildFeature.DISCOVERABLE, "FORCE_RELAY"}
        assert own_guild.is_owner is False
        assert own_guild.my_permissions == permission_models.Permission(2147483647)

    def test_deserialize_own_guild_with_null_and_unset_fields(self, entity_factory_impl):
        own_guild = entity_factory_impl.deserialize_own_guild(
            {
                "id": "152559372126519269",
                "name": "Isopropyl",
                "icon": None,
                "owner": False,
                "permissions": 2147483647,
                "features": ["DISCOVERABLE", "FORCE_RELAY"],
            }
        )
        assert own_guild.icon_hash is None

    @pytest.fixture()
    def owner_payload(self, user_payload):
        return {**user_payload, "flags": 1 << 10}

    @pytest.fixture()
    def application_information_payload(self, owner_payload, user_payload):
        return {
            "id": "209333111222",
            "name": "Dream Sweet in Sea Major",
            "icon": "iwiwiwiwiw",
            "description": "I am an application",
            "rpc_origins": ["127.0.0.0"],
            "bot_public": True,
            "bot_require_code_grant": False,
            "owner": owner_payload,
            "summary": "not a blank string",
            "verify_key": "698c5d0859abb686be1f8a19e0e7634d8471e33817650f9fb29076de227bca90",
            "team": {
                "icon": "hashtag",
                "id": "202020202",
                "members": [
                    {"membership_state": 1, "permissions": ["*"], "team_id": "209333111222", "user": user_payload}
                ],
                "owner_user_id": "393030292",
            },
            "guild_id": "2020293939",
            "primary_sku_id": "2020202002",
            "slug": "192.168.1.254",
            "cover_image": "hashmebaby",
        }

    def test_deserialize_application(
        self, entity_factory_impl, mock_app, application_information_payload, owner_payload, user_payload
    ):
        application = entity_factory_impl.deserialize_application(application_information_payload)
        assert application.app is mock_app
        assert application.id == 209333111222
        assert application.name == "Dream Sweet in Sea Major"
        assert application.description == "I am an application"
        assert application.is_bot_public is True
        assert application.is_bot_code_grant_required is False
        assert application.owner == entity_factory_impl.deserialize_user(owner_payload)
        assert application.rpc_origins == {"127.0.0.0"}
        assert application.summary == "not a blank string"
        assert application.verify_key == b"698c5d0859abb686be1f8a19e0e7634d8471e33817650f9fb29076de227bca90"
        assert application.icon_hash == "iwiwiwiwiw"
        # Team
        assert application.team.id == 202020202
        assert application.team.icon_hash == "hashtag"
        assert application.team.owner_user_id == 393030292
        assert isinstance(application.team, application_models.Team)
        # TeamMember
        assert len(application.team.members) == 1
        member = application.team.members[115590097100865541]
        assert member.membership_state == application_models.TeamMembershipState.INVITED
        assert member.permissions == {"*"}
        assert member.team_id == 209333111222
        assert member.user == entity_factory_impl.deserialize_user(user_payload)
        assert isinstance(member, application_models.TeamMember)

        assert application.guild_id == 2020293939
        assert application.primary_sku_id == 2020202002
        assert application.slug == "192.168.1.254"
        assert application.cover_image_hash == "hashmebaby"
        assert isinstance(application, application_models.Application)

    def test_deserialize_application_with_unset_fields(self, entity_factory_impl, mock_app, owner_payload):
        application = entity_factory_impl.deserialize_application(
            {
                "id": "209333111222",
                "name": "Dream Sweet in Sea Major",
                "icon": "3123123",
                "description": "I am an application",
                "summary": "not a blank string",
            }
        )
        assert application.is_bot_public is None
        assert application.is_bot_code_grant_required is None
        assert application.owner is None
        assert application.rpc_origins is None
        assert application.verify_key is None
        assert application.team is None
        assert application.guild_id is None
        assert application.primary_sku_id is None
        assert application.slug is None
        assert application.cover_image_hash is None

    def test_deserialize_application_with_null_fields(self, entity_factory_impl, mock_app, owner_payload):
        application = entity_factory_impl.deserialize_application(
            {
                "id": "209333111222",
                "name": "Dream Sweet in Sea Major",
                "icon": None,
                "description": "I am an application",
                "summary": "not a blank string",
                "team": None,
            }
        )
        assert application.icon_hash is None
        assert application.team is None

    #####################
    # AUDIT LOGS MODELS #
    #####################

    def test__deserialize_audit_log_change_roles(self, entity_factory_impl):
        test_role_payloads = [
            {"id": "24", "name": "roleA"},
        ]
        roles = entity_factory_impl._deserialize_audit_log_change_roles(test_role_payloads)
        assert len(roles) == 1
        role = roles[24]
        assert role.id == 24
        assert role.name == "roleA"
        assert isinstance(role, guild_models.PartialRole)

    def test__deserialize_audit_log_overwrites(self, entity_factory_impl):
        test_overwrite_payloads = [
            {"id": "24", "type": "role", "allow": 21, "deny": 0},
            {"id": "48", "type": "role", "deny": 42, "allow": 0},
        ]
        overwrites = entity_factory_impl._deserialize_audit_log_overwrites(test_overwrite_payloads)
        assert overwrites == {
            24: entity_factory_impl.deserialize_permission_overwrite(
                {"id": "24", "type": "role", "allow": 21, "deny": 0}
            ),
            48: entity_factory_impl.deserialize_permission_overwrite(
                {"id": "48", "type": "role", "deny": 42, "allow": 0}
            ),
        }

    @pytest.fixture()
    def overwrite_info_payload(self):
        return {"id": "123123123", "type": "role", "role_name": "aRole"}

    def test__deserialize_channel_overwrite_entry_info(self, entity_factory_impl, overwrite_info_payload):
        overwrite_entry_info = entity_factory_impl._deserialize_channel_overwrite_entry_info(overwrite_info_payload)
        assert overwrite_entry_info.id == 123123123
        assert overwrite_entry_info.type is channel_models.PermissionOverwriteType.ROLE
        assert overwrite_entry_info.role_name == "aRole"
        assert isinstance(overwrite_entry_info, audit_log_models.ChannelOverwriteEntryInfo)

    @pytest.fixture()
    def message_pin_info_payload(self):
        return {
            "channel_id": "123123123",
            "message_id": "69696969",
        }

    def test__deserialize_message_pin_entry_info(self, entity_factory_impl, message_pin_info_payload):
        message_pin_info = entity_factory_impl._deserialize_message_pin_entry_info(message_pin_info_payload)
        assert message_pin_info.channel_id == 123123123
        assert message_pin_info.message_id == 69696969
        assert isinstance(message_pin_info, audit_log_models.MessagePinEntryInfo)

    @pytest.fixture()
    def member_prune_info_payload(self):
        return {
            "delete_member_days": "7",
            "members_removed": "1",
        }

    def test__deserialize_member_prune_entry_info(self, entity_factory_impl, member_prune_info_payload):
        member_prune_info = entity_factory_impl._deserialize_member_prune_entry_info(member_prune_info_payload)
        assert member_prune_info.delete_member_days == datetime.timedelta(days=7)
        assert member_prune_info.members_removed == 1
        assert isinstance(member_prune_info, audit_log_models.MemberPruneEntryInfo)

    @pytest.fixture()
    def message_bulk_delete_info_payload(self):
        return {"count": "42"}

    def test__deserialize_message_bulk_delete_entry_info(self, entity_factory_impl, message_bulk_delete_info_payload):
        message_bulk_delete_entry_info = entity_factory_impl._deserialize_message_bulk_delete_entry_info(
            message_bulk_delete_info_payload
        )
        assert message_bulk_delete_entry_info.count == 42
        assert isinstance(message_bulk_delete_entry_info, audit_log_models.MessageBulkDeleteEntryInfo)

    @pytest.fixture()
    def message_delete_info_payload(self):
        return {"count": "42", "channel_id": "4206942069"}

    def test__deserialize_message_delete_entry_info(self, entity_factory_impl, message_delete_info_payload):
        message_delete_entry_info = entity_factory_impl._deserialize_message_delete_entry_info(
            message_delete_info_payload
        )
        assert message_delete_entry_info.count == 42
        assert message_delete_entry_info.channel_id == 4206942069
        assert isinstance(message_delete_entry_info, audit_log_models.MessageDeleteEntryInfo)

    @pytest.fixture()
    def member_disconnect_info_payload(self):
        return {"count": "42"}

    def test__deserialize_member_disconnect_entry_info(self, entity_factory_impl, member_disconnect_info_payload):
        member_disconnect_entry_info = entity_factory_impl._deserialize_member_disconnect_entry_info(
            member_disconnect_info_payload
        )
        assert member_disconnect_entry_info.count == 42
        assert isinstance(member_disconnect_entry_info, audit_log_models.MemberDisconnectEntryInfo)

    @pytest.fixture()
    def member_move_info_payload(self):
        return {"count": "42", "channel_id": "22222222"}

    def test__deserialize_member_move_entry_info(self, entity_factory_impl, member_move_info_payload):
        member_move_entry_info = entity_factory_impl._deserialize_member_move_entry_info(member_move_info_payload)
        assert member_move_entry_info.channel_id == 22222222
        assert isinstance(member_move_entry_info, audit_log_models.MemberMoveEntryInfo)

    @pytest.fixture()
    def unrecognised_audit_log_entry(self):
        return {"count": "5412", "action": "nyaa'd"}

    def test__deserialize_unrecognised_audit_log_entry_info(self, entity_factory_impl, unrecognised_audit_log_entry):
        unrecognised_info = entity_factory_impl._deserialize_unrecognised_audit_log_entry_info(
            unrecognised_audit_log_entry
        )
        assert unrecognised_info.count == "5412"
        assert unrecognised_info.action == "nyaa'd"
        assert isinstance(unrecognised_info, audit_log_models.UnrecognisedAuditLogEntryInfo)

    @pytest.fixture()
    def audit_log_entry_payload(self):
        return {
            "action_type": 14,
            "changes": [
                {
                    "key": "$add",
                    "old_value": [{"id": "568651298858074123", "name": "Casual"}],
                    "new_value": [{"id": "123123123312312", "name": "aRole"}],
                }
            ],
            "id": "694026906592477214",
            "options": {"id": "115590097100865541", "type": "member"},
            "target_id": "115590097100865541",
            "user_id": "560984860634644482",
            "reason": "An artificial insanity.",
        }

    @pytest.mark.skip("TODO")
    def test_deserialize_audit_log(self, entity_factory_impl, mock_app, audit_log_entry_payload):
        raise NotImplementedError  # TODO: test coverage for audit log cases

    ##################
    # CHANNEL MODELS #
    ##################

    @pytest.fixture()
    def permission_overwrite_payload(self):
        return {"id": "4242", "type": "member", "allow": 65, "deny": 49152}

    def test_deserialize_permission_overwrite(self, entity_factory_impl, permission_overwrite_payload):
        overwrite = entity_factory_impl.deserialize_permission_overwrite(permission_overwrite_payload)
        assert overwrite.type == channel_models.PermissionOverwriteType.MEMBER
        assert overwrite.allow == permission_models.Permission(65)
        assert overwrite.deny == permission_models.Permission(49152)
        assert isinstance(overwrite, channel_models.PermissionOverwrite)

    def test_serialize_permission_overwrite(self, entity_factory_impl):
        overwrite = channel_models.PermissionOverwrite(id=123123, type="member", allow=42, deny=62)
        payload = entity_factory_impl.serialize_permission_overwrite(overwrite)
        assert payload == {"id": "123123", "type": "member", "allow": 42, "deny": 62}

    @pytest.fixture()
    def partial_channel_payload(self):
        return {"id": "561884984214814750", "name": "general", "type": 0}

    def test_deserialize_partial_channel(self, entity_factory_impl, mock_app, partial_channel_payload):
        partial_channel = entity_factory_impl.deserialize_partial_channel(partial_channel_payload)
        assert partial_channel.app is mock_app
        assert partial_channel.id == 561884984214814750
        assert partial_channel.name == "general"
        assert partial_channel.type == channel_models.ChannelType.GUILD_TEXT
        assert isinstance(partial_channel, channel_models.PartialChannel)

    def test_deserialize_partial_channel_with_unset_fields(self, entity_factory_impl):
        assert entity_factory_impl.deserialize_partial_channel({"id": "22", "type": 0}).name is None

    @pytest.fixture()
    def dm_channel_payload(self, user_payload):
        return {
            "id": "123",
            "last_message_id": "456",
            "type": 1,
            "recipients": [user_payload],
        }

    def test_deserialize_dm_channel(self, entity_factory_impl, mock_app, dm_channel_payload, user_payload):
        dm_channel = entity_factory_impl.deserialize_dm_channel(dm_channel_payload)
        assert dm_channel.app is mock_app
        assert dm_channel.id == 123
        assert dm_channel.name is None
        assert dm_channel.last_message_id == 456
        assert dm_channel.type is channel_models.ChannelType.DM
        assert dm_channel.recipients == {115590097100865541: entity_factory_impl.deserialize_user(user_payload)}
        assert isinstance(dm_channel, channel_models.DMChannel)

    def test_deserialize_dm_channel_with_null_fields(self, entity_factory_impl, user_payload):
        dm_channel = entity_factory_impl.deserialize_dm_channel(
            {"id": "123", "last_message_id": None, "type": 1, "recipients": [user_payload]}
        )
        assert dm_channel.last_message_id is None

    @pytest.fixture()
    def group_dm_channel_payload(self, user_payload):
        return {
            "id": "123",
            "name": "Secret Developer Group",
            "icon": "123asdf123adsf",
            "owner_id": "456",
            "application_id": "123789",
            "last_message_id": "456",
            "nicks": [{"id": "115590097100865541", "nick": "nyaa"}],
            "type": 3,
            "recipients": [user_payload],
        }

    def test_deserialize_group_dm_channel(self, entity_factory_impl, mock_app, group_dm_channel_payload, user_payload):
        group_dm = entity_factory_impl.deserialize_group_dm_channel(group_dm_channel_payload)
        assert group_dm.app is mock_app
        assert group_dm.id == 123
        assert group_dm.name == "Secret Developer Group"
        assert group_dm.icon_hash == "123asdf123adsf"
        assert group_dm.application_id == 123789
        assert group_dm.nicknames == {115590097100865541: "nyaa"}
        assert group_dm.last_message_id == 456
        assert group_dm.type == channel_models.ChannelType.GROUP_DM
        assert group_dm.recipients == {115590097100865541: entity_factory_impl.deserialize_user(user_payload)}
        assert isinstance(group_dm, channel_models.GroupDMChannel)

    def test_test_deserialize_group_dm_channel_with_unset_fields(self, entity_factory_impl, user_payload):
        group_dm = entity_factory_impl.deserialize_group_dm_channel(
            {
                "id": "123",
                "name": "Secret Developer Group",
                "icon": "123asdf123adsf",
                "owner_id": "456",
                "last_message_id": "456",
                "type": 3,
                "recipients": [user_payload],
            }
        )
        assert group_dm.nicknames == {}
        assert group_dm.application_id is None

    @pytest.fixture()
    def guild_category_payload(self, permission_overwrite_payload):
        return {
            "id": "123",
            "permission_overwrites": [permission_overwrite_payload],
            "name": "Test",
            "parent_id": "664565",
            "nsfw": True,
            "position": 3,
            "guild_id": "9876",
            "type": 4,
        }

    def test_deserialize_guild_category(
        self, entity_factory_impl, mock_app, guild_category_payload, permission_overwrite_payload
    ):
        guild_category = entity_factory_impl.deserialize_guild_category(guild_category_payload)
        assert guild_category.app is mock_app
        assert guild_category.id == 123
        assert guild_category.name == "Test"
        assert guild_category.type == channel_models.ChannelType.GUILD_CATEGORY
        assert guild_category.guild_id == 9876
        assert guild_category.position == 3
        assert guild_category.permission_overwrites == {
            4242: entity_factory_impl.deserialize_permission_overwrite(permission_overwrite_payload)
        }
        assert guild_category.is_nsfw is True
        assert guild_category.parent_id == 664565
        assert isinstance(guild_category, channel_models.GuildCategory)

    def test_deserialize_guild_category_with_unset_fields(self, entity_factory_impl, permission_overwrite_payload):
        guild_category = entity_factory_impl.deserialize_guild_category(
            {
                "id": "123",
                "permission_overwrites": [permission_overwrite_payload],
                "name": "Test",
                "position": 3,
                "type": 4,
            }
        )
        assert guild_category.parent_id is None
        assert guild_category.is_nsfw is None
        assert guild_category.guild_id is None

    def test_deserialize_guild_category_with_null_fields(self, entity_factory_impl, permission_overwrite_payload):
        guild_category = entity_factory_impl.deserialize_guild_category(
            {
                "id": "123",
                "permission_overwrites": [permission_overwrite_payload],
                "name": "Test",
                "parent_id": None,
                "nsfw": True,
                "position": 3,
                "guild_id": "9876",
                "type": 4,
            }
        )
        assert guild_category.parent_id is None

    @pytest.fixture()
    def guild_text_channel_payload(self, permission_overwrite_payload):
        return {
            "id": "123",
            "guild_id": "567",
            "name": "general",
            "type": 0,
            "position": 6,
            "permission_overwrites": [permission_overwrite_payload],
            "rate_limit_per_user": 2,
            "nsfw": True,
            "topic": "¯\\_(ツ)_/¯",
            "last_message_id": "123456",
            "last_pin_timestamp": "2020-05-27T15:58:51.545252+00:00",
            "parent_id": "987",
        }

    def test_deserialize_guild_text_channel(
        self, entity_factory_impl, mock_app, guild_text_channel_payload, permission_overwrite_payload
    ):
        guild_text_channel = entity_factory_impl.deserialize_guild_text_channel(guild_text_channel_payload)
        assert guild_text_channel.app is mock_app
        assert guild_text_channel.id == 123
        assert guild_text_channel.name == "general"
        assert guild_text_channel.type == channel_models.ChannelType.GUILD_TEXT
        assert guild_text_channel.guild_id == 567
        assert guild_text_channel.position == 6
        assert guild_text_channel.permission_overwrites == {
            4242: entity_factory_impl.deserialize_permission_overwrite(permission_overwrite_payload)
        }
        assert guild_text_channel.is_nsfw is True
        assert guild_text_channel.parent_id == 987
        assert guild_text_channel.topic == "¯\\_(ツ)_/¯"
        assert guild_text_channel.last_message_id == 123456
        assert guild_text_channel.rate_limit_per_user == datetime.timedelta(seconds=2)
        assert guild_text_channel.last_pin_timestamp == datetime.datetime(
            2020, 5, 27, 15, 58, 51, 545252, tzinfo=datetime.timezone.utc
        )
        assert isinstance(guild_text_channel, channel_models.GuildTextChannel)

    def test_deserialize_guild_text_channel_with_unset_fields(self, entity_factory_impl):
        guild_text_channel = entity_factory_impl.deserialize_guild_text_channel(
            {
                "id": "123",
                "name": "general",
                "type": 0,
                "position": 6,
                "permission_overwrites": [],
                "rate_limit_per_user": 2,
                "topic": "¯\\_(ツ)_/¯",
                "last_message_id": "123456",
            }
        )
        assert guild_text_channel.guild_id is None
        assert guild_text_channel.is_nsfw is None
        assert guild_text_channel.last_pin_timestamp is None
        assert guild_text_channel.parent_id is None

    def test_deserialize_guild_text_channel_with_null_fields(self, entity_factory_impl):
        guild_text_channel = entity_factory_impl.deserialize_guild_text_channel(
            {
                "id": "123",
                "guild_id": "567",
                "name": "general",
                "type": 0,
                "position": 6,
                "permission_overwrites": [],
                "rate_limit_per_user": 2,
                "nsfw": True,
                "topic": None,
                "last_message_id": None,
                "last_pin_timestamp": None,
                "parent_id": None,
            }
        )
        assert guild_text_channel.topic is None
        assert guild_text_channel.last_message_id is None
        assert guild_text_channel.last_pin_timestamp is None
        assert guild_text_channel.parent_id is None

    @pytest.fixture()
    def guild_news_channel_payload(self, permission_overwrite_payload):
        return {
            "id": "7777",
            "guild_id": "123",
            "name": "Important Announcements",
            "type": 5,
            "position": 0,
            "permission_overwrites": [permission_overwrite_payload],
            "nsfw": True,
            "topic": "Super Important Announcements",
            "last_message_id": "456",
            "parent_id": "654",
            "last_pin_timestamp": "2020-05-27T15:58:51.545252+00:00",
        }

    def test_deserialize_guild_news_channel(
        self, entity_factory_impl, mock_app, guild_news_channel_payload, permission_overwrite_payload
    ):
        news_channel = entity_factory_impl.deserialize_guild_news_channel(guild_news_channel_payload)
        assert news_channel.app is mock_app
        assert news_channel.id == 7777
        assert news_channel.name == "Important Announcements"
        assert news_channel.type == channel_models.ChannelType.GUILD_NEWS
        assert news_channel.guild_id == 123
        assert news_channel.position == 0
        assert news_channel.permission_overwrites == {
            4242: entity_factory_impl.deserialize_permission_overwrite(permission_overwrite_payload)
        }
        assert news_channel.is_nsfw is True
        assert news_channel.parent_id == 654
        assert news_channel.topic == "Super Important Announcements"
        assert news_channel.last_message_id == 456
        assert news_channel.last_pin_timestamp == datetime.datetime(
            2020, 5, 27, 15, 58, 51, 545252, tzinfo=datetime.timezone.utc
        )
        assert isinstance(news_channel, channel_models.GuildNewsChannel)

    def test_deserialize_guild_news_channel_with_unset_fields(self, entity_factory_impl):
        news_channel = entity_factory_impl.deserialize_guild_news_channel(
            {
                "id": "567",
                "name": "Important Announcements",
                "type": 5,
                "position": 0,
                "permission_overwrites": [],
                "topic": "Super Important Announcements",
                "last_message_id": "456",
            }
        )
        assert news_channel.guild_id is None
        assert news_channel.is_nsfw is None
        assert news_channel.parent_id is None
        assert news_channel.last_pin_timestamp is None

    def test_deserialize_guild_news_channel_with_null_fields(self, entity_factory_impl):
        news_channel = entity_factory_impl.deserialize_guild_news_channel(
            {
                "id": "567",
                "guild_id": "123",
                "name": "Important Announcements",
                "type": 5,
                "position": 0,
                "permission_overwrites": [],
                "nsfw": True,
                "topic": None,
                "last_message_id": None,
                "parent_id": None,
                "last_pin_timestamp": None,
            }
        )
        assert news_channel.topic is None
        assert news_channel.last_message_id is None
        assert news_channel.parent_id is None
        assert news_channel.last_pin_timestamp is None

    @pytest.fixture()
    def guild_store_channel_payload(self, permission_overwrite_payload):
        return {
            "id": "123",
            "permission_overwrites": [permission_overwrite_payload],
            "name": "Half Life 3",
            "parent_id": "9876",
            "nsfw": True,
            "position": 2,
            "guild_id": "1234",
            "type": 6,
        }

    def test_deserialize_guild_store_channel(
        self, entity_factory_impl, mock_app, guild_store_channel_payload, permission_overwrite_payload
    ):
        store_chanel = entity_factory_impl.deserialize_guild_store_channel(guild_store_channel_payload)
        assert store_chanel.id == 123
        assert store_chanel.name == "Half Life 3"
        assert store_chanel.type == channel_models.ChannelType.GUILD_STORE
        assert store_chanel.guild_id == 1234
        assert store_chanel.position == 2
        assert store_chanel.permission_overwrites == {
            4242: entity_factory_impl.deserialize_permission_overwrite(permission_overwrite_payload)
        }
        assert store_chanel.is_nsfw is True
        assert store_chanel.parent_id == 9876
        assert isinstance(store_chanel, channel_models.GuildStoreChannel)

    def test_deserialize_guild_store_channel_with_unset_fields(self, entity_factory_impl):
        store_chanel = entity_factory_impl.deserialize_guild_store_channel(
            {"id": "123", "permission_overwrites": [], "name": "Half Life 3", "position": 2, "type": 6,}
        )
        assert store_chanel.parent_id is None
        assert store_chanel.is_nsfw is None
        assert store_chanel.guild_id is None

    def test_deserialize_guild_store_channel_with_null_fields(self, entity_factory_impl):
        store_chanel = entity_factory_impl.deserialize_guild_store_channel(
            {
                "id": "123",
                "permission_overwrites": [],
                "name": "Half Life 3",
                "parent_id": None,
                "nsfw": True,
                "position": 2,
                "guild_id": "1234",
                "type": 6,
            }
        )
        assert store_chanel.parent_id is None

    @pytest.fixture()
    def guild_voice_channel_payload(self, permission_overwrite_payload):
        return {
            "id": "555",
            "guild_id": "789",
            "name": "Secret Developer Discussions",
            "type": 2,
            "nsfw": True,
            "position": 4,
            "permission_overwrites": [permission_overwrite_payload],
            "bitrate": 64000,
            "user_limit": 3,
            "parent_id": "456",
        }

    def test_deserialize_guild_voice_channel(
        self, entity_factory_impl, mock_app, guild_voice_channel_payload, permission_overwrite_payload
    ):
        voice_channel = entity_factory_impl.deserialize_guild_voice_channel(guild_voice_channel_payload)
        assert voice_channel.id == 555
        assert voice_channel.name == "Secret Developer Discussions"
        assert voice_channel.type == channel_models.ChannelType.GUILD_VOICE
        assert voice_channel.guild_id == 789
        assert voice_channel.position == 4
        assert voice_channel.permission_overwrites == {
            4242: entity_factory_impl.deserialize_permission_overwrite(permission_overwrite_payload)
        }
        assert voice_channel.is_nsfw is True
        assert voice_channel.parent_id == 456
        assert voice_channel.bitrate == 64000
        assert voice_channel.user_limit == 3
        assert isinstance(voice_channel, channel_models.GuildVoiceChannel)

    def test_deserialize_guild_voice_channel_with_null_fields(self, entity_factory_impl):
        voice_channel = entity_factory_impl.deserialize_guild_voice_channel(
            {
                "id": "123",
                "permission_overwrites": [],
                "name": "Half Life 3",
                "parent_id": None,
                "nsfw": True,
                "position": 2,
                "guild_id": "1234",
                "bitrate": 64000,
                "user_limit": 3,
                "type": 6,
            }
        )
        assert voice_channel.parent_id is None

    def test_deserialize_guild_voice_channel_with_unset_fields(self, entity_factory_impl):
        voice_channel = entity_factory_impl.deserialize_guild_voice_channel(
            {
                "id": "123",
                "permission_overwrites": [],
                "name": "Half Life 3",
                "position": 2,
                "bitrate": 64000,
                "user_limit": 3,
                "type": 6,
            }
        )
        assert voice_channel.parent_id is None
        assert voice_channel.is_nsfw is None
        assert voice_channel.guild_id is None

    def test_deserialize_channel_returns_right_type(
        self,
        entity_factory_impl,
        dm_channel_payload,
        group_dm_channel_payload,
        guild_category_payload,
        guild_text_channel_payload,
        guild_news_channel_payload,
        guild_store_channel_payload,
        guild_voice_channel_payload,
    ):
        for payload, expected_type in [
            (dm_channel_payload, channel_models.DMChannel),
            (group_dm_channel_payload, channel_models.GroupDMChannel),
            (guild_category_payload, channel_models.GuildCategory),
            (guild_text_channel_payload, channel_models.GuildTextChannel),
            (guild_news_channel_payload, channel_models.GuildNewsChannel),
            (guild_store_channel_payload, channel_models.GuildStoreChannel),
            (guild_voice_channel_payload, channel_models.GuildVoiceChannel),
        ]:
            assert isinstance(entity_factory_impl.deserialize_channel(payload), expected_type)

    ################
    # EMBED MODELS #
    ################

    @pytest.fixture
    def embed_payload(self):
        return {
            "title": "embed title",
            "description": "embed description",
            "url": "https://somewhere.com",
            "timestamp": "2020-03-22T16:40:39.218000+00:00",
            "color": 14014915,
            "footer": {
                "text": "footer text",
                "icon_url": "https://somewhere.com/footer.png",
                "proxy_icon_url": "https://media.somewhere.com/footer.png",
            },
            "image": {
                "url": "https://somewhere.com/image.png",
                "proxy_url": "https://media.somewhere.com/image.png",
                "height": 122,
                "width": 133,
            },
            "thumbnail": {
                "url": "https://somewhere.com/thumbnail.png",
                "proxy_url": "https://media.somewhere.com/thumbnail.png",
                "height": 123,
                "width": 456,
            },
            "video": {"url": "https://somewhere.com/video.mp4", "height": 1234, "width": 4567},
            "provider": {"name": "some name", "url": "https://somewhere.com/provider"},
            "author": {
                "name": "some name",
                "url": "https://somewhere.com/author-url",
                "icon_url": "https://somewhere.com/author.png",
                "proxy_icon_url": "https://media.somewhere.com/author.png",
            },
            "fields": [{"name": "title", "value": "some value", "inline": True}],
        }

    def test_deserialize_embed_with_full_embed(self, entity_factory_impl, embed_payload):
        embed = entity_factory_impl.deserialize_embed(embed_payload)
        assert embed.title == "embed title"
        assert embed.description == "embed description"
        assert embed.url == "https://somewhere.com"
        assert embed.timestamp == datetime.datetime(2020, 3, 22, 16, 40, 39, 218000, tzinfo=datetime.timezone.utc)
        assert embed.color == color_models.Color(14014915)
        assert isinstance(embed.color, color_models.Color)
        # EmbedFooter
        assert embed.footer.text == "footer text"
        assert embed.footer.icon.resource.url == "https://somewhere.com/footer.png"
        assert embed.footer.icon.proxy_resource.url == "https://media.somewhere.com/footer.png"
        assert isinstance(embed.footer, embed_models.EmbedFooter)
        # EmbedImage
        assert embed.image.url == "https://somewhere.com/image.png"
        assert embed.image.proxy_resource.url == "https://media.somewhere.com/image.png"
        assert embed.image.height == 122
        assert embed.image.width == 133
        assert isinstance(embed.image, embed_models.EmbedImage)
        # EmbedThumbnail
        assert embed.thumbnail.url == "https://somewhere.com/thumbnail.png"
        assert embed.thumbnail.proxy_resource.url == "https://media.somewhere.com/thumbnail.png"
        assert embed.thumbnail.height == 123
        assert embed.thumbnail.width == 456
        assert isinstance(embed.thumbnail, embed_models.EmbedImage)
        # EmbedVideo
        assert embed.video.url == "https://somewhere.com/video.mp4"
        assert embed.video.height == 1234
        assert embed.video.width == 4567
        assert isinstance(embed.video, embed_models.EmbedVideo)
        # EmbedProvider
        assert embed.provider.name == "some name"
        assert embed.provider.url == "https://somewhere.com/provider"
        assert isinstance(embed.provider, embed_models.EmbedProvider)
        # EmbedAuthor
        assert embed.author.name == "some name"
        assert embed.author.url == "https://somewhere.com/author-url"
        assert embed.author.icon.url == "https://somewhere.com/author.png"
        assert embed.author.icon.proxy_resource.url == "https://media.somewhere.com/author.png"
        assert isinstance(embed.author, embed_models.EmbedAuthor)
        # EmbedField
        assert len(embed.fields) == 1
        field = embed.fields[0]
        assert field.name == "title"
        assert field.value == "some value"
        assert field.is_inline is True
        assert isinstance(field, embed_models.EmbedField)

    def test_deserialize_embed_with_partial_fields(self, entity_factory_impl, embed_payload):
        embed = entity_factory_impl.deserialize_embed(
            {
                "footer": {"text": "footer text"},
                "image": {},
                "thumbnail": {},
                "video": {},
                "provider": {},
                "author": {},
                "fields": [{"name": "title", "value": "some value"}],
            }
        )
        # EmbedFooter
        assert embed.footer.text == "footer text"
        assert embed.footer.icon is None
        # EmbedImage
        assert embed.image is None
        # EmbedThumbnail
        assert embed.thumbnail is None
        # EmbedVideo
        assert embed.video is None
        # EmbedProvider
        assert embed.provider is None
        # EmbedAuthor
        assert embed.author is None
        # EmbedField
        assert len(embed.fields) == 1
        field = embed.fields[0]
        assert field.name == "title"
        assert field.value == "some value"
        assert field.is_inline is False
        assert isinstance(field, embed_models.EmbedField)

    def test_deserialize_embed_with_empty_embed(self, entity_factory_impl):
        embed = entity_factory_impl.deserialize_embed({})
        assert embed.title is None
        assert embed.description is None
        assert embed.url is None
        assert embed.timestamp is None
        assert embed.color is None
        assert embed.footer is None
        assert embed.image is None
        assert embed.thumbnail is None
        assert embed.video is None
        assert embed.provider is None
        assert embed.author is None
        assert embed.fields == []

    def test_serialize_embed_with_non_url_resources_provides_attachments(self, entity_factory_impl):
        footer_icon = embed_models.EmbedResource(resource=files.File("cat.png"))
        thumbnail = embed_models.EmbedImage(resource=files.File("dog.png"))
        image = embed_models.EmbedImage(resource=files.Bytes(b"potato kung fu", filename="sushi.pdf"))
        author_icon = embed_models.EmbedResource(resource=files.Bytes(b"potato kung fu^2", filename="sushi².jpg"))

        payload, resources = entity_factory_impl.serialize_embed(
            embed_models.Embed(
                title="Title",
                description="Nyaa",
                url="https://some-url",
                timestamp=datetime.datetime(2020, 5, 29, 20, 37, 22, 865139),
                color=color_models.Color(321321),
                footer=embed_models.EmbedFooter(text="TEXT", icon=footer_icon),
                image=image,
                thumbnail=thumbnail,
                author=embed_models.EmbedAuthor(name="AUTH ME", url="wss://\\_/-_-\\_/", icon=author_icon),
                fields=[embed_models.EmbedField(value="VALUE", name="NAME", inline=True)],
            )
        )

        # Non URL bois should be returned in the resources container.
        assert len(resources) == 4
        assert footer_icon.resource in resources
        assert thumbnail.resource in resources
        assert image.resource in resources
        assert author_icon.resource in resources

        assert payload == {
            "title": "Title",
            "description": "Nyaa",
            "url": "https://some-url",
            "timestamp": "2020-05-29T20:37:22.865139",
            "color": 321321,
            "footer": {"text": "TEXT", "icon_url": footer_icon.url},
            "image": {"url": image.url},
            "thumbnail": {"url": thumbnail.url},
            "author": {"name": "AUTH ME", "url": "wss://\\_/-_-\\_/", "icon_url": author_icon.url},
            "fields": [{"value": "VALUE", "name": "NAME", "inline": True}],
        }

    def test_serialize_embed_with_url_resources_does_not_provide_attachments(self, entity_factory_impl):
        class DummyWebResource(files.WebResource):
            @property
            def url(self) -> str:
                return "http://lolbook.com"

            @property
            def filename(self) -> str:
                return "lolbook.png"

        footer_icon = embed_models.EmbedResource(resource=files.URL("http://http.cat"))
        thumbnail = embed_models.EmbedImage(resource=DummyWebResource())
        image = embed_models.EmbedImage(resource=files.URL("http://bazbork.com"))
        author_icon = embed_models.EmbedResource(resource=files.URL("http://foobar.com"))

        payload, resources = entity_factory_impl.serialize_embed(
            embed_models.Embed(
                title="Title",
                description="Nyaa",
                url="https://some-url",
                timestamp=datetime.datetime(2020, 5, 29, 20, 37, 22, 865139),
                color=color_models.Color(321321),
                footer=embed_models.EmbedFooter(text="TEXT", icon=footer_icon),
                image=image,
                thumbnail=thumbnail,
                author=embed_models.EmbedAuthor(name="AUTH ME", url="wss://\\_/-_-\\_/", icon=author_icon),
                fields=[embed_models.EmbedField(value="VALUE", name="NAME", inline=True)],
            )
        )

        # Non URL bois should be returned in the resources container.
        assert footer_icon.resource not in resources
        assert thumbnail.resource not in resources
        assert image.resource not in resources
        assert author_icon.resource not in resources
        assert not resources

        assert payload == {
            "title": "Title",
            "description": "Nyaa",
            "url": "https://some-url",
            "timestamp": "2020-05-29T20:37:22.865139",
            "color": 321321,
            "footer": {"text": "TEXT", "icon_url": footer_icon.url},
            "image": {"url": image.url},
            "thumbnail": {"url": thumbnail.url},
            "author": {"name": "AUTH ME", "url": "wss://\\_/-_-\\_/", "icon_url": author_icon.url},
            "fields": [{"value": "VALUE", "name": "NAME", "inline": True}],
        }

    def test_serialize_embed_with_null_sub_fields(self, entity_factory_impl):
        payload, resources = entity_factory_impl.serialize_embed(
            embed_models.Embed(
                title="Title",
                description="Nyaa",
                url="https://some-url",
                timestamp=datetime.datetime(2020, 5, 29, 20, 37, 22, 865139),
                color=color_models.Color(321321),
                footer=embed_models.EmbedFooter(),
                image=None,
                thumbnail=None,
                author=embed_models.EmbedAuthor(),
            )
        )
        assert payload == {
            "title": "Title",
            "description": "Nyaa",
            "url": "https://some-url",
            "timestamp": "2020-05-29T20:37:22.865139",
            "color": 321321,
        }
        assert resources == []

    def test_serialize_embed_with_null_attributes(self, entity_factory_impl):
        assert entity_factory_impl.serialize_embed(embed_models.Embed()) == ({}, [])

    ################
    # EMOJI MODELS #
    ################

    def test_deserialize_unicode_emoji(self, entity_factory_impl):
        emoji = entity_factory_impl.deserialize_unicode_emoji({"name": "🤷"})
        assert emoji.name == "🤷"
        assert isinstance(emoji, emoji_models.UnicodeEmoji)

    @pytest.fixture()
    def custom_emoji_payload(self):
        return {"id": "691225175349395456", "name": "test", "animated": True}

    def test_deserialize_custom_emoji(self, entity_factory_impl, mock_app, custom_emoji_payload):
        emoji = entity_factory_impl.deserialize_custom_emoji(custom_emoji_payload)
        assert emoji.app is mock_app
        assert emoji.id == 691225175349395456
        assert emoji.name == "test"
        assert emoji.is_animated is True
        assert isinstance(emoji, emoji_models.CustomEmoji)

    def test_deserialize_custom_emoji_with_unset_and_null_fields(
        self, entity_factory_impl, mock_app, custom_emoji_payload
    ):
        emoji = entity_factory_impl.deserialize_custom_emoji({"id": "691225175349395456", "name": None})
        assert emoji.is_animated is False
        assert emoji.name is None

    @pytest.fixture()
    def known_custom_emoji_payload(self, user_payload):
        return {
            "id": "12345",
            "name": "testing",
            "animated": False,
            "available": True,
            "roles": ["123", "456"],
            "user": user_payload,
            "require_colons": True,
            "managed": False,
        }

    def test_deserialize_known_custom_emoji(
        self, entity_factory_impl, mock_app, user_payload, known_custom_emoji_payload
    ):
        emoji = entity_factory_impl.deserialize_known_custom_emoji(known_custom_emoji_payload)
        assert emoji.app is mock_app
        assert emoji.id == 12345
        assert emoji.name == "testing"
        assert emoji.is_animated is False
        assert emoji.role_ids == {123, 456}
        assert emoji.user == entity_factory_impl.deserialize_user(user_payload)
        assert emoji.is_colons_required is True
        assert emoji.is_managed is False
        assert emoji.is_available is True
        assert isinstance(emoji, emoji_models.KnownCustomEmoji)

    def test_deserialize_known_custom_emoji_with_unset_fields(self, entity_factory_impl):
        emoji = entity_factory_impl.deserialize_known_custom_emoji(
            {
                "id": "12345",
                "name": "testing",
                "available": True,
                "roles": ["123", "456"],
                "require_colons": True,
                "managed": False,
            }
        )
        assert emoji.user is None
        assert emoji.is_animated is False

    @pytest.mark.parametrize(
        ["payload", "expected_type"],
        [({"name": "🤷"}, emoji_models.UnicodeEmoji), ({"id": "1234", "name": "test"}, emoji_models.CustomEmoji)],
    )
    def test_deserialize_emoji_returns_expected_type(self, entity_factory_impl, payload, expected_type):
        isinstance(entity_factory_impl.deserialize_emoji(payload), expected_type)

    ##################
    # GATEWAY MODELS #
    ##################

    @pytest.fixture()
    def gateway_bot_payload(self):
        return {
            "url": "wss://gateway.discord.gg",
            "shards": 1,
            "session_start_limit": {"total": 1000, "remaining": 991, "reset_after": 14170186, "max_concurrency": 5},
        }

    def test_deserialize_gateway_bot(self, entity_factory_impl, gateway_bot_payload):
        gateway_bot = entity_factory_impl.deserialize_gateway_bot(gateway_bot_payload)
        assert isinstance(gateway_bot, gateway_models.GatewayBot)
        assert gateway_bot.url == "wss://gateway.discord.gg"
        assert gateway_bot.shard_count == 1
        # SessionStartLimit
        assert isinstance(gateway_bot.session_start_limit, gateway_models.SessionStartLimit)
        assert gateway_bot.session_start_limit.max_concurrency == 5
        assert gateway_bot.session_start_limit.total == 1000
        assert gateway_bot.session_start_limit.remaining == 991
        assert gateway_bot.session_start_limit.reset_after == datetime.timedelta(milliseconds=14170186)

    ################
    # GUILD MODELS #
    ################

    @pytest.fixture()
    def guild_embed_payload(self):
        return {"channel_id": "123123123", "enabled": True}

    def test_deserialize_widget_embed(self, entity_factory_impl, mock_app, guild_embed_payload):
        guild_embed = entity_factory_impl.deserialize_guild_widget(guild_embed_payload)
        assert guild_embed.app is mock_app
        assert guild_embed.channel_id == 123123123
        assert guild_embed.is_enabled is True
        assert isinstance(guild_embed, guild_models.GuildWidget)

    def test_deserialize_guild_embed_with_null_fields(self, entity_factory_impl, mock_app):
        assert entity_factory_impl.deserialize_guild_widget({"channel_id": None, "enabled": True}).channel_id is None

    @pytest.fixture()
    def member_payload(self, user_payload):
        return {
            "nick": "foobarbaz",
            "roles": ["11111", "22222", "33333", "44444"],
            "joined_at": "2015-04-26T06:26:56.936000+00:00",
            "premium_since": "2019-05-17T06:26:56.936000+00:00",
            "deaf": False,
            "mute": True,
            "user": user_payload,
        }

    def test_deserialize_member(self, entity_factory_impl, mock_app, member_payload, user_payload):
        member = entity_factory_impl.deserialize_member(member_payload)
        assert member.app is mock_app
        assert member.user == entity_factory_impl.deserialize_user(user_payload)
        assert member.nickname == "foobarbaz"
        assert member.role_ids == {11111, 22222, 33333, 44444}
        assert member.joined_at == datetime.datetime(2015, 4, 26, 6, 26, 56, 936000, tzinfo=datetime.timezone.utc)
        assert member.premium_since == datetime.datetime(2019, 5, 17, 6, 26, 56, 936000, tzinfo=datetime.timezone.utc)
        assert member.is_deaf is False
        assert member.is_mute is True
        assert isinstance(member, guild_models.Member)

    def test_deserialize_member_with_null_fields(self, entity_factory_impl, user_payload):
        member = entity_factory_impl.deserialize_member(
            {
                "nick": None,
                "roles": ["11111", "22222", "33333", "44444"],
                "joined_at": None,
                "premium_since": None,
                "deaf": False,
                "mute": True,
                "user": user_payload,
            }
        )
        assert member.nickname is None
        assert member.premium_since is None
        assert member.is_deaf is False
        assert member.is_mute is True
        assert isinstance(member, guild_models.Member)
        assert member.joined_at is undefined.UNDEFINED

    def test_deserialize_member_with_undefined_fields(self, entity_factory_impl, user_payload):
        member = entity_factory_impl.deserialize_member(
            {
                "roles": ["11111", "22222", "33333", "44444"],
                "joined_at": "2015-04-26T06:26:56.936000+00:00",
                "user": user_payload,
            }
        )
        assert member.nickname is undefined.UNDEFINED
        assert member.premium_since is undefined.UNDEFINED
        assert member.is_deaf is undefined.UNDEFINED
        assert member.is_mute is undefined.UNDEFINED

    def test_deserialize_member_with_passed_through_user_object(self, entity_factory_impl):
        mock_user = mock.MagicMock(user_models.User)
        member = entity_factory_impl.deserialize_member(
            {
                "nick": "foobarbaz",
                "roles": ["11111", "22222", "33333", "44444"],
                "joined_at": "2015-04-26T06:26:56.936000+00:00",
                "premium_since": "2019-05-17T06:26:56.936000+00:00",
                "deaf": False,
                "mute": True,
            },
            user=mock_user,
        )
        assert member.user is mock_user

    @pytest.fixture()
    def guild_role_payload(self):
        return {
            "id": "41771983423143936",
            "name": "WE DEM BOYZZ!!!!!!",
            "color": 3_447_003,
            "hoist": True,
            "position": 0,
            "permissions": 66_321_471,
            "managed": False,
            "mentionable": False,
        }

    def test_deserialize_role(self, entity_factory_impl, mock_app, guild_role_payload):
        guild_role = entity_factory_impl.deserialize_role(guild_role_payload)
        assert guild_role.app is mock_app
        assert guild_role.id == 41771983423143936
        assert guild_role.name == "WE DEM BOYZZ!!!!!!"
        assert guild_role.color == color_models.Color(3_447_003)
        assert guild_role.is_hoisted is True
        assert guild_role.position == 0
        assert guild_role.permissions == permission_models.Permission(66_321_471)
        assert guild_role.is_managed is False
        assert guild_role.is_mentionable is False
        assert isinstance(guild_role, guild_models.Role)

    @pytest.fixture()
    def partial_integration_payload(self):
        return {
            "id": "4949494949",
            "name": "Blah blah",
            "type": "twitch",
            "account": {"id": "543453", "name": "Blam"},
        }

    def test_deserialize_partial_integration(self, entity_factory_impl, partial_integration_payload):
        partial_integration = entity_factory_impl.deserialize_partial_integration(partial_integration_payload)
        assert partial_integration.id == 4949494949
        assert partial_integration.name == "Blah blah"
        assert partial_integration.type == "twitch"
        assert isinstance(partial_integration, guild_models.PartialIntegration)
        # IntegrationAccount
        assert partial_integration.account.id == "543453"
        assert partial_integration.account.name == "Blam"
        assert isinstance(partial_integration.account, guild_models.IntegrationAccount)

    @pytest.fixture()
    def integration_payload(self, user_payload):
        return {
            "id": "420",
            "name": "blaze it",
            "type": "youtube",
            "account": {"id": "6969", "name": "Blaze it"},
            "enabled": True,
            "syncing": False,
            "role_id": "98494949",
            "enable_emoticons": False,
            "expire_behavior": 1,
            "expire_grace_period": 7,
            "user": user_payload,
            "synced_at": "2015-04-26T06:26:56.936000+00:00",
        }

    def test_deserialize_integration(self, entity_factory_impl, integration_payload, user_payload):
        integration = entity_factory_impl.deserialize_integration(integration_payload)
        assert integration.id == 420
        assert integration.name == "blaze it"
        assert integration.type == "youtube"
        # IntegrationAccount
        assert integration.account.id == "6969"
        assert integration.account.name == "Blaze it"
        assert isinstance(integration.account, guild_models.IntegrationAccount)

        assert integration.is_enabled is True
        assert integration.is_syncing is False
        assert integration.role_id == 98494949
        assert integration.is_emojis_enabled is False
        assert integration.expire_behavior == guild_models.IntegrationExpireBehaviour.KICK
        assert integration.expire_grace_period == datetime.timedelta(days=7)
        assert integration.user == entity_factory_impl.deserialize_user(user_payload)
        assert integration.last_synced_at == datetime.datetime(
            2015, 4, 26, 6, 26, 56, 936000, tzinfo=datetime.timezone.utc
        )
        assert isinstance(integration, guild_models.Integration)

    def test_deserialize_guild_integration_with_null_and_unset_fields(self, entity_factory_impl, user_payload):
        integration = entity_factory_impl.deserialize_integration(
            {
                "id": "420",
                "name": "blaze it",
                "type": "youtube",
                "account": {"id": "6969", "name": "Blaze it"},
                "enabled": True,
                "syncing": False,
                "role_id": "98494949",
                "expire_behavior": 1,
                "expire_grace_period": 7,
                "user": user_payload,
                "synced_at": None,
            }
        )
        assert integration.is_emojis_enabled is None
        assert integration.last_synced_at is None

    @pytest.fixture()
    def guild_member_ban_payload(self, user_payload):
        return {"reason": "Get nyaa'ed", "user": user_payload}

    def test_deserialize_guild_member_ban(self, entity_factory_impl, guild_member_ban_payload, user_payload):
        member_ban = entity_factory_impl.deserialize_guild_member_ban(guild_member_ban_payload)
        assert member_ban.reason == "Get nyaa'ed"
        assert member_ban.user == entity_factory_impl.deserialize_user(user_payload)
        assert isinstance(member_ban, guild_models.GuildMemberBan)

    def test_deserialize_guild_member_ban_with_null_fields(self, entity_factory_impl, user_payload):
        assert entity_factory_impl.deserialize_guild_member_ban({"reason": None, "user": user_payload}).reason is None

    def test_deserialize_unavailable_guild(self, entity_factory_impl, mock_app):
        unavailable_guild = entity_factory_impl.deserialize_unavailable_guild({"id": "42069", "unavailable": True})
        assert unavailable_guild.id == 42069
        assert unavailable_guild.is_unavailable is True
        assert isinstance(unavailable_guild, guild_models.UnavailableGuild)

    @pytest.fixture()
    def guild_preview_payload(self, known_custom_emoji_payload):
        return {
            "id": "152559372126519269",
            "name": "Isopropyl",
            "icon": "d4a983885dsaa7691ce8bcaaf945a",
            "splash": "dsa345tfcdg54b",
            "discovery_splash": "lkodwaidi09239uid",
            "emojis": [known_custom_emoji_payload],
            "features": ["DISCOVERABLE", "FORCE_RELAY"],
            "approximate_member_count": 69,
            "approximate_presence_count": 42,
            "description": "A DESCRIPTION.",
        }

    def test_deserialize_guild_preview(
        self, entity_factory_impl, mock_app, guild_preview_payload, known_custom_emoji_payload
    ):
        guild_preview = entity_factory_impl.deserialize_guild_preview(guild_preview_payload)
        assert guild_preview.app is mock_app
        assert guild_preview.id == 152559372126519269
        assert guild_preview.name == "Isopropyl"
        assert guild_preview.icon_hash == "d4a983885dsaa7691ce8bcaaf945a"
        assert guild_preview.features == {guild_models.GuildFeature.DISCOVERABLE, "FORCE_RELAY"}
        assert guild_preview.splash_hash == "dsa345tfcdg54b"
        assert guild_preview.discovery_splash_hash == "lkodwaidi09239uid"
        assert guild_preview.emojis == {
            12345: entity_factory_impl.deserialize_known_custom_emoji(known_custom_emoji_payload)
        }
        assert guild_preview.approximate_member_count == 69
        assert guild_preview.approximate_presence_count == 42
        assert guild_preview.description == "A DESCRIPTION."
        assert isinstance(guild_preview, guild_models.GuildPreview)

    def test_deserialize_guild_preview_with_null_fields(self, entity_factory_impl, mock_app, guild_preview_payload):
        guild_preview = entity_factory_impl.deserialize_guild_preview(
            {
                "id": "152559372126519269",
                "name": "Isopropyl",
                "icon": None,
                "splash": None,
                "discovery_splash": None,
                "emojis": [],
                "features": ["DISCOVERABLE", "FORCE_RELAY"],
                "approximate_member_count": 69,
                "approximate_presence_count": 42,
                "description": None,
            }
        )
        assert guild_preview.icon_hash is None
        assert guild_preview.splash_hash is None
        assert guild_preview.discovery_splash_hash is None
        assert guild_preview.description is None

    @pytest.fixture()
    def guild_payload(
        self,
        guild_text_channel_payload,
        guild_voice_channel_payload,
        guild_news_channel_payload,
        known_custom_emoji_payload,
        member_payload,
        member_presence_payload,
        guild_role_payload,
        voice_state_payload,
    ):
        return {
            "afk_channel_id": "99998888777766",
            "afk_timeout": 1200,
            "application_id": "39494949",
            "approximate_member_count": 15,
            "approximate_presence_count": 7,
            "banner": "1a2b3c",
            "channels": [guild_text_channel_payload, guild_voice_channel_payload, guild_news_channel_payload],
            "default_message_notifications": 1,
            "description": "This is a server I guess, its a bit crap though",
            "discovery_splash": "famfamFAMFAMfam",
            "embed_channel_id": "9439394949",
            "embed_enabled": True,
            "emojis": [known_custom_emoji_payload],
            "explicit_content_filter": 2,
            "features": ["ANIMATED_ICON", "MORE_EMOJI", "NEWS", "SOME_UNDOCUMENTED_FEATURE"],
            "icon": "1a2b3c4d",
            "id": "265828729970753537",
            "joined_at": "2019-05-17T06:26:56.936000+00:00",
            "large": False,
            "max_members": 25000,
            "max_presences": 250,
            "max_video_channel_users": 25,
            "member_count": 14,
            "members": [member_payload],
            "mfa_level": 1,
            "name": "L33t guild",
            "owner_id": "6969696",
            "permissions": 66_321_471,
            "preferred_locale": "en-GB",
            "premium_subscription_count": 1,
            "premium_tier": 2,
            "presences": [member_presence_payload],
            "public_updates_channel_id": "33333333",
            "region": "eu-central",
            "roles": [guild_role_payload],
            "rules_channel_id": "42042069",
            "splash": "0ff0ff0ff",
            "system_channel_flags": 3,
            "system_channel_id": "19216801",
            "unavailable": False,
            "vanity_url_code": "loool",
            "verification_level": 4,
            "voice_states": [voice_state_payload],
            "widget_channel_id": "9439394949",
            "widget_enabled": True,
        }

    def test_deserialize_guild(
        self,
        entity_factory_impl,
        mock_app,
        guild_payload,
        guild_text_channel_payload,
        guild_voice_channel_payload,
        guild_news_channel_payload,
        known_custom_emoji_payload,
        member_payload,
        member_presence_payload,
        guild_role_payload,
        voice_state_payload,
    ):
        guild = entity_factory_impl.deserialize_guild(guild_payload)
        assert guild.app is mock_app
        assert guild.id == 265828729970753537
        assert guild.name == "L33t guild"
        assert guild.icon_hash == "1a2b3c4d"
        assert guild.features == {
            guild_models.GuildFeature.ANIMATED_ICON,
            guild_models.GuildFeature.MORE_EMOJI,
            guild_models.GuildFeature.NEWS,
            "SOME_UNDOCUMENTED_FEATURE",
        }
        assert guild.splash_hash == "0ff0ff0ff"
        assert guild.discovery_splash_hash == "famfamFAMFAMfam"
        assert guild.owner_id == 6969696
        assert guild.my_permissions == permission_models.Permission(66_321_471)
        assert guild.region == "eu-central"
        assert guild.afk_channel_id == 99998888777766
        assert guild.afk_timeout == datetime.timedelta(seconds=1200)
        assert guild.is_embed_enabled is True
        assert guild.embed_channel_id == 9439394949
        assert guild.verification_level == guild_models.GuildVerificationLevel.VERY_HIGH
        assert guild.default_message_notifications == guild_models.GuildMessageNotificationsLevel.ONLY_MENTIONS
        assert guild.explicit_content_filter == guild_models.GuildExplicitContentFilterLevel.ALL_MEMBERS
        assert guild.roles == {41771983423143936: entity_factory_impl.deserialize_role(guild_role_payload)}
        assert guild.emojis == {12345: entity_factory_impl.deserialize_known_custom_emoji(known_custom_emoji_payload)}
        assert guild.mfa_level == guild_models.GuildMFALevel.ELEVATED
        assert guild.application_id == 39494949
        assert guild.is_unavailable is False
        assert guild.widget_channel_id == 9439394949
        assert guild.is_widget_enabled is True
        assert guild.system_channel_id == 19216801
        assert guild.system_channel_flags == guild_models.GuildSystemChannelFlag(3)
        assert guild.rules_channel_id == 42042069
        assert guild.joined_at == datetime.datetime(2019, 5, 17, 6, 26, 56, 936000, tzinfo=datetime.timezone.utc)
        assert guild.is_large is False
        assert guild.member_count == 14
        assert guild.members == {115590097100865541: entity_factory_impl.deserialize_member(member_payload)}
        assert guild.channels == {
            123: entity_factory_impl.deserialize_guild_text_channel(guild_text_channel_payload),
            555: entity_factory_impl.deserialize_guild_voice_channel(guild_voice_channel_payload),
            7777: entity_factory_impl.deserialize_guild_news_channel(guild_news_channel_payload),
        }
        assert guild.presences == {
            115590097100865541: entity_factory_impl.deserialize_member_presence(member_presence_payload)
        }
        assert guild.max_presences == 250
        assert guild.max_members == 25000
        assert guild.max_video_channel_users == 25
        assert guild.vanity_url_code == "loool"
        assert guild.description == "This is a server I guess, its a bit crap though"
        assert guild.banner_hash == "1a2b3c"
        assert guild.premium_tier == guild_models.GuildPremiumTier.TIER_2
        assert guild.premium_subscription_count == 1
        assert guild.preferred_locale == "en-GB"
        assert guild.public_updates_channel_id == 33333333
        assert guild.approximate_member_count == 15
        assert guild.approximate_active_member_count == 7

    def test_deserialize_guild_with_unset_fields(self, entity_factory_impl):
        guild = entity_factory_impl.deserialize_guild(
            {
                "afk_channel_id": "99998888777766",
                "afk_timeout": 1200,
                "application_id": "39494949",
                "banner": "1a2b3c",
                "default_message_notifications": 1,
                "description": "This is a server I guess, its a bit crap though",
                "discovery_splash": "famfamFAMFAMfam",
                "emojis": [],
                "explicit_content_filter": 2,
                "features": ["ANIMATED_ICON", "MORE_EMOJI", "NEWS", "SOME_UNDOCUMENTED_FEATURE"],
                "icon": "1a2b3c4d",
                "id": "265828729970753537",
                "mfa_level": 1,
                "name": "L33t guild",
                "owner_id": "6969696",
                "preferred_locale": "en-GB",
                "premium_tier": 2,
                "public_updates_channel_id": "33333333",
                "region": "eu-central",
                "roles": [],
                "rules_channel_id": "42042069",
                "splash": "0ff0ff0ff",
                "system_channel_flags": 3,
                "system_channel_id": "19216801",
                "vanity_url_code": "loool",
                "verification_level": 4,
            }
        )
        assert guild.channels == {}
        assert guild.embed_channel_id is None
        assert guild.is_embed_enabled is False
        assert guild.joined_at is None
        assert guild.is_large is None
        assert guild.max_members is None
        assert guild.max_presences is None
        assert guild.max_video_channel_users is None
        assert guild.member_count is None
        assert guild.members == {}
        assert guild.my_permissions is None
        assert guild.premium_subscription_count is None
        assert guild.presences == {}
        assert guild.is_unavailable is None
        assert guild.widget_channel_id is None
        assert guild.is_widget_enabled is None
        assert guild.approximate_active_member_count is None
        assert guild.approximate_active_member_count is None

    def test_deserialize_guild_with_null_fields(self, entity_factory_impl):
        guild = entity_factory_impl.deserialize_guild(
            {
                "afk_channel_id": None,
                "afk_timeout": 1200,
                "application_id": None,
                "approximate_member_count": 15,
                "approximate_presence_count": 7,
                "banner": None,
                "channels": [],
                "default_message_notifications": 1,
                "description": None,
                "discovery_splash": None,
                "embed_channel_id": None,
                "embed_enabled": True,
                "emojis": [],
                "explicit_content_filter": 2,
                "features": ["ANIMATED_ICON", "MORE_EMOJI", "NEWS", "SOME_UNDOCUMENTED_FEATURE"],
                "icon": None,
                "id": "265828729970753537",
                "joined_at": "2019-05-17T06:26:56.936000+00:00",
                "large": False,
                "max_members": 25000,
                "max_presences": None,
                "max_video_channel_users": 25,
                "member_count": 14,
                "members": [],
                "mfa_level": 1,
                "name": "L33t guild",
                "owner_id": "6969696",
                "permissions": 66_321_471,
                "preferred_locale": "en-GB",
                "premium_subscription_count": None,
                "premium_tier": 2,
                "presences": [],
                "public_updates_channel_id": None,
                "region": "eu-central",
                "roles": [],
                "rules_channel_id": None,
                "splash": None,
                "system_channel_flags": 3,
                "system_channel_id": None,
                "unavailable": False,
                "vanity_url_code": None,
                "verification_level": 4,
                "voice_states": [],
                "widget_channel_id": None,
                "widget_enabled": True,
            }
        )
        assert guild.icon_hash is None
        assert guild.splash_hash is None
        assert guild.discovery_splash_hash is None
        assert guild.afk_channel_id is None
        assert guild.embed_channel_id is None
        assert guild.application_id is None
        assert guild.widget_channel_id is None
        assert guild.system_channel_id is None
        assert guild.rules_channel_id is None
        assert guild.max_presences is None
        assert guild.vanity_url_code is None
        assert guild.description is None
        assert guild.banner_hash is None
        assert guild.premium_subscription_count is None
        assert guild.public_updates_channel_id is None

    #################
    # INVITE MODELS #
    #################

    @pytest.fixture()
    def vanity_url_payload(self):
        return {"code": "iamacode", "uses": 42}

    def test_deserialize_vanity_url(self, entity_factory_impl, mock_app, vanity_url_payload):
        vanity_url = entity_factory_impl.deserialize_vanity_url(vanity_url_payload)
        assert vanity_url.app is mock_app
        assert vanity_url.code == "iamacode"
        assert vanity_url.uses == 42
        assert isinstance(vanity_url, invite_models.VanityURL)

    @pytest.fixture()
    def alternative_user_payload(self):
        return {"id": "1231231", "username": "soad", "discriminator": "3333", "avatar": None}

    @pytest.fixture()
    def invite_payload(self, partial_channel_payload, user_payload, alternative_user_payload):
        return {
            "code": "aCode",
            "guild": {
                "id": "56188492224814744",
                "name": "Testin' Your Scene",
                "splash": "aSplashForSure",
                "banner": "aBannerForSure",
                "description": "Describe me cute kitty.",
                "icon": "bb71f469c158984e265093a81b3397fb",
                "features": ["FORCE_RELAY"],
                "verification_level": 2,
                "vanity_url_code": "I-am-very-vain",
            },
            "channel": partial_channel_payload,
            "inviter": user_payload,
            "target_user": alternative_user_payload,
            "target_user_type": 1,
            "approximate_presence_count": 42,
            "approximate_member_count": 84,
        }

    def test_deserialize_invite(
        self,
        entity_factory_impl,
        mock_app,
        invite_payload,
        partial_channel_payload,
        user_payload,
        alternative_user_payload,
    ):
        invite = entity_factory_impl.deserialize_invite(invite_payload)
        assert invite.app is mock_app
        assert invite.code == "aCode"
        # InviteGuild
        assert invite.guild.id == 56188492224814744
        assert invite.guild.name == "Testin' Your Scene"
        assert invite.guild.icon_hash == "bb71f469c158984e265093a81b3397fb"
        assert invite.guild.features == {"FORCE_RELAY"}
        assert invite.guild.splash_hash == "aSplashForSure"
        assert invite.guild.banner_hash == "aBannerForSure"
        assert invite.guild.description == "Describe me cute kitty."
        assert invite.guild.verification_level == guild_models.GuildVerificationLevel.MEDIUM
        assert invite.guild.vanity_url_code == "I-am-very-vain"

        assert invite.guild_id == 56188492224814744
        assert invite.channel == entity_factory_impl.deserialize_partial_channel(partial_channel_payload)
        assert invite.channel_id == 561884984214814750
        assert invite.inviter == entity_factory_impl.deserialize_user(user_payload)
        assert invite.target_user == entity_factory_impl.deserialize_user(alternative_user_payload)
        assert invite.target_user_type == invite_models.TargetUserType.STREAM
        assert invite.approximate_member_count == 84
        assert invite.approximate_presence_count == 42
        assert isinstance(invite, invite_models.Invite)

    def test_deserialize_invite_with_null_and_unset_fields(self, entity_factory_impl, partial_channel_payload):
        invite = entity_factory_impl.deserialize_invite({"code": "aCode", "channel_id": "43123123"})
        assert invite.channel is None
        assert invite.channel_id == 43123123
        assert invite.guild is None
        assert invite.inviter is None
        assert invite.target_user is None
        assert invite.target_user_type is None
        assert invite.approximate_presence_count is None
        assert invite.approximate_member_count is None

    def test_deserialize_invite_with_guild_and_channel_ids_without_objects(self, entity_factory_impl):
        invite = entity_factory_impl.deserialize_invite({"code": "aCode", "guild_id": "42", "channel_id": "202020"})
        assert invite.channel is None
        assert invite.channel_id == 202020
        assert invite.guild is None
        assert invite.guild_id == 42

    @pytest.fixture()
    def invite_with_metadata_payload(self, partial_channel_payload, user_payload, alternative_user_payload):
        return {
            "code": "aCode",
            "guild": {
                "id": "56188492224814744",
                "name": "Testin' Your Scene",
                "splash": "aSplashForSure",
                "banner": "aBannerForSure",
                "description": "Describe me cute kitty.",
                "icon": "bb71f469c158984e265093a81b3397fb",
                "features": ["FORCE_RELAY"],
                "verification_level": 2,
                "vanity_url_code": "I-am-very-vain",
            },
            "channel": partial_channel_payload,
            "inviter": user_payload,
            "target_user": alternative_user_payload,
            "target_user_type": 1,
            "approximate_presence_count": 42,
            "approximate_member_count": 84,
            "uses": 3,
            "max_uses": 8,
            "max_age": 239349393,
            "temporary": True,
            "created_at": "2015-04-26T06:26:56.936000+00:00",
        }

    def test_deserialize_invite_with_metadata(
        self,
        entity_factory_impl,
        mock_app,
        invite_with_metadata_payload,
        partial_channel_payload,
        user_payload,
        alternative_user_payload,
    ):
        invite_with_metadata = entity_factory_impl.deserialize_invite_with_metadata(invite_with_metadata_payload)
        assert invite_with_metadata.app is mock_app
        assert invite_with_metadata.code == "aCode"
        # InviteGuild
        assert invite_with_metadata.guild.id == 56188492224814744
        assert invite_with_metadata.guild.name == "Testin' Your Scene"
        assert invite_with_metadata.guild.icon_hash == "bb71f469c158984e265093a81b3397fb"
        assert invite_with_metadata.guild.features == {"FORCE_RELAY"}
        assert invite_with_metadata.guild.splash_hash == "aSplashForSure"
        assert invite_with_metadata.guild.banner_hash == "aBannerForSure"
        assert invite_with_metadata.guild.description == "Describe me cute kitty."
        assert invite_with_metadata.guild.verification_level == guild_models.GuildVerificationLevel.MEDIUM
        assert invite_with_metadata.guild.vanity_url_code == "I-am-very-vain"

        assert invite_with_metadata.channel == entity_factory_impl.deserialize_partial_channel(partial_channel_payload)
        assert invite_with_metadata.inviter == entity_factory_impl.deserialize_user(user_payload)
        assert invite_with_metadata.target_user == entity_factory_impl.deserialize_user(alternative_user_payload)
        assert invite_with_metadata.target_user_type == invite_models.TargetUserType.STREAM
        assert invite_with_metadata.approximate_member_count == 84
        assert invite_with_metadata.approximate_presence_count == 42
        assert invite_with_metadata.uses == 3
        assert invite_with_metadata.max_uses == 8
        assert invite_with_metadata.max_age == datetime.timedelta(seconds=239349393)
        assert invite_with_metadata.is_temporary is True
        assert invite_with_metadata.created_at == datetime.datetime(
            2015, 4, 26, 6, 26, 56, 936000, tzinfo=datetime.timezone.utc
        )
        assert isinstance(invite_with_metadata, invite_models.InviteWithMetadata)

    def test_deserialize_invite_with_metadata_with_null_and_unset_fields(
        self, entity_factory_impl, partial_channel_payload
    ):
        invite_with_metadata = entity_factory_impl.deserialize_invite(
            {
                "code": "aCode",
                "channel": partial_channel_payload,
                "uses": 42,
                "max_uses": 0,
                "max_age": 0,
                "temporary": True,
                "created_at": "2015-04-26T06:26:56.936000+00:00",
            }
        )
        assert invite_with_metadata.guild is None
        assert invite_with_metadata.inviter is None
        assert invite_with_metadata.target_user is None
        assert invite_with_metadata.target_user_type is None
        assert invite_with_metadata.approximate_presence_count is None
        assert invite_with_metadata.approximate_member_count is None

    def test_max_age_when_zero(self, entity_factory_impl, invite_with_metadata_payload):
        invite_with_metadata_payload["max_age"] = 0
        assert entity_factory_impl.deserialize_invite_with_metadata(invite_with_metadata_payload).max_age is None

    ##################
    # MESSAGE MODELS #
    ##################

    @pytest.fixture()
    def partial_application_payload(self):
        return {
            "id": "456",
            "name": "hikari",
            "description": "The best application",
            "icon": "2658b3029e775a931ffb49380073fa63",
            "cover_image": "58982a23790c4f22787b05d3be38a026",
            "summary": "asas",
        }

    @pytest.fixture()
    def message_payload(
        self, user_payload, member_payload, custom_emoji_payload, partial_application_payload, embed_payload
    ):
        del member_payload["user"]
        return {
            "id": "123",
            "channel_id": "456",
            "guild_id": "678",
            "author": user_payload,
            "member": member_payload,
            "content": "some info",
            "timestamp": "2020-03-21T21:20:16.510000+00:00",
            "edited_timestamp": "2020-04-21T21:20:16.510000+00:00",
            "tts": True,
            "mention_everyone": True,
            "mentions": [
                {"id": "5678", "username": "uncool username", "avatar": "129387dskjafhasf", "discriminator": "4532"}
            ],
            "mention_roles": ["987"],
            "mention_channels": [{"id": "456", "guild_id": "678", "type": 1, "name": "hikari-testing"}],
            "attachments": [
                {
                    "id": "690922406474154014",
                    "filename": "IMG.jpg",
                    "size": 660521,
                    "url": "https://somewhere.com/attachments/123/456/IMG.jpg",
                    "proxy_url": "https://media.somewhere.com/attachments/123/456/IMG.jpg",
                    "width": 1844,
                    "height": 2638,
                }
            ],
            "embeds": [embed_payload],
            "reactions": [{"emoji": custom_emoji_payload, "count": 100, "me": True}],
            "pinned": True,
            "webhook_id": "1234",
            "type": 0,
            "activity": {"type": 5, "party_id": "ae488379-351d-4a4f-ad32-2b9b01c91657"},
            "application": partial_application_payload,
            "message_reference": {
                "channel_id": "278325129692446722",
                "guild_id": "278325129692446720",
                "message_id": "306588351130107906",
            },
            "flags": 2,
            "nonce": "171000788183678976",
        }

    def test_deserialize_full_message(
        self,
        entity_factory_impl,
        mock_app,
        message_payload,
        user_payload,
        member_payload,
        partial_application_payload,
        custom_emoji_payload,
        embed_payload,
    ):
        message = entity_factory_impl.deserialize_message(message_payload)
        assert message.app is mock_app
        assert message.id == 123
        assert message.channel_id == 456
        assert message.guild_id == 678
        assert message.author == entity_factory_impl.deserialize_user(user_payload)
        assert message.member == entity_factory_impl.deserialize_member(member_payload, user=message.author)
        assert message.content == "some info"
        assert message.timestamp == datetime.datetime(2020, 3, 21, 21, 20, 16, 510000, tzinfo=datetime.timezone.utc)
        assert message.edited_timestamp == datetime.datetime(
            2020, 4, 21, 21, 20, 16, 510000, tzinfo=datetime.timezone.utc
        )
        assert message.is_tts is True
        assert message.is_mentioning_everyone is True
        assert message.user_mentions == {5678}
        assert message.role_mentions == {987}
        assert message.channel_mentions == {456}
        # Attachment
        assert len(message.attachments) == 1
        attachment = message.attachments[0]
        assert attachment.id == 690922406474154014
        assert attachment.filename == "IMG.jpg"
        assert attachment.size == 660521
        assert attachment.url == "https://somewhere.com/attachments/123/456/IMG.jpg"
        assert attachment.proxy_url == "https://media.somewhere.com/attachments/123/456/IMG.jpg"
        assert attachment.width == 1844
        assert attachment.height == 2638
        assert isinstance(attachment, message_models.Attachment)

        expected_embed = entity_factory_impl.deserialize_embed(embed_payload)
        assert message.embeds == [expected_embed]
        # Reaction
        reaction = message.reactions[0]
        assert reaction.count == 100
        assert reaction.is_reacted_by_me is True
        expected_emoji = entity_factory_impl.deserialize_emoji(custom_emoji_payload)
        assert reaction.emoji == expected_emoji
        assert isinstance(reaction, message_models.Reaction)

        assert message.is_pinned is True
        assert message.webhook_id == 1234
        assert message.type == message_models.MessageType.DEFAULT

        # Activity
        assert message.activity.type == message_models.MessageActivityType.JOIN_REQUEST
        assert message.activity.party_id == "ae488379-351d-4a4f-ad32-2b9b01c91657"
        assert isinstance(message.activity, message_models.MessageActivity)

        assert message.application == entity_factory_impl.deserialize_application(partial_application_payload)
        # MessageCrosspost
        assert message.message_reference.app is mock_app
        assert message.message_reference.id == 306588351130107906
        assert message.message_reference.channel_id == 278325129692446722
        assert message.message_reference.guild_id == 278325129692446720

        assert message.flags == message_models.MessageFlag.IS_CROSSPOST
        assert message.nonce == "171000788183678976"

    def test_deserialize_message_with_null_and_unset_fields(
        self, entity_factory_impl, mock_app, user_payload,
    ):
        message_payload = {
            "id": "123",
            "channel_id": "456",
            "author": user_payload,
            "content": "some info",
            "timestamp": "2020-03-21T21:20:16.510000+00:00",
            "edited_timestamp": None,
            "tts": True,
            "mention_everyone": True,
            "mentions": [],
            "mention_roles": [],
            "attachments": [],
            "embeds": [],
            "pinned": True,
            "type": 0,
        }

        message = entity_factory_impl.deserialize_message(message_payload)
        assert message.app is mock_app
        assert message.guild_id is None
        assert message.member is None
        assert message.edited_timestamp is None
        assert message.channel_mentions == set()
        assert message.role_mentions == set()
        assert message.channel_mentions == set()
        assert message.attachments == []
        assert message.embeds == []
        assert message.reactions == []
        assert message.webhook_id is None
        assert message.activity is None
        assert message.application is None
        assert message.message_reference is None
        assert message.nonce is None

    ###################
    # PRESENCE MODELS #
    ###################

    @pytest.fixture()
    def presence_activity_payload(self, custom_emoji_payload):
        return {
            "name": "an activity",
            "type": 1,
            "url": "https://69.420.owouwunyaa",
            "created_at": 1584996792798,
            "timestamps": {"start": 1584996792798, "end": 1999999792798},
            "application_id": "40404040404040",
            "details": "They are doing stuff",
            "state": "STATED",
            "emoji": custom_emoji_payload,
            "party": {"id": "spotify:3234234234", "size": [2, 5]},
            "assets": {
                "large_image": "34234234234243",
                "large_text": "LARGE TEXT",
                "small_image": "3939393",
                "small_text": "small text",
            },
            "secrets": {"join": "who's a good secret?", "spectate": "I'm a good secret", "match": "No."},
            "instance": True,
            "flags": 3,
        }

    @pytest.fixture()
    def member_presence_payload(self, user_payload, presence_activity_payload):
        return {
            "user": user_payload,
            "roles": ["49494949"],
            "game": presence_activity_payload,
            "guild_id": "44004040",
            "status": "dnd",
            "activities": [presence_activity_payload],
            "client_status": {"desktop": "online", "mobile": "idle", "web": "dnd"},
            "premium_since": "2015-04-26T06:26:56.936000+00:00",
            "nick": "Nick",
        }

    def test_deserialize_member_presence(
        self, entity_factory_impl, mock_app, member_presence_payload, custom_emoji_payload, user_payload
    ):
        presence = entity_factory_impl.deserialize_member_presence(member_presence_payload)
        assert presence.app is mock_app
        # PresenceUser
        assert presence.user.app is mock_app
        assert presence.user.id == 115590097100865541
        assert presence.user.discriminator == "6127"
        assert presence.user.username == "nyaa"
        assert presence.user.avatar_hash == "b3b24c6d7cbcdec129d5d537067061a8"
        assert presence.user.is_bot is True
        assert presence.user.is_system is True
        assert presence.user.flags == user_models.UserFlag(131072)

        assert isinstance(presence.user, user_models.PartialUser)
        assert presence.role_ids == {49494949}
        assert presence.guild_id == 44004040
        assert presence.visible_status == presence_models.Status.DND
        # PresenceActivity
        assert len(presence.activities) == 1
        activity = presence.activities[0]
        assert activity.name == "an activity"
        assert activity.type == presence_models.ActivityType.STREAMING
        assert activity.url == "https://69.420.owouwunyaa"
        assert activity.created_at == datetime.datetime(2020, 3, 23, 20, 53, 12, 798000, tzinfo=datetime.timezone.utc)
        # ActivityTimestamps
        assert activity.timestamps.start == datetime.datetime(
            2020, 3, 23, 20, 53, 12, 798000, tzinfo=datetime.timezone.utc
        )
        assert activity.timestamps.end == datetime.datetime(
            2033, 5, 18, 3, 29, 52, 798000, tzinfo=datetime.timezone.utc
        )

        assert activity.application_id == 40404040404040
        assert activity.details == "They are doing stuff"
        assert activity.state == "STATED"
        assert activity.emoji == entity_factory_impl.deserialize_emoji(custom_emoji_payload)
        # ActivityParty
        assert activity.party is not None
        assert activity.party.id == "spotify:3234234234"
        assert activity.party.current_size == 2
        assert activity.party.max_size == 5
        assert isinstance(activity.party, presence_models.ActivityParty)
        # ActivityAssets
        assert activity.assets is not None
        assert activity.assets.large_image == "34234234234243"
        assert activity.assets.large_text == "LARGE TEXT"
        assert activity.assets.small_image == "3939393"
        assert activity.assets.small_text == "small text"
        assert isinstance(activity.assets, presence_models.ActivityAssets)
        # ActivitySecrets
        assert activity.secrets is not None
        assert activity.secrets.join == "who's a good secret?"
        assert activity.secrets.spectate == "I'm a good secret"
        assert activity.secrets.match == "No."
        assert isinstance(activity.secrets, presence_models.ActivitySecret)
        assert activity.is_instance is True
        assert activity.flags == presence_models.ActivityFlag(3)
        assert isinstance(activity, presence_models.RichActivity)

        # ClientStatus
        assert presence.client_status.desktop == presence_models.Status.ONLINE
        assert presence.client_status.mobile == presence_models.Status.IDLE
        assert presence.client_status.web == presence_models.Status.DND
        assert isinstance(presence.client_status, presence_models.ClientStatus)

        assert presence.premium_since == datetime.datetime(2015, 4, 26, 6, 26, 56, 936000, tzinfo=datetime.timezone.utc)
        assert presence.nickname == "Nick"
        assert isinstance(presence, presence_models.MemberPresence)

    def test_deserialize_member_presence_with_null_fields(self, entity_factory_impl, user_payload):
        presence = entity_factory_impl.deserialize_member_presence(
            {
                "user": {"username": "agent 47", "avatar": None, "discriminator": "4747", "id": "474747474"},
                "roles": [],
                "game": None,
                "guild_id": "42",
                "status": "dnd",
                "activities": [],
                "client_status": {},
                "premium_since": None,
                "nick": None,
            }
        )
        assert presence.premium_since is None
        assert presence.nickname is None
        # PresenceUser
        assert presence.user.avatar_hash is None

    def test_deserialize_member_presence_with_unset_fields(
        self, entity_factory_impl, user_payload, presence_activity_payload
    ):
        presence = entity_factory_impl.deserialize_member_presence(
            {
                "user": {"id": "42"},
                "game": presence_activity_payload,
                "guild_id": "44004040",
                "status": "dnd",
                "activities": [],
                "client_status": {},
            }
        )
        assert presence.premium_since is None
        assert presence.nickname is None
        assert presence.role_ids is None
        # ClientStatus
        assert presence.client_status.desktop is presence_models.Status.OFFLINE
        assert presence.client_status.mobile is presence_models.Status.OFFLINE
        assert presence.client_status.web is presence_models.Status.OFFLINE
        # PresenceUser
        assert presence.user.id == 42
        assert presence.user.discriminator is undefined.UNDEFINED
        assert presence.user.username is undefined.UNDEFINED
        assert presence.user.avatar_hash is undefined.UNDEFINED
        assert presence.user.is_bot is undefined.UNDEFINED
        assert presence.user.is_system is undefined.UNDEFINED
        assert presence.user.flags is undefined.UNDEFINED

    def test_deserialize_member_presence_with_unset_activity_fields(self, entity_factory_impl, user_payload):
        presence = entity_factory_impl.deserialize_member_presence(
            {
                "user": user_payload,
                "roles": ["49494949"],
                "game": None,
                "guild_id": "44004040",
                "status": "dnd",
                "activities": [{"name": "an activity", "type": 1, "created_at": 1584996792798,}],
                "client_status": {},
            }
        )
        assert len(presence.activities) == 1
        activity = presence.activities[0]
        assert activity.url is None
        assert activity.timestamps is None
        assert activity.application_id is None
        assert activity.details is None
        assert activity.state is None
        assert activity.emoji is None
        assert activity.party is None
        assert activity.assets is None
        assert activity.secrets is None
        assert activity.is_instance is None
        assert activity.flags is None

    def test_deserialize_member_presence_with_null_activity_fields(self, entity_factory_impl, user_payload):
        presence = entity_factory_impl.deserialize_member_presence(
            {
                "user": user_payload,
                "roles": ["49494949"],
                "game": None,
                "guild_id": "44004040",
                "status": "dnd",
                "activities": [
                    {
                        "name": "an activity",
                        "type": 1,
                        "url": None,
                        "created_at": 1584996792798,
                        "timestamps": {"start": 1584996792798, "end": 1999999792798,},
                        "application_id": "40404040404040",
                        "details": None,
                        "state": None,
                        "emoji": None,
                        "party": {"id": "spotify:3234234234", "size": [2, 5]},
                        "assets": {
                            "large_image": "34234234234243",
                            "large_text": "LARGE TEXT",
                            "small_image": "3939393",
                            "small_text": "small text",
                        },
                        "secrets": {"join": "who's a good secret?", "spectate": "I'm a good secret", "match": "No."},
                        "instance": True,
                        "flags": 3,
                    }
                ],
                "client_status": {},
            }
        )
        assert len(presence.activities) == 1
        activity = presence.activities[0]
        assert activity.url is None
        assert activity.details is None
        assert activity.state is None
        assert activity.emoji is None

    def test_deserialize_member_presence_with_unset_activity_sub_fields(self, entity_factory_impl, user_payload):
        presence = entity_factory_impl.deserialize_member_presence(
            {
                "user": user_payload,
                "roles": ["49494949"],
                "game": None,
                "guild_id": "44004040",
                "status": "dnd",
                "activities": [
                    {
                        "name": "an activity",
                        "type": 1,
                        "url": "https://69.420.owouwunyaa",
                        "created_at": 1584996792798,
                        "timestamps": {},
                        "application_id": "40404040404040",
                        "details": "They are doing stuff",
                        "state": "STATED",
                        "emoji": None,
                        "party": {},
                        "assets": {},
                        "secrets": {},
                        "instance": True,
                        "flags": 3,
                    }
                ],
                "client_status": {},
            }
        )
        activity = presence.activities[0]
        # ActivityTimestamps
        assert activity.timestamps is not None
        assert activity.timestamps.start is None
        assert activity.timestamps.end is None
        # ActivityParty
        assert activity.party is not None
        assert activity.party.id is None
        assert activity.party.max_size is None
        assert activity.party.current_size is None
        # ActivityAssets
        assert activity.assets is not None
        assert activity.assets.small_text is None
        assert activity.assets.small_image is None
        assert activity.assets.large_text is None
        assert activity.assets.large_image is None
        # ActivitySecrets
        assert activity.secrets is not None
        assert activity.secrets.join is None
        assert activity.secrets.spectate is None
        assert activity.secrets.match is None

    ###############
    # USER MODELS #
    ###############

    @pytest.fixture()
    def user_payload(self):
        return {
            "id": "115590097100865541",
            "username": "nyaa",
            "avatar": "b3b24c6d7cbcdec129d5d537067061a8",
            "discriminator": "6127",
            "bot": True,
            "system": True,
            "public_flags": int(user_models.UserFlag.VERIFIED_BOT_DEVELOPER),
        }

    def test_deserialize_user(self, entity_factory_impl, mock_app, user_payload):
        user = entity_factory_impl.deserialize_user(user_payload)
        assert user.app is mock_app
        assert user.id == 115590097100865541
        assert user.username == "nyaa"
        assert user.avatar_hash == "b3b24c6d7cbcdec129d5d537067061a8"
        assert user.discriminator == "6127"
        assert user.is_bot is True
        assert user.is_system is True
        assert user.flags == user_models.UserFlag.VERIFIED_BOT_DEVELOPER
        assert isinstance(user, user_models.User)

    def test_deserialize_user_with_unset_fields(self, entity_factory_impl, mock_app, user_payload):
        user = entity_factory_impl.deserialize_user(
            {
                "id": "115590097100865541",
                "username": "nyaa",
                "avatar": "b3b24c6d7cbcdec129d5d537067061a8",
                "discriminator": "6127",
            }
        )
        assert user.is_bot is False
        assert user.is_system is False
        assert user.flags == user_models.UserFlag.NONE

    @pytest.fixture()
    def my_user_payload(self):
        return {
            "id": "379953393319542784",
            "username": "qt pi",
            "avatar": "820d0e50543216e812ad94e6ab7",
            "discriminator": "2880",
            "bot": True,
            "system": True,
            "email": "blahblah@blah.blah",
            "verified": True,
            "locale": "en-US",
            "mfa_enabled": True,
            "public_flags": int(user_models.UserFlag.VERIFIED_BOT_DEVELOPER),
            "flags": int(user_models.UserFlag.DISCORD_PARTNER | user_models.UserFlag.DISCORD_EMPLOYEE),
            "premium_type": 1,
        }

    def test_deserialize_my_user(self, entity_factory_impl, mock_app, my_user_payload):
        my_user = entity_factory_impl.deserialize_my_user(my_user_payload)
        assert my_user.app is mock_app
        assert my_user.id == 379953393319542784
        assert my_user.username == "qt pi"
        assert my_user.avatar_hash == "820d0e50543216e812ad94e6ab7"
        assert my_user.discriminator == "2880"
        assert my_user.is_bot is True
        assert my_user.is_system is True
        assert my_user.is_mfa_enabled is True
        assert my_user.locale == "en-US"
        assert my_user.is_verified is True
        assert my_user.email == "blahblah@blah.blah"
        assert my_user.flags == user_models.UserFlag.DISCORD_PARTNER | user_models.UserFlag.DISCORD_EMPLOYEE
        assert my_user.premium_type is user_models.PremiumType.NITRO_CLASSIC
        assert isinstance(my_user, user_models.OwnUser)

    def test_deserialize_my_user_with_unset_fields(self, entity_factory_impl, mock_app, my_user_payload):
        my_user = entity_factory_impl.deserialize_my_user(
            {
                "id": "379953393319542784",
                "username": "qt pi",
                "avatar": "820d0e50543216e812ad94e6ab7",
                "discriminator": "2880",
                "locale": "en-US",
                "mfa_enabled": True,
                "public_flags": int(user_models.UserFlag.VERIFIED_BOT_DEVELOPER),
                "flags": int(user_models.UserFlag.DISCORD_PARTNER | user_models.UserFlag.DISCORD_EMPLOYEE),
                "premium_type": 1,
            }
        )
        assert my_user.app is mock_app
        assert my_user.is_bot is False
        assert my_user.is_system is False
        assert my_user.is_verified is None
        assert my_user.email is None
        assert isinstance(my_user, user_models.OwnUser)

    ################
    # VOICE MODELS #
    ################

    @pytest.fixture()
    def voice_state_payload(self, member_payload):
        return {
            "guild_id": "929292929292992",
            "channel_id": "157733188964188161",
            "user_id": "80351110224678912",
            "member": member_payload,
            "session_id": "90326bd25d71d39b9ef95b299e3872ff",
            "deaf": True,
            "mute": True,
            "self_deaf": False,
            "self_mute": True,
            "self_stream": True,
            "self_video": True,
            "suppress": False,
        }

    def test_deserialize_voice_state(self, entity_factory_impl, mock_app, voice_state_payload, member_payload):
        voice_state = entity_factory_impl.deserialize_voice_state(voice_state_payload)
        assert voice_state.app is mock_app
        assert voice_state.guild_id == 929292929292992
        assert voice_state.channel_id == 157733188964188161
        assert voice_state.user_id == 80351110224678912
        assert voice_state.member == entity_factory_impl.deserialize_member(member_payload)
        assert voice_state.session_id == "90326bd25d71d39b9ef95b299e3872ff"
        assert voice_state.is_guild_deafened is True
        assert voice_state.is_guild_muted is True
        assert voice_state.is_self_deafened is False
        assert voice_state.is_self_muted is True
        assert voice_state.is_streaming is True
        assert voice_state.is_video_enabled is True
        assert voice_state.is_suppressed is False
        assert isinstance(voice_state, voice_models.VoiceState)

    def test_deserialize_voice_state_with_null_and_unset_fields(self, entity_factory_impl):
        voice_state = entity_factory_impl.deserialize_voice_state(
            {
                "channel_id": None,
                "user_id": "80351110224678912",
                "session_id": "90326bd25d71d39b9ef95b299e3872ff",
                "deaf": True,
                "mute": True,
                "self_deaf": False,
                "self_mute": True,
                "self_video": False,
                "suppress": False,
            }
        )
        assert voice_state.guild_id is None
        assert voice_state.channel_id is None
        assert voice_state.member is None
        assert voice_state.is_streaming is False

    @pytest.fixture()
    def voice_region_payload(self):
        return {"id": "london", "name": "LONDON", "vip": True, "optimal": False, "deprecated": True, "custom": False}

    def test_deserialize_voice_region(self, entity_factory_impl, voice_region_payload):
        voice_region = entity_factory_impl.deserialize_voice_region(voice_region_payload)
        assert voice_region.id == "london"
        assert voice_region.name == "LONDON"
        assert voice_region.is_vip is True
        assert voice_region.is_optimal_location is False
        assert voice_region.is_deprecated is True
        assert voice_region.is_custom is False
        assert isinstance(voice_region, voice_models.VoiceRegion)

    ##################
    # WEBHOOK MODELS #
    ##################

    @pytest.fixture()
    def webhook_payload(self, user_payload):
        return {
            "id": "1234",
            "type": 1,
            "guild_id": "123",
            "channel_id": "456",
            "user": user_payload,
            "name": "hikari webhook",
            "avatar": "bb71f469c158984e265093a81b3397fb",
            "token": "ueoqrialsdfaKJLKfajslkdf",
        }

    def test_deserialize_webhook(self, entity_factory_impl, mock_app, webhook_payload, user_payload):
        webhook = entity_factory_impl.deserialize_webhook(webhook_payload)
        assert webhook.id == 1234
        assert webhook.type == webhook_models.WebhookType.INCOMING
        assert webhook.guild_id == 123
        assert webhook.channel_id == 456
        assert webhook.author == entity_factory_impl.deserialize_user(user_payload)
        assert webhook.name == "hikari webhook"
        assert webhook.avatar_hash == "bb71f469c158984e265093a81b3397fb"
        assert webhook.token == "ueoqrialsdfaKJLKfajslkdf"
        assert isinstance(webhook, webhook_models.Webhook)

    def test_deserialize_webhook_with_null_and_unset_fields(self, entity_factory_impl):
        webhook = entity_factory_impl.deserialize_webhook(
            {"id": "1234", "type": 1, "channel_id": "456", "name": None, "avatar": None}
        )
        assert webhook.guild_id is None
        assert webhook.author is None
        assert webhook.name is None
        assert webhook.avatar_hash is None
        assert webhook.token is None

    ##################
    # CHANNEL EVENTS #
    ##################

    def test_deserialize_channel_create_event(
        self, entity_factory_impl, guild_text_channel_payload, guild_voice_channel_payload, dm_channel_payload
    ):
        channel_create_event = entity_factory_impl.deserialize_channel_create_event(guild_text_channel_payload)
        assert channel_create_event.channel == entity_factory_impl.deserialize_guild_text_channel(
            guild_text_channel_payload
        )
        assert isinstance(channel_create_event, channel_events.ChannelCreateEvent)

        assert entity_factory_impl.deserialize_channel_create_event(
            guild_voice_channel_payload
        ).channel == entity_factory_impl.deserialize_guild_voice_channel(guild_voice_channel_payload)
        assert entity_factory_impl.deserialize_channel_create_event(
            dm_channel_payload
        ).channel == entity_factory_impl.deserialize_dm_channel(dm_channel_payload)

    def test_deserialize_channel_update_event(
        self, entity_factory_impl, guild_text_channel_payload, guild_voice_channel_payload, dm_channel_payload
    ):
        channel_update_event = entity_factory_impl.deserialize_channel_update_event(guild_text_channel_payload)
        assert channel_update_event.channel == entity_factory_impl.deserialize_guild_text_channel(
            guild_text_channel_payload
        )
        assert isinstance(channel_update_event, channel_events.ChannelUpdateEvent)

        assert entity_factory_impl.deserialize_channel_update_event(
            guild_voice_channel_payload
        ).channel == entity_factory_impl.deserialize_guild_voice_channel(guild_voice_channel_payload)
        assert entity_factory_impl.deserialize_channel_update_event(
            dm_channel_payload
        ).channel == entity_factory_impl.deserialize_dm_channel(dm_channel_payload)

    def test_deserialize_channel_delete_event(
        self, entity_factory_impl, guild_text_channel_payload, guild_voice_channel_payload, dm_channel_payload
    ):
        channel_delete_event = entity_factory_impl.deserialize_channel_delete_event(guild_text_channel_payload)
        assert channel_delete_event.channel == entity_factory_impl.deserialize_guild_text_channel(
            guild_text_channel_payload
        )
        assert isinstance(channel_delete_event, channel_events.ChannelDeleteEvent)

        assert entity_factory_impl.deserialize_channel_delete_event(
            guild_voice_channel_payload
        ).channel == entity_factory_impl.deserialize_guild_voice_channel(guild_voice_channel_payload)
        assert entity_factory_impl.deserialize_channel_delete_event(
            dm_channel_payload
        ).channel == entity_factory_impl.deserialize_dm_channel(dm_channel_payload)

    @pytest.fixture()
    def channel_pins_update_payload(self):
        return {"channel_id": "123123", "guild_id": "9439494", "last_pin_timestamp": "2020-05-27T15:58:51.545252+00:00"}

    def test_deserialize_channel_pins_update_event(self, entity_factory_impl, mock_app, channel_pins_update_payload):
        channel_pins_update = entity_factory_impl.deserialize_channel_pins_update_event(channel_pins_update_payload)
        assert channel_pins_update.app is mock_app
        assert channel_pins_update.channel_id == 123123
        assert channel_pins_update.guild_id == 9439494
        assert channel_pins_update.last_pin_timestamp == datetime.datetime(
            2020, 5, 27, 15, 58, 51, 545252, tzinfo=datetime.timezone.utc
        )
        assert isinstance(channel_pins_update, channel_events.ChannelPinsUpdateEvent)

    def test_deserialize_channel_pins_update_event_with_unset_fields(self, entity_factory_impl, mock_app):
        channel_pins_update = entity_factory_impl.deserialize_channel_pins_update_event({"channel_id": "123123"})
        assert channel_pins_update.app is mock_app
        assert channel_pins_update.guild_id is None
        assert channel_pins_update.last_pin_timestamp is None

    @pytest.fixture()
    def webhook_update_payload(self):
        return {"guild_id": "123123123", "channel_id": "93493939"}

    def test_deserialize_webhook_update_event(self, entity_factory_impl, mock_app, webhook_update_payload):
        webhook_update = entity_factory_impl.deserialize_webhook_update_event(webhook_update_payload)
        assert webhook_update.app is mock_app
        assert webhook_update.guild_id == 123123123
        assert webhook_update.channel_id == 93493939
        assert isinstance(webhook_update, channel_events.WebhookUpdateEvent)

    @pytest.fixture()
    def typing_start_payload(self, member_payload):
        return {
            "channel_id": "123123",
            "guild_id": "4542242",
            "user_id": "29292929",
            "timestamp": 1591122971,
            "member": member_payload,
        }

    def test_deserialize_typing_start_event(self, entity_factory_impl, mock_app, typing_start_payload, member_payload):
        typing_start = entity_factory_impl.deserialize_typing_start_event(typing_start_payload)
        assert typing_start.app is mock_app
        assert typing_start.channel_id == 123123
        assert typing_start.guild_id == 4542242
        assert typing_start.user_id == 29292929
        assert typing_start.timestamp == datetime.datetime(2020, 6, 2, 18, 36, 11, tzinfo=datetime.timezone.utc)
        assert typing_start.member == entity_factory_impl.deserialize_member(member_payload)
        assert isinstance(typing_start, channel_events.TypingStartEvent)

    def test_deserialize_typing_start_event_with_unset_fields(self, entity_factory_impl):
        typing_start = entity_factory_impl.deserialize_typing_start_event(
            {"channel_id": "123123", "user_id": "4444", "timestamp": 1591122971}
        )
        assert typing_start.guild_id is None
        assert typing_start.member is None

    def test_deserialize_invite_create_event(self, entity_factory_impl, invite_with_metadata_payload):
        invite_create = entity_factory_impl.deserialize_invite_create_event(invite_with_metadata_payload)
        assert invite_create.invite == entity_factory_impl.deserialize_invite_with_metadata(
            invite_with_metadata_payload
        )
        assert isinstance(invite_create, channel_events.InviteCreateEvent)

    @pytest.fixture()
    def invite_delete_payload(self):
        return {"channel_id": "123123", "guild_id": "93939393", "code": "Heck"}

    def test_deserialize_invite_delete_event(self, entity_factory_impl, mock_app, invite_delete_payload):
        invite_delete = entity_factory_impl.deserialize_invite_delete_event(invite_delete_payload)
        assert invite_delete.app is mock_app
        assert invite_delete.code == "Heck"
        assert invite_delete.channel_id == 123123
        assert invite_delete.guild_id == 93939393
        assert isinstance(invite_delete, channel_events.InviteDeleteEvent)

    def test_deserialize_invite_delete_event_with_unset_fields(self, entity_factory_impl):
        assert entity_factory_impl.deserialize_invite_delete_event({"code": "OK", "channel_id": "123"}).guild_id is None

    ################
    # GUILD EVENTS #
    ################

    def test_deserialize_guild_create_event(self, entity_factory_impl, guild_payload):
        guild_create = entity_factory_impl.deserialize_guild_create_event(guild_payload)
        assert guild_create.guild == entity_factory_impl.deserialize_guild(guild_payload)
        assert isinstance(guild_create, guild_events.GuildCreateEvent)

    def test_deserialize_guild_update_event(self, entity_factory_impl, guild_payload):
        guild_update = entity_factory_impl.deserialize_guild_update_event(guild_payload)
        assert guild_update.guild == entity_factory_impl.deserialize_guild(guild_payload)
        assert isinstance(guild_update, guild_events.GuildUpdateEvent)

    @pytest.fixture()
    def guild_leave_payload(self):
        return {"id": "44332211"}

    def test_deserialize_guild_leave_event(self, entity_factory_impl, guild_leave_payload):
        guild_leave = entity_factory_impl.deserialize_guild_leave_event(guild_leave_payload)
        assert guild_leave.id == 44332211
        assert isinstance(guild_leave, guild_events.GuildLeaveEvent)

    @pytest.fixture()
    def guild_unavailable_payload(self):
        return {"id": "4123123", "unavailable": True}

    def test_deserialize_guild_unavailable_event(self, entity_factory_impl, mock_app, guild_unavailable_payload):
        guild_unavailable = entity_factory_impl.deserialize_guild_unavailable_event(guild_unavailable_payload)
        assert guild_unavailable.app is mock_app
        assert guild_unavailable.id == 4123123
        assert isinstance(guild_unavailable, guild_events.GuildUnavailableEvent)

    @pytest.fixture()
    def guild_ban_payload(self, user_payload):
        return {"user": user_payload, "guild_id": "2002020202022"}

    def test_deserialize_guild_ban_add_event(self, entity_factory_impl, mock_app, guild_ban_payload, user_payload):
        guild_ban_add = entity_factory_impl.deserialize_guild_ban_add_event(guild_ban_payload)
        assert guild_ban_add.app is mock_app
        assert guild_ban_add.guild_id == 2002020202022
        assert guild_ban_add.user == entity_factory_impl.deserialize_user(user_payload)
        assert isinstance(guild_ban_add, guild_events.GuildBanAddEvent)

    def test_deserialize_guild_ban_remove_event(self, entity_factory_impl, mock_app, guild_ban_payload, user_payload):
        guild_ban_add = entity_factory_impl.deserialize_guild_ban_remove_event(guild_ban_payload)
        assert guild_ban_add.app is mock_app
        assert guild_ban_add.guild_id == 2002020202022
        assert guild_ban_add.user == entity_factory_impl.deserialize_user(user_payload)
        assert isinstance(guild_ban_add, guild_events.GuildBanRemoveEvent)

    @pytest.fixture()
    def guild_emojis_update_payload(self, known_custom_emoji_payload):
        return {"emojis": [known_custom_emoji_payload], "guild_id": "424242"}

    def test_deserialize_guild_emojis_update_event(
        self, entity_factory_impl, mock_app, guild_emojis_update_payload, known_custom_emoji_payload
    ):
        guild_emoji_update = entity_factory_impl.deserialize_guild_emojis_update_event(guild_emojis_update_payload)
        assert guild_emoji_update.app is mock_app
        assert guild_emoji_update.guild_id == 424242
        assert guild_emoji_update.emojis == {
            12345: entity_factory_impl.deserialize_known_custom_emoji(known_custom_emoji_payload)
        }
        assert isinstance(guild_emoji_update, guild_events.GuildEmojisUpdateEvent)

    @pytest.fixture()
    def guild_integrations_update_payload(self):
        return {"guild_id": "439399393"}

    def test_deserialize_guild_integrations_update_event(
        self, entity_factory_impl, mock_app, guild_integrations_update_payload
    ):
        guild_integrations_update = entity_factory_impl.deserialize_guild_integrations_update_event(
            guild_integrations_update_payload
        )
        assert guild_integrations_update.app is mock_app
        assert guild_integrations_update.guild_id == 439399393
        assert isinstance(guild_integrations_update, guild_events.GuildIntegrationsUpdateEvent)

    @pytest.fixture()
    def guild_member_add_payload(self, member_payload):
        return {**member_payload, "guild_id": "20202020202020"}

    def test_deserialize_guild_member_add_event(
        self, entity_factory_impl, mock_app, guild_member_add_payload, member_payload
    ):
        guild_member_add = entity_factory_impl.deserialize_guild_member_add_event(guild_member_add_payload)
        assert guild_member_add.app is mock_app
        assert guild_member_add.guild_id == 20202020202020
        assert guild_member_add.member == entity_factory_impl.deserialize_member(member_payload)
        assert isinstance(guild_member_add, guild_events.GuildMemberAddEvent)

    def test_deserialize_guild_member_update_event(self, entity_factory_impl, member_payload):
        member_update_event = entity_factory_impl.deserialize_guild_member_update_event(member_payload)
        assert member_update_event.member == entity_factory_impl.deserialize_member(member_payload)
        assert isinstance(member_update_event, guild_events.GuildMemberUpdateEvent)

    @pytest.fixture()
    def guild_member_remove_payload(self, user_payload):
        return {"guild_id": "20202020", "user": user_payload}

    def test_deserialize_guild_member_remove_event(
        self, entity_factory_impl, mock_app, guild_member_remove_payload, user_payload
    ):
        guild_member_remove = entity_factory_impl.deserialize_guild_member_remove_event(guild_member_remove_payload)
        assert guild_member_remove.app is mock_app
        assert guild_member_remove.guild_id == 20202020
        assert guild_member_remove.user == entity_factory_impl.deserialize_user(user_payload)
        assert isinstance(guild_member_remove, guild_events.GuildMemberRemoveEvent)

    @pytest.fixture()
    def guild_role_create_update_payload(self, guild_role_payload):
        return {"guild_id": "303030300303", "role": guild_role_payload}

    def test_deserialize_guild_role_create_event(
        self, entity_factory_impl, mock_app, guild_role_create_update_payload, guild_role_payload
    ):
        guild_role_create = entity_factory_impl.deserialize_guild_role_create_event(guild_role_create_update_payload)
        assert guild_role_create.app is mock_app
        assert guild_role_create.guild_id == 303030300303
        assert guild_role_create.role == entity_factory_impl.deserialize_role(guild_role_payload)
        assert isinstance(guild_role_create, guild_events.GuildRoleCreateEvent)

    def test_deserialize_guild_role_update_event(
        self, entity_factory_impl, mock_app, guild_role_create_update_payload, guild_role_payload
    ):
        guild_role_create = entity_factory_impl.deserialize_guild_role_update_event(guild_role_create_update_payload)
        assert guild_role_create.app is mock_app
        assert guild_role_create.guild_id == 303030300303
        assert guild_role_create.role == entity_factory_impl.deserialize_role(guild_role_payload)
        assert isinstance(guild_role_create, guild_events.GuildRoleUpdateEvent)

    @pytest.fixture()
    def guild_role_delete_payload(self):
        return {"guild_id": "93939393939", "role_id": "8383483848484848"}

    def test_deserialize_guild_role_delete_event(self, entity_factory_impl, mock_app, guild_role_delete_payload):
        guild_role_delete = entity_factory_impl.deserialize_guild_role_delete_event(guild_role_delete_payload)
        assert guild_role_delete.app is mock_app
        assert guild_role_delete.guild_id == 93939393939
        assert guild_role_delete.role_id == 8383483848484848
        assert isinstance(guild_role_delete, guild_events.GuildRoleDeleteEvent)

    def test_deserialize_presence_update_event(self, entity_factory_impl, member_presence_payload):
        presence_update = entity_factory_impl.deserialize_presence_update_event(member_presence_payload)
        assert presence_update.presence == entity_factory_impl.deserialize_member_presence(member_presence_payload)
        assert isinstance(presence_update, guild_events.PresenceUpdateEvent)

    ##################
    # MESSAGE EVENTS #
    ##################

    def test_deserialize_message_create_event(self, entity_factory_impl, message_payload):
        message_create = entity_factory_impl.deserialize_message_create_event(message_payload)
        assert message_create.message == entity_factory_impl.deserialize_message(message_payload)
        assert isinstance(message_create, message_events.MessageCreateEvent)

    def test_deserialize_message_update_event_with_full_payload(
        self,
        entity_factory_impl,
        mock_app,
        message_payload,
        user_payload,
        member_payload,
        partial_application_payload,
        custom_emoji_payload,
        embed_payload,
    ):
        message_update = entity_factory_impl.deserialize_message_update_event(message_payload)

        assert message_update.message.app is mock_app
        assert message_update.message.id == 123
        assert message_update.message.channel_id == 456
        assert message_update.message.guild_id == 678
        assert message_update.message.author == entity_factory_impl.deserialize_user(user_payload)
        assert message_update.message.member == entity_factory_impl.deserialize_member(
            member_payload, user=message_update.message.author
        )
        assert message_update.message.content == "some info"
        assert message_update.message.timestamp == datetime.datetime(
            2020, 3, 21, 21, 20, 16, 510000, tzinfo=datetime.timezone.utc
        )
        assert message_update.message.edited_timestamp == datetime.datetime(
            2020, 4, 21, 21, 20, 16, 510000, tzinfo=datetime.timezone.utc
        )
        assert message_update.message.is_tts is True
        assert message_update.message.is_mentioning_everyone is True
        assert message_update.message.user_mentions == {5678}
        assert message_update.message.role_mentions == {987}
        assert message_update.message.channel_mentions == {456}
        # Attachment
        assert len(message_update.message.attachments) == 1
        attachment = message_update.message.attachments[0]
        assert attachment.id == 690922406474154014
        assert attachment.filename == "IMG.jpg"
        assert attachment.size == 660521
        assert attachment.url == "https://somewhere.com/attachments/123/456/IMG.jpg"
        assert attachment.proxy_url == "https://media.somewhere.com/attachments/123/456/IMG.jpg"
        assert attachment.width == 1844
        assert attachment.height == 2638
        assert isinstance(attachment, message_models.Attachment)

        assert message_update.message.embeds == [entity_factory_impl.deserialize_embed(embed_payload)]
        # Reaction
        reaction = message_update.message.reactions[0]
        assert reaction.count == 100
        assert reaction.is_reacted_by_me is True
        assert reaction.emoji == entity_factory_impl.deserialize_emoji(custom_emoji_payload)
        assert isinstance(reaction, message_models.Reaction)

        assert message_update.message.is_pinned is True
        assert message_update.message.webhook_id == 1234
        assert message_update.message.type == message_models.MessageType.DEFAULT
        # Activity
        assert message_update.message.activity.type == message_models.MessageActivityType.JOIN_REQUEST
        assert message_update.message.activity.party_id == "ae488379-351d-4a4f-ad32-2b9b01c91657"
        assert isinstance(message_update.message.activity, message_models.MessageActivity)

        assert message_update.message.application == entity_factory_impl.deserialize_application(
            partial_application_payload
        )
        # MessageCrosspost
        assert message_update.message.message_reference.app is mock_app
        assert message_update.message.message_reference.id == 306588351130107906
        assert message_update.message.message_reference.channel_id == 278325129692446722
        assert message_update.message.message_reference.guild_id == 278325129692446720

        assert message_update.message.flags == message_models.MessageFlag.IS_CROSSPOST
        assert message_update.message.nonce == "171000788183678976"
        assert isinstance(message_update.message, message_events.UpdatedMessageFields)
        assert isinstance(message_update, message_events.MessageUpdateEvent)

    def test_deserialize_message_update_event_with_partial_payload(self, entity_factory_impl):
        message_update = entity_factory_impl.deserialize_message_update_event({"id": "42424242", "channel_id": "99420"})

        assert message_update.message.id == 42424242
        assert message_update.message.channel_id == 99420
        assert message_update.message.guild_id is undefined.UNDEFINED
        assert message_update.message.author is undefined.UNDEFINED
        assert message_update.message.member is undefined.UNDEFINED
        assert message_update.message.content is undefined.UNDEFINED
        assert message_update.message.timestamp is undefined.UNDEFINED
        assert message_update.message.edited_timestamp is undefined.UNDEFINED
        assert message_update.message.is_tts is undefined.UNDEFINED
        assert message_update.message.is_mentioning_everyone is undefined.UNDEFINED
        assert message_update.message.user_mentions is undefined.UNDEFINED
        assert message_update.message.role_mentions is undefined.UNDEFINED
        assert message_update.message.channel_mentions is undefined.UNDEFINED
        assert message_update.message.attachments is undefined.UNDEFINED
        assert message_update.message.embeds is undefined.UNDEFINED
        assert message_update.message.reactions is undefined.UNDEFINED
        assert message_update.message.is_pinned is undefined.UNDEFINED
        assert message_update.message.webhook_id is undefined.UNDEFINED
        assert message_update.message.type is undefined.UNDEFINED
        assert message_update.message.activity is undefined.UNDEFINED
        assert message_update.message.application is undefined.UNDEFINED
        assert message_update.message.message_reference is undefined.UNDEFINED
        assert message_update.message.flags is undefined.UNDEFINED
        assert message_update.message.nonce is undefined.UNDEFINED

    def test_deserialize_message_update_event_with_null_fields(self, entity_factory_impl):
        message_update = entity_factory_impl.deserialize_message_update_event(
            {"id": "42424242", "edited_timestamp": None, "channel_id": "69420"}
        )
        assert message_update.message.edited_timestamp is None

    @pytest.fixture()
    def message_delete_payload(self):
        return {"id": "123123", "channel_id": "9292929", "guild_id": "202020202"}

    def test_deserialize_message_delete_event(self, entity_factory_impl, mock_app, message_delete_payload):
        message_delete = entity_factory_impl.deserialize_message_delete_event(message_delete_payload)
        assert message_delete.app is mock_app
        assert message_delete.message_id == 123123
        assert message_delete.channel_id == 9292929
        assert message_delete.guild_id == 202020202
        assert isinstance(message_delete, message_events.MessageDeleteEvent)

    @pytest.fixture()
    def message_delete_bulk_payload(self):
        return {"ids": ["123123", "9349299"], "channel_id": "92392929", "guild_id": "92929292"}

    def test_deserialize_message_delete_bulk_event(self, entity_factory_impl, mock_app, message_delete_bulk_payload):
        message_delete_bulk = entity_factory_impl.deserialize_message_delete_bulk_event(message_delete_bulk_payload)
        assert message_delete_bulk.app is mock_app
        assert message_delete_bulk.message_ids == {123123, 9349299}
        assert message_delete_bulk.channel_id == 92392929
        assert message_delete_bulk.guild_id == 92929292
        assert isinstance(message_delete_bulk, message_events.MessageDeleteBulkEvent)

    @pytest.fixture()
    def message_reaction_add_payload(self, member_payload, custom_emoji_payload):
        return {
            "user_id": "202020",
            "channel_id": "23848774",
            "message_id": "484848",
            "guild_id": "12123",
            "member": member_payload,
            "emoji": custom_emoji_payload,
        }

    def test_deserialize_message_reaction_add_event(
        self, entity_factory_impl, mock_app, message_reaction_add_payload, member_payload, custom_emoji_payload
    ):
        message_reaction_add = entity_factory_impl.deserialize_message_reaction_add_event(message_reaction_add_payload)
        assert message_reaction_add.app is mock_app
        assert message_reaction_add.user_id == 202020
        assert message_reaction_add.channel_id == 23848774
        assert message_reaction_add.message_id == 484848
        assert message_reaction_add.guild_id == 12123
        assert message_reaction_add.member == entity_factory_impl.deserialize_member(member_payload)
        assert message_reaction_add.emoji == entity_factory_impl.deserialize_emoji(custom_emoji_payload)
        assert isinstance(message_reaction_add, message_events.MessageReactionAddEvent)

    def test_deserialize_message_reaction_add_event_with_unset_fields(
        self, entity_factory_impl, message_reaction_add_payload, custom_emoji_payload
    ):
        message_reaction_add = entity_factory_impl.deserialize_message_reaction_add_event(
            {"user_id": "202020", "channel_id": "23848774", "message_id": "484848", "emoji": custom_emoji_payload}
        )
        assert message_reaction_add.guild_id is None
        assert message_reaction_add.member is None

    @pytest.fixture()
    def reaction_remove_payload(self, custom_emoji_payload):
        return {
            "user_id": "945939389393939393",
            "channel_id": "92903893923",
            "message_id": "222222222",
            "guild_id": "123123",
            "emoji": custom_emoji_payload,
        }

    def test_deserialize_message_reaction_remove_event(
        self, entity_factory_impl, mock_app, reaction_remove_payload, custom_emoji_payload
    ):
        reaction_remove = entity_factory_impl.deserialize_message_reaction_remove_event(reaction_remove_payload)
        assert reaction_remove.app is mock_app
        assert reaction_remove.user_id == 945939389393939393
        assert reaction_remove.channel_id == 92903893923
        assert reaction_remove.message_id == 222222222
        assert reaction_remove.guild_id == 123123
        assert reaction_remove.emoji == entity_factory_impl.deserialize_emoji(custom_emoji_payload)
        assert isinstance(reaction_remove, message_events.MessageReactionRemoveEvent)

    def test_deserialize_message_reaction_remove_event_with_unset_fields(
        self, entity_factory_impl, custom_emoji_payload
    ):
        reaction_remove = entity_factory_impl.deserialize_message_reaction_remove_event(
            {
                "user_id": "945939389393939393",
                "channel_id": "92903893923",
                "message_id": "222222222",
                "emoji": custom_emoji_payload,
            }
        )
        assert reaction_remove.guild_id is None

    @pytest.fixture()
    def message_reaction_remove_all_payload(self, custom_emoji_payload):
        return {"channel_id": "222293844884", "message_id": "93493939", "guild_id": "939393939390"}

    def test_deserialize_message_reaction_remove_all_event(
        self, entity_factory_impl, mock_app, message_reaction_remove_all_payload
    ):
        message_reaction_remove_all = entity_factory_impl.deserialize_message_reaction_remove_all_event(
            message_reaction_remove_all_payload
        )
        assert message_reaction_remove_all.app is mock_app
        assert message_reaction_remove_all.channel_id == 222293844884
        assert message_reaction_remove_all.message_id == 93493939
        assert message_reaction_remove_all.guild_id == 939393939390
        assert isinstance(message_reaction_remove_all, message_events.MessageReactionRemoveAllEvent)

    def test_deserialize_message_reaction_remove_all_event_with_unset_fields(self, entity_factory_impl, mock_app):
        message_reaction_remove_all = entity_factory_impl.deserialize_message_reaction_remove_all_event(
            {"channel_id": "222293844884", "message_id": "93493939"}
        )
        assert message_reaction_remove_all.guild_id is None

    @pytest.fixture()
    def message_reaction_remove_emoji_payload(self, custom_emoji_payload):
        return {
            "channel_id": "123123",
            "guild_id": "495485494945",
            "message_id": "93999328484",
            "emoji": custom_emoji_payload,
        }

    def test_deserialize_message_reaction_remove_emoji_event(
        self, entity_factory_impl, mock_app, message_reaction_remove_emoji_payload, custom_emoji_payload
    ):
        message_reaction_remove_emoji = entity_factory_impl.deserialize_message_reaction_remove_emoji_event(
            message_reaction_remove_emoji_payload
        )
        assert message_reaction_remove_emoji.app is mock_app
        assert message_reaction_remove_emoji.channel_id == 123123
        assert message_reaction_remove_emoji.guild_id == 495485494945
        assert message_reaction_remove_emoji.message_id == 93999328484
        assert isinstance(message_reaction_remove_emoji, message_events.MessageReactionRemoveEmojiEvent)

    def test_deserialize_message_reaction_remove_emoji_event_with_unset_fields(
        self, entity_factory_impl, mock_app, custom_emoji_payload
    ):
        message_reaction_remove_emoji = entity_factory_impl.deserialize_message_reaction_remove_emoji_event(
            {"channel_id": "123123", "message_id": "93999328484", "emoji": custom_emoji_payload}
        )
        assert message_reaction_remove_emoji.guild_id is None

    ################
    # OTHER EVENTS #
    ################

    @pytest.fixture()
    def ready_payload(self, my_user_payload, guild_unavailable_payload):
        return {
            "v": 6,
            "user": my_user_payload,
            "private_channels": [],
            "guilds": [guild_unavailable_payload],
            "session_id": "mlksdfoijpsdfioprewi09u43rw",
            "shard": [0, 1],
        }

    def test_deserialize_ready_event(
        self, entity_factory_impl, ready_payload, my_user_payload, guild_unavailable_payload
    ):
        shard = mock.MagicMock()
        ready_event = entity_factory_impl.deserialize_ready_event(shard, ready_payload)
        assert ready_event.shard is shard
        assert ready_event.gateway_version == 6
        assert ready_event.my_user == entity_factory_impl.deserialize_my_user(my_user_payload)
        assert ready_event.unavailable_guilds == {
            4123123: entity_factory_impl.deserialize_unavailable_guild(guild_unavailable_payload)
        }
        assert ready_event.session_id == "mlksdfoijpsdfioprewi09u43rw"
        assert ready_event.shard_id == 0
        assert ready_event.shard_count == 1
        assert isinstance(ready_event, other_events.ReadyEvent)

    def test_deserialize_ready_event_with_unset_fields(
        self, entity_factory_impl, ready_payload, my_user_payload, guild_unavailable_payload
    ):
        shard = mock.MagicMock()
        ready_event = entity_factory_impl.deserialize_ready_event(
            shard,
            {
                "v": 6,
                "user": my_user_payload,
                "private_channels": [],
                "guilds": [],
                "session_id": "mlksdfoijpsdfioprewi09u43rw",
            },
        )
        assert ready_event.shard is shard
        assert ready_event.shard_id is None
        assert ready_event.shard_count is None

    def test_deserialize_own_user_update_event(self, entity_factory_impl, my_user_payload):
        my_user_update = entity_factory_impl.deserialize_own_user_update_event(my_user_payload)
        assert my_user_update.my_user == entity_factory_impl.deserialize_my_user(my_user_payload)
        assert isinstance(my_user_update, other_events.OwnUserUpdateEvent)

    ################
    # VOICE EVENTS #
    ################

    def test_deserialize_voice_state_update_event(self, entity_factory_impl, voice_state_payload):
        voice_state_update = entity_factory_impl.deserialize_voice_state_update_event(voice_state_payload)
        assert voice_state_update.state == entity_factory_impl.deserialize_voice_state(voice_state_payload)
        assert isinstance(voice_state_update, voice_events.VoiceStateUpdateEvent)

    @pytest.fixture()
    def voice_server_update_payload(self):
        return {"token": "9292929iiasdiasdio", "guild_id": "29219929", "endpoint": "wss:>...<"}

    def test_deserialize_voice_server_update_event(self, entity_factory_impl, mock_app, voice_server_update_payload):
        voice_server_update = entity_factory_impl.deserialize_voice_server_update_event(voice_server_update_payload)
        assert voice_server_update.token == "9292929iiasdiasdio"
        assert voice_server_update.guild_id == 29219929
        assert voice_server_update.endpoint == "wss:>...<"