let currentPage = 0;

let touchStartX = 0;
let touchStartY = 0;

let latestMusic = null;
let notificationTimer = null;

const pages =
    document.getElementById("pages");

const home =
    document.getElementById("home");

const dashboard =
    document.getElementById("dashboard");

const pairScreen =
    document.getElementById("pair-screen");

const dynamicCard =
    document.getElementById("dynamic-card");

const musicCard =
    document.getElementById("music-card");

const notificationCard =
    document.getElementById("notification-card");


/* Clock */

function updateClock() {
    const now = new Date();

    document.getElementById(
        "clock"
    ).textContent =
        now.toLocaleTimeString(
            "tr-TR",
            {
                hour: "2-digit",
                minute: "2-digit"
            }
        );

    document.getElementById(
        "date-day"
    ).textContent =
        now.getDate();

    document.getElementById(
        "date-month"
    ).textContent =
        now.toLocaleDateString(
            "tr-TR",
            {
                month: "long"
            }
        );

    document.getElementById(
        "date-weekday"
    ).textContent =
        now.toLocaleDateString(
            "tr-TR",
            {
                weekday: "long"
            }
        );
}


/* Pair */

async function checkAuth() {
    try {
        const response =
            await fetch(
                "/api/auth",
                {
                    cache: "no-store"
                }
            );

        const data =
            await response.json();

        if (
            data.authenticated
            && data.wifi_allowed
        ) {
            pairScreen.classList.add(
                "hidden"
            );

            dashboard.classList.remove(
                "hidden"
            );

            updateStatus();
            updateSystem();

            return;
        }

        dashboard.classList.add(
            "hidden"
        );

        pairScreen.classList.remove(
            "hidden"
        );

        if (!data.wifi_allowed) {
            document.getElementById(
                "pair-error"
            ).textContent =
                "İzin verilen Wi-Fi ağına bağlı değilsin.";
        }

    } catch {
        dashboard.classList.add(
            "hidden"
        );

        pairScreen.classList.remove(
            "hidden"
        );
    }
}


async function pairDevice() {
    const input =
        document.getElementById(
            "pair-code"
        );

    const error =
        document.getElementById(
            "pair-error"
        );

    const code =
        input.value.replace(
            /\D/g,
            ""
        );

    if (code.length !== 6) {
        error.textContent =
            "6 haneli kodu gir.";

        return;
    }

    error.textContent =
        "Bağlanıyor...";

    try {
        const response =
            await fetch(
                "/api/pair",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            code
                        })
                }
            );

        if (!response.ok) {
            error.textContent =
                "Kod hatalı.";

            return;
        }

        error.textContent = "";

        await checkAuth();

    } catch {
        error.textContent =
            "Mac'e ulaşılamıyor.";
    }
}


document.getElementById(
    "pair-button"
).addEventListener(
    "click",
    pairDevice
);


/* Helpers */

function formatTime(seconds) {
    seconds =
        Math.max(
            0,
            Number(seconds) || 0
        );

    const minutes =
        Math.floor(
            seconds / 60
        );

    const rest =
        Math.floor(
            seconds % 60
        );

    return (
        minutes +
        ":" +
        String(rest).padStart(
            2,
            "0"
        )
    );
}


function setMeter(id, value) {
    document.getElementById(
        id
    ).style.width =
        Math.max(
            0,
            Math.min(
                100,
                Number(value) || 0
            )
        ) + "%";
}


/* Battery */

function updateBattery(battery) {
    if (
        !battery ||
        battery.percentage == null
    ) {
        return;
    }

    const percentage =
        battery.percentage;

    document.getElementById(
        "battery-text"
    ).textContent =
        percentage + "%";

    document.getElementById(
        "battery-fill"
    ).style.width =
        percentage + "%";

    let state = "";

    if (
        battery.state === "charging"
    ) {
        state = "⚡";
    }

    if (
        battery.state === "charged"
    ) {
        state = "✓";
    }

    document.getElementById(
        "battery-charge"
    ).textContent =
        state;
}


/* Dynamic home card */

function normalClock() {
    dynamicCard.classList.add(
        "hidden"
    );

    musicCard.classList.add(
        "hidden"
    );

    notificationCard.classList.add(
        "hidden"
    );

    home.classList.remove(
        "has-card"
    );
}


function showMusic(music) {
    home.classList.add(
        "has-card"
    );

    dynamicCard.classList.remove(
        "hidden"
    );

    notificationCard.classList.add(
        "hidden"
    );

    musicCard.classList.remove(
        "hidden"
    );

    document.getElementById(
        "music-source"
    ).textContent =
        music.source.toUpperCase();

    document.getElementById(
        "music-title"
    ).textContent =
        music.title ||
        "Bilinmeyen Şarkı";

    document.getElementById(
        "music-artist"
    ).textContent =
        music.artist || "";

    document.getElementById(
        "music-play"
    ).textContent =
        music.playing
            ? "❚❚"
            : "▶";

    const duration =
        Number(
            music.duration
        ) || 0;

    const position =
        Number(
            music.position
        ) || 0;

    const progress =
        duration > 0
            ? (
                position /
                duration *
                100
            )
            : 0;

    document.getElementById(
        "music-progress"
    ).style.width =
        Math.min(
            100,
            progress
        ) + "%";

    document.getElementById(
        "music-position"
    ).textContent =
        formatTime(position);

    document.getElementById(
        "music-duration"
    ).textContent =
        formatTime(duration);
}


