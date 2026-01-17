# github-monitor
This is a small app for a [Pi Pico 2W](https://www.raspberrypi.com/products/raspberry-pi-pico-2/) and a [Pimoroni Pico Unicorn Pack](https://shop.pimoroni.com/products/pico-unicorn-pack?variant=32369501306963) to display your github contributions on your desk.

## Setup
### Flash Firmware
The Pico Unicorn Pack needs a specific firmware on the Pico in order to work. To flash it:
1. Plug the pico into your computer while holding the BOOTSEL button
2. Verify the pico has mounted onto your system as a drive
3. Copy the *rpi_pico2_w-v1.26.1-micropython.uf2* to the root of the drive
4. The pico should restart, loading the new firmware

### Generate Github Token
You'll need to generate a github token to access your account data. This works with a classic token with limited scope:
1. Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Select "Personal access tokens" -> "Tokens (classic)"
3. Create a token with only read:user scoping
4. Copy token into config.py

### Configure and Load App
1. Setup your config file with WiFi credentials (2.4GHz only) and Github token & username
2. Copy all py files to the pico with the following command from the project root:
```zsh
mpremote fs cp *.py :.
```
```zsh
# if mpremote is not installed, you can install it with brew:
brew install mpremote
```
3. Powercycle the Pico

## Button Controls
 - A/X : Increase brightness
 - B/Y : Decrease brightness
 - A+B : Force data refresh

## LED Feedback
The upper left LED gives basic status information:

**Blue** -> Connecting to WiFi

**Yellow** -> Fetching data from Github

**Red** -> One of the following errors has ocurred:
  - failed to connect to WiFi (retries every 15s)
  - failed to update the Unicorn Pack (retry flashing firmware)
  - failed to fetch data (check internet connection)

## Additional Links:
[Pimoroni Getting Started Page for Pico Unicorn Pack](https://learn.pimoroni.com/article/getting-started-with-pico)
