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

## 4. Alternative Hosting Options

If Fly.io doesn't meet your needs, here are the best alternatives for running this Docker container 24/7:

### A. Render (Simplest Free/Cheap Option)
- **Free Tier**: Yes (Web Services spin down after 15 mins of inactivity).
- **Paid**: ~$7/month for "always on".
- **Setup**: Connect your GitHub repo, select "Docker" as the environment.
- **Pros**: Extremely easy to use.

### B. Oracle Cloud "Always Free" (Best Free Option)
- **Free Tier**: Generous "Always Free" ARM Ampere instances (4 OCPUs, 24GB RAM).
- **Why**: It's a full Virtual Machine (VPS), not just a container runner.
- **Setup**: 
    1. Create an account (can be tricky to verify).
    2. Create a "VM.Standard.A1.Flex" instance (Ubuntu).
    3. SSH in and run your `deploy_rpi.sh` script (it works on Ubuntu too!).
- **Pros**: Truly free, powerful, always on, persistent storage included.

### C. DigitalOcean / Hetzner (Most Reliable)
- **Cost**: ~$4-6/month.
- **Why**: You get a full Linux server with a public IP.
- **Setup**: Create a "Droplet" (legacy Ubuntu VM), SSH in, and run your deployment script or Docker.
- **Pros**: total control, no "spin down", easy persistent files.

### D. Google Cloud Run
- **Free Tier**: 2 million requests/month free.
- **Why**: Great for containerized apps.
- **Caveat**: "Scale to zero" model meant for web requests, might need configuration to keep "always on" (min instances = 1) which costs money (~$6/mo+).