/*
 Future notification hook.

 Gerçek macOS notification kaynağını
 ileride buraya bağlayacağız.
*/

function showNotification(
    app,
    title,
    body
) {
    clearTimeout(
        notificationTimer
    );

    home.classList.add(
        "has-card"
    );

    dynamicCard.classList.remove(
        "hidden"
    );

    musicCard.classList.add(
        "hidden"
    );

    notificationCard.classList.remove(
        "hidden"
    );

    document.getElementById(
        "notification-app"
    ).textContent =
        app;

    document.getElementById(
        "notification-title"
    ).textContent =
        title;

    document.getElementById(
        "notification-body"
    ).textContent =
        body;

    notificationTimer =
        setTimeout(
            () => {
                notificationCard
                    .classList
                    .add("hidden");

                if (
                    latestMusic &&
                    latestMusic.available
                ) {
                    showMusic(
                        latestMusic
                    );
                } else {
                    normalClock();
                }
            },
            5000
        );
}


/* Status */

async function updateStatus() {
    try {
        const response =
            await fetch(
                "/api/status",
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            throw new Error();
        }

        const data =
            await response.json();

        document.getElementById(
            "connection-text"
        ).textContent =
            "MAC BAĞLI";

        updateBattery(
            data.battery
        );

        updateVolume(
            data.volume
        );

        latestMusic =
            data.music;

        if (
            notificationCard
                .classList
                .contains("hidden")
        ) {
            if (
                data.music &&
                data.music.available
            ) {
                showMusic(
                    data.music
                );
            } else {
                normalClock();
            }
        }

        document.body.classList.toggle(
            "night",
            Boolean(
                data.night_mode
            )
        );

    } catch {
        document.getElementById(
            "connection-text"
        ).textContent =
            "MAC ÇEVRİMDIŞI";
    }
}


/* System */

async function updateSystem() {
    try {
        const response =
            await fetch(
                "/api/system",
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            return;
        }

        const data =
            await response.json();


        /* CPU */

        const cpuValue =
            document.getElementById(
                "cpu-value"
            );

        if (
            data.cpu != null &&
            Number.isFinite(
                Number(data.cpu)
            )
        ) {
            cpuValue.textContent =
                Number(data.cpu)
                    .toFixed(1)
                    .replace(".0", "")
                + "%";

            setMeter(
                "cpu-meter",
                data.cpu
            );

        } else {
            cpuValue.textContent = "—";

            setMeter(
                "cpu-meter",
                0
            );
        }


        /* RAM */

        const ramValue =
            document.getElementById(
                "ram-value"
            );

        if (
            data.memory &&
            data.memory.used_gb != null &&
            data.memory.total_gb != null
        ) {
            ramValue.textContent =
                data.memory.used_gb +
                " / " +
                data.memory.total_gb +
                " GB";

            setMeter(
                "ram-meter",
                data.memory.percentage
            );

        } else {
            ramValue.textContent = "—";

            setMeter(
                "ram-meter",
                0
            );
        }


        /* Disk */

        const diskValue =
            document.getElementById(
                "disk-value"
            );

        if (
            data.disk &&
            data.disk.used_gb != null &&
            data.disk.total_gb != null
        ) {
            diskValue.textContent =
                data.disk.used_gb +
                " / " +
                data.disk.total_gb +
                " GB";

            setMeter(
                "disk-meter",
                data.disk.percentage
            );

        } else {
            diskValue.textContent = "—";

            setMeter(
                "disk-meter",
                0
            );
        }


        /* Uptime */

        document.getElementById(
            "uptime-value"
        ).textContent =
            data.uptime || "—";


        /* Bluetooth */

        updateBluetooth(
            data.bluetooth || []
        );

    } catch {}
}

/* Bluetooth */

function deviceIcon(name) {
    const lower =
        name.toLowerCase();

    if (
        lower.includes("airpod") ||
        lower.includes("headphone") ||
        lower.includes("buds")
    ) {
        return "♪";
    }

    if (
        lower.includes("mouse") ||
        lower.includes("master")
    ) {
        return "◉";
    }

    if (
        lower.includes("keyboard")
    ) {
        return "⌨";
    }

    return "ᛒ";
}


function updateBluetooth(devices) {
    const list =
        document.getElementById(
            "bluetooth-list"
        );

    document.getElementById(
        "bluetooth-count"
    ).textContent =
        devices.length;

    if (!devices.length) {
        list.innerHTML =
            `
            <div class="no-devices">
                Bağlı Bluetooth cihazı yok
            </div>
            `;

        return;
    }

    list.innerHTML =
        devices.map(
            device => `
                <div class="bt-device">

                    <div class="bt-left">

                        <div class="bt-icon">
                            ${deviceIcon(
                                device.name
                            )}
                        </div>

                        <strong>
                            ${escapeHTML(
                                device.name
                            )}
                        </strong>

                    </div>

                    <span>
                        ${
                            device.battery != null
                                ? device.battery + "%"
                                : "BAĞLI"
                        }
                    </span>

                </div>
            `
        ).join("");
}


