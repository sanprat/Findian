# Production Deployment Guide (Oracle Cloud / VPS)

Since `.env` is **gitignored** (for security), it will not exist when you clone the repo on your server. You must create it manually.

## 1. Initial Setup on Server

1.  **SSH into your Oracle Cloud Instance**:
    ```bash
    ssh ubuntu@<your-server-ip>
    ```

2.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/Pystock.git
    cd Pystock
    ```

3.  **Create Production `.env` File**:
    This is the **most critical step**. You must create the secrets file on the server.
    ```bash
    nano .env
    ```

4.  **Paste Your Production Secrets**:
    Copy the content from your local `.env`, but update values for production (e.g., strong passwords).
    ```ini
    # Database (Change these!)
    DB_ROOT_PASSWORD=VeryStrongProdPassword123!
    DB_USER=pystock_user
    DB_PASSWORD=AnotherStrongPassword!
    DB_NAME=pystock_prod

    # Admin IDs (Comma-separated list of Telegram User IDs)
    # Get your ID from the bot logs or @userinfobot
    ADMIN_IDS=11223344,55667788

    # APIs
    TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    CHUTES_API_TOKEN=your_chutes_token
    # ... (Add Finvasia credentials)
    ```
    *Press `Ctrl+O`, `Enter` to save, and `Ctrl+X` to exit.*

5.  **Lock Down File Permissions (Security Best Practice)**:
    Ensure only the root/owner can read this file so other users on the server cannot access your secrets.
    ```bash
    chmod 600 .env
    ```

## 2. Start the Application

1.  **Run Docker Compose**:
    ```bash
    docker-compose up --build -d
    ```

2.  **Verify Status**:
    ```bash
    docker-compose ps
    docker-compose logs -f backend
    ```

## 3. Maintenance

-   **Updating Code**:
    ```bash
    git pull
    docker-compose up --build -d
    ```
-   **Changing Secrets**:
    Just run `nano .env` again, edit the values, and run `docker-compose restart`.
