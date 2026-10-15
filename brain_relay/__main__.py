import argparse
from .app import create_app


def main():
    parser = argparse.ArgumentParser(description='Brain Relay — local task capsules')
    parser.add_argument('--port', type=int, default=7332)
    args = parser.parse_args()
    create_app().run(host='127.0.0.1', port=args.port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
