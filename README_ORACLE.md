# Oracle Cloud Deployment Guide

This guide details how to host the TellTims Automator on Oracle Cloud's "Always Free" tier. This allows you to run the application 24/7 for free on a powerful virtual server.

## 1. Create an Account
1.  Go to [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/).
2.  Sign up. **Note:** Verify your credit card (they wont charge you) and phone number. This step can be picky; ensure your details match your bank's exactly.
3.  Choose a "Home Region" close to you (e.g., Ashburn, Phoenix, Frankfurt). **Vital:** You cannot change this later, and "Always Free" resources are only available in your home region.

## 2. Create the Instance (VM)
Once logged in to the console:
1.  Click **"Create a VM instance"**.
2.  **Name:** `telltims-server` (or similar).
3.  **Image & Shape:**
    *   Click "Change Image". Choose **Canonical Ubuntu** (latest version, e.g., 22.04 or 24.04).
    *   Click "Change Shape". Select **Ampere** (ARM) -> **VM.Standard.A1.Flex**.
    *   *Tip:* You can max out the specs to 4 OCPUs and 24GB RAM for free, but 1 OCPU and 6GB RAM is plenty for this app.
4.  **Networking:**
    *   "Create new virtual cloud network": Only if you don't have one.
    *   "Assign a public IPv4 address": **Yes**.
5.  **Add SSH Keys:**
    *   Select "Generate a key pair for me" -> **Save Private Key**.
    *   **IMPORTANT:** Keep this `.key` file safe! It is your only way to access the server.
6.  Click **Create**.

## 3. Configure Network (Open Port 5001)
Oracle blocks ports by default in two places: the Cloud VCN and the OS firewall.

### A. Cloud Console (Security List)
1.  On your instance page, click the **Subnet** link (under "Primary VNIC").
2.  Click **Default Security List**.
3.  Click **Add Ingress Rules**.
    *   **Source CIDR:** `0.0.0.0/0` (Allows access from anywhere).
    *   **Destination Port Range:** `5001`.
    *   **Description:** `TellTims Web`.
4.  Click **Add Ingress Rules**.

## 4. Connect & Deploy
1.  Open a terminal (Powershell on Windows, Terminal on Mac/Linux).
2.  Move your downloaded private key to a safe folder (e.g., `~/.ssh/oracle.key`).
3.  Set permissions (needed on Mac/Linux, skip on Windows): `chmod 400 ~/.ssh/oracle.key`.
4.  **SSH into the server:**
    ```bash
    ssh -i path/to/your/key.key ubuntu@YOUR_INSTANCE_IP
    ```

### B. Configure OS Firewall (Inside the server)
Once connected via SSH, run:
```bash
# Allow port 5001 in iptables (Oracle Ubuntu uses iptables by default)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5001 -j ACCEPT
sudo netfilter-persistent save
```
*(If you install `ufw` later, remember to allow 5001 too).*

### C. Install the App
Now, use your existing deployment script!
1.  Clone your repository:
    ```bash
    git clone https://github.com/jjoseph357/TimsSurvey.git
    cd TimsSurvey
    ```
2.  Run the setup script:
    ```bash
    chmod +x deploy_rpi.sh
    ./deploy_rpi.sh
    ```
    *(Note: The script establishes a Virtual Environment and installs dependencies. It was designed for RPi but works perfectly on Ubuntu ARM).*

3.  **Run the App (Background Mode):**
    For 24/7 uptime, use `screen` or `systemd`. The easiest quick way is:
    ```bash
    # Install screen
    sudo apt install screen -y
    
    # Start a new screen session
    screen -S survey
    
    # Run the start script
    ./start_app.sh
    ```
    *   Press `Ctrl+A`, then `D` to detach (app keeps running).
    *   To resume: `screen -r survey`.

## 5. Access
Open your browser and go to: `http://YOUR_INSTANCE_IP:5001`
