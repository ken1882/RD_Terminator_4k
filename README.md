# RD_Terminator_4k

Automated news and X (previously Twitter) monitoring bot for games. It fetches, parses, and posts news updates and tweets from various official sources to Discord webhooks, supporting multiple games and accounts.

## Features

- Monitors official news pages for supported games and posts updates to Discord.
- Monitors official Twitter accounts and relays new tweets to Discord.
- Handles multiple games:
    - Angelica Aster
    - Mist Train Girls
    - Monster Musume TD
    - Twinkle Star Knights
    - Azur Lane
- Robust error handling and logging.
- Configurable via environment variables.
- Modular architecture for easy extension.

## Setup

1. **Clone the repository**

2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   - Copy `example.env` to `.env`
   - Refer to the comments and source code to edit the content
   - DO NOT EXPOSE YOUR SENSITIVE INFORMATIONS


## Usage

Run the bot:
```sh
python main.py
```

The bot will start monitoring news and Twitter feeds, posting updates to the configured Discord webhooks.

## Adding Support for a New Game

1. Create a new module in `module/` (see `module/xxx_news.py` as an example).
2. Implement the required functions: `update`, `init`, `reload`, and others if needed.
3. Add the module to `import_modules()` in `main.py`.


## License

This project is licensed under the MIT License.
See the [LICENSE](LICENSE) file for details.

---

**Note:** This project is not affiliated with any of the games or companies mentioned. Use responsibly and respect rate limits and terms of service.
