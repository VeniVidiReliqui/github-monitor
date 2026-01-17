import time

import network
import picounicorn as picounicorn_module
import ujson
import urequests

import config

# Save button constants before overwriting module reference
BUTTON_A = picounicorn_module.BUTTON_A
BUTTON_B = picounicorn_module.BUTTON_B
BUTTON_X = picounicorn_module.BUTTON_X
BUTTON_Y = picounicorn_module.BUTTON_Y

# Initialize the Unicorn Pack
picounicorn = picounicorn_module.PicoUnicorn()

WIDTH = picounicorn.get_width()  # 16
HEIGHT = picounicorn.get_height()  # 7

# Brightness is mutable - can be adjusted with buttons
brightness = config.BRIGHTNESS_CONFIG
BRIGHTNESS_FILE = "brightness.txt"


def load_brightness():
    """Load brightness from file, or return default if not found."""
    global brightness
    try:
        with open(BRIGHTNESS_FILE, "r") as f:
            saved = float(f.read().strip())
            brightness = max(0.1, min(1.0, saved))
            print(f"Loaded brightness: {brightness:.0%}")
    except (OSError, ValueError):
        # File doesn't exist or invalid - use config default
        brightness = config.BRIGHTNESS_CONFIG
        print(f"Using default brightness: {brightness:.0%}")


def save_brightness():
    """Save current brightness to file."""
    try:
        with open(BRIGHTNESS_FILE, "w") as f:
            f.write(str(brightness))
    except OSError as e:
        print(f"Failed to save brightness: {e}")


# GitHub contribution level colors
# Scaled for LED brightness
COLORS = {
    "NONE": (3, 7, 6),  # Dark gray - very dim
    "FIRST_QUARTILE": (14, 80, 41),  # Darkest green
    "SECOND_QUARTILE": (0, 140, 50),  # Dark green
    "THIRD_QUARTILE": (38, 180, 65),  # Medium green
    "FOURTH_QUARTILE": (57, 255, 83),  # Bright green
}

# GraphQL query to fetch contribution data
GRAPHQL_QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            contributionLevel
            weekday
          }
        }
      }
    }
  }
}
"""


def apply_brightness(color):
    """Apply brightness setting to a color tuple."""
    global brightness
    r, g, b = color
    return (
        int(r * brightness),
        int(g * brightness),
        int(b * brightness),
    )


def adjust_brightness(delta):
    """Adjust brightness by delta, clamping to valid range."""
    global brightness
    brightness = max(0.1, min(1.0, brightness + delta))
    print(f"Brightness: {brightness:.0%}")
    save_brightness()


def check_force_refresh():
    """Check if A+B are pressed together for force refresh."""
    return picounicorn.is_pressed(BUTTON_A) and picounicorn.is_pressed(BUTTON_B)


def check_buttons():
    """Check button presses and adjust brightness. Returns True if brightness changed."""
    # Skip brightness adjustment if force refresh combo is pressed
    if check_force_refresh():
        return True

    changed = False

    # A and X increase brightness by 10%
    if picounicorn.is_pressed(BUTTON_A) or picounicorn.is_pressed(BUTTON_X):
        adjust_brightness(0.1)
        changed = True

    # B and Y decrease brightness by 10%
    if picounicorn.is_pressed(BUTTON_B) or picounicorn.is_pressed(BUTTON_Y):
        adjust_brightness(-0.1)
        changed = True

    return changed


def clear_display():
    """Turn off all LEDs."""
    for x in range(WIDTH):
        for y in range(HEIGHT):
            picounicorn.set_pixel(x, y, 0, 0, 0)


def startup_animation():
    """Play a startup animation - green wave sweep across the display."""
    # GitHub green gradient colors for the wave
    wave_colors = [
        (5, 7, 9),  # NONE - dim
        (14, 68, 41),  # FIRST_QUARTILE
        (0, 109, 50),  # SECOND_QUARTILE
        (38, 166, 65),  # THIRD_QUARTILE
        (57, 211, 83),  # FOURTH_QUARTILE
        (38, 166, 65),  # THIRD_QUARTILE
        (0, 109, 50),  # SECOND_QUARTILE
        (14, 68, 41),  # FIRST_QUARTILE
    ]
    wave_len = len(wave_colors)

    clear_display()

    # Sweep wave from left to right
    for frame in range(WIDTH + wave_len):
        for x in range(WIDTH):
            wave_pos = frame - x
            if 0 <= wave_pos < wave_len:
                r, g, b = wave_colors[wave_pos]
                r, g, b = int(r * brightness), int(g * brightness), int(b * brightness)
                for y in range(HEIGHT):
                    picounicorn.set_pixel(x, y, r, g, b)
            elif wave_pos >= wave_len:
                # Trail off to dim
                for y in range(HEIGHT):
                    picounicorn.set_pixel(x, y, 0, 0, 0)
        time.sleep(0.04)

    # Brief pause then fade in all LEDs to bright green
    time.sleep(0.1)
    bright_green = (57, 211, 83)
    for step in range(6):
        factor = step / 5
        r = int(bright_green[0] * factor * brightness)
        g = int(bright_green[1] * factor * brightness)
        b = int(bright_green[2] * factor * brightness)
        for x in range(WIDTH):
            for y in range(HEIGHT):
                picounicorn.set_pixel(x, y, r, g, b)
        time.sleep(0.05)

    time.sleep(0.3)

    # Fade out
    for step in range(5, -1, -1):
        factor = step / 5
        r = int(bright_green[0] * factor * brightness)
        g = int(bright_green[1] * factor * brightness)
        b = int(bright_green[2] * factor * brightness)
        for x in range(WIDTH):
            for y in range(HEIGHT):
                picounicorn.set_pixel(x, y, r, g, b)
        time.sleep(0.05)

    clear_display()


def show_status(color):
    """Flash the first LED to show status."""
    r, g, b = color
    picounicorn.set_pixel(0, 0, r, g, b)


def show_error():
    """Display red on first LED to indicate error."""
    clear_display()
    show_status((255, 0, 0))


def show_connecting():
    """Display blue on first LED while connecting."""
    clear_display()
    show_status((0, 0, 255))


def show_fetching():
    """Display yellow on first LED while fetching data."""
    show_status((255, 255, 0))


def connect_wifi():
    """Connect to WiFi network with retry logic."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return True

    print(f"Connecting to {config.WIFI_SSID}...")
    show_connecting()

    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    max_attempts = 20
    attempt = 0
    while not wlan.isconnected() and attempt < max_attempts:
        time.sleep(0.5)
        attempt += 1

    if wlan.isconnected():
        print(f"Connected! IP: {wlan.ifconfig()[0]}")
        return True
    else:
        print("Failed to connect to WiFi")
        show_error()
        return False


