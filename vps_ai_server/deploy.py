import os
import sys
import time
import socket

try:
    import paramiko
except ImportError:
    print("Error: paramiko is not installed. Please run '.venv\\Scripts\\pip install paramiko' first.")
    sys.exit(1)

# VPS Configuration
IP = "46.250.226.23"
USERNAME = "root"
PASSWORD = "Nwmicrgy"
DOMAIN = "api.occaserve.com"
REMOTE_DIR = "/srv/vps_ai_server"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

def run_command(ssh_client, command, description):
    print(f"\n[Deploy] {description}...")
    print(f"Executing: {command}")
    stdin, stdout, stderr = ssh_client.exec_command(command)
    
    def safe_print(text):
        try:
            print(text)
        except UnicodeEncodeError:
            try:
                encoding = sys.stdout.encoding or 'utf-8'
                print(text.encode(encoding, errors='replace').decode(encoding))
            except Exception:
                print(text.encode('ascii', errors='replace').decode('ascii'))

    # Read output line by line to keep track of progress
    while not stdout.channel.exit_status_ready() or stdout.channel.recv_ready() or stderr.channel.recv_stderr_ready():
        if stdout.channel.recv_ready():
            line = stdout.readline()
            if line:
                safe_print(f"  stdout: {line.strip()}")
        if stderr.channel.recv_stderr_ready():
            line = stderr.readline()
            if line:
                safe_print(f"  stderr: {line.strip()}")
        time.sleep(0.1)
                
    exit_code = stdout.channel.recv_exit_status()
    print(f"Exit Code: {exit_code}")
    return exit_code == 0

def upload_file(sftp, local_path, remote_path):
    print(f"[Deploy] Uploading {os.path.basename(local_path)} -> {remote_path}...")
    sftp.put(local_path, remote_path)

