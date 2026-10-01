"""API bootstrap; normal mode preserves backend dotenv and hot reload."""
import argparse
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--api-port', type=int, default=8000)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    import uvicorn

    if args.offline:
        if not os.environ.get('FORGE_DATA_DIR'):
            parser.error('--offline requires an isolated FORGE_DATA_DIR')
        # Set before importing app.py, which constructs its default app eagerly.
        from forge.config import Settings
        Settings.model_config['env_file'] = None
        os.environ['GEMINI_API_KEY'] = ''
        os.environ['FORGE_DATABASE_URL'] = ''
        from forge.api.app import create_app
        app = create_app(Settings(_env_file=None))
        uvicorn.run(app, host=args.host, port=args.api_port)
    else:
        uvicorn.run('forge.api.app:app', host=args.host, port=args.api_port, reload=True)


if __name__ == '__main__':
    main()