function escapeHTML(value) {
    const div =
        document.createElement(
            "div"
        );

    div.textContent =
        value;

    return div.innerHTML;
}


/* Volume */

function updateVolume(volume) {
    if (!volume) {
        return;
    }

    document.getElementById(
        "volume-value"
    ).textContent =
        volume.volume + "%";

    document.getElementById(
        "volume-fill"
    ).style.width =
        volume.volume + "%";

    document.getElementById(
        "mute-button"
    ).textContent =
        volume.muted
            ? "UNMUTE"
            : "MUTE";
}


/* Music commands */

document
    .querySelectorAll(
        "[data-music]"
    )
    .forEach(
        button => {
            button.addEventListener(
                "click",
                async () => {
                    try {
                        await fetch(
                            "/api/music/" +
                            button.dataset.music,
                            {
                                method:
                                    "POST"
                            }
                        );

                        setTimeout(
                            updateStatus,
                            250
                        );
                    } catch {}
                }
            );
        }
    );


/* Normal controls */

document
    .querySelectorAll(
        "[data-control]"
    )
    .forEach(
        button => {
            button.addEventListener(
                "click",
                async () => {
                    try {
                        const response =
                            await fetch(
                                "/api/control/" +
                                button.dataset.control,
                                {
                                    method:
                                        "POST"
                                }
                            );

                        const data =
                            await response.json();

                        updateVolume(
                            data.volume
                        );

                    } catch {}
                }
            );
        }
    );


/* Hold-to-confirm controls */

document
    .querySelectorAll(
        ".hold-action"
    )
    .forEach(
        button => {
            let timer = null;
            let completed = false;

            const progress =
                button.querySelector(
                    ":scope > i"
                );

            function start() {
                completed = false;

                progress.style.transition =
                    "width 1.4s linear";

                progress.style.width =
                    "100%";

                timer =
                    setTimeout(
                        async () => {
                            completed = true;

                            try {
                                await fetch(
                                    "/api/control/" +
                                    button.dataset.hold,
                                    {
                                        method:
                                            "POST"
                                    }
                                );
                            } catch {}

                            progress.style.transition =
                                "none";

                            progress.style.width =
                                "0";
                        },
                        1400
                    );
            }

            function cancel() {
                if (!completed) {
                    clearTimeout(timer);

                    progress.style.transition =
                        "width .2s ease";

                    progress.style.width =
                        "0";
                }
            }

            button.addEventListener(
                "touchstart",
                start,
                {
                    passive: true
                }
            );

            button.addEventListener(
                "touchend",
                cancel
            );

            button.addEventListener(
                "touchcancel",
                cancel
            );
        }
    );


/* Swipe */

function showPage(index) {
    currentPage =
        Math.max(
            0,
            Math.min(
                2,
                index
            )
        );

    pages.style.transform =
        `translateX(-${
            currentPage * 100
        }vw)`;

    document
        .querySelectorAll(
            ".page-indicator i"
        )
        .forEach(
            (dot, index) => {
                dot.classList.toggle(
                    "active",
                    index === currentPage
                );
            }
        );

    if (currentPage === 1) {
        updateSystem();
    }
}


document.addEventListener(
    "touchstart",
    event => {
        const touch =
            event.changedTouches[0];

        touchStartX =
            touch.screenX;

        touchStartY =
            touch.screenY;
    },
    {
        passive: true
    }
);


document.addEventListener(
    "touchend",
    event => {
        const touch =
            event.changedTouches[0];

        const dx =
            touch.screenX -
            touchStartX;

        const dy =
            touch.screenY -
            touchStartY;

        if (
            Math.abs(dx) < 50 ||
            Math.abs(dx) <
            Math.abs(dy)
        ) {
            return;
        }

        if (dx < 0) {
            showPage(
                currentPage + 1
            );
        } else {
            showPage(
                currentPage - 1
            );
        }
    },
    {
        passive: true
    }
);


/* Burn-in / static-screen protection */

const burninLayer =
    document.getElementById(
        "burnin-layer"
    );

function shiftScreen() {
    const x =
        Math.floor(
            Math.random() * 7
        ) - 3;

    const y =
        Math.floor(
            Math.random() * 7
        ) - 3;

    burninLayer.style.transform =
        `translate(${x}px, ${y}px)`;
}


/* Init */

updateClock();

setInterval(
    updateClock,
    1000
);

checkAuth();

setInterval(
    () => {
        if (
            !dashboard
                .classList
                .contains("hidden")
        ) {
            updateStatus();
        }
    },
    3000
);

setInterval(
    () => {
        if (
            currentPage === 1 &&
            !dashboard
                .classList
                .contains("hidden")
        ) {
            updateSystem();
        }
    },
    10000
);

setInterval(
    shiftScreen,
    120000
);