def main():
    print("==================================================")
    print("Starting deployment of OccaServe AI Processing Server")
    print(f"Target VPS: {IP} (username: {USERNAME})")
    print(f"Target Domain: {DOMAIN}")
    print("==================================================")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("[Deploy] Connecting to VPS via SSH...")
        ssh.connect(IP, username=USERNAME, password=PASSWORD, timeout=30)
        print("[Deploy] SSH Connection Successful!")
    except Exception as e:
        print(f"[Deploy ERROR] SSH Connection failed: {e}")
        sys.exit(1)
        
    sftp = ssh.open_sftp()
    
    try:
        # 1. Create remote directories (clean up old ones first)
        ssh.exec_command(f"rm -rf {REMOTE_DIR}*")
        time.sleep(0.5)
        ssh.exec_command(f"mkdir -p {REMOTE_DIR}")
        time.sleep(1)
        
        # 2. Upload application files
        files_to_upload = ["main.py", "requirements.txt", "Dockerfile", "docker-compose.yml"]
        for f in files_to_upload:
            local_path = os.path.join(LOCAL_DIR, f)
            remote_path = f"{REMOTE_DIR}/{f}"
            if os.path.exists(local_path):
                upload_file(sftp, local_path, remote_path)
            else:
                print(f"[Deploy ERROR] Local file missing: {local_path}")
                sys.exit(1)
                
        # 2b. Write .env on VPS with VPS_API_KEY
        vps_api_key = "occaserve_vps_secure_key_a8d3e2f49c1b7e6d" # fallback
        try:
            local_env_path = os.path.join(os.path.dirname(LOCAL_DIR), "OccaShare", ".env")
            if os.path.exists(local_env_path):
                with open(local_env_path, "r") as env_f:
                    for line in env_f:
                        if line.startswith("VPS_API_KEY="):
                            vps_api_key = line.split("=", 1)[1].strip()
                            print(f"[Deploy] Found VPS_API_KEY in local OccaShare/.env: {vps_api_key[:8]}...")
                            break
        except Exception as e:
            print(f"[Deploy WARNING] Could not parse VPS_API_KEY from OccaShare/.env: {e}")

        print("[Deploy] Writing .env file on VPS...")
        sftp_env = sftp.open(f"{REMOTE_DIR}/.env", "w")
        sftp_env.write(f"VPS_API_KEY={vps_api_key}\n")
        sftp_env.close()
                
        # 3. Update server and install system packages
        run_command(ssh, "apt-get update && apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git ufw nginx certbot python3-certbot-nginx", "Installing Nginx, Git, UFW, and Certbot")
        
        # 4. Install Docker & Docker Compose if not installed
        docker_check = run_command(ssh, "which docker", "Checking if Docker is installed")
        if not docker_check:
            print("[Deploy] Docker not found. Installing Docker...")
            # Use docker official install script for simplicity
            run_command(ssh, "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh", "Installing Docker Engine")
            run_command(ssh, "rm get-docker.sh", "Cleaning up docker script")
            
        compose_check = run_command(ssh, "which docker-compose", "Checking if docker-compose is installed")
        if not compose_check:
            print("[Deploy] Docker Compose not found. Installing docker-compose...")
            run_command(ssh, "curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose", "Installing Docker Compose binary")
            
        # Enable and start Docker service
        run_command(ssh, "systemctl enable docker && systemctl start docker", "Enabling and starting Docker service")
        
        # 5. Configure UFW Firewall
        run_command(ssh, "ufw default deny incoming", "Setting UFW default deny incoming")
        run_command(ssh, "ufw default allow outgoing", "Setting UFW default allow outgoing")
        run_command(ssh, "ufw allow 22/tcp", "Allowing SSH (Port 22)")
        run_command(ssh, "ufw allow 80/tcp", "Allowing HTTP (Port 80)")
        run_command(ssh, "ufw allow 443/tcp", "Allowing HTTPS (Port 443)")
        run_command(ssh, "ufw allow 8000/tcp", "Allowing FastAPI (Port 8000)")
        run_command(ssh, "echo 'y' | ufw enable", "Enabling UFW Firewall")
        run_command(ssh, "ufw status verbose", "Checking firewall status")
        
        # 6. Build and start the Docker container
        run_command(ssh, f"cd {REMOTE_DIR} && docker-compose down && docker-compose up -d --build", "Building and launching Docker containers")
        
        # Wait for container startup and health check
        print("[Deploy] Waiting 15 seconds for container services to initialize...")
        time.sleep(15)
        run_command(ssh, "docker ps", "Listing active containers")
        run_command(ssh, "docker logs occaserve-ai-server --tail 50", "Checking container logs for errors")
        
        # 7. Setup Nginx Reverse Proxy
        nginx_config = f"""server {{
    listen 80;
    server_name {DOMAIN};

    location / {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Adjust timeouts for heavy AI models processing
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # Max upload size for multiple selfie frames
        client_max_body_size 50M;
    }}
}}"""
        # Write config temporarily to a file on VPS and move it
        sftp_file = sftp.open("/tmp/nginx_ai_server.conf", "w")
        sftp_file.write(nginx_config)
        sftp_file.close()
        
        run_command(ssh, f"mv /tmp/nginx_ai_server.conf /etc/nginx/sites-available/{DOMAIN}", "Moving Nginx configuration")
        run_command(ssh, f"ln -sf /etc/nginx/sites-available/{DOMAIN} /etc/nginx/sites-enabled/{DOMAIN}", "Enabling Nginx site configuration")
        run_command(ssh, "rm -f /etc/nginx/sites-enabled/default", "Disabling default Nginx site")
        run_command(ssh, "nginx -t", "Testing Nginx configuration")
        run_command(ssh, "systemctl restart nginx", "Restarting Nginx")
        
        # 8. Setup Certbot SSL
        print("\n[Deploy] Attempting Certbot SSL Certificate generation...")
        print("Note: This will succeed only if DNS records are already propagated.")
        
        # Test if DNS resolves to the VPS IP
        dns_ok = False
        try:
            resolved_ip = socket.gethostbyname(DOMAIN)
            if resolved_ip == IP:
                dns_ok = True
                print(f"[Deploy] DNS check passed: {DOMAIN} resolves to {resolved_ip}")
            else:
                print(f"[Deploy WARNING] DNS check mismatched: {DOMAIN} resolves to {resolved_ip}, but VPS IP is {IP}.")
        except socket.gaierror:
            print(f"[Deploy WARNING] DNS check failed: Could not resolve {DOMAIN}. DNS may not be pointed yet.")
            
        if dns_ok:
            ssl_success = run_command(
                ssh, 
                f"certbot --nginx -d {DOMAIN} --non-interactive --agree-tos --register-unsafely-without-email --redirect", 
                "Acquiring SSL certificate with Certbot"
            )
            if ssl_success:
                print(f"[Deploy SUCCESS] HTTPS configured successfully for https://{DOMAIN}")
            else:
                print("[Deploy WARNING] Certbot execution failed. Proceeding with HTTP.")
        else:
            print("[Deploy WARNING] Skipping Certbot SSL configuration because DNS does not resolve to this VPS. You can configure SSL later by running:")
            print(f"  ssh root@{IP} 'certbot --nginx -d {DOMAIN}'")
            
        print("\n==================================================")
        print("DEPLOYMENT COMPLETE!")
        print(f"API is running on: http://{IP}:8000 and http://{DOMAIN}")
        if dns_ok:
            print(f"HTTPS Endpoint: https://{DOMAIN}")
        print("==================================================")
        
    finally:
        sftp.close()
        ssh.close()

if __name__ == "__main__":
    main()
