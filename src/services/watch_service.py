"""
Watch service for managing channel watching and drop progress monitoring.

This service handles the core watching loop that sends watch payloads to Twitch,
monitors drop progress, and determines when to switch channels.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from time import time
from typing import TYPE_CHECKING, NoReturn

from src.config import CALL, GQL_OPERATIONS, WATCH_INTERVAL
from src.exceptions import GQLException
from src.i18n import _
from src.utils import task_wrapper


if TYPE_CHECKING:
    from src.config import JsonType
    from src.core.client import Twitch
    from src.models import TimedDrop
    from src.models.channel import Channel


logger = logging.getLogger("TwitchDrops")

# These messages used to be logged below INFO (the CALL level), which the logger
# discards by default - so a miner that "watches" a channel while Twitch ignores
# every watch signal looked perfectly healthy. They are now surfaced, but throttled
# so a persistent problem doesn't flood the console.
WATCH_FAILURES_BEFORE_REPORT = 3  # consecutive failures (~1 min) before the first warning
WATCH_FAILURE_REPEAT_EVERY = 15  # then repeat roughly every 5 minutes
ESTIMATE_WARNING_REPEAT_SECONDS = 600


class WatchService:
    """
    Service responsible for watching channels and monitoring drop progress.

    Handles:
    - Starting/stopping channel watching
    - Watch loop that sends periodic watch payloads
    - Drop progress monitoring via GQL and websocket
    - Channel switch eligibility checks
    - Watch loop sleep with restart capability
    """

    def __init__(self, twitch: Twitch) -> None:
        """
        Initialize the watch service.

        Args:
            twitch: The Twitch client instance
        """
        self._twitch = twitch
        self._watch_failures: int = 0
        self._watch_failure_channel_id: int | None = None
        self._last_estimate_warning: float = 0.0
        self._status_tick: int = 0

    def can_watch(self, channel: Channel) -> bool:
        """
        Determines if the given channel qualifies as a watching candidate.

        A channel can be watched if:
        - The channel is online
        - A campaign for a wanted game can be progressed on this channel
        - Drops are enabled, unless the campaign uses a special category

        Campaign eligibility enforces the game match, with a cross-category
        exception for participating channels in special-category campaigns.

        Args:
            channel: The channel to evaluate

        Returns:
            True if the channel can be watched, False otherwise
        """
        wanted_games = self._twitch.wanted_games
        if not wanted_games or not channel.online:
            return False

        return any(
            # Respect the user's selection using the campaign's category.
            campaign.game in wanted_games
            and campaign.can_earn(channel)
            # Special campaigns may progress without the channel's drops flag.
            and (campaign.game.is_special() or channel.drops_enabled)
            for campaign in self._twitch.inventory
        )

    def should_switch(self, channel: Channel) -> bool:
        """
        Determines if the given channel qualifies as a switch candidate.

        A channel should be switched to if:
        - We're not currently watching anything
        - The currently watched channel can no longer progress a wanted campaign
        - The channel's game has higher priority than the watching channel's game
        - The channel has the same game priority but is ACL-based and watching isn't

        Args:
            channel: The channel to evaluate as a switch candidate

        Returns:
            True if we should switch to this channel, False otherwise
        """
        watching_channel = self._twitch.watching_channel.get_with_default(None)
        if watching_channel is None or not self.can_watch(watching_channel):
            return True

        channel_order = self._twitch._channel_service.get_priority(channel)
        watching_order = self._twitch._channel_service.get_priority(watching_channel)

        return (
            # this channel's game is higher order than the watching one's
            channel_order < watching_order
            or channel_order == watching_order  # or the order is the same
            # and this channel is ACL-based and the watching channel isn't
            and channel.acl_based > watching_channel.acl_based
        )

    def watch(self, channel: Channel, *, update_status: bool = True) -> None:
        """
        Start watching a specific channel.

        Updates GUI elements and sets the watching channel. Optionally prints
        a status message and updates the status bar.

        Args:
            channel: The channel to start watching
            update_status: Whether to print status message and update status bar
        """
        self._twitch.gui.channels.set_watching(channel)
        self._twitch.watching_channel.set(channel)

        if update_status:
            # Check if manual mode is active for custom status message
            if self._twitch.is_manual_mode() and self._twitch._manual_target_game:
                status_text = f"🎯 Manual Mode: Watching {channel.name} for {self._twitch._manual_target_game.name}"
            else:
                status_text = _.t["status"]["watching"].format(channel=channel.name)
            self._twitch.print(status_text)
            self._twitch.gui.status.update(status_text)

    def stop_watching(self) -> None:
        """
        Stop watching the current channel.

        Clears the watching channel and updates GUI elements.
        """
        self._twitch.gui.clear_drop()
        self._twitch.watching_channel.clear()
        self._twitch.gui.channels.clear_watching()

    def restart_watching(self) -> None:
        """
        Restart the watch loop (forces immediate re-send of watch payload).

        Stops the progress timer and signals the watch loop to restart.
        """
        self._twitch.gui.progress.stop_timer()
        self._twitch._watching_restart.set()

    def _report_watch_result(self, channel: Channel, succeeded: bool) -> None:
        """Tell the user when Twitch stops accepting watch signals (and when it recovers)."""
        if succeeded:
            if self._watch_failures >= WATCH_FAILURES_BEFORE_REPORT:
                logger.info(f"Twitch is accepting watch signals for {channel.name} again.")
            self._watch_failures = 0
            return
        if self._watch_failure_channel_id != channel.id:
            self._watch_failure_channel_id = channel.id
            self._watch_failures = 0
        self._watch_failures += 1
        count = self._watch_failures
        if count == WATCH_FAILURES_BEFORE_REPORT or (
            count > WATCH_FAILURES_BEFORE_REPORT and count % WATCH_FAILURE_REPEAT_EVERY == 0
        ):
            reason = channel.last_watch_error or "unknown reason"
            logger.warning(
                f"Twitch is NOT accepting watch signals for {channel.name} "
                f"({reason}) - {count} failures in a row, so drop progress is not being earned."
            )

    def _warn_progress_not_confirmed(self, detail: str) -> None:
        """Warn (throttled) that the shown drop progress is not coming from Twitch."""
        now = time()
        if now - self._last_estimate_warning < ESTIMATE_WARNING_REPEAT_SECONDS:
            return
        self._last_estimate_warning = now
        logger.warning(f"Drop progress is not confirmed by Twitch: {detail}")

    async def watch_sleep(self, delay: float) -> None:
        """
        Sleep for a delay that can be interrupted by restart_watching().

        Uses wait_for with a timeout to allow an asyncio.sleep-like behavior
        that can be ended prematurely via the watching restart event.

        Args:
            delay: Time in seconds to sleep
        """
        self._twitch._watching_restart.clear()
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._twitch._watching_restart.wait(), timeout=delay)

    @task_wrapper(critical=True)
    async def watch_loop(self) -> NoReturn:
        """
        Main watch loop that sends watch payloads and monitors drop progress.

        This loop:
        1. Waits for a channel to watch
        2. Sends watch payload to the channel
        3. Waits ~20 seconds for websocket progress update
        4. If no update received, queries drop progress via GQL or estimates it
        5. Sleeps until next watch interval (~20 seconds)
        6. Repeats

        The loop handles cases where Twitch temporarily stops reporting progress
        by falling back to GQL queries or minute bumping.
        """
        interval: float = WATCH_INTERVAL.total_seconds()

        while True:
            channel: Channel = await self._twitch.watching_channel.get()

            if not channel.online:
                # if the channel isn't online anymore, we stop watching it
                self.stop_watching()
                continue

            # logger.log(CALL, f"Sending watch payload to: {channel.name}")
            # NOTE: timestamped BEFORE the request, because the playlist method can
            # take several seconds (one HEAD per chunk) and that time has to count
            # towards the watch interval - same as upstream.
            last_sent: float = time()
            succeeded: bool = await channel.send_watch()

            if not succeeded:
                logger.log(CALL, f"Watch requested failed for channel: {channel.name}")
            self._report_watch_result(channel, succeeded)

            # refresh the dashboard's mining status every ~5th cycle (~2 min), so the
            # "waiting for a live channel" text reflects the live channel count
            self._status_tick += 1
            if self._status_tick % 5 == 0:
                set_state = getattr(self._twitch.gui, "set_mining_state", None)
                if callable(set_state):
                    set_state()

            # wait ~15 seconds for a progress update
            await asyncio.sleep(15 - min(time() - last_sent, 15))

            if self._twitch.gui.progress.minute_almost_done():
                # If the previous update was more than ~60s ago, and the progress tracker
                # isn't counting down anymore, that means Twitch has temporarily
                # stopped reporting drop's progress. To ensure the timer keeps at least somewhat
                # accurate time, we can use GQL to query for the current drop,
                # or even "pretend" mining as a last resort option.
                handled: bool = False

                # Solution 1: use GQL to query for the currently mined drop status
                try:
                    context = await self._twitch.gql_request(
                        GQL_OPERATIONS["CurrentDrop"].with_variables({"channelID": str(channel.id)})
                    )
                    drop_data: JsonType | None = context["data"]["currentUser"][
                        "dropCurrentSession"
                    ]
                except GQLException:
                    drop_data = None

                if drop_data is not None:
                    gql_drop: TimedDrop | None = self._twitch._drops.get(drop_data["dropID"])
                    if gql_drop is not None and gql_drop.can_earn(channel):
                        gql_drop.update_minutes(drop_data["currentMinutesWatched"])
                        drop_text: str = (
                            f"{gql_drop.name} ({gql_drop.campaign.game}, "
                            f"{gql_drop.current_minutes}/{gql_drop.required_minutes})"
                        )
                        logger.log(CALL, f"Drop progress from GQL: {drop_text}")
                        handled = True

                # Solution 2: If GQL fails, figure out which campaign we're most likely mining
                # right now, and then bump up the minutes on it's drops
                if not handled:
                    active_campaign = self._twitch._inventory_service.get_active_campaign(channel)
                    if active_campaign is not None:
                        active_campaign.bump_minutes(channel)
                        # NOTE: This usually gets overwritten below
                        drop_text = f"Unknown drop ({active_campaign.game})"
                        if (active_drop := active_campaign.first_drop) is not None:
                            active_drop.display()
                            drop_text = (
                                f"{active_drop.name} ({active_drop.campaign.game}, "
                                f"{active_drop.current_minutes}/{active_drop.required_minutes})"
                            )
                        logger.log(CALL, f"Drop progress from active search: {drop_text}")
                        self._warn_progress_not_confirmed(
                            "Twitch reported no progress, so the minutes shown for "
                            f"{drop_text} are only estimated by this app. If they never "
                            "move on Twitch itself, check that your account is linked to "
                            "this game and that you are not watching on another device."
                        )
                        handled = True
                    else:
                        logger.log(CALL, "No active drop could be determined")
                        self._warn_progress_not_confirmed(
                            f"no drop could be matched to {channel.name} - Twitch may not "
                            "be crediting this channel (drops not enabled there, or the "
                            "campaign is not linked to your account)."
                        )

            await self.watch_sleep(interval - min(time() - last_sent, interval))
