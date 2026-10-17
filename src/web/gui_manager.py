"""Main web GUI manager coordinating all UI components."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from src.models.game import Game
from src.services.stream_selector import StreamSelector
from src.web.managers.broadcaster import WebSocketBroadcaster
from src.web.managers.cache import ImageCache
from src.web.managers.campaigns import CampaignProgressManager
from src.web.managers.channels import ChannelListManager
from src.web.managers.console import ConsoleOutputManager
from src.web.managers.inventory import InventoryManager
from src.web.managers.login import LoginFormManager
from src.web.managers.settings import SettingsManager
from src.web.managers.status import StatusManager, WebsocketStatusManager


if TYPE_CHECKING:
    from socketio import AsyncServer

    from src.core.client import Twitch
    from src.models import TimedDrop


logger = logging.getLogger("TwitchDrops")


class WebGUIManager:
    """Web-based GUI manager coordinating all UI components.

    This class serves as the main coordinator for the web-based interface,
    managing all component managers and providing the same interface as the
    desktop GUIManager for compatibility with the core application logic.

    The WebGUIManager uses Socket.IO for real-time bidirectional communication
    with browser clients, enabling live updates of drop progress, channel lists,
    and other dynamic content.
    """

    def __init__(self, twitch: Twitch):
        self._twitch: Twitch = twitch
        self._broadcaster = WebSocketBroadcaster()

        # Create component managers
        self.status = StatusManager(self._broadcaster)
        self.websockets = WebsocketStatusManager(self._broadcaster)
        self.output = ConsoleOutputManager(self._broadcaster)
        self.progress = CampaignProgressManager(self._broadcaster)
        self.channels = ChannelListManager(self._broadcaster, self)
        self.inv = InventoryManager(self._broadcaster, ImageCache(self))
        self.login = LoginFormManager(self._broadcaster, self)
        self.inv = InventoryManager(self._broadcaster, ImageCache(self))
        self.login = LoginFormManager(self._broadcaster, self)

        # Callback to trigger game update when relevant settings change
        def on_settings_change() -> None:
            self._twitch.request_games_update()

        self.settings = SettingsManager(
            self._broadcaster, twitch.settings, self.output, on_change=on_settings_change
        )

        # Selected channel tracking (set by web client)
        self._selected_channel_id: int | None = None
        self._stream_selector = StreamSelector()

        # Start message
        logger.info("Web GUI Manager initialized")

    def set_socketio(self, sio: AsyncServer):
        """Set the Socket.IO instance for real-time communication.

        Called by webapp during initialization to connect the broadcaster
        to the Socket.IO server.

        Args:
            sio: The Socket.IO AsyncServer instance
        """
        self._broadcaster.set_socketio(sio)

    def print(self, message: str, *, collapse_key: str | None = None) -> None:
        """Print message to console output.

        Args:
            message: Message to display in console
            collapse_key: Suppress a consecutive identical keyed message
        """
        self.output.print(message, collapse_key=collapse_key)

    def set_games(self, games: set[Game]):
        """Set available games for settings panel.

        Args:
            games: Set of Game objects from discovered campaigns
        """
        self.settings.set_games(games)

    def display_drop(self, drop: TimedDrop, *, countdown: bool = True, subone: bool = False):
        """Display drop mining progress with countdown.

        Args:
            drop: The drop currently being mined
            countdown: Whether to show countdown timer
            subone: Subtract one minute from remaining time
        """
        remaining = drop.remaining_minutes * 60  # Convert to seconds
        if subone:
            remaining -= 60
        self.progress.update(drop, remaining)

    def clear_drop(self):
        """Clear the drop progress display."""
        self.progress.stop_timer()

    def refresh_mining_panel(self, drop: TimedDrop) -> None:
        """Re-emit the "Active Mining" payload when a drop's state changes.

        Only for the drop the panel currently shows - other drops are plain
        inventory updates. This is what keeps the panel in sync during a
        websocket-driven mining session, where display() is no longer called
        for every minute.
        """
        current = self.progress.get_current_drop()
        if current is None or current["drop_id"] != drop.id:
            return
        self.progress.update(drop, drop.remaining_minutes * 60)

    def mining_status(self) -> dict:
        """Honest state behind the "Active Mining" panel.

        "mining" = a channel is being watched, "waiting" = campaigns are active
        but nothing can be mined, "idle" = no campaigns at all.
        """
        twitch = self._twitch
        watching = twitch.watching_channel.get_with_default(None)
        campaigns = len(twitch.inventory)
        live_channels = sum(1 for ch in twitch.channels.values() if ch.online)
        if watching is not None:
            state = "mining"
        elif campaigns:
            state = "waiting"
        else:
            state = "idle"
        return {
            "state": state,
            "watching_channel": watching.name if watching is not None else None,
            "campaigns": campaigns,
            "live_channels": live_channels,
        }

    def set_mining_state(self) -> None:
        """Broadcast the mining status so the dashboard never lies about why nothing is mined."""
        asyncio.create_task(self._broadcaster.emit("miner_status", self.mining_status()))

    def grab_attention(self, *, sound: bool = True):
        """Get user's attention via notification.

        Args:
            sound: Whether to play notification sound
        """
        asyncio.create_task(self._broadcaster.emit("attention_required", {"sound": sound}))

    def select_channel(self, channel_id: int):
        """Select a channel (called by webapp when user clicks channel).

        Args:
            channel_id: Twitch channel ID to select
        """
        self._selected_channel_id = channel_id

    def get_selected_channel_id(self) -> int | None:
        """Get the currently selected channel ID and clear the selection.

        Returns:
            Channel ID if one was selected, None otherwise
        """
        result = self._selected_channel_id
        self._selected_channel_id = None  # Clear after reading
        return result

    def clear_channel_selection(self) -> None:
        """Discard a pending channel selection."""
        self._selected_channel_id = None

    def apply_theme(self, dark_mode: bool):
        """Apply UI theme (handled client-side in web mode).

        Args:
            dark_mode: Whether to use dark theme
        """
        asyncio.create_task(self._broadcaster.emit("theme_change", {"dark_mode": dark_mode}))

    def broadcast_manual_mode_change(self, manual_mode_info: dict):
        """Broadcast manual mode status change to connected clients.

        Args:
            manual_mode_info: Manual mode status from get_manual_mode_info()
        """
        asyncio.create_task(self._broadcaster.emit("manual_mode_update", manual_mode_info))

    def get_wanted_game_tree(self) -> list[dict]:
        return self._stream_selector.get_wanted_game_tree(
            self._twitch.settings, self._twitch.inventory
        )

    async def broadcast_wanted_items_now(self) -> None:
        """Broadcast wanted items and wait until the Socket.IO emit completes."""
        tree = self.get_wanted_game_tree()
        try:
            await self._broadcaster.emit("wanted_items_update", tree)
        except Exception:
            logger.exception("Failed to broadcast wanted items update")

    def broadcast_wanted_items(self) -> None:
        """Schedule a wanted-items broadcast using the stable synchronous API."""
        asyncio.create_task(self.broadcast_wanted_items_now())


# Type aliases for backwards compatibility with code that imports from gui
LoginForm = LoginFormManager
ChannelList = ChannelListManager
WebsocketStatus = WebsocketStatusManager
GUIManager = WebGUIManager
