# Deploying on Oracle Cloud "Always Free" + Neon

Runs the bot 24/7 for (almost) nothing: the **bot** on a small free Oracle VM, the **database** on Neon.
Oracle changes its free tier from time to time; check the official page before you start:
<https://www.oracle.com/cloud/free/> · limits: <https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm>

> **Read this first — idle reclamation.** Oracle may stop an Always Free VM whose CPU, network
> (and, on ARM shapes, memory) use stays under 20% for 7 days. A task bot is mostly idle, so it
> qualifies. Oracle's documented safeguard is upgrading the account to **Pay As You Go** while
> staying inside the Always Free limits (you are only charged for resources *beyond* them).
> Step 8 covers this. Without it, expect the VM to be stopped some day and the bot to go silent.

## What you need
* A phone number and a credit/debit card (verification; not charged for free resources)
* The bot token from [@BotFather](https://t.me/BotFather) (a separate one from your dev bot)
* An SSH client (Windows 10/11, macOS and Linux have `ssh` built in; VS Code can use it too)

## 1. Neon database (5 min)
1. Sign up at <https://neon.tech> and create a project (any name, Postgres 16 or newer, pick a
   region near the VM).
2. Open **Connect** and copy the connection string. **Turn off "Connection pooling"** so the host
   has no `-pooler` in it. It looks like
   `postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`.
   Paste it as-is later; the bot converts it.

## 2. Oracle account
1. Go to <https://www.oracle.com/cloud/free/> → **Start for free**.
2. Fill in your details, verify email and phone, add the card.
3. Choose the **home region** carefully — it **cannot be changed**, and Always Free resources
   only exist in the home region. Pick one close to you with capacity (for example Frankfurt or
   Dubai). Latency does not matter for a chat bot.
4. Wait for the "account ready" email, then sign in at <https://cloud.oracle.com>.

## 3. Create the VM
Console menu (☰) → **Compute → Instances → Create instance**.

| Field | Value |
|---|---|
| Name | `qul-bot` |
| Image | **Canonical Ubuntu 24.04** (22.04 also fine) |
| Shape | **Change shape → AMD → `VM.Standard.E2.1.Micro`** (marked *Always Free-eligible*) |
| Networking | default VCN/public subnet, **Assign a public IPv4 address** |
| SSH keys | **Generate a key pair** and download the *private* key (or paste your own public key) |
| Boot volume | default (~50 GB) |

Only create resources labelled *Always Free-eligible*. If creation fails with
**"Out of host capacity"**, retry later or pick another availability domain.
The create screen may show a small boot-volume price; after creating, check
**Billing → Cost analysis** that you are charged 0.

Copy the instance's **Public IP** from its page.

## 4. Connect
```bash
chmod 600 ~/Downloads/ssh-key-*.key          # macOS/Linux
ssh -i ~/Downloads/ssh-key-XXXX.key ubuntu@<PUBLIC_IP>
```
The login user on Ubuntu images is `ubuntu`. No inbound ports other than SSH (22) are needed —
the bot only connects out to Telegram and Neon.

## 5. Prepare the server
The VM has only 1 GB RAM; add swap so building the image never runs out of memory.
```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

curl -fsSL https://get.docker.com | sudo sh        # installs Docker + Compose, starts on boot
sudo usermod -aG docker $USER
exit                                               # log in again so the group applies
```
(`ssh` back in, then `docker --version` should work without `sudo`.)

## 6. Get and configure the bot
```bash
git clone -b claude/festive-ride-6ap78d https://github.com/vipgpt1-cell/qul_bot.git
cd qul_bot
cp .env.example .env
nano .env
```
Set at least:
```ini
BOT_TOKEN=<token from BotFather>
DATABASE_URL=<the Neon string from step 1>
ADMIN_USER_IDS=            # fill in after step 7
ALLOWED_CHAT_IDS=          # fill in after step 7
```
(Once the work is merged into `main`, clone `main` instead of the branch above.)

## 7. First start
```bash
docker compose -f docker-compose.neon.yml up -d --build
docker compose -f docker-compose.neon.yml logs -f --tail=50      # Ctrl+C to leave
```
You should see `Starting @your_bot`. Then:
1. Add the bot to your team group (making it a group admin is recommended).
2. In the group send `/chatid`. The bot replies with the **chat id** and **your user id**.
3. Put them into `.env` (`ALLOWED_CHAT_IDS`, `ADMIN_USER_IDS`) and apply:
   ```bash
   nano .env
   docker compose -f docker-compose.neon.yml up -d --force-recreate
   ```
4. In the group: `/help`, then `/addarea mobile`, `/role @someone reviewer`, `/task Test #mobile`.

The container restarts itself after crashes, and Docker starts it again after a VM reboot.

## 8. Protect the free VM (do this)
1. In the console: **Billing & Cost Management → Upgrade to Pay As You Go** (the documented way
   to avoid idle reclamation; free resources stay free).
2. Immediately create a **budget alert**: Billing → **Budgets → Create budget**, amount `$1`,
   alert at 1%, sent to your email — so any accidental charge is noticed at once.
3. Never create resources that are not labelled *Always Free-eligible*.

Not on Pay As You Go? Then watch your email for Oracle's idle warnings and check
**Compute → Instances** regularly; a stopped instance can be started again from the console.

## Updating the bot
```bash
cd ~/qul_bot
git pull
docker compose -f docker-compose.neon.yml up -d --build
```
Database migrations run automatically on start.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `Telegram rejected BOT_TOKEN` in logs | Wrong/old token in `.env`; recreate the container |
| `Conflict: terminated by other getUpdates request` | Another copy uses the same token (your laptop?). Stop it, or use a separate dev bot |
| Bot silent in the group | `/chatid` there; is the id in `ALLOWED_CHAT_IDS`? Check the logs for "Ignoring chat" |
| Nobody is admin | Put your user id (from `/chatid`) in `ADMIN_USER_IDS`, then `--force-recreate` |
| `Cannot reach Telegram` | VM has no outbound internet; check the subnet's route table / security list allows egress |
| DB connection errors | Use the Neon string without `-pooler`; check the project is not paused; the first query after idle can be slow |
| Build killed / out of memory | Confirm swap is on: `free -h` |

Useful: `docker compose -f docker-compose.neon.yml ps`, `... logs --tail=100`, `... restart`.
