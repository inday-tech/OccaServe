import requests
import base64
import hmac
import hashlib
from ..core.config import settings

class PaymongoService:
    def __init__(self):
        self.secret_key = settings.PAYMONGO_SECRET_KEY
        if not self.secret_key:
            print("ERROR: PAYMONGO_SECRET_KEY is not set in .env! Paymongo link generation will fail.")
            self.auth_token = ""
        else:
            # Paymongo uses Basic Auth with the secret key as the username and no password
            auth_bytes = f"{self.secret_key}:".encode("utf-8")
            self.auth_token = base64.b64encode(auth_bytes).decode("utf-8")

        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.auth_token}" if self.auth_token else ""
        }
        self.base_url = "https://api.paymongo.com/v1"

    def create_payment_link(self, amount: float, description: str, remarks: str):
        """
        Creates a payment link. Amount should be in Pesos (converted to cents internally).
        """
        url = f"{self.base_url}/links"
        payload = {
            "data": {
                "attributes": {
                    "amount": int(round(amount * 100)), # Convert to cents
                    "description": description,
                    "remarks": remarks
                }
            }
        }
        response = requests.post(url, json=payload, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            return {
                "id": data["data"]["id"],
                "url": data["data"]["attributes"]["checkout_url"]
            }
        else:
             raise Exception(f"Paymongo Error: {response.status_code} - {response.text}")

    def verify_webhook_signature(self, body: bytes, signature: str, timestamp: str):
        """
        Verifies the signature of a Paymongo webhook.
        """
        webhook_key = settings.PAYMONGO_WEBHOOK_SIG_KEY
        if not webhook_key:
            return True # If not configured, we skip for now (security risk but allowing dev)
            
        signed_payload = f"{timestamp}.{body.decode('utf-8')}"
        expected_signature = hmac.new(
            webhook_key.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

paymongo_service = PaymongoService()