def fetch_contributions():
    """Fetch contribution data from GitHub GraphQL API."""
    show_fetching()

    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "PicoUnicorn-GitHub-Display",
    }

    payload = ujson.dumps(
        {"query": GRAPHQL_QUERY, "variables": {"username": config.GITHUB_USERNAME}}
    )

    try:
        response = urequests.post(url, data=payload, headers=headers)

        if response.status_code != 200:
            print(f"GitHub API error: {response.status_code}")
            response.close()
            return None

        data = response.json()
        response.close()

        if "errors" in data:
            print(f"GraphQL error: {data['errors']}")
            return None

        return data
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def parse_contributions(data):
    """Parse the GitHub API response into a 2D grid of contribution levels."""
    try:
        weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"][
            "weeks"
        ]
    except (KeyError, TypeError) as e:
        print(f"Parse error: {e}")
        return None

    # Get the last 16 weeks
    recent_weeks = weeks[-16:] if len(weeks) >= 16 else weeks

    # Pad with empty weeks if we have fewer than 16
    while len(recent_weeks) < 16:
        recent_weeks.insert(0, {"contributionDays": []})

    # Create the grid: grid[x][y] where x is week (0-15), y is day (0-6)
    grid = []
    for week in recent_weeks:
        week_data = ["NONE"] * 7  # Default to no contributions
        for day in week.get("contributionDays", []):
            weekday = day.get("weekday", 0)
            level = day.get("contributionLevel", "NONE")
            if 0 <= weekday < 7:
                week_data[weekday] = level
        grid.append(week_data)

    return grid


def update_display(grid):
    """Update the LED display with the contribution grid."""
    if grid is None:
        show_error()
        return

    for x, week in enumerate(grid):
        for y, level in enumerate(week):
            color = COLORS.get(level, COLORS["NONE"])
            # Don't apply brightness to NONE - keep it at fixed dim level
            if level == "NONE":
                r, g, b = color
            else:
                r, g, b = apply_brightness(color)
            picounicorn.set_pixel(x, y, r, g, b)

    print("Display updated")


def wait_with_button_check(seconds, grid):
    """Wait for specified seconds while checking buttons. Returns True if force refresh requested."""
    elapsed = 0
    check_interval = 0.1  # Check buttons every 100ms

    while elapsed < seconds:
        # Check for force refresh combo (A+B)
        if check_force_refresh():
            print("Force refresh requested")
            # Debounce - wait for buttons to be released
            while check_force_refresh():
                time.sleep(0.1)
            return True

        if check_buttons():
            # Brightness changed, refresh display
            update_display(grid)
            # Debounce - wait for button release
            time.sleep(0.2)

        time.sleep(check_interval)
        elapsed += check_interval

    return False


def main():
    """Main loop: connect, fetch, display, repeat."""
    print("GitHub Contribution Display")
    print(f"User: {config.GITHUB_USERNAME}")
    print(f"Poll interval: {config.POLL_INTERVAL}s")
    print("Buttons: A/X = brighter, B/Y = dimmer, A+B = refresh")

    load_brightness()
    startup_animation()
    current_grid = None

    while True:
        # Ensure WiFi is connected
        if not connect_wifi():
            print("WiFi connection failed, retrying in 10s...")
            time.sleep(10)
            continue

        # Fetch contribution data
        data = fetch_contributions()

        if data:
            current_grid = parse_contributions(data)
            print(current_grid)
            update_display(current_grid)
        else:
            print("Failed to fetch data, will retry...")
            show_error()

        # Wait before next poll, checking buttons continuously
        print(f"Next update in {config.POLL_INTERVAL}s...")
        if current_grid:
            if wait_with_button_check(config.POLL_INTERVAL, current_grid):
                # Force refresh was requested, skip remaining wait
                continue
        else:
            time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
