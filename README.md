Mac Desk

Mac Desk turns an iPhone or another device on your local network into a compact companion dashboard for macOS.

It runs a lightweight Python server on the Mac and provides a touch-friendly web interface that can be opened from Safari and added to the iPhone Home Screen.

No cloud server is required. Communication stays on the local network.

Features

Dashboard

* Large digital clock and date
* Mac connection status
* MacBook battery percentage and charging state
* Automatic night mode
* Burn-in protection for devices used as always-on displays
* Swipe-based multi-page interface

Now Playing

Supports:

* Spotify
* Apple Music

The dashboard can display:

* Track title
* Artist
* Album
* Playback state
* Track progress
* Current position and duration

Playback controls:

* Previous track
* Play / pause
* Next track

When no media is active, the interface automatically returns to the large clock view.

Mac System Monitor

Displays live system information including:

* CPU usage
* Memory usage
* Disk usage
* System uptime
* MacBook battery status
* Connected Bluetooth devices
* Bluetooth device battery level when available

Mac Controls

The dashboard can remotely control basic Mac functions over the local network:

* Volume up
* Volume down
* Mute / unmute
* Lock Mac
* Put Mac to sleep

Sensitive actions use a hold-to-confirm interaction to reduce accidental activation.

Bluetooth Devices

Mac Desk reads connected Bluetooth devices directly from macOS.

Supported information may include:

* Device name
* Device type
* Battery percentage
* Connection state

Only currently connected devices are displayed.

Device Pairing

A new six-digit pairing code is generated every time the Mac Desk server starts.

Example:

🔐 Yeni cihaz eşleştirme kodu:
             178 659

Enter this code on the iPhone to authorize the device.

After successful pairing, the browser receives an authentication cookie so the device does not need to enter the code on every page refresh.

The access token itself is randomly generated when the server starts.

Local Network Security

Mac Desk is designed for use only on a trusted local network.

The server verifies the Wi-Fi SSID configured in .env.

If the Mac is not connected to the configured Wi-Fi network, the dashboard will not start.

While running, Mac Desk periodically checks the Wi-Fi connection. If the Mac leaves the allowed network, the server shuts itself down.

The server listens on:

0.0.0.0

but access is protected by:

1. Allowed Wi-Fi verification
2. Six-digit device pairing
3. Random session token
4. Authentication cookie

Mac Desk should not be directly exposed to the public internet.

Requirements

* macOS
* Python 3
* iPhone, iPad, or another device with a modern web browser
* Both devices connected to the same local network

Some features also require:

* Spotify for Spotify integration
* Apple Music for Music integration
* macOS Automation permissions for media and system controls

No external Python packages are currently required.

Installation

Clone the repository:

git clone YOUR_REPOSITORY_URL
cd mac-iphone-dashboard

Create the local environment file:

cp .env.example .env

Edit .env:

DASHBOARD_ALLOWED_WIFI=YOUR_WIFI_NAME
DASHBOARD_PORT=57321
DASHBOARD_WIFI_CHECK_INTERVAL=15
NIGHT_MODE_START=23
NIGHT_MODE_END=7

Do not commit your real .env file.

Environment Variables

DASHBOARD_ALLOWED_WIFI

Wi-Fi SSID on which Mac Desk is allowed to operate.

Example:

DASHBOARD_ALLOWED_WIFI=MyHomeWiFi

DASHBOARD_PORT

Local HTTP server port.

Default:

DASHBOARD_PORT=57321

DASHBOARD_WIFI_CHECK_INTERVAL

How often Mac Desk verifies that the Mac is still connected to the allowed Wi-Fi network.

Value is in seconds.

Example:

DASHBOARD_WIFI_CHECK_INTERVAL=15

NIGHT_MODE_START

Hour when automatic night mode begins.

NIGHT_MODE_START=23

NIGHT_MODE_END

Hour when automatic night mode ends.

NIGHT_MODE_END=7

Running Mac Desk

Start the server:

python3 server.py

The terminal will display something similar to:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              MAC DESK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wi-Fi : MyHomeWiFi
Port  : 57321
📱 http://192.168.x.x:57321
🔐 Yeni cihaz eşleştirme kodu:
             123 456
🔒 Wi-Fi kontrolü: 15 saniye
Kapatmak için: Control + C

Open the displayed address from Safari on the iPhone.

Enter the six-digit pairing code shown on the Mac.

Add to iPhone Home Screen

For a more app-like experience:

1. Open Mac Desk in Safari.
2. Tap the Share button.
3. Select Add to Home Screen.
4. Launch Mac Desk from the new Home Screen icon.

This provides a cleaner dashboard experience than keeping the page open in a regular Safari tab.

Project Structure

mac-iphone-dashboard/
├── server.py
├── .env
├── .env.example
├── .gitignore
├── README.md
└── static/
    ├── index.html
    ├── style.css
    └── app.js

server.py

Python HTTP server and macOS integration layer.

Responsible for:

* Authentication
* Pairing
* Wi-Fi verification
* Battery information
* CPU usage
* Memory usage
* Disk usage
* Uptime
* Bluetooth devices
* Spotify
* Apple Music
* Volume control
* Mac lock
* Mac sleep
* Night mode

static/index.html

Dashboard structure and interface.

static/style.css

Visual design, responsive layout, animations, night mode, and dashboard cards.

static/app.js

Frontend logic including:

* API communication
* Clock
* Pairing
* Media state
* System information
* Bluetooth devices
* Touch gestures
* Mac controls
* Burn-in protection

API

Mac Desk exposes a small local API used by its frontend.

Authentication

GET /api/auth
POST /api/pair

Dashboard

GET /api/status
GET /api/system

Music

POST /api/music/playpause
POST /api/music/previous
POST /api/music/next

Mac Controls

POST /api/control/volume-up
POST /api/control/volume-down
POST /api/control/mute
POST /api/control/lock
POST /api/control/sleep

These endpoints are intended for local dashboard use, not as a public internet API.

Privacy

Mac Desk does not require a cloud backend.

System information is read locally from macOS and delivered directly to the paired device over the local network.

The project does not intentionally transmit Mac system information to an external service.

Your .env file may contain private information such as your Wi-Fi SSID and must remain outside version control.

.gitignore

At minimum, the repository should contain:

.env
__pycache__/
*.pyc
.DS_Store

Before publishing changes, you can verify that .env is not tracked:

git ls-files | grep -E '(^|/)(\.env|config\.json)$'

No output means those files are not currently tracked.

You can also check repository history:

git log --all -- .env config.json

Security Notes

Mac Desk is a personal local-network utility and is not designed to be an internet-facing remote administration system.

Do not:

* Forward the Mac Desk port from your router
* Expose the server directly to the internet
* Commit .env
* Commit Wi-Fi credentials or private device identifiers
* Hard-code access tokens into the repository

Pairing codes and access tokens are generated at runtime.

Known Limitations

* Bluetooth information depends on what macOS exposes through system_profiler.
* Battery information may not be available for every Bluetooth device.
* Spotify and Apple Music controls depend on macOS Automation permissions.
* The dashboard currently targets local-network operation.
* macOS notifications are not currently mirrored to the dashboard.
* Browser behavior may differ between normal Safari and Home Screen mode.

Development

Check Python syntax before starting:

python3 -m py_compile server.py

Then run:

python3 server.py

Changes to frontend files can normally be tested by refreshing Mac Desk on the iPhone.

Disclaimer

Mac Desk is an independent personal project and is not affiliated with Apple or Spotify.

Apple, macOS, iPhone, Apple Music, and related names are trademarks of their respective owners.