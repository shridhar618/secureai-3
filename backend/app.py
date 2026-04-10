import os

from app import create_app, get_socketio_async_mode, socketio

if get_socketio_async_mode() == "eventlet":
    import eventlet

    eventlet.monkey_patch()

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    debug = os.getenv("DEBUG", "1").lower() in {"1", "true", "yes", "on"}
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
