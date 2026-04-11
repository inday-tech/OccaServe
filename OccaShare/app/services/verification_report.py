import random
from datetime import datetime, timedelta

class VerificationReportService:
    def generate_accuracy_report(self, days=30):
        """
        Simulates the generation of an accuracy report for the Admin.
        In a real app, this would query the DB for OCR/Liveness success vs. failure rates.
        """
        total_attempts = random.randint(500, 1500)
        successful_ocr = int(total_attempts * random.uniform(0.92, 0.98))
        successful_liveness = int(total_attempts * random.uniform(0.88, 0.95))
        
        return {
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "period_days": days,
            "metrics": {
                "total_attempts": total_attempts,
                "ocr_accuracy": f"{(successful_ocr / total_attempts) * 100:.2f}%",
                "liveness_accuracy": f"{(successful_liveness / total_attempts) * 100:.2f}%",
                "false_positives": random.randint(0, 5),
                "system_status": "Healthy"
            }
        }

verification_report = VerificationReportService()
