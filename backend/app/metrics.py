from prometheus_client import Counter, Gauge, Histogram

# --- HTTP: incremented by app/middlewares/metrics.py ---
HTTP_REQUESTS_TOTAL = Counter(
    "chantepafo_http_requests_total",
    "Total HTTP requests processed",
    labelnames=("method", "path", "status"),
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "chantepafo_http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=("method", "path"),
)

# --- Rooms: wired in this task into app/rooms/service.py ---
ROOMS_CREATED_TOTAL = Counter(
    "chantepafo_rooms_created_total",
    "Total number of rooms created",
)
ROOMS_ACTIVE = Gauge(
    "chantepafo_rooms_active",
    "Number of rooms currently stored in Redis",
)

# --- Games: stubs for future game-mode tasks ---
GAMES_STARTED_TOTAL = Counter(
    "chantepafo_games_started_total",
    "Games started, by mode",
    labelnames=("mode",),
)
PLAYERS_PER_ROOM = Histogram(
    "chantepafo_players_per_room",
    "Number of players present when a game starts",
    buckets=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
)

# --- Deezer API: stubs for Task 7 ---
DEEZER_API_CALLS_TOTAL = Counter(
    "chantepafo_deezer_api_calls_total",
    "Deezer API calls",
    labelnames=("endpoint", "status"),
)
DEEZER_API_CALL_DURATION_SECONDS = Histogram(
    "chantepafo_deezer_api_call_duration_seconds",
    "Deezer API call latency in seconds",
    labelnames=("endpoint",),
)

# --- Fuzzy matching: stub for Task 8 ---
FUZZY_MATCH_DURATION_SECONDS = Histogram(
    "chantepafo_fuzzy_match_duration_seconds",
    "Fuzzy match computation time in seconds",
)

# --- Socket.IO: wired in this task into app/sockets/handlers.py ---
SOCKETIO_EVENTS_TOTAL = Counter(
    "chantepafo_socketio_events_total",
    "Socket.IO events handled",
    labelnames=("event",),
)
SOCKETIO_CONNECTIONS_ACTIVE = Gauge(
    "chantepafo_socketio_connections_active",
    "Active Socket.IO connections",
)
