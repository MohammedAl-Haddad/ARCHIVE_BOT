# Setup Guide

This guide walks a new owner through a fresh installation of the bot.
It covers the first run wizard and bulk import/export utilities.

## 1. Install dependencies
1. Clone the repository.
2. Create a virtual environment (optional) and install requirements:
   ```bash
   pip install -r requirements.txt
   ```

## 2. Configure environment variables
1. Create a `.env` file in the project root with at least:
   ```dotenv
   BOT_TOKEN=123456:ABCDEF
   ARCHIVE_CHANNEL_ID=-1009876543210
   OWNER_TG_ID=123456789
   ```
2. Any missing mandatory variable will stop the bot with a clear error.

## 3. Run the owner wizard
1. Start the bot:
   ```bash
   python -m bot.main
   ```
2. In a supergroup, run `/insert_group` to link the group to a level and term.
3. Inside a topic of that group run `/insert_sub` and provide the subject and
   section. This binds the topic to the subject.

## 4. Importing and exporting data
The `import_export` module supports bulk JSON transfers.

*Export*
```bash
python -m scripts.export_db > dump.json
```

*Import*
```bash
python -m scripts.import_db dump.json
```

## 5. Verification
After the initial setup, run the test suite to ensure the installation works:
```bash
pytest
```
