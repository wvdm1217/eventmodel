import sys


def main() -> None:
    try:
        import eventmodel
        from eventmodel import App, EventModel, Service  # noqa: F401

        print(f"eventmodel version: {getattr(eventmodel, '__version__', 'unknown')}")
        print("Smoke test passed: eventmodel imported successfully.")
        sys.exit(0)
    except Exception as e:
        print(f"Smoke test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
