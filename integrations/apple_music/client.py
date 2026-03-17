"""Apple Music integration via AppleScript — playback control, search, playlists."""

import subprocess


def _osascript(script: str, timeout: int = 10) -> tuple[str, str, int]:
    """Run an AppleScript and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout dépassé", 1
    except FileNotFoundError:
        return "", "osascript non disponible", 127


class AppleMusicClient:
    """Control Apple Music via AppleScript (macOS only)."""

    # ═══════════════════════════ PLAYBACK ═══════════════════════════

    def play(self) -> str:
        """Resume playback."""
        _, stderr, rc = _osascript('tell application "Music" to play')
        if rc != 0:
            return f"Erreur: {stderr}"
        return "▶️ Lecture reprise."

    def pause(self) -> str:
        """Pause playback."""
        _, stderr, rc = _osascript('tell application "Music" to pause')
        if rc != 0:
            return f"Erreur: {stderr}"
        return "⏸️ Musique en pause."

    def play_pause(self) -> str:
        """Toggle play/pause."""
        _, stderr, rc = _osascript('tell application "Music" to playpause')
        if rc != 0:
            return f"Erreur: {stderr}"
        return "⏯️ Play/Pause basculé."

    def next_track(self) -> str:
        """Skip to next track."""
        _, stderr, rc = _osascript('tell application "Music" to next track')
        if rc != 0:
            return f"Erreur: {stderr}"
        return "⏭️ Morceau suivant."

    def previous_track(self) -> str:
        """Go to previous track."""
        _, stderr, rc = _osascript('tell application "Music" to previous track')
        if rc != 0:
            return f"Erreur: {stderr}"
        return "⏮️ Morceau précédent."

    def set_volume(self, level: int) -> str:
        """Set volume (0-100)."""
        level = max(0, min(100, level))
        _, stderr, rc = _osascript(f'tell application "Music" to set sound volume to {level}')
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"🔊 Volume réglé à {level}%."

    def get_volume(self) -> str:
        """Get current volume level."""
        stdout, stderr, rc = _osascript('tell application "Music" to get sound volume')
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"🔊 Volume actuel: {stdout}%"

    # ═══════════════════════════ NOW PLAYING ═══════════════════════════

    def now_playing(self) -> str:
        """Get info about the currently playing track."""
        script = """
        tell application "Music"
            if player state is playing or player state is paused then
                set trackName to name of current track
                set trackArtist to artist of current track
                set trackAlbum to album of current track
                set trackDuration to duration of current track
                set trackPosition to player position
                set playerState to player state as string
                set trackDurationMin to (trackDuration div 60) as string
                set trackDurationSec to text -2 thru -1 of ("0" & (trackDuration mod 60 as integer) as string)
                set trackPositionMin to (trackPosition div 60) as string
                set trackPositionSec to text -2 thru -1 of ("0" & (trackPosition mod 60 as integer) as string)
                return trackName & "|||" & trackArtist & "|||" & trackAlbum & "|||" & playerState & "|||" & trackPositionMin & ":" & trackPositionSec & "/" & trackDurationMin & ":" & trackDurationSec
            else
                return "NOT_PLAYING"
            end if
        end tell
        """
        stdout, stderr, rc = _osascript(script)
        if rc != 0:
            return f"Erreur: {stderr}"
        if stdout == "NOT_PLAYING":
            return "🎵 Aucun morceau en cours de lecture."

        parts = stdout.split("|||")
        if len(parts) >= 6:
            name, artist, album, state, position = parts[0], parts[1], parts[2], parts[3], parts[4]
            state_emoji = "▶️" if state == "playing" else "⏸️"
            return (
                f"{state_emoji} **{name}**\n"
                f"   🎤 {artist}\n"
                f"   💿 {album}\n"
                f"   ⏱️ {position}"
            )
        return f"🎵 {stdout}"

    # ═══════════════════════════ SEARCH & PLAY ═══════════════════════════

    def search_and_play(self, query: str) -> str:
        """Search Apple Music library and play the first match."""
        # Escape quotes in query
        safe_query = query.replace('"', '\\"').replace("'", "'\\''")
        script = f"""
        tell application "Music"
            set searchResults to search playlist "Bibliothèque" for "{safe_query}"
            if searchResults is not {{}} then
                play item 1 of searchResults
                set trackName to name of item 1 of searchResults
                set trackArtist to artist of item 1 of searchResults
                return trackName & " — " & trackArtist
            else
                return "NOT_FOUND"
            end if
        end tell
        """
        stdout, stderr, rc = _osascript(script, timeout=15)
        if rc != 0:
            return f"Erreur: {stderr}"
        if stdout == "NOT_FOUND":
            return f"🔍 Aucun résultat pour « {query} » dans ta bibliothèque."
        return f"▶️ Lecture de: **{stdout}**"

    def search_library(self, query: str, limit: int = 10) -> str:
        """Search Apple Music library and return results."""
        safe_query = query.replace('"', '\\"').replace("'", "'\\''")
        script = f"""
        tell application "Music"
            set searchResults to search playlist "Bibliothèque" for "{safe_query}"
            set output to ""
            set maxItems to {limit}
            if (count of searchResults) < maxItems then set maxItems to (count of searchResults)
            repeat with i from 1 to maxItems
                set t to item i of searchResults
                set output to output & name of t & "|||" & artist of t & "|||" & album of t & linefeed
            end repeat
            return output
        end tell
        """
        stdout, stderr, rc = _osascript(script, timeout=15)
        if rc != 0:
            return f"Erreur: {stderr}"
        if not stdout.strip():
            return f"🔍 Aucun résultat pour « {query} »."

        lines = []
        for i, line in enumerate(stdout.strip().split("\n"), 1):
            parts = line.split("|||")
            if len(parts) >= 3:
                lines.append(f"  {i}. **{parts[0]}** — {parts[1]} ({parts[2]})")

        return f"🔍 Résultats pour « {query} »:\n" + "\n".join(lines)

    # ═══════════════════════════ PLAYLISTS ═══════════════════════════

    def list_playlists(self) -> str:
        """List all user playlists."""
        script = """
        tell application "Music"
            set output to ""
            repeat with p in user playlists
                set output to output & name of p & "|||" & (count of tracks of p) & linefeed
            end repeat
            return output
        end tell
        """
        stdout, stderr, rc = _osascript(script, timeout=15)
        if rc != 0:
            return f"Erreur: {stderr}"
        if not stdout.strip():
            return "Aucune playlist trouvée."

        lines = []
        for line in stdout.strip().split("\n"):
            parts = line.split("|||")
            if len(parts) >= 2:
                lines.append(f"  🎶 **{parts[0]}** ({parts[1]} morceaux)")

        return "**Tes playlists:**\n" + "\n".join(lines)

    def play_playlist(self, name: str) -> str:
        """Play a specific playlist by name."""
        safe_name = name.replace('"', '\\"')
        script = f"""
        tell application "Music"
            try
                play playlist "{safe_name}"
                return "OK"
            on error
                return "NOT_FOUND"
            end try
        end tell
        """
        stdout, stderr, rc = _osascript(script)
        if rc != 0:
            return f"Erreur: {stderr}"
        if stdout == "NOT_FOUND":
            return f"❌ Playlist « {name} » introuvable."
        return f"▶️ Lecture de la playlist **{name}**."

    # ═══════════════════════════ SHUFFLE / REPEAT ═══════════════════════════

    def set_shuffle(self, enabled: bool) -> str:
        """Enable or disable shuffle."""
        val = "true" if enabled else "false"
        _, stderr, rc = _osascript(f'tell application "Music" to set shuffle enabled to {val}')
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"🔀 Shuffle {'activé' if enabled else 'désactivé'}."

    def set_repeat(self, mode: str = "off") -> str:
        """Set repeat mode: off, one, all."""
        mode_map = {"off": "off", "one": "one", "all": "all"}
        if mode not in mode_map:
            return f"Mode invalide. Utilise: off, one, all"
        _, stderr, rc = _osascript(f'tell application "Music" to set song repeat to {mode_map[mode]}')
        if rc != 0:
            return f"Erreur: {stderr}"
        emoji = {"off": "➡️", "one": "🔂", "all": "🔁"}[mode]
        return f"{emoji} Répétition: **{mode}**."
