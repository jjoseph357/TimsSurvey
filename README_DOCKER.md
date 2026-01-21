# Docker Deployment Instructions

This guide explains how to run the TellTims Automator in a Docker container, allowing you to deploy it on any cloud platform (Fly.io, Render, DigitalOcean, etc.) instead of a Raspberry Pi.

## Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on your computer.

## 1. Build the Image
Open a terminal in the project directory and run:

```bash
docker build -t telltims-automator .
```

This will download Python, Chrome, and all dependencies into a self-contained image.

## 2. Run Locally
To test the container on your own machine:

```bash
docker run -p 5001:5001 telltims-automator
```

You can now access the app at `http://localhost:5001`.

## 3. Deploy to the Cloud (Example: Fly.io)
Fly.io is a great option because it has a free tier and supports Docker natively.

1.  **Install flyctl**: [https://fly.io/docs/hands-on/install-flyctl/](https://fly.io/docs/hands-on/install-flyctl/)
2.  **Login**: `fly auth login`
3.  **Launch**:
    ```bash
    fly launch
    ```
    - Follow the prompts.
    - It will generate a `fly.toml` file.
4.  **Deploy**:
    ```bash
    fly deploy
    ```

Your app will be live at `https://your-app-name.fly.dev`.

### Note on Persistent Data
The global counter runs from a text file inside the container. On most cloud platforms, the file system is ephemeral (resets on restart). If you want the counter to persist across deployments, you will need to map a volume.
- **Docker**: `docker run -p 5001:5001 -v $(pwd)/data:/app/data telltims-automator` (You'd need to update `app.py` to save `counter.txt` in `/app/data`).
- **Fly.io**: Use [Fly Volumes](https://fly.io/docs/reference/volumes/).
