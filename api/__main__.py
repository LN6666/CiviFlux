import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Start same-origin CiviFlux on loopback only")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run("api.app:create_app", factory=True, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